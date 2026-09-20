"""Convert an OpenWiki deep-dive markdown file into a styled EPUB 3 with a
clickable endnote bibliography.

Citation handling:
- each reference is <a epub:type="noteref"> renumbered sequentially by first
  appearance across the book
- references link across files to their entry in the final
  "Works Cited & Sources" chapter, and each entry backlinks to the citing
  chapter's first reference — so any citation is one click from its source
  and one click back, without notes interrupting the body text
- sources listed but never cited render as unnumbered bullets in the same
  chapter
"""
import os
import re
import sys
from pathlib import Path

import markdown
from ebooklib import epub

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epub_diagrams as diag  # noqa: E402  (same-directory module, stdlib only)

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])

md_text = SRC.read_text(encoding="utf-8")

# --- parse figure data from the source markdown (pre-render) ---------------
fob = diag.parse_fob_tables(md_text)
origins, matrix = diag.parse_matrix(md_text)
warned = []
for origin in origins:
    if origin not in fob:
        warned.append(f"no FOB table parsed for {origin!r} — its figures are skipped")
if not matrix:
    warned.append("annotation matrix not found — chain maps omit credit/power/gatekeeper notes")

# --- d3/bun Sankey rendering (falls back to the pure-Python generator) -----
def render_sankeys_d3(fob_data):
    """Render the FOB Sankeys via scripts/render_sankeys.js (bun + d3-sankey).
    Returns {origin: svg text}; an empty dict on any failure, in which case
    the built-in SVG generator is used instead."""
    import json, shutil, subprocess, tempfile
    js = Path(__file__).resolve().parent / "render_sankeys.js"
    if shutil.which("bun") is None or not js.exists():
        return {}
    try:
        with tempfile.TemporaryDirectory() as td:
            job = Path(td) / "sankey_job.json"
            out = Path(td) / "out"
            job.write_text(json.dumps(fob_data))
            # explicit TMPDIR: some sandboxes block bun's default temp location
            env = {**os.environ, "TMPDIR": td,
                   "BUN_INSTALL_CACHE_DIR": str(Path(td) / "cache")}
            subprocess.run(["bun", str(js), str(job), str(out)], check=True,
                           capture_output=True, timeout=120, env=env)
            return {p.stem: p.read_text(encoding="utf-8") for p in sorted(out.glob("*.svg"))}
    except Exception as exc:
        warned.append(f"d3/bun Sankey render unavailable ({exc.__class__.__name__}: {exc}) "
                      "— using built-in generator")
        return {}

sankey_svgs = render_sankeys_d3(fob)
if sankey_svgs:
    print(f"rendered {len(sankey_svgs)} Sankey diagrams with bun/d3")

# Render the whole document in one pass so footnote defs/resolves link up.
full_html = markdown.markdown(md_text, extensions=["tables", "footnotes"])

# python-markdown only unescapes a fixed set of punctuation; for characters
# outside that set (e.g. "\&", "\~") it emits the backslash verbatim into the
# HTML. Strip those stray backslashes ("\&amp;" -> "&amp;", "\~" -> "~").
full_html = re.sub(r'\\&amp;', '&amp;', full_html)
full_html = re.sub(r'\\([~])', r'\1', full_html)

# strip the source document's "Works cited" heading — the bibliography
# lives in its own chapter, and the bare heading would dangle above
# whatever endnotes happen to close the previous chapter
full_html = re.sub(r'(?i)<h4><strong>works cited</strong></h4>', "", full_html)

# --- extract the footnote-definition block produced by python-markdown -----
notes_match = re.search(r'(?s)<div class="footnote">.*?</div>', full_html)
footnotes_html = notes_match.group(0) if notes_match else ""
if notes_match:
    full_html = full_html[:notes_match.start()] + full_html[notes_match.end():]

# id -> citation inner HTML (backlinks removed; rebuilt per chapter)
fn_items = {}
for fid, inner in re.findall(r'(?s)<li id="(fn:\d+)">(.*?)</li>', footnotes_html):
    inner = re.sub(r'(?s)\s*<a[^>]*href="#fnref[^"]*"[^>]*>.*?</a>', "", inner).strip()
    fn_items[fid] = inner

