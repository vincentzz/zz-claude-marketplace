#!/usr/bin/env python3
"""Web search / page fetch for sessions where the built-in WebSearch and
WebFetch tools do not exist (typically a non-Anthropic provider).

  web.py search "QUERY" ["QUERY" ...]   # ddgr, best effort
  web.py fetch URL                      # curl, rewritten to JS-free sources

Every result carries CHANNEL / RETRIEVED / SAVED. bash + python3 only; node is
touched only when a page proves to be a JavaScript shell. No API key, ever.

Exit codes: 0 ok · 3 no/ambiguous search backend · 4 RENDER_REQUIRED · 5 fetch failed.
"""
import argparse, fcntl, html.parser, json, os, re, shutil, subprocess, sys, tempfile, time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

def _state_dir():
    """Machine-stable, NOT `tempfile.gettempdir()`.

    The gaps and the strike count are only meaningful if every agent on this
    machine reads and locks the *same* files. `tempfile.gettempdir()` honours
    `$TMPDIR`, which on macOS is a per-user, sometimes per-session sandbox path
    (`/var/folders/<hash>/T/`) — so agents could each land in a private
    directory and the "machine-global" pacing would silently become per-agent,
    which is no pacing at all in exactly the fan-out case it exists for.

    `/tmp` is shared but world-writable, so the directory is per-uid and 0700,
    and we refuse a directory we do not own rather than trusting it."""
    override = os.environ.get("WEB_STATE_DIR")
    if override:
        return Path(override)
    base = Path("/tmp") / f"claude-web-{os.getuid()}"
    try:
        base.mkdir(mode=0o700, parents=True, exist_ok=True)
        if base.stat().st_uid != os.getuid():        # someone else got there first
            raise PermissionError(f"{base} is not owned by uid {os.getuid()}")
    except OSError:
        return Path(tempfile.gettempdir()) / "claude-web"   # degraded: pacing is local
    return base


OUT = _state_dir()
TODAY = datetime.now().strftime("%Y-%m-%d")
MAX_QUERIES = 3       # per invocation — DuckDuckGo throttles bursts
# Pacing is tuned for unattended availability, not for throughput: an agent that
# gets itself throttled at 03:00 has failed, whereas one that took 20s longer has
# not. Every gap below is machine-global (see `paced`) and env-overridable.
SEARCH_GAP = float(os.environ.get("WEB_SEARCH_GAP", 20))    # s between any two ddgr calls
FETCH_GAP = float(os.environ.get("WEB_FETCH_GAP", 1.5))     # s between two hits on one host
BACKOFF_MAX = 600     # ceiling on the escalating gap after suspected throttling
RETRY_WAIT_MAX = 120  # obey Retry-After up to here; past it, report instead of sleeping
# A caller runs this script from a Bash tool whose default timeout is 120s. Being
# killed at that ceiling returns *no output at all* — no channel, no backoff line,
# nothing — which inverts this plugin's whole contract exactly when it matters. So
# the invocation budgets its own time and reports what it did not do, rather than
# sleeping into a silent kill. Same principle the 429 branch already follows.
BUDGET = float(os.environ.get("WEB_TIME_BUDGET", 100))
DDGR_TIMEOUT = 45     # ddgr's own ceiling, reserved out of the budget before waiting
# A block that expired hours ago must not tax an unrelated run tomorrow: strikes
# older than this are treated as spent. The one real block measured here outlasted
# 7 minutes, so 30 leaves margin without keeping a dead penalty alive.
STRIKE_TTL = float(os.environ.get("WEB_STRIKE_TTL", 1800))
STARTED = time.time()
PRINT_CAP = 20000     # chars echoed to stdout; the SAVED file always has it all
SHELL_MIN = 600       # less extracted text than this ⇒ *maybe* a JS shell
JS_MARK = re.compile(r"enable JavaScript|requires JavaScript|JavaScript is (?:required|disabled)", re.I)
# Identify honestly by default: bot managers fingerprint TLS and header order, so a
# spoofed Chrome UA reads as a *mismatch* and gets 403'd where plain curl passes
# (measured on Cloudflare-fronted hosts). Only retry as a browser when blocked.
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

NO_BACKEND = """No search backend is available in this session: the built-in WebSearch tool is
absent (non-Anthropic provider) and `ddgr` is not on PATH.

Do NOT answer from memory and do NOT scrape a search engine by hand. Two paths
still work right now:
  (a) Fetch a specific URL — needs no setup at all. Ask the user for the URL, then:
        python3 {me} fetch https://example.com/page
  (b) Restore search:  brew install ddgr
      (Linux: pipx install ddgr, or apt/dnf install ddgr)"""

