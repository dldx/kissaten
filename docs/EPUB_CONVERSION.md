# EPUB Conversion for OpenWiki Reports

Convert an OpenWiki deep-dive report (e.g. `openwiki/production/deep-dive.md`)
into a styled EPUB 3 e-book with a clickable endnote bibliography.

## Quick start

```bash
uv run --with ebooklib --with markdown python scripts/md_to_epub.py \
    openwiki/production/deep-dive.md \
    openwiki/production/deep-dive.epub
```

No system dependencies (pandoc, Calibre, etc.) are required — `uv` pulls in
`markdown` and `ebooklib` on the fly and the EPUB itself is assembled with
Python's stdlib plus those two packages. If [bun](https://bun.sh) is
available, the FOB Sankey diagrams are rendered with d3 (see "Diagrams"
below); without it the converter automatically falls back to its built-in
pure-Python SVG generator.

```
scripts/md_to_epub.py <input.md> <output.epub>
```

## What the converter does

1. **Single-pass markdown render** — the whole document is converted once with
   python-markdown (`tables` + `footnotes` extensions) so footnote references
   and definitions are linked before any splitting happens.
2. **Chapter split** — the rendered HTML is split into chapters at `<h2>`
   boundaries; the `<h1>` becomes the book title page. A chapter containing
   `<h3>` sub-sections (the origin deep dives) is further split at `<h3>`
   boundaries so each origin gets its own page and TOC entry, nested under
   the h2 overview in the navigation document. A final "Works Cited &
   Sources" chapter holds the full bibliography.
3. **Footnote restructuring** — see below.
4. **Diagrams** — see "Diagrams" below.
5. **Callout boxes** — the report's blockquote callouts (those opening with a
   bold lead-in, e.g. "**Data note:**", "**Why wet hulling?**") get an
   `infobox` panel class: shaded, coffee-toned border, kept on one page.
   Plain blockquotes keep the default quote styling.
6. **Keep-together pass** — every table is wrapped in an avoid-break block so
   reading systems that paginate keep each table on a single page (see
   "Tables stay on one page" below).
7. **EPUB 3 packaging** — `ebooklib` assembles the container, OPF package,
   nav TOC (EPUB 3) and NCX (EPUB 2 fallback), and a coffee-toned stylesheet
   (styled tables, blockquotes, serif body).

## Footnote handling

OpenWiki reports cite sources with `[^N]` markers and a numbered definition
list at the end. These do **not** map directly to a good reading experience:

- The `[^N]` IDs are arbitrary — non-sequential within any chapter and with
  gaps (`[^21]` is never defined in `deep-dive.md`).
- python-markdown renders definitions as a single `<ol>` at the end of the
  document, so numbers live in list markers and disappear when notes are
  moved per-chapter.

The converter therefore rebuilds citations from scratch as a clickable
endnote bibliography — all notes live in the final "Works Cited & Sources"
chapter, not at the bottom of each chapter, so the body text is never
interrupted:

| Element | Markup |
| :---- | :---- |
| In-text reference | `<a epub:type="noteref" role="doc-noteref" aria-label="Footnote N" href="chNN.xhtml#fn-N" id="ref-N-k"><sup>N</sup></a>` — links across files to the bibliography entry |
| Bibliography entry | `<li id="fn-N">` in the "Works Cited & Sources" chapter, carrying a bold `N.` prefix that links back to the citing chapter's **first** reference of the note |
| Bibliography | `<ol class="bibliography">` (CSS suppresses the list markers; the backlink prefix *is* the number), ordered to match the renumbered citations |

Key properties (all verified by the checks below):

- **Sequential renumbering.** Citations are renumbered 1..M in order of first
  appearance across the whole book. Superscript N always equals bibliography
  entry N; repeated citations keep their number (academic-book style).
- **Consecutive citations grouped with commas.** Adjacent citations
  (`[^70][^107][^106]`) would render as a jammed "70107106" run; the
  converter regroups each run into a single `<sup>` whose linked numbers are
  joined by superscripted commas (7,8,9). Every number in a group remains its
  own clickable `noteref` link, and single citations keep the plain
  `<a><sup>N</sup></a>` markup.
