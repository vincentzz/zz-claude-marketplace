#!/usr/bin/env python3
"""Web search / page fetch for sessions where the built-in WebSearch and
WebFetch tools do not exist (typically a non-Anthropic provider).

  web.py search "QUERY" ["QUERY" ...]   # ddgr, best effort
  web.py fetch URL                      # curl, rewritten to JS-free sources

Every result carries CHANNEL / RETRIEVED / SAVED. bash + python3 only; node is
touched only when a page proves to be a JavaScript shell. No API key, ever.

Exit codes: 0 ok · 3 no/ambiguous search backend · 4 RENDER_REQUIRED · 5 fetch failed.
"""
import argparse, html.parser, json, os, re, shutil, subprocess, sys, tempfile, time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

OUT = Path(tempfile.gettempdir()) / "claude-web"
TODAY = datetime.now().strftime("%Y-%m-%d")
MAX_QUERIES = 3       # per invocation — DuckDuckGo throttles bursts
SEARCH_GAP = 2.5      # seconds enforced between consecutive ddgr calls
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

This is AMBIGUOUS and must NOT be reported as "no results found" — it means
either the query genuinely has no hits, or DuckDuckGo throttled this session.
The two mean opposite things to a reader.

Retry once, ~30s later, with different wording. If it repeats, stop searching
and fetch a specific URL instead."""

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
    path.write_text(head + "\n" + body)
    shown = body if len(body) <= PRINT_CAP else (
        body[:PRINT_CAP] + f"\n... [stdout truncated at {PRINT_CAP} chars — full text in SAVED]")
    print("=== WEB RESULT ===\n" + head + "\n" + shown)


def curl(url, timeout=40, ua=None):
    p = subprocess.run(
        ["curl", "-sSL", "--compressed", "--max-time", str(timeout)]
        + (["-A", ua] if ua else [])
        + ["-H", "Accept: text/html,application/json,text/plain,*/*",
           "-w", "\n__HTTP__%{http_code}", url],
        capture_output=True, text=True)
    out, _, code = p.stdout.rpartition("__HTTP__")
    return out.rstrip("\n"), code.strip(), p.stderr.strip()


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
    One cheap probe; if it is there, say so instead of scraping more HTML."""
    p = urlsplit(url)
    if p.path in ("", "/"):
        return ""
    probe = f"{p.scheme}://{p.netloc}/llms.txt"
    body, code, _ = curl(probe, timeout=8)
    if code.startswith("2") and body.strip() and "<html" not in body[:400].lower():
        return (f"NOTE: this site publishes {probe} — a JS-free text index of its docs.\n"
                f"Fetch that instead of scraping further HTML pages here.\n\n")
    return ""


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
    body, code, err = curl(target)
    if code in ("403", "429"):        # a few WAFs block curl's own UA; ask once as a browser
        body, code, err = curl(target, ua=BROWSER_UA)
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
    worst, stamp = 0, OUT / ".last-search"
    for query in queries[:MAX_QUERIES]:
        try:                                  # pace consecutive calls, across invocations too
            time.sleep(max(0.0, SEARCH_GAP - (time.time() - stamp.stat().st_mtime)))
        except OSError:
            pass
        OUT.mkdir(parents=True, exist_ok=True)
        stamp.touch()
        try:
            p = subprocess.run(["ddgr", "--json", "-n", "8", query],
                               capture_output=True, text=True, timeout=60)
            items = json.loads(p.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
            items = None
        if not items:
            emit("ddgr-best-effort", "QUERY", query, "EMPTY-OR-THROTTLED (ambiguous)", THROTTLED)
            worst = 3
            continue
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