THROTTLED = """ddgr returned nothing parseable.

Never report this as "no results found" — that claims the web was searched and
came up empty, which is the opposite of what may have happened. Say the search
did not complete.

DuckDuckGo's soft block looks like `HTTP Error 202: Accepted` with an empty
result array; when that line appears under UPSTREAM below, it is a throttle,
not an empty index. With no UPSTREAM line the two remain indistinguishable.

Do not retry in a loop — the backoff below is enforced whether you wait or not.
If it repeats, stop searching and fetch specific URLs instead."""

BACKOFF = """No search was sent. An earlier search was throttled, and {owed:.0f}s of that
backoff is still owed — longer than this invocation will block, because being
killed at a tool timeout would return you nothing at all.

Nothing was retrieved and nothing is known about {n} quer(y/ies) you asked for.
Do not report an answer as if the search had run.

What to do instead, in order of preference:
  1. Fetch specific URLs — fetch has its own, much shorter pacing and is
     unaffected by a search backoff:
         python3 {me} fetch <url>
  2. Ask the user for a source, or answer from what you already retrieved.
  3. Only if searching is genuinely required, wait {owed:.0f}s and re-run. The
     wait is enforced either way, so an immediate retry only wastes a turn."""

RENDER_REQ = """This page is a JavaScript shell: curl retrieved markup but no usable text, and
no headless browser was available to render it.

NOTHING about this page's content has been retrieved. Do not fill it in from
memory, from the URL, or from the page title.

To render it (first run downloads a ~150MB browser):
    npm i -g playwright && npx playwright install chromium
then re-run:
    python3 {me} fetch {url}

Otherwise ask the user for a JS-free equivalent — a raw file, an API endpoint,
a documentation mirror, or an RSS feed."""

# JS-free equivalents, tried in order. Prefer these over scraping HTML.
REWRITES = [
    (r"^https?://github\.com/([^/]+)/([^/]+)/blob/(.+)$",
     r"https://raw.githubusercontent.com/\1/\2/\3"),
    (r"^https?://github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)/?$",
     r"https://api.github.com/repos/\1/\2/issues/\3"),
    (r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
     r"https://raw.githubusercontent.com/\1/\2/HEAD/README.md"),
    (r"^https?://(?:www\.)?npmjs\.com/package/(@?[^/?#]+(?:/[^/?#]+)?)/?$",
     r"https://registry.npmjs.org/\1/latest"),
    (r"^https?://pypi\.org/project/([^/?#]+)/?$", r"https://pypi.org/pypi/\1/json"),
    (r"^https?://crates\.io/crates/([^/?#]+)/?$", r"https://crates.io/api/v1/crates/\1"),
]

RENDER_JS = """const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto(process.argv[2], { waitUntil: 'networkidle', timeout: 45000 });
  process.stdout.write(await p.evaluate(() => document.body.innerText));
  await b.close();
})().catch(e => { console.error(e.message); process.exit(1); });
"""

ME = __file__
_render_err = ""


