"""SVG diagram generation for the OpenWiki deep-dive EPUB.

Targets B&W e-ink screens: node types are distinguished by tone + hatch
pattern + text label (never color alone), no emoji glyphs, generous font
sizes, and every number that matters also appears in the XHTML caption.

All functions are pure stdlib and return SVG strings. Parsing helpers read
the *source markdown* (pre-render) so figures stay in sync with the tables.
"""
import re
import textwrap
from xml.sax.saxutils import escape

INK = "#241d18"        # near-black warm ink (renders as dark gray on e-ink)
MID = "#8a7a6d"        # mid gray-brown
LIGHT = "#ded4c9"      # light warm gray
PAPER = "#ffffff"
FAINT = "#f3efea"

# segment styles by node index: farmgate / collection / processing / export.
# (fill, text fill) — dark solid, dark hatch, light hatch, light solid.
SEG_STYLES = [
    (INK, PAPER),              # farmgate: darkest — the farmer's share
    ("url(#hatch-d)", INK),    # collectors / intermediaries
    ("url(#hatch-l)", INK),    # processing / milling
    (LIGHT, INK),              # exporter / logistics
]
SEG_LEGEND = [
    "Farmgate seller",
    "Collection / aggregation",
    "Processing / milling",
    "Export / logistics",
]


# ------------------------------------------------------------------ helpers

def _esc(text):
    return escape(str(text))


def _txt(x, y, s, size=11, anchor="start", fill=INK, weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}">{_esc(s)}</text>')


def _txt_wrap(x, y, s, width_chars, lh, **kw):
    out = []
    for i, line in enumerate(textwrap.wrap(str(s), width_chars,
                                           break_long_words=False,
                                           break_on_hyphens=False) or [""]):
        out.append(_txt(x, y + i * lh, line, **kw))
    return "".join(out)


def _defs():
    return (
        '<pattern id="hatch-d" width="5" height="5" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="5" height="5" fill="#efe9e3"/>'
        '<line x1="0" y1="0" x2="0" y2="5" stroke="#6b5e52" stroke-width="1.5"/></pattern>'
        '<pattern id="hatch-l" width="5" height="5" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(-45)"><rect width="5" height="5" fill="#f7f4f0"/>'
        '<line x1="0" y1="0" x2="0" y2="5" stroke="#a89a8d" stroke-width="1"/></pattern>'
    )


def _svg(w, h, body):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'width="{w:.0f}" height="{h:.0f}" role="img">{_defs()}{body}</svg>')


def _shorten(s, limit=48):
    """First clause of a long annotation cell, for diagram labels."""
    s = s.strip()
    if len(s) <= limit:
        return s
    head = s.split(";")[0].strip()
    if 18 <= len(head) <= limit:
        return head
    if len(head) < 18:
        head = s
    return head[:limit].rsplit(" ", 1)[0].rstrip(",;") + "…"


def _pct(v):
    return f"{v:g}%"


def _range(lo, hi):
    return f"{lo:g}%–{hi:g}%" if hi != lo else f"{lo:g}%"


def _arrow(x0, y0, x1, y1, stroke=INK, width=1.4):
    """Horizontal arrow with a small triangular head."""
    head = 6
    return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1 - head:.1f}" y2="{y1:.1f}" '
            f'stroke="{stroke}" stroke-width="{width}"/>'
            f'<polygon points="{x1 - head},{y1 - head * 0.6:.1f} {x1},{y1} '
            f'{x1 - head},{y1 + head * 0.6:.1f}" fill="{stroke}"/>')


# ------------------------------------------------------------------ parsing

_FOB_ROW = re.compile(r"^\s*\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*$")