# --- move the "Additional sources consulted" block into the bibliography ---
extra_sources = ""
m = re.search(r'(?s)(<h4><strong>Additional sources consulted</strong></h4>.*?)$', full_html)
if m:
    extra_sources = m.group(1)
    # the source wrote it as a numbered list ("21. ..."), which would collide
    # with real citation numbers — make it an unnumbered bullet instead
    extra_sources = re.sub(r'(?s)<ol[^>]*>(.*?)</ol>', r'<ul>\1</ul>', extra_sources)
    # the latest reports wrap the block in a blockquote; unwrap it so it
    # renders as a plain bullet list, matching the numbered bibliography above
    extra_sources = re.sub(r'(?s)<blockquote>\s*(<ul>.*?</ul>)\s*</blockquote>', r'\1', extra_sources)
    full_html = full_html[:m.start()]

# --- split into chapters at <h2> boundaries --------------------------------
def clean_title(raw: str) -> str:
    t = re.sub(r"<[^>]+>", "", raw)
    return t.replace("**", "").replace("\\", "").strip()

def escape_ampersands(html: str) -> str:
    # raw & in hand-written URLs would break strict XHTML parsers (Thorium etc.)
    return re.sub(r"&(?!#?\w+;)", "&amp;", html)

parts = re.split(r"(?i)(?=<h2)", full_html)
title_match = re.match(r"(?s)<h1[^>]*>(.*?)</h1>", parts[0])
book_title = clean_title(title_match.group(1)) if title_match else SRC.stem
if title_match:
    parts[0] = parts[0][title_match.end():]

chapters = []
for i, part in enumerate(parts):
    body = part.strip()
    if not body:
        continue
    h2 = re.match(r"(?s)<h2[^>]*>(.*?)</h2>", body)
    label = clean_title(h2.group(1)) if h2 else (book_title if i == 0 else f"Section {i}")
    chapters.append((label, body))

# --- split the origin deep-dive chapter into per-origin chapters -----------
# The 'Origin-by-Origin Deep Dives' h2 holds one <h3> per origin; give each
# origin its own chapter (own page, TOC entry nested under the h2 overview).
def explode_h3(label, body):
    parts = re.split(r"(?=<h3)", body)
    head = parts[0].strip()
    out = []
    if head:
        out.append((label, head))
    for p in parts[1:]:
        m = re.match(r"(?s)<h3[^>]*>(.*?)</h3>", p)
        out.append((clean_title(m.group(1)) if m else "Section", p))
    return out

chapters = [c for label, body in chapters for c in (explode_h3(label, body)
            if body.count("<h3") else [(label, body)])]

# --- citations: renumber in order of first appearance ---------------------
# The source markdown's footnote ids are arbitrary (non-sequential, with
# gaps), so renumber all citations sequentially by first appearance across
# the book. Citations live only in the final "Works Cited & Sources"
# chapter: every noteref links across files to its bibliography entry, and
# each entry backlinks to the citing chapter's first reference.
SUP_REF = re.compile(
    r'<sup id="(fnref[^"]*)">\s*<a class="footnote-ref" href="#fn:(\d+)">\s*\d+\s*</a>\s*</sup>'
)

XHTML_NS = 'xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"'
renumber = {}          # original fn id number -> new sequential number
occurrence = {}        # new number -> times seen so far (for ref ids)
new_to_orig = {}       # new number -> original number
first_ref = {}         # new number -> (chapter file, ref id) of first occurrence
bib_file = f"ch{len(chapters) + 1:02d}.xhtml"
rewritten = []
for ch_idx, (label, body) in enumerate(chapters):
    ch_file = f"ch{ch_idx + 1:02d}.xhtml"

    def repl(m, ch_file=ch_file):
        orig = m.group(2)
        if orig not in renumber:
            renumber[orig] = len(renumber) + 1
            new_to_orig[renumber[orig]] = orig
        n = renumber[orig]
        occurrence[n] = occurrence.get(n, 0) + 1
        rid = f"ref-{n}-{occurrence[n]}"
        if n not in first_ref:
            first_ref[n] = (ch_file, rid)
        return (f'<a epub:type="noteref" role="doc-noteref" aria-label="Footnote {n}" '
                f'href="{bib_file}#fn-{n}" id="{rid}"><sup>{n}</sup></a>')
    rewritten.append((label, SUP_REF.sub(repl, body)))