def emit(channel, key, subject, status, body, resolved=None):
    """Write the result to a file under a temp path and echo it. One contract
    for every tier, so a reader can always tell how the evidence was obtained."""
    OUT.mkdir(parents=True, exist_ok=True)
    slug = (re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")[:60] or "result")
    path = OUT / f"{TODAY}-{channel}-{slug}.txt"
    head = [f"CHANNEL: {channel}", f"{key}: {subject}"]
    if resolved and resolved != subject:
        head.append(f"RESOLVED: {resolved}")
    head += [f"RETRIEVED: {TODAY}", f"STATUS: {status}", f"SAVED: {path}", "---"]
    head = "\n".join(head)
    tmp = path.with_suffix(f".{os.getpid()}.part")   # atomic: a concurrent agent
    tmp.write_text(head + "\n" + body)               # reading SAVED never sees a
    os.replace(tmp, path)                            # half-written result file
    shown = body if len(body) <= PRINT_CAP else (
        body[:PRINT_CAP] + f"\n... [stdout truncated at {PRINT_CAP} chars — full text in SAVED]")
    print("=== WEB RESULT ===\n" + head + "\n" + shown)


def left():
    """Seconds of this invocation's self-imposed budget still unspent."""
    return BUDGET - (time.time() - STARTED)


def locked(name, deadline=None):
    """Open `name` under an exclusive flock. Every reader and writer of a shared
    state file goes through here, so read-modify-write is atomic between
    processes. flock is released by the kernel when the fd closes or the process
    dies, so a killed agent cannot strand the lock. (Local FS only — $TMPDIR is,
    but flock over NFS/SMB is not dependable.)

    With a deadline the wait is bounded and returns None instead of blocking:
    a blocking LOCK_EX behind another agent's 600s hold is a silent kill."""
    OUT.mkdir(parents=True, exist_ok=True)
    fd = os.open(OUT / re.sub(r"[^A-Za-z0-9._-]+", "_", name), os.O_CREAT | os.O_RDWR, 0o644)
    if deadline is None:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            if time.time() >= deadline:
                os.close(fd)
                return None
            time.sleep(0.25)


def paced(key, gap, budget=None):
    """Space out requests of one kind across every process on this machine.

    The lock is held *across* the sleep, so N agents starting at the same instant
    queue up one gap apart instead of all reading a stale timestamp and firing
    together — the failure mode that matters when a profile fans out parallel
    scouts. Waiting is the cheap outcome here; being throttled is the expensive one.

    `gap` may be a callable, evaluated *under* the lock: a process that queued
    behind a 300s wait must honour the backoff as it stands when its turn comes,
    not the shorter one it computed before joining the queue.

    Returns 0.0 when the caller may proceed, or the seconds still owed when
    honouring the gap would outlast `budget`. Owed time is for *reporting*, not
    for sleeping — the caller must emit and stop. Nothing is stamped in that
    case, so giving up costs the next caller nothing."""
    budget = left() if budget is None else budget
    deadline = time.time() + budget
    fd = locked(f".pace-{key}", deadline)
    if fd is None:                          # another agent holds it past our budget
        return max(1.0, gap() if callable(gap) else gap)
    try:
        st = os.fstat(fd)
        if st.st_size:                      # size 0 ⇒ first ever call, no wait owed
            owed = (gap() if callable(gap) else gap) - (time.time() - st.st_mtime)
            if owed > deadline - time.time():
                return owed
            if owed > 0:
                time.sleep(owed)
        os.pwrite(fd, b"x", 0)              # stamp = when this request goes out
        return 0.0
    finally:
        os.close(fd)                        # releases the lock


def strikes(delta=None):
    """Consecutive suspected-throttle events, persisted so a fresh invocation
    does not reset the backoff and walk straight back into the wall.

    Read-modify-write happens under the lock and writes go through pwrite on the
    locked fd — an unlocked `read_text`/`write_text` pair loses concurrent
    increments and lets a reader catch the file mid-truncate, and both errors
    shorten the backoff rather than lengthen it.

    Lock order is always pace → strikes (never the reverse), so no deadlock."""
    fd = locked(".ddgr-strikes")
    try:
        st = os.fstat(fd)
        try:
            n = int(os.pread(fd, 32, 0).decode().strip() or 0)
        except ValueError:
            n = 0
        # Decay by the file's own mtime. A pure read never rewrites it, so the
        # clock keeps running instead of being refreshed by whoever looks.
        if st.st_size and time.time() - st.st_mtime > STRIKE_TTL:
            n = 0
        if delta is not None:
            n = 0 if delta == 0 else n + delta
            os.ftruncate(fd, 0)
            os.pwrite(fd, str(n).encode(), 0)
        return n
    finally:
        os.close(fd)


def curl(url, timeout=40, ua=None):
    p = subprocess.run(
        ["curl", "-sSL", "--compressed", "--max-time", str(timeout)]
        + (["-A", ua] if ua else [])
        + ["-H", "Accept: text/html,application/json,text/plain,*/*",
           "-w", "\n__HTTP__%{http_code}__HDR__%{header_json}", url],
        capture_output=True, text=True)
    out, _, tail = p.stdout.rpartition("__HTTP__")
    code, _, hdr = tail.partition("__HDR__")
    return out.rstrip("\n"), code.strip(), p.stderr.strip(), hdr


def retry_after(hdr):
    """Seconds the server asked us to wait, or None. Older curl has no
    %{header_json}; then we simply do not know, and the caller uses its default."""
    try:
        v = json.loads(hdr).get("retry-after", [None])[0]
        return float(v) if v and v.strip().isdigit() else None
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return None


class Stripper(html.parser.HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "template"}
    BREAK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "section", "article", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.buf, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BREAK:
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)

    def text(self):
        t = re.sub(r"[ \t\r\f\v]+", " ", "".join(self.buf))
        return re.sub(r"\n[ \n]*\n[ \n]*", "\n\n", t).strip()


def extract(markup):
    s = Stripper()
    try:
        s.feed(markup)
    except Exception:
        pass
    return s.text()