def parse_fob_tables(md_text):
    """{origin: [{"node","lo","hi","mid","qual"}]} from the per-origin FOB tables."""
    fob = {}
    heads = list(re.finditer(r"^### \*\*([^*]+)\*\*\s*$", md_text, re.M))
    for i, m in enumerate(heads):
        origin = m.group(1).strip()
        seg = md_text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(md_text)]
        tm = re.search(r"Share of FOB Export Price\s*\|\s*\n\s*\|[^|]*\|[^|]*\|\s*\n((?:\s*\|.*\n)+)", seg)
        if not tm:
            continue
        rows = []
        for line in tm.group(1).splitlines():
            rm = _FOB_ROW.match(line)
            if not rm:
                continue
            node = re.sub(r"[*\\]", "", rm.group(1)).strip()
            raw = re.sub(r"[*\\]", "", rm.group(2)).strip()
            qm = re.search(r"\(([^()]*)\)", raw)
            valpart = re.sub(r"\([^()]*\)", "", raw)
            nums = re.findall(r"(\d+(?:\.\d+)?)\s*%", valpart)
            if not nums:
                continue
            lo = float(nums[0])
            hi = float(nums[1]) if len(nums) > 1 else lo
            rows.append({"node": node, "lo": lo, "hi": hi,
                         "mid": (lo + hi) / 2, "qual": qm.group(1) if qm else ""})
        if rows:
            fob[origin] = rows
    return fob


def _cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _strip_md(s):
    return re.sub(r"\s+", " ", re.sub(r"[*\\]", "", s)).strip()


def parse_matrix(md_text):
    """Parse the 'Dimension | <origins>' annotation matrix.

    Returns (origins, {origin: {dimension: text}}).
    """
    m = re.search(r"^\s*\|\s*Dimension\s*\|.*$", md_text, re.M)
    if not m:
        return [], {}
    header = _cells(m.group(0))
    origins = [_strip_md(c) for c in header[1:]]
    data = {o: {} for o in origins}
    for line in md_text[m.end():].splitlines():
        if not line.strip():
            continue
        if not line.strip().startswith("|"):
            break
        cells = _cells(line)
        if len(cells) < len(origins) + 1 or cells[0].startswith(":") or cells[0] == "Dimension":
            continue
        dim = _strip_md(cells[0])
        for o, v in zip(origins, cells[1:]):
            data[o][dim] = _strip_md(v)
    return origins, data


# ------------------------------------------------------------------ diagrams