chapters = rewritten

# --- group consecutive citations -------------------------------------------
# Adjacent citations ([^70][^107][^106]) would render as a jammed "70107106"
# superscript run. Regroup each run of two or more into a single <sup> whose
# linked numbers are joined by superscript commas; single citations keep
# their existing <a><sup>N</sup></a> markup (and the source markdown,
# footnote ids and URLs, are untouched).
CITE_ANCHOR = r'<a epub:type="noteref"[^>]*><sup>\d+</sup></a>'
CITE_RUN = re.compile(rf'(?s)({CITE_ANCHOR})(?:\s*{CITE_ANCHOR})+')

def group_citations(html: str) -> str:
    def grp(m):
        anchors = re.findall(CITE_ANCHOR, m.group(0))
        # keep each <a> (link target, aria-label); drop only its <sup> wrapper
        inner = ",".join(
            re.sub(r'(?s)^(<a [^>]*>)<sup>(\d+)</sup>(</a>)$', r'\1\2\3', a)
            for a in anchors)
        return f"<sup>{inner}</sup>"
    return CITE_RUN.sub(grp, html)

chapters = [(label, group_citations(body)) for label, body in chapters]

# --- flag very wide tables -------------------------------------------------
# The comparative matrix grew to 11 columns (Dimension + ten origins); at the
# default table font size that overflows every e-reader screen. Tag tables
# with >= WIDE_TABLE_COLS columns so CSS can shrink them.
WIDE_TABLE_COLS = 8

def tag_wide_tables(html: str) -> str:
    def tag(m):
        tbl = m.group(0)
        header = tbl.split('</tr>', 1)[0]
        if header.count('<th ') >= WIDE_TABLE_COLS:
            tbl = tbl.replace('<table>', '<table class="wide">', 1)
        return tbl
    return re.sub(r'(?s)<table>.*?</table>', tag, html)

chapters = [(label, tag_wide_tables(body)) for label, body in chapters]

# --- callout boxes ----------------------------------------------------------
# The report marks callouts as blockquotes opening with a bold lead-in
# ("**Data note:**", "**Why wet hulling?**"). Give those an infobox panel
# class — a shaded, bordered panel that is kept on one page — while plain
# blockquotes (if any are added later) keep the default quote style.
CALLOUT = re.compile(r'(?s)<blockquote>\s*<p><strong>.*?</blockquote>')

def tag_callouts(html: str) -> str:
    def tag(m):
        return m.group(0).replace('<blockquote>', '<blockquote class="infobox">', 1)
    return CALLOUT.sub(tag, html)

chapters = [(label, tag_callouts(body)) for label, body in chapters]

# --- keep tables on one page -----------------------------------------------
# EPUB is reflowable, so pagination belongs to the reading system; CSS hints
# are the only lever. Wrap every table in an avoid-break block AND set
# break-inside on the table itself — some engines honor the rule only on plain
# block containers, others only on the table element. A reading system that
# cannot fit a taller-than-page table (the wide matrix on a small screen)
# simply ignores the hint rather than clipping content, so nothing is lost.
def keep_tables_together(html: str) -> str:
    def wrap(m):
        return f'<div class="tbl-keep">{m.group(0)}</div>'
    return re.sub(r'(?s)<table[^>]*>.*?</table>', wrap, html)

final_chapters_src = []
for label, body in chapters:
    final_chapters_src.append((label, escape_ampersands(body)))

# --- figures ----------------------------------------------------------------
# Diagrams are generated as standalone SVG EPUB items (core media type, e-ink
# friendly: grayscale tones + hatch patterns + text labels). If the data for a
# figure fails to parse, the figure is skipped with a warning — never a crash.

def _rng(r):
    return f"{r['lo']:g}%\u2013{r['hi']:g}%"

# FOB figures share one source caveat, but each figure type appends the
# sentence that describes *its own* encoding — the chain maps are fixed-size
# box diagrams whose only width-free encoding is the printed range label, so
# they must not claim "bar/arrow widths" the way the bar chart and Sankeys do.
_FOB_SOURCE = ("Source: the report's “Share of FOB Export Price” tables — directional "
               "estimates from practitioner accounts, presented as indicative ranges, "
               "not audited statistics.")

