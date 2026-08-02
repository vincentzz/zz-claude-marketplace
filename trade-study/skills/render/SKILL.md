---
name: render
description: Derive the three deliverables (synthesis.html, synthesis.pdf, deck.pptx) from synthesis.md — single source, three renders, one shared design system. Use when analyst closes a study, or when the user asks to re-render after a synthesis edit.
---

# Render · single source, three derived deliverables

`synthesis.md` is the only source of truth. The HTML, the PDF, and the PPTX are all derived from it in one pass; none is ever edited directly — a content fix goes into synthesis.md and everything re-renders. All three land in `studies/<id>/out/`.

## Step 0 · Check the toolchain before promising anything

```bash
python3 -c "import pptx" 2>/dev/null && echo pptx-ok
[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] && echo chrome-ok
command -v chromium >/dev/null && echo chromium-ok
python3 -c "import weasyprint" 2>/dev/null && echo weasyprint-ok
command -v soffice >/dev/null && echo soffice-ok
```

- **HTML** needs nothing — it always renders.
- **PDF** uses the first available of: Chrome/Chromium headless (`--headless=new --print-to-pdf=<abs path> <abs html path>`), then weasyprint, then `soffice --convert-to pdf`.
- **PPTX** needs python-pptx (`pip install python-pptx`).

If a renderer is missing, produce what renders, and tell the user exactly which package unlocks the rest — never emit a placeholder file or claim a deliverable that does not open.

## Design system (shared by all three; deliverables are designed, not default-themed)

- **Palette**: ink `#1F2430` (text, dark surfaces) · paper `#FAF7F2` (background) · accent `#C4552D` (recommendation, section markers) · muted `#8A8578` (captions, sources). Ratings: `++` `#2E6E4E` · `+` `#7FA88F` · `0` `#B8B2A6` · `-` `#D99A4E` · `--` `#B3423A` · veto `#B3423A` on `#F7E6E4`. Never encode a rating by color alone — the glyph (`++`…`--`) always appears.
- **Type**: headings in a geometric sans (Avenir Next → Helvetica Neue → system sans), body in a readable serif (Iowan Old Style → Georgia). CJK output: PingFang SC / Noto Sans CJK for both roles. Generous whitespace; a thin accent rule under section headings; no clip art, no gradients, no stock imagery.
- **The recommendation is the visual protagonist**: one accent-colored callout block near the top of every deliverable; everything else is quiet paper-and-ink.

## HTML (`out/synthesis.html`)

Hand-authored, fully self-contained (inline CSS, no external requests), print-aware. Structure mirrors synthesis.md: recommendation callout → veto table → matrix → per-criterion details → sensitivity → sources. The matrix renders as a real `<table>` with rating chips (colored pill + glyph); vetoed candidates get a struck header and a veto banner in their column. Body max-width ~46rem; `@media print` sets page margins and avoids breaking the matrix across pages.

## PDF (`out/synthesis.pdf`)

Print the HTML — one source of styling, two paginated forms. Verify it opens and is non-trivial: `pdftotext` if available, otherwise check the file is >10KB and starts with `%PDF`.

## PPTX (`out/deck.pptx`)

A **decision brief**, not a document dump — someone should be able to present the decision from it in five minutes. Write a one-off python-pptx script for this study (keep it at `out/make_deck.py` so a re-render is reproducible), 16:9, slides:

1. **Title** — the brief's question, study id, date, one-line recommendation in accent.
2. **Recommendation** — the winner, the single strongest reason, the runner-up condition, the sensitivity caveat verbatim from synthesis.md.
3. **Matrix** — the criteria×candidates table with weights, colored rating cells (glyph always present), weighted totals row, veto marks.
4. **One slide per candidate** — verdict line, top 2–3 strengths and weaknesses as evidence-backed bullets (≤ 12 words each), hard-constraint flags.
5. **Method** — criteria and weights (and who set them: the user), depth posture, source count per candidate, evidence file paths.

Text on slides is distilled from synthesis.md, never pasted paragraphs; anything that needs a paragraph belongs to the PDF, and the deck's job is to make the reader open it.

## Step last · verify

Open-check each artifact (HTML parses, PDF magic bytes, `python3 -c "from pptx import Presentation; Presentation('out/deck.pptx')"`), then report the three paths and any renderer that was skipped and why.