def fob_sankey(origin, rows, width=640):
    """Sankey in the classic sketch style: a solid source block on the left,
    S-curved arrow-shaped ribbons whose widths are the range midpoints, and
    labels drawn inside the ribbons (leader-line labels in the right margin
    for bands too thin to hold text). All B&W-safe: tone + text, no color."""
    top, flow_h = 26, 236
    x1, base_x, tip_x = 40, 396, 414
    label_x = 426
    total = sum(r["mid"] for r in rows)
    scale = flow_h / total

    tones = ["#e5ddd4", "#6b5e52", "#a5988b", "#c9bfb3"]
    tones_txt = [INK, PAPER, INK, INK]

    body = []
    # source block with rotated label, like the sketch's "PACKAGING IN"
    body.append(f'<rect x="24" y="{top}" width="16" height="{flow_h}" fill="{INK}"/>')
    cy = top + flow_h / 2
    body.append(f'<text x="32" y="{cy:.1f}" transform="rotate(-90 32 {cy:.1f})" '
                f'font-family="Helvetica,Arial,sans-serif" font-size="10" font-weight="bold" '
                f'text-anchor="middle" fill="{PAPER}">FOB EXPORT PRICE = 100%</text>')

    y = top
    margin = []          # (desired_y, lines, range_text) leader-line labels
    for i, r in enumerate(rows):
        h = r["mid"] * scale
        ty0, ty1 = y, y + h
        my = (ty0 + ty1) / 2
        y = ty1
        fill = tones[i % 4]
        tfill = tones_txt[i % 4]
        rng = _range(r["lo"], r["hi"])
        qual = f" ({r['qual']})" if r["qual"] else ""

        cx = (x1 + base_x) / 2
        # ribbon: band from the source block to the arrow base; both edges get
        # a gentle S (control points pulled toward the band's centreline) so
        # the flow reads as leaving the block, sketch-style
        dyc = (my - (ty0 + ty1) / 2)  # 0 by construction; keep edges parallel
        body.append(
            f'<path d="M {x1},{ty0:.1f} C {cx},{ty0:.1f} {cx},{ty0:.1f} '
            f'{base_x},{ty0:.1f} L {base_x},{ty1:.1f} C {cx},{ty1:.1f} {cx},{ty1:.1f} '
            f'{x1},{ty1:.1f} Z" fill="{fill}" stroke="{INK}" stroke-width="1"/>')
        # arrowhead, slightly wider than the ribbon like the sketch
        body.append(f'<polygon points="{base_x - 1},{ty0 - 2:.1f} {tip_x},{my:.1f} '
                    f'{base_x - 1},{ty1 + 2:.1f}" fill="{fill}" stroke="{INK}" stroke-width="1"/>')

        name_lines = textwrap.wrap(r["node"], 20)[:3]
        needed = len(name_lines) + 1 + (1 if r["qual"] else 0)
        max_lines = int((h - 10) / 12)
        if needed <= max_lines and h >= 26:
            # label inside the ribbon
            lines = name_lines + [rng + (f" {qual}" if r["qual"] and len(name_lines) == 1 else "")]
            if r["qual"] and len(name_lines) > 1:
                lines.append(qual)
            ty = my - (len(lines) - 1) * 6 + 4
            for ln in lines:
                body.append(_txt(cx, ty, ln, size=10, anchor="middle", fill=tfill, weight="bold"))
                ty += 12
        else:
            margin.append((my, name_lines, rng + qual))

    # leader-line labels for thin bands, stacked without collisions
    last_bottom = top + flow_h
    for my, name_lines, label in margin:
        sy = max(my - 8, last_bottom + 4)
        body.append(f'<line x1="{tip_x}" y1="{my:.1f}" x2="{label_x}" y2="{sy + 8:.1f}" '
                    f'stroke="{MID}" stroke-width="0.8"/>')
        ty = sy + 9
        for ln in name_lines[:3]:
            body.append(_txt(label_x, ty, ln, size=9.5))
            ty += 11
        for ln in textwrap.wrap(label, 30)[:2]:
            body.append(_txt(label_x, ty, ln, size=9.5, weight="bold"))
            ty += 11
        last_bottom = ty + 4
        height_floor = last_bottom
    height = max(top + flow_h, height_floor if margin else 0) + 14
    return _svg(width, height, "".join(body))