svg_figs = []

def make_figure(svg, caption, alt):
    n = len(svg_figs) + 1
    fname = f"fig{n:02d}.svg"
    svg_figs.append((fname, svg))
    return (f'<figure><img src="figures/{fname}" alt="{alt}"/>'
            f'<figcaption><span class="fig-num">Figure {n}.</span> '
            f'{escape_ampersands(caption)}</figcaption></figure>')

def insert_after(body, pattern, insertion):
    m = re.search(pattern, body, re.S)
    if not m:
        return body, False
    return body[:m.end()] + insertion + body[m.end():], True

final_chapters = []
for label, body in final_chapters_src:
    if label == "Commodity vs. Specialty Structural Comparison Table":
        fig = make_figure(
            diag.commodity_specialty(),
            "Schematic comparison of commodity and specialty coffee supply chains "
            "(curated from the report's channel descriptions, not per-origin data): "
            "the commodity chain passes through many hands at thin margins, while "
            "specialty chains shorten the path via direct trade, plot-level "
            "traceability, and quality premiums that improve farmgate terms.",
            "Commodity versus specialty coffee supply chain schematic")
        body, ok = insert_after(body, r"</h2>", fig)
        if not ok:
            warned.append("could not place commodity-vs-specialty figure")
    elif label == "Actor Terminology: Farmers, Producers, and Intermediaries":
        fig = make_figure(
            diag.fob_comparison(fob),
            "Estimated share of the FOB export price by value-chain node across the "
            "ten origins, sorted by farmgate capture (bar segments sized by range "
            "midpoints, normalised within each bar to sum to 100%). The spread of "
            "first-segment sizes is the report's central "
            "value-distribution finding. " + _FOB_SOURCE,
            "Stacked bar chart of FOB export price shares across ten origins")
        body, ok = insert_after(body, r"<th[^>]*>\s*Dimension\s*</th>.*?</table>", fig)
        if not ok:
            warned.append("could not place FOB comparison figure (Dimension matrix not found)")
    elif label in fob:
        rows = fob[label]
        ann = matrix.get(label, {})
        farm = rows[0]
        chain_fig = make_figure(
            diag.chain_diagram(label, rows, ann),
            f"{label} supply chain: farmgate share of FOB {_rng(farm)}. "
            f"Double border marks the largest non-farmgate node; percentage "
            f"ranges are printed under each node. "
            + (f"Credit: {ann.get('Dominant credit mechanism', 'n/a')} "
               f"Power: {ann.get('Key power asymmetry', 'n/a')} "
               f"Gatekeeper: {ann.get('Regulatory gatekeeper', 'n/a')} " if ann else "")
            + _FOB_SOURCE,
            f"{label} coffee supply chain diagram")
        body, ok = insert_after(body, r"</h3>", chain_fig)
        if not ok:
            warned.append(f"could not place chain figure for {label}")
        sankey_fig = make_figure(
            sankey_svgs.get(label) or diag.fob_sankey(label, rows),
            f"{label}: estimated distribution of the FOB export price across "
            "value-chain nodes (arrow widths use range midpoints, normalised "
            "to sum to 100%; labels give the exact ranges). " + _FOB_SOURCE,
            f"{label} FOB export price share Sankey diagram")
        body, ok = insert_after(
            body, r"<th[^>]*>\s*Share of FOB Export Price\s*</th>.*?</table>", sankey_fig)
        if not ok:
            warned.append(f"could not place Sankey figure for {label}")
    final_chapters.append((label, body))

# wrap tables in avoid-break blocks after figure placement, so each table and
# each figure is its own keep-together unit (gluing a table to the Sankey
# figure that follows it would produce a block taller than most pages)
final_chapters = [(label, keep_tables_together(body)) for label, body in final_chapters]

# full bibliography, re-ordered to the new sequential numbering; each entry
# is the link target for its citations and backlinks to the first reference
if new_to_orig:
    items = []
    for n, orig in sorted(new_to_orig.items()):
        ch_file, rid = first_ref[n]
        back = f'<a class="footnote-number" href="{ch_file}#{rid}">{n}.</a>'
        items.append(f'<li id="fn-{n}">{back} {fn_items[f"fn:{orig}"]}</li>')
    bib = '<ol class="bibliography">' + "".join(items) + "</ol>" + extra_sources
    final_chapters.append(("Works Cited & Sources", escape_ampersands(bib)))

