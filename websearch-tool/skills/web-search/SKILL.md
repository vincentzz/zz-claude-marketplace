---
name: web-search
description: Search the web or fetch a web page when the built-in WebSearch / WebFetch tools are unavailable, missing from the tool list, or returning errors — the normal case when the session runs against a non-Anthropic endpoint such as a local Ollama model (`ollama launch claude`) or an OpenAI-compatible proxy. Also use when a fetched page comes back as an empty JavaScript shell, or when you need something you cannot answer from training data: the current contents of a URL, a GitHub file or issue, the latest npm/PyPI/crates version, recent docs or release notes. Provides curl fetch (works with zero setup) plus best-effort ddgr search.
---

# web-search · web access without the built-in tools

You have a script. Run it with Bash. It always prints the result to stdout **and** saves it to a file, and it always tags how the content was obtained.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/web-search/scripts/web.py" fetch  "<URL>"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/web-search/scripts/web.py" search "<QUERY>"
```

Saved files land in `$TMPDIR/claude-web/` (on Linux, `/tmp/claude-web/`), named `<date>-<channel>-<slug>.txt`. The exact path is printed on the `SAVED:` line of every result — quote that path when you hand results to another agent or cite them later.

## Which tier to use

1. **Built-in first.** If `WebSearch` / `WebFetch` are in your tool list and working, use them — this skill does not replace or disable them. Tag anything you got that way `CHANNEL: builtin`. Only fall through to the script when they are absent or erroring.
2. **`fetch`** — plain curl. No API key, no daemon, always available. Use it whenever you have a specific URL.
3. **`search`** — needs `ddgr` on PATH. Best effort; may be empty or throttled.
4. **Render** — the script escalates to a headless browser *by itself*, only when a page turns out to be a JavaScript shell. You never invoke it directly.

## Worked example

```
$ python3 "${CLAUDE_PLUGIN_ROOT}/skills/web-search/scripts/web.py" fetch "https://github.com/psf/requests"
=== WEB RESULT ===
CHANNEL: raw-api
URL: https://github.com/psf/requests
RESOLVED: https://raw.githubusercontent.com/psf/requests/HEAD/README.md
RETRIEVED: 2026-08-04
STATUS: OK (plain text, 4312 chars)
SAVED: /tmp/claude-web/2026-08-04-raw-api-https-github-com-psf-requests.txt
---
# Requests
...
```

`RESOLVED:` appeared because the script rewrote the URL to a JS-free source. It does this automatically for github.com (`/blob/` → raw, `/issues/N` and `/pull/N` → the GitHub API, a bare repo → its README), npmjs.com → `registry.npmjs.org`, pypi.org → the PyPI JSON API, and crates.io → its API. Just pass the ordinary human URL; do not hand-build the raw URL yourself.

Search looks the same, with `QUERY:` instead of `URL:` and numbered `title / url / abstract` triples. Pass up to 3 queries in one call (`search "a" "b"`); the script paces them to stay under DuckDuckGo's tolerance.

## Reading the CHANNEL tag

Every result carries one. It tells the reader whether the evidence is mechanically reproducible or best-effort scraping to be discounted — downstream profiles in this marketplace require a source **and** a retrieval date on every factual claim, so carry `CHANNEL` + `RETRIEVED` + the URL through into whatever you write.

| CHANNEL | Means |
|---|---|
| `builtin` | Anthropic's own WebSearch/WebFetch. Most trustworthy. |
| `raw-api` | A registry or raw-file API. Mechanically reproducible; treat as fact. |
| `curl` | HTML fetched and stripped to text. Reliable content, lossy formatting. |
| `rendered` | Headless browser. Correct, but slow and version-sensitive. |
| `ddgr-best-effort` | Scraped search results. Titles and abstracts are **hints**, not evidence — fetch the URL before citing anything. |
| `RENDER_REQUIRED` | **Nothing was retrieved.** See below. |
| `NO-BACKEND` | **No search happened.** See below. |

## When it fails, say so

The two failure tags are not soft failures. The content does not exist in your context, and you must not supply it from memory, from the URL, or from a page title.

- **`RENDER_REQUIRED`** (exit 4) — the page is a JS shell and no headless browser was available. Report the URL as unretrieved. Offer the user the fix the script prints (`npm i -g playwright && npx playwright install chromium`; the first run downloads a ~150MB browser), or ask them for a JS-free equivalent.
- **`NO-BACKEND`** (exit 3) — `ddgr` is not installed, so no search is possible. Do not scrape Google or any other engine by hand. Tell the user plainly, and offer both working paths: they can give you a specific **URL** (fetch needs no setup at all), or install search with `brew install ddgr` (Linux: `pipx install ddgr`).
- **`THROTTLED`** / **`EMPTY-OR-THROTTLED`** (exit 3) — ddgr returned nothing parseable. Never report either as "no results found": that asserts the web was searched and is empty, which may be the opposite of what happened. Say the search did not complete. `THROTTLED` means DuckDuckGo said so itself (its soft block is `HTTP Error 202: Accepted`, quoted back to you on the `UPSTREAM:` line); plain `EMPTY-OR-THROTTLED` means the two causes are genuinely indistinguishable. Either way, stop searching and fetch specific URLs instead — retrying in a loop only deepens the backoff.

## Pacing — it will make you wait, on purpose

This plugin is tuned so an unattended run never gets itself blocked, not so it finishes fast. Searches are spaced ~20s apart and requests to one host ~1.5s apart; the gaps are enforced by a lock shared across **every** agent on the machine, so a profile that fans out parallel scouts gets them queued rather than fired in a burst. After a suspected throttle the search gap escalates ×4 per strike (20s → 80s → 320s, capped at 600s) and persists across invocations — a fresh process does not reset it.

So: a `search` call may simply sit there for a while. That is the script working. Do not "work around" it by launching more processes, and do not treat the wait as a hang. If you need it faster for a one-off interactive task, `WEB_SEARCH_GAP` and `WEB_FETCH_GAP` (seconds) override the defaults — but leave them alone for unattended work.

## Boundaries

Read-only: fetches URLs and writes only under the temp directory. No API key is required anywhere. Search is DuckDuckGo via `ddgr` only — never scrape a search engine directly, and never fall back to Google.