def chain_diagram(origin, rows, ann, width=640):
    """Per-origin supply chain map: actor boxes sized/annotated per the report.

    Farmer -> report's FOB nodes -> Importer -> Roaster, with the credit /
    power / gatekeeper annotation strip below (plain-text labels, e-ink safe).
    """
    def short(name, fallback):
        base = re.split(r"[(/]", name)[0].strip() or fallback
        # let _txt_wrap handle line breaks; only cap pathological lengths
        if len(base) <= 34:
            return base
        return base[:32].rsplit(" ", 1)[0]

    boxes = [("Farmer", INK, PAPER)]
    for i, r in enumerate(rows[1:], start=1):
        boxes.append((short(r["node"], f"Node {i}"), None, INK))
    boxes += [("Importer", None, INK), ("Roaster", None, INK)]

    n = len(boxes)
    bw, gap = min(104, (width - 32 - (n - 1) * 26) / n), 26
    bx, by, bh = 16, 34, 52
    total_w = n * bw + (n - 1) * gap
    x0 = (width - total_w) / 2

    body = [_txt(width / 2, 20, origin, size=13, anchor="middle", weight="bold")]

    # chokepoint = largest non-farmgate share
    choke = max(range(1, len(rows)), key=lambda i: rows[i]["mid"]) if len(rows) > 1 else None

    centers = []
    for i, (label, fill, tfill) in enumerate(boxes):
        x = x0 + i * (bw + gap)
        centers.append(x + bw / 2)
        extra = ""
        if fill is None:
            fill = FAINT
        if 1 <= i <= len(rows) - 1:
            fill, tfill = SEG_STYLES[i % len(SEG_STYLES)]
        body.append(f'<rect x="{x:.1f}" y="{by}" width="{bw:.1f}" height="{bh}" '
                    f'fill="{fill}" stroke="{INK}" stroke-width="1.2"/>')
        if i == choke:
            body.append(f'<rect x="{x - 3:.1f}" y="{by - 3}" width="{bw + 6:.1f}" '
                        f'height="{bh + 6}" fill="none" stroke="{INK}" stroke-width="1"/>')
        body.append(_txt_wrap(x + bw / 2, by + 16, label, max(9, int(bw / 6)), 11,
                              size=9.5, anchor="middle", fill=tfill, weight="bold"))
        if i < len(rows):
            body.append(_txt(x + bw / 2, by + bh + 12, _range(rows[i]["lo"], rows[i]["hi"]),
                             size=9.5, anchor="middle", fill=MID, weight="bold"))
        if i:
            body.append(_arrow(x - gap, by + bh / 2, x, by + bh / 2))
    body.append(_txt(x0 + total_w, by + bh + 26, "share of FOB export price (ranges)",
                     size=8.5, anchor="end", fill=MID))

    # annotation strip
    lines = []
    for key, label in (("Dominant credit mechanism", "Credit"),
                       ("Key power asymmetry", "Power"),
                       ("Regulatory gatekeeper", "Gatekeeper")):
        if ann.get(key):
            lines.append((label, _shorten(ann[key])))
    y = by + bh + 46
    for label, text in lines:
        body.append(_txt(16, y, f"{label}:", size=10, weight="bold", fill=MID))
        body.append(_txt_wrap(104, y, text, 80, 12, size=10))
        y += 12 * max(1, (len(text) + 79) // 80) + 6
    return _svg(width, max(y + 4, 170), "".join(body))


def fob_comparison(fob, width=640):
    """All origins: 100% stacked bars of FOB share, sorted by farmgate capture."""
    rows = [(o, rs) for o, rs in fob.items() if rs]
    rows.sort(key=lambda kv: -kv[1][0]["mid"])
    nseg = max(len(rs) for _, rs in rows)

    x0, x1 = 104, 560
    top, rowh, gap = 46, 22, 8
    h = top + len(rows) * (rowh + gap) + 6 + 16 * ((nseg + 1) // 2) + 16

    body = [_txt(x0, 16, "Estimated share of FOB export price by value-chain node",
                 size=11, weight="bold")]
    # grid
    for p in (25, 50, 75):
        gx = x0 + (x1 - x0) * p / 100
        body.append(f'<line x1="{gx:.1f}" y1="{top - 8}" x2="{gx:.1f}" y2="{top + len(rows) * (rowh + gap) - gap}" '
                    f'stroke="#cfc5ba" stroke-width="0.6" stroke-dasharray="2,3"/>')
        body.append(_txt(gx, top - 12, f"{p}%", size=8, anchor="middle", fill=MID))
    body.append(_txt(x1, top - 12, "100%", size=8, fill=MID))

    y = top
    for origin, rs in rows:
        body.append(_txt_wrap(x0 - 8, y + rowh / 2 + 3.5, origin, 12, 10, size=10, anchor="end"))
        scale = (x1 - x0) / sum(r["mid"] for r in rs)
        x = x0
        for i, r in enumerate(rs):
            w = r["mid"] * scale
            fill, tfill = SEG_STYLES[i % len(SEG_STYLES)]
            body.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{rowh}" '
                        f'fill="{fill}" stroke="{PAPER}" stroke-width="0.6"/>')
            if w >= 30:
                body.append(_txt(x + w / 2, y + rowh / 2 + 3.5, _pct(r["mid"]),
                                 size=9, anchor="middle", fill=tfill, weight="bold"))
            x += w
        y += rowh + gap

    # legend (two columns, horizontally centered)
    ly = y + 14
    CH = 5.3  # approx char width at 9.5px sans
    col_items = [(i, i % 2) for i in range(nseg)]
    col_w = []
    for c in (0, 1):
        widths = [12 + 6 + len(SEG_LEGEND[i]) * CH for i, cc in col_items if cc == c]
        col_w.append(max(widths) if widths else 0)
    gap = 30
    total = col_w[0] + (gap if nseg > 1 else 0) + (col_w[1] if nseg > 1 else 0)
    col_x = [(width - total) / 2, (width - total) / 2 + col_w[0] + gap]
    for i in range(nseg):
        fill, _ = SEG_STYLES[i % len(SEG_STYLES)]
        cx = col_x[i % 2]
        yy = ly + (i // 2) * 16
        body.append(f'<rect x="{cx:.1f}" y="{yy - 9}" width="12" height="12" fill="{fill}" '
                    f'stroke="{INK}" stroke-width="0.8"/>')
        body.append(_txt(cx + 18, yy + 1, SEG_LEGEND[i], size=9.5))
    return _svg(width, h, "".join(body))


def commodity_specialty(width=640):
    """Schematic: commodity vs specialty chain, direct-trade bypass arc."""
    commodity = ["Farmer", "Local buyer", "Aggregator", "Dry mill", "Exporter", "Importer", "Roaster"]
    specialty = ["Farmer", "CWS / dry mill", "Specialty exporter", "Importer", "Roaster"]

    def row(labels, y, label, box_w, box_h=34, gap=14):
        n = len(labels)
        total = n * box_w + (n - 1) * gap
        x0 = 92 + (width - 92 - total) / 2
        out = [_txt(16, y + box_h / 2 + 3, label, size=10, weight="bold", fill=MID)]
        centers = []
        for i, lab in enumerate(labels):
            x = x0 + i * (box_w + gap)
            centers.append(x + box_w / 2)
            fill = INK if i == 0 else FAINT
            tfill = PAPER if i == 0 else INK
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{box_w}" height="{box_h}" '
                       f'fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
            out.append(_txt_wrap(x + box_w / 2, y + 14, lab, max(8, int(box_w / 6.5)), 11,
                                 size=9.5, anchor="middle", fill=tfill, weight="bold"))
            if i:
                out.append(_arrow(x - gap, y + box_h / 2, x, y + box_h / 2))
        return out, centers, x0, x0 + total

    body = []
    r1, _, s0, s1 = row(commodity, 22, "Commodity", 66, gap=12)
    body += r1
    body.append(_txt(s1, 68, "farmgate 50–65% of FOB", size=8.5, anchor="end", fill=MID))
    r2, c2, t0, t1 = row(specialty, 86, "Specialty", 92)
    body += r2

    # direct-trade bypass arc: farmer -> roaster, under the middle of the row
    fx, rx = c2[0], c2[-1]
    y_base = 86 + 34
    mx = (fx + rx) / 2
    depth = 22
    body.append(f'<path d="M {fx:.1f},{y_base} C {mx:.1f},{y_base + depth} '
                f'{mx:.1f},{y_base + depth} {rx - 6:.1f},{y_base}" fill="none" '
                f'stroke="{INK}" stroke-width="1.3" stroke-dasharray="4,3"/>')
    body.append(f'<polygon points="{rx - 6},{y_base - 3.6} {rx},{y_base} '
                f'{rx - 6},{y_base + 3.6}" fill="{INK}"/>')
    body.append(_txt(mx, y_base + depth + 12,
                     "direct trade: plot-level traceability, quality premiums, better farmgate terms",
                     size=9, anchor="middle", fill=MID))
    return _svg(width, 170, "".join(body))