- **Round-trip navigation.** Reference → bibliography entry is one click
  (cross-file anchor); entry → first in-text reference is one click back.
- **Notes at the back only.** No per-chapter asides — readers who don't want
  to leave the page simply don't tap the superscript; nothing else changes.
- **Stray backslash cleanup.** python-markdown only unescapes a fixed set of
  punctuation; sequences like `\&` or `\~` in the source markdown would
  otherwise reach the EPUB as a literal backslash in the text. The converter
  strips those backslashes so URLs such as `?sequence=1\&isAllowed=y` render
  and parse correctly.
- **"Additional sources consulted" caveat.** Sources listed but never cited
  (written as a numbered item — currently inside a blockquote — in the source
  markdown) are rendered as an *unnumbered* bullet so they cannot be mistaken
  for a citation number.
- **Wide-table handling.** Tables with eight or more columns (the comparative
  matrix is now 11 columns wide) get a `wide` class and a much smaller font
  size so they stay readable on e-reader screens.
- **Tables stay on one page.** Each table is wrapped in
  `<div class="tbl-keep">` and carries `break-inside: avoid` / `page-break-inside:
  avoid` on both the wrapper and the `<table>` itself, so paginating reading
  systems (Apple Books, Thorium, Calibre, e-ink devices) never split a table
  across a page break. A table taller than one page (the wide matrix on a
  small screen) cannot be kept whole — the reading system ignores the hint
  rather than clipping content; `thead { display: table-header-group; }`
  makes the header row repeat in that case. This is CSS only: EPUB has no
  real page model, so readers that reflow without pagination simply ignore it.

### Why not real page-bottom footnotes (or popups)?

EPUB is reflowable — pages don't exist until the reading system lays the text
out at the user's font size and screen size, so there is no "bottom of the
page" to anchor content to. The EPUB 3 alternative is popup footnotes
(`<aside epub:type="footnote">` appended to each citing chapter), which this
converter previously produced. They were dropped in favor of a single
endnote bibliography: popups repeat notes on every page, and round-trip
links to a consolidated chapter keep citations one click away without
cluttering the text. The markup still carries `epub:type="noteref"`, so
readers with footnote-aware navigation treat the links as citations.

## Diagrams

The converter generates 22 SVG figures. The FOB Sankeys are rendered by
`scripts/render_sankeys.js` (run with bun): the Python converter parses the
source markdown pre-render, hands the per-origin share data to the script as
JSON (`{ "<origin>": [ {node, lo, hi, mid, qual}, ... ] }`), and embeds the
returned SVGs. When bun is missing or the render fails, the built-in
stdlib-only generator in `scripts/epub_diagrams.py` (`fob_sankey`) produces
the same figure (a warning is printed for unexpected failures, never for a
plain "bun not installed"). All other figures are generated by
`epub_diagrams.py` directly:

| Figure | Where | Data source |
| :---- | :---- | :---- |
| FOB comparison (stacked bars, ten origins sorted by farmgate capture) | after the Dimension matrix (Actor Terminology) | per-origin FOB tables |
| Per-origin supply chain map (Farmer → … → Roaster; fixed-size boxes with the share range printed under each node — no width encoding; credit / power / gatekeeper strip; double border marks the largest non-farmgate node) | top of each origin chapter | FOB tables + Dimension matrix |
| Per-origin FOB Sankey (100% FOB price fanning into arrow-shaped ribbons, widths = normalized range midpoints so the source block and ribbons share one exact scale, labels inside the arrows with leader-line labels for thin bands) — bun rendering | after each origin's FOB table | per-origin FOB tables |
| Commodity vs specialty chain schematic (direct-trade bypass arc) | top of the Commodity vs Specialty chapter | hand-curated from the report's channel descriptions |

Design rules — the book targets B&W e-ink screens:

- **No color-only encoding.** The dominant farmgate band is a flat warm
  gray; secondary bands carry distinct light textures (diagonal hatch,
  diamond lattice, dot grid), each also identified by a matching swatch
  beside its margin label and by its text label. Tone or texture is never
  the only carrier of meaning.