def is_shell(markup, text):
    """A short page is not automatically a JS shell — example.com is 200 chars
    of complete content. Require a script tag and a markup:text ratio that only
    an unrendered app produces, so real short pages are not thrown away."""
    return bool(JS_MARK.search(markup)) or (
        len(text) < SHELL_MIN and "<script" in markup.lower() and len(text) * 12 < len(markup))


def llms_hint(url):
    """Documentation sites increasingly publish /llms.txt — a clean text index.
    Probed once per host and cached: an un-cached probe would double this
    plugin's request rate against the very host we are already reading."""
    p = urlsplit(url)
    if p.path in ("", "/"):
        return ""
    probe = f"{p.scheme}://{p.netloc}/llms.txt"
    note = (f"NOTE: this site publishes {probe} — a JS-free text index of its docs.\n"
            f"Fetch that instead of scraping further HTML pages here.\n\n")
    cache = OUT / f".llms-{re.sub(r'[^A-Za-z0-9._-]+', '_', p.netloc)}"
    try:
        return note if cache.read_text() == "1" else ""
    except OSError:
        pass
    if paced(p.netloc, FETCH_GAP, budget=min(15.0, left() - 20)):
        return ""                     # a nicety, never worth spending the budget on
    body, code, _, _ = curl(probe, timeout=8)
    ok = code.startswith("2") and bool(body.strip()) and "<html" not in body[:400].lower()
    cache.write_text("1" if ok else "0")
    return note if ok else ""


def render(url):
    """Tier 4, on detection only. Returns rendered text, or None to escalate to
    RENDER_REQUIRED. Never downloads anything on its own."""
    global _render_err
    if os.environ.get("WEB_NO_RENDER") or not shutil.which("node"):
        _render_err = "node/playwright not available (or WEB_NO_RENDER set)"
        return None
    roots = [Path.cwd() / "node_modules"]
    if shutil.which("npm"):
        g = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True)
        if g.returncode == 0:
            roots.append(Path(g.stdout.strip()))
    root = next((r for r in roots if (r / "playwright").is_dir()), None)
    if root is None:
        _render_err = "the playwright module is not installed locally or globally"
        return None
    OUT.mkdir(parents=True, exist_ok=True)
    js = OUT / "render.js"
    js.write_text(RENDER_JS)
    p = subprocess.run(["node", str(js), url], capture_output=True, text=True,
                       env={**os.environ, "NODE_PATH": str(root)})
    if p.returncode != 0 or not p.stdout.strip():
        _render_err = p.stderr.strip()[:400] or "playwright produced no text"
        return None
    return p.stdout


