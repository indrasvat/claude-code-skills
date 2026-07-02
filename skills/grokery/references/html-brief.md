# grokery HTML brief

Two ways to produce the shareable, self-contained, dark-mode brief
(`--html` / "give me an HTML brief" / "export as html"). Both are offline:
inline CSS, no JavaScript, system fonts, print-friendly.

## A. Deterministic (CLI) — `render-html.sh`
Write your synthesized markdown to a file, then convert:
```bash
bash skills/grokery/scripts/render-html.sh ~/Documents/Grokery/<slug>-synthesis.md \
  --title 'grokery — <topic>' --out ~/Documents/Grokery/<slug>-brief.html
```
The script handles headings, bold/italic, links, autolinks (`<https://…>`),
bullets, code, and `---` rules, and wraps them in the styled shell with a badge
and the `✅ All sources reported back.` footer.

## B. Hand-crafted (richer)
For a higher-touch brief (callouts, a verdict hero, simple inline-SVG bars for
engagement), copy [`brief-template.html`](brief-template.html) and fill the
`<!-- CONTENT -->` slot. Keep it self-contained: no external fonts, scripts, or
images. Reuse the template's CSS variables so it stays on-brand.

## Conventions
- **Filename:** `<slug>-brief.html` in the memory dir (default `~/Documents/Grokery/`).
- **Top:** badge → topic `<h1>` → metadata line (window, date, sources that reported).
- **Body:** the synthesis — themes as `<h2>`, citations as inline links, engagement numbers in `<strong>`.
- **Footer:** a one-line colophon naming grokery and "ranked by engagement, not SEO", plus the sources that **actually returned** (e.g. "Sources: X, HN, GitHub, Polymarket"). Never claim a source that failed or was skipped.
- Verify it opens offline (double-click) before declaring done.