CSS = """
body { font-family: serif; line-height: 1.5; }
h1, h2, h3, h4 { font-family: sans-serif; line-height: 1.2; color: #3b2f2f; }
h1 { font-size: 1.6em; border-bottom: 2px solid #6f4e37; padding-bottom: .3em; }
h2 { font-size: 1.35em; border-bottom: 1px solid #c4b5a5; padding-bottom: .2em; margin-top: 1.5em; }
table { border-collapse: collapse; width: 100%; font-size: .85em; margin: 1em 0; page-break-inside: avoid; break-inside: avoid; }
.tbl-keep { page-break-inside: avoid; break-inside: avoid; }
thead { display: table-header-group; }
th, td { border: 1px solid #b09a8a; padding: .4em .5em; text-align: left; vertical-align: top; overflow-wrap: break-word; }
th { background: #efe6dc; }
table.wide { font-size: .58em; line-height: 1.3; }
table.wide th, table.wide td { padding: .2em .25em; }
table.wide th { white-space: nowrap; }
blockquote { border-left: 4px solid #6f4e37; margin: 1em 0; padding: .2em 1em; color: #4a3c33; background: #f7f2ec; }
blockquote.infobox { background: #f0e7db; border: 1.5px solid #6f4e37; border-left: 6px solid #6f4e37; border-radius: 6px; padding: .55em .9em; margin: 1.1em 0; page-break-inside: avoid; break-inside: avoid; }
blockquote.infobox > p:first-child { margin-top: 0; }
blockquote.infobox > p:last-child { margin-bottom: 0; }
blockquote.infobox p:first-child > strong:first-child { font-family: sans-serif; color: #6f4e37; }
code { font-family: monospace; font-size: .9em; }
a.footnote-number { font-weight: bold; font-family: sans-serif; text-decoration: none; color: #6f4e37; }
ol.bibliography { list-style: none; padding-left: .4em; }
ol.bibliography li { margin: .4em 0; }
sup a { text-decoration: none; }
figure { margin: 1.2em 0; text-align: center; page-break-inside: avoid; break-inside: avoid; }
figure img { max-width: 100%; height: auto; }
figcaption { font-size: .78em; line-height: 1.4; color: #4a3c33; text-align: left; margin-top: .4em; }
.fig-num { font-weight: bold; font-family: sans-serif; color: #6f4e37; }
"""

book = epub.EpubBook()
book.set_identifier(f"kissaten-openwiki-{SRC.stem}")
book.set_title(book_title)
book.set_language("en")
book.add_author("Kissaten OpenWiki")
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

style = epub.EpubItem(uid="style", file_name="style/main.css", media_type="text/css", content=CSS)
book.add_item(style)

for fname, content in svg_figs:
    book.add_item(epub.EpubItem(uid=f"fig-{fname}", file_name=f"figures/{fname}",
                                media_type="image/svg+xml", content=content))

spine = ["nav"]
toc = []
origin_children = None
assert final_chapters, "no chapters produced"
for i, (label, body) in enumerate(final_chapters, 1):
    ch = epub.EpubHtml(title=label, file_name=f"ch{i:02d}.xhtml", lang="en")
    head = f"<h1>{book_title}</h1>" if i == 1 else ""
    ch.content = f"<html {XHTML_NS}><head><title>{label}</title></head><body>{head}{body}</body></html>"
    ch.add_item(style)
    book.add_item(ch)
    # nest the per-origin chapters under the deep-dive overview in the TOC
    if label == "Origin-by-Origin Deep Dives":
        origin_children = []
        toc.append((ch, origin_children))
    elif origin_children is not None and label in fob:
        origin_children.append(ch)
    else:
        toc.append(ch)
    spine.append(ch)

book.toc = toc
book.spine = spine

epub.write_epub(str(OUT), book)
print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB) with {len(final_chapters)} chapters "
      f"and {len(svg_figs)} figures:")
for label, _ in final_chapters:
    print(f"  - {label}")
for w in warned:
    print(f"  WARNING: {w}")