def fetch(url):
    target, channel = url, "curl"
    for pat, rep in REWRITES:
        if re.match(pat, url):
            target, channel = re.sub(pat, rep, url), "raw-api"
            break
    host = urlsplit(target).netloc
    owed = paced(host, FETCH_GAP, budget=left() - 45)   # 45s reserved for the fetch itself
    if owed:
        emit("BACKOFF", "URL", url, f"not sent — {host} is busy with other agents",
             f"Could not get a turn on {host} within this invocation's budget.\n"
             f"Nothing was retrieved. Retry in ~{owed:.0f}s, or fetch a different host.", target)
        return 5
    body, code, err, hdr = curl(target)
    if code == "403":                 # a UA block, not a rate limit: ask again as a browser
        paced(host, FETCH_GAP, budget=left() - 45)
        body, code, err, hdr = curl(target, ua=BROWSER_UA)
    if code == "429":                 # an explicit "slow down" — the one signal never to ignore
        wait = retry_after(hdr)
        # Bounded by what is left of the budget, not just by RETRY_WAIT_MAX: sleeping
        # into a tool timeout would discard this report along with everything else.
        room = min(RETRY_WAIT_MAX, left() - 45)
        if wait is not None and wait > room:
            emit(channel, "URL", url, f"HTTP 429 — rate limited, Retry-After {wait:.0f}s",
                 f"{host} asked for a {wait:.0f}s pause, longer than this invocation will block.\n"
                 f"Nothing was retrieved. Wait it out before touching {host} again;\n"
                 f"do not retry in a loop, and do not report this as 'page not found'.", target)
            return 5
        if room <= 0:
            emit(channel, "URL", url, "HTTP 429 — rate limited, no budget left to wait",
                 f"{host} is rate limiting and this invocation has no time left to honour it.\n"
                 f"Nothing was retrieved. Re-run in a minute; do not retry in a loop.", target)
            return 5
        time.sleep(wait if wait is not None else min(60.0, room))
        paced(host, FETCH_GAP, budget=left() - 45)
        body, code, err, hdr = curl(target)
    if code and not code.startswith("2"):
        emit(channel, "URL", url, f"HTTP {code} — fetch failed", f"{err}\n{body[:2000]}", target)
        return 5
    if not body.strip():
        emit(channel, "URL", url, "EMPTY RESPONSE — nothing retrieved", err or "curl returned no bytes", target)
        return 5
    if body.lstrip()[:1] in "{[":
        try:
            body = json.dumps(json.loads(body), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        emit(channel, "URL", url, "OK (JSON)", body, target)
        return 0
    if "<html" in body[:4000].lower() or body[:200].lower().startswith("<!doctype html"):
        text = extract(body)
        if is_shell(body, text):
            page = render(target)
            if page is None:
                emit("RENDER_REQUIRED", "URL", url, f"JS shell — {_render_err}",
                     RENDER_REQ.format(me=ME, url=target), target)
                return 4
            emit("rendered", "URL", url, f"OK (headless browser, {len(page)} chars)", page, target)
            return 0
        emit(channel, "URL", url, f"OK (HTML → text, {len(text)} chars)",
             llms_hint(target) + text, target)
        return 0
    emit(channel, "URL", url, f"OK (plain text, {len(body)} chars)", body, target)
    return 0


def search(queries):
    if not shutil.which("ddgr"):
        emit("NO-BACKEND", "QUERY", queries[0], "no search backend installed",
             NO_BACKEND.format(me=ME))
        return 3
    if len(queries) > MAX_QUERIES:
        print(f"[capped at {MAX_QUERIES} queries per invocation; dropped: "
              f"{', '.join(queries[MAX_QUERIES:])}]", file=sys.stderr)
    worst = 0
    for query in queries[:MAX_QUERIES]:
        # Escalate the gap after each suspected throttle, and keep escalating
        # across invocations — a backoff that resets per process is no backoff.
        # Deliberately a lambda: the strike count is read when our turn actually
        # comes, so a throttle recorded while we queued still lengthens our wait.
        # Reserve room for the search itself — capped at DDGR_TIMEOUT, but never
        # more than half of what is left, so a small WEB_TIME_BUDGET degrades into
        # a short wait rather than into "always report, never search".
        owed = paced("ddgr", lambda: min(SEARCH_GAP * 4 ** strikes(), BACKOFF_MAX),
                     budget=left() - min(DDGR_TIMEOUT, left() / 2))
        if owed:
            emit("BACKOFF", "QUERY", query, f"not sent — {owed:.0f}s of backoff still owed",
                 BACKOFF.format(owed=owed, me=ME, n=len(queries[:MAX_QUERIES])))
            return 3
        p, items = None, None
        wait = max(5.0, min(DDGR_TIMEOUT, left()))
        try:
            p = subprocess.run(["ddgr", "--json", "-n", "8", query],
                               capture_output=True, text=True, timeout=wait)
            items = json.loads(p.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
            pass
        if not items:
            # ddgr exits 0 and prints [] when DuckDuckGo soft-blocks, but says so
            # on stderr. That line is the only thing that tells a throttle apart
            # from a genuinely empty index — surface it instead of dropping it.
            note = (p.stderr or "").strip() if p else f"ddgr did not return within {wait:.0f}s"
            hard = bool(re.search(r"HTTP Error|\b(202|403|429)\b|too many", note, re.I)) or not p
            nxt = min(SEARCH_GAP * 4 ** strikes(1), BACKOFF_MAX)
            emit("ddgr-best-effort", "QUERY", query,
                 "THROTTLED (upstream said so)" if hard else "EMPTY-OR-THROTTLED (ambiguous)",
                 THROTTLED + (f"\n\nUPSTREAM: {note}" if note else "")
                 + f"\n\nBackoff: the next search cannot go out for {nxt:.0f}s (strike {strikes()}).")
            worst = 3
            continue
        strikes(0)
        emit("ddgr-best-effort", "QUERY", query, f"OK ({len(items)} results)",
             "\n".join(f"{n}. {i.get('title', '')}\n   {i.get('url', '')}\n   {i.get('abstract', '')}"
                       for n, i in enumerate(items, 1)))
    return worst


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("search", help="best-effort web search via ddgr").add_argument("query", nargs="+")
    sub.add_parser("fetch", help="fetch one URL via curl").add_argument("url")
    a = ap.parse_args()
    sys.exit(search(a.query) if a.cmd == "search" else fetch(a.url))