- **No emoji glyphs** (inconsistent rendering on e-ink); annotation strips
  use plain-text prefixes (`Credit:`, `Power:`, `Gatekeeper:`).
- **No heavy ink.** A huge solid-black farmgate ribbon dominates a 1-bit
  e-ink page and dithers badly — light fills with crisp ink outlines read
  far better. The intermediary takes still pop because they are darker.
- **Captions carry the exact percentage ranges** plus the report's data note
  (directional estimates, indicative ranges — not audited statistics), so no
  information is lost even if a reader drops images. The data note describes
  each figure type's own encoding — width/normalization language is attached
  only to the bar chart and Sankeys; chain-map captions say the ranges are
  printed under each node instead, and never claim widths their boxes don't
  have.
- **Center legends/charts deliberately** — e.g. the legend of the stacked
  comparison chart is measured and centered rather than hugging the left
  edge.

### Sankey geometry — hard-won rules

The Sankey diagrams went through several broken geometries before landing on
the current one. The rules that make them read correctly, in
`render_sankeys.js`:

1. **One scale for both sides.** The source block is 100% = `flowH` px tall,
   and every ribbon is `share × flowH / 100` tall at the source *and* at the
   head. A single `K = flowH / 100` constant — never two scales derived from
   source- vs head-side gap budgets (that was the original bug: the fan-out
   gaps silently compressed the head-side ribbons relative to the block).
2. **Normalize the shares to sum to 100%.** The report's range midpoints sum
   to ~93–96%, so a flush stack can never tile the block unless the shares
   are normalized (`mid / total × 100`). The drawn width is the normalized
   share; the printed label still shows the report's exact range, and the
   caption discloses the normalization.
3. **Constant ribbon width, no taper.** A taper looks dynamic but breaks the
   width-equals-share encoding between the two ends.
4. **Source-side slots are flush** (no gaps) so the ribbons tile the block
   edge-to-edge; **head-side gaps are pure spacing** — never absorbed into
   the scale.
5. **Never draw ribbons as a stroked centerline** when you need outlines —
   a 0.7px outline stroke along the center of a thick band renders as a
   stray rule across the fill. Either build a closed ribbon path or layer a
   narrower fill stroke on top of a wider ink stroke.
6. **Thin bands (< ~26px) cannot hold text.** Use leader-line labels; check
   label fit with measured per-character width estimates, not optimistic
   guesses, and wrap margin text so it cannot overflow the viewBox edge.
7. **Degenerate inputs must degrade**: zero-width bands, missing qualifiers,
   and odd characters (`&`, quotes, diacritics) get margin labels or are
   skipped — the renderer never crashes on one bad row.

SVG is a core media type in EPUB 3, so all conformant readers (Apple Books,
Kobo, Thorium, Calibre, Send-to-Kindle) render the figures. If a figure's
source data fails to parse (e.g. after future report edits), that figure is
skipped with a `WARNING:` line in the script output — the conversion never
fails because of a diagram.

### Bun notes

- The renderer has **no npm dependencies** (it moved from d3-sankey to a
  hand-rolled layout for finer control); `scripts/package.json` still lists
  the earlier d3 packages but they are unused, and `bun run` works without
  `node_modules`.
- In restricted sandboxes, `bun install`/`bun run` can fail with `EROFS` on
  its default temp location. Fix: point `TMPDIR` and
  `BUN_INSTALL_CACHE_DIR` at a writable directory. The Python converter
  already does this for its `bun` subprocess.

## Verifying a build

The script prints the chapter list on success. For a deeper check, unzip the
EPUB (it is a plain zip) and validate:

```bash
unzip -q -d /tmp/epubcheck openwiki/production/deep-dive.epub
python3 - <<'EOF'
import re, glob, pathlib
import xml.etree.ElementTree as ET

base = pathlib.Path("/tmp/epubcheck/EPUB")
files = {f.name: f.read_text() for f in sorted(base.glob("ch[0-9][0-9].xhtml"))}
ids = {name: set(re.findall(r'id="(fn-\d+|ref-\d+-\d+)"', text))
       for name, text in files.items()}

ok = True
seen = []
for name, text in files.items():
    try:
        ET.fromstring(text)                      # strict XHTML parse
    except ET.ParseError as e:
        print(f"XML FAIL {name}: {e}"); ok = False
    for t in re.findall(r'href="#(fn-\d+|ref-\d+-\d+)"', text):
        if t not in ids[name]:                   # same-file anchors
            print(f"dead same-file anchor {t} in {name}"); ok = False
    for tgt, anchor in re.findall(r'href="([^#"]+\.xhtml)#(fn-\d+|ref-\d+-\d+)"', text):
        if anchor not in ids.get(tgt.split("/")[-1], set()):
            print(f"dead cross-file anchor {tgt}#{anchor} in {name}"); ok = False
    for m in re.finditer(r'<a epub:type="noteref"[^>]*href="[^"]*#fn-(\d+)"[^>]*>(?:<sup>)?\1(?:</sup>|</a>)', text):
        seen.append(int(m.group(1)))             # ref number == target number
        # (regex matches both the single form <sup>N</sup> and the comma-grouped
        # form, where the <sup> wrapper sits outside the <a> links)
firsts = []
for n in seen:
    if n not in firsts:
        firsts.append(n)
print("first appearances sequential:",
      firsts == list(range(1, len(firsts) + 1)))
print("OK" if ok else "FAILED")
EOF
```

Expected output: strict XML parses for every chapter, no dead (same-file or
cross-file) anchors, and `first appearances sequential: True`. A deeper
check also XML-parses every embedded SVG, verifies each `<img src>` target
exists in the package, and confirms figure numbers run 1..N in book order.

For visual QA of diagrams, rasterize and inspect (iterate until it looks
right — geometry bugs like zero-area ribbons or stray outline strokes are
invisible in the code and obvious in a render):

```bash
uv run --with cairosvg python -c "
import cairosvg
cairosvg.svg2png(url='sankey_preview/Brazil.svg',
                 write_to='sankey_preview/Brazil.png', scale=2.0,
                 background_color='white')
"
```

Check at minimum one origin with a huge farmgate band (Brazil), one with
thin bands and qualifiers (Kenya), and one with long node names
(Indonesia).

## Limitations

- Tables assume the report's pipe-table style; very wide tables (the
  comparative matrix is now 11 columns) are shrunk via a `wide` CSS class but
  will still be dense on small phone screens — best read on a tablet or in
  landscape, depending on the reader. The keep-together CSS is a hint, not a
  guarantee: a reading system splits a table anyway when it cannot fit on
  one page (then repeating the header row).
- The "Additional sources consulted" block lands as a subsection of the
  bibliography chapter, not inside any citing chapter.
- The origin deep dives are one chapter per origin (split at `<h3>`), so
  chapter count scales with the number of origins in the report.
- Chapter titles are derived from `## **…**` headings; documents without
  `h2`/`h3` headings become a single chapter. Origin chapters are matched to
  FOB tables by heading text — renamed headings silently skip their figures
  (with a warning).
- Figures assume the report's current table shapes (a `Share of FOB Export
  Price` table per origin, a `Dimension`-row annotation matrix). Different
  structures degrade gracefully: figures are skipped, never wrong.
- The script targets OpenWiki report structure (`h1` title, `h2`/`h3`
  sections, `[^N]` footnotes). It is not a general-purpose markdown→EPUB
  tool — for that, use pandoc.

## Related

- `scripts/md_to_epub.py` — the converter itself
- `scripts/epub_diagrams.py` — SVG figure generation (parsing + drawing)
- `scripts/render_sankeys.js` — bun renderer for the FOB Sankeys (hand-rolled
  one-stage layout, no npm dependencies; optional, automatic Python fallback
  otherwise)
- `docs/TESTING.md` — the repo's testing conventions
- [toolkit.bot: EPUB footnotes](https://toolkit.bot/blog/epub-footnotes) —
  reference for the `noteref`/`footnote` markup pattern (the popup variant
  this converter moved away from)
