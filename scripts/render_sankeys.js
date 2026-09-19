#!/usr/bin/env bun
/**
 * Sankey renderer for the OpenWiki deep-dive EPUB (sketch-planations style).
 * Previously d3-sankey based; now uses a small hand-rolled one-stage layout
 * so thin bands fan out cleanly instead of braiding at the source edge.
 *
 * Input:  argv[2] = job JSON  { "<origin>": [ {node, lo, hi, mid, qual}, ... ] }
 *         argv[3] = output directory (one "<origin>.svg" per entry)
 *
 * Design (B&W / e-ink safe, 640px viewBox, sketch-style):
 *  - light outlined source block with rotated caption (sketch-style)
 *  - ribbons drawn as closed, slightly tapered arrow shapes with bold ink
 *    outlines and generous S-curves; width (mid taper) encodes the share
 *  - dominant band = flat warm gray; secondary bands carry distinct light
 *    hatch / lattice / dot textures (pattern encoding, not color)
 *  - thick bands carry their label directly on the flat fill; patterned bands
 *    that must hold text get a small white plaque; thin bands get margin
 *    labels keyed by tone swatches, connected via a shared leader rail
 *  - exact percentage ranges appear verbatim on or next to every ribbon
 *  - grayscale only, no transparency tricks, strict XML output
 *
 * Graceful degradation: the Python converter falls back to its built-in
 * SVG generator when bun or this script is unavailable.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const [jobPath, outDir] = process.argv.slice(2);
if (!jobPath || !outDir) {
  console.error("usage: bun render_sankeys.js <job.json> <out-dir>");
  process.exit(2);
}
const job = JSON.parse(readFileSync(jobPath, "utf8"));
mkdirSync(outDir, { recursive: true });

const INK = "#241d18";
const MID = "#7d6f61";
const BLOCK = "#e9e1d7"; // source block fill
const FLAT = "#ddd3c7";  // dominant band fill
const PAT_BG = "#f1ebe2"; // texture tile background
const SERIF = "Georgia, 'Times New Roman', serif";
const SANS = "Helvetica, Arial, sans-serif";

// texture per secondary band (index 1..): diagonal hatch, lattice, dots
const PATS = [
  { id: "hx1", line: "#a5977f" },
  { id: "hx2", line: "#9a8b74" },
  { id: "hxd", line: "#a08f77" },
];

const esc = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const fmt = (v) => (Math.round(v * 100) / 100).toString();
const pct = (v) => (Number.isInteger(v) ? `${v}%` : `${v.toFixed(1).replace(/\.0$/, "")}%`);
const rng = (r) => (r.hi !== r.lo ? `${pct(r.lo)}\u2013${pct(r.hi)}` : pct(r.lo));

function wrap(text, max) {
  const lines = [];
  let cur = [];
  for (const word of String(text).split(/\s+/)) {
    if (cur.length && (cur.join(" ") + " " + word).length > max) {
      lines.push(cur.join(" "));
      cur = [];
    }
    cur.push(word);
  }
  if (cur.length) lines.push(cur.join(" "));
  return lines;
}

function textEl(x, y, s, o = {}) {
  const { size = 11, anchor = "start", fill = INK, weight = "normal",
          family = SERIF, italic = false, spacing = null } = o;
  return (`<text x="${fmt(x)}" y="${fmt(y)}" font-family="${family}" font-size="${size}"` +
          ` text-anchor="${anchor}" fill="${fill}" font-weight="${weight}"` +
          (italic ? ` font-style="italic"` : "") +
          (spacing ? ` letter-spacing="${spacing}"` : "") + `>${esc(s)}</text>`);
}

// generous advance-width estimates (px per char) for wrapping/fit decisions
const CHAR_W = {
  serifItalic: { 11: 6.2, 10: 5.6, 9: 5.1 },
  sansBold: { 11: 6.8, 10: 6.3, 9: 5.7 },
  sans: { 9: 5.1 },
};
function textWidth(s, kind, size) {
  const table = CHAR_W[kind] || CHAR_W.serifItalic;
  return String(s).length * (table[size] || table[10] || 5);
}

/**
 * Closed sketch-style arrow ribbon: starts `w0` tall at the source edge,
 * arrives `w1` tall after a generous S-curve, and finishes in a triangular
 * arrowhead proportional to the band. Returns an SVG path string.
 */
function arrowRibbon(x0, y0c, w0, x1, y1c, w1) {
  const h0 = w0 / 2, h1 = w1 / 2;
  const k = 0.58; // curve swing
  const cx1 = x0 + k * (x1 - x0), cx2 = x1 - k * (x1 - x0);
  const L = Math.min(22, 9 + w1 * 0.09); // head length
  const hw = h1 + 3;                     // head half-height
  return (
    `M${fmt(x0)},${fmt(y0c - h0)}` +
    `C${fmt(cx1)},${fmt(y0c - h0)} ${fmt(cx2)},${fmt(y1c - h1)} ${fmt(x1)},${fmt(y1c - h1)}` +
    `L${fmt(x1 + L)},${fmt(y1c)}` +
    `L${fmt(x1)},${fmt(y1c + h1)}` +
    `C${fmt(cx2)},${fmt(y1c + h1)} ${fmt(cx1)},${fmt(y0c + h0)} ${fmt(x0)},${fmt(y0c + h0)}Z`
  );
}

function sankeyFor(origin, rows) {
  const top = 24, flowH = 232, W = 640;
  const X0 = 49, X1 = 450;      // ribbon span (arrowheads reach ~X1+22)
  const ELBOW = 484;            // leader rail x
  const SWX = 494;              // swatch x
  const TX = 508;               // margin text x

  // Hand-rolled one-stage layout. ONE common scale for both sides: the
  // source block is 100% = flowH tall. Ribbon shares are the range midpoints
  // NORMALIZED to sum to exactly 100 (the report's indicative ranges sum to
  // ~93–96%), so the flush source-side stack tiles the block perfectly and
  // 50% on the left is exactly as tall as 50% on the right. Head-side gaps
  // between arrows are pure spacing and never absorbed into the scale.
  const n = rows.length;
  const total = rows.reduce((a, r) => a + Math.max(r.mid, 0.01), 0);
  const K = flowH / 100;
  const share = (r) => (Math.max(r.mid, 0.01) / total) * 100; // normalized %
  const gT = 13;

  const defs =
    `<defs>` +
    PATS.map((p, i) => {
      // every tile carries a solid light base so no dark ink shows through
      if (p.id === "hxd") {
        return (`<pattern id="${p.id}" width="7" height="7" patternUnits="userSpaceOnUse">` +
                `<rect width="7" height="7" fill="${PAT_BG}"/>` +
                `<circle cx="2.2" cy="2.2" r="1" fill="${p.line}"/>` +
                `<circle cx="5.7" cy="5.7" r="1" fill="${p.line}"/></pattern>`);
      }
      if (p.id === "hx2") {
        // diamond lattice: two crossing lines per tile, clearly distinct
        return (`<pattern id="${p.id}" width="7" height="7" patternUnits="userSpaceOnUse"` +
                ` patternTransform="rotate(45)">` +
                `<rect width="7" height="7" fill="${PAT_BG}"/>` +
                `<line x1="0" y1="0" x2="0" y2="7" stroke="${p.line}" stroke-width="0.9"/>` +
                `<line x1="0" y1="0" x2="7" y2="0" stroke="${p.line}" stroke-width="0.9"/></pattern>`);
      }
      return (`<pattern id="${p.id}" width="7" height="7" patternUnits="userSpaceOnUse"` +
              ` patternTransform="rotate(45)">` +
              `<rect width="7" height="7" fill="${PAT_BG}"/>` +
              `<line x1="0" y1="0" x2="0" y2="7" stroke="${p.line}" stroke-width="1"/></pattern>`);
    }).join("") +
    `</defs>`;

  const parts = [];

  // ---- source block, sketch-style: light fill, bold outline, vertical caption
  const srcH = flowH;
  parts.push(`<rect x="30" y="${top}" width="17" height="${fmt(srcH)}" rx="3"` +
             ` fill="${BLOCK}" stroke="${INK}" stroke-width="1.8"/>`);
  const cy = top + srcH / 2;
  parts.push(`<text x="38.5" y="${fmt(cy)}" transform="rotate(-90 38.5 ${fmt(cy)})"` +
             ` font-family="${SANS}" font-size="9.5" font-weight="bold" letter-spacing="1.4"` +
             ` text-anchor="middle" fill="${INK}">FOB EXPORT PRICE = 100%</text>`);

  const margin = []; // { y0, tone, nameLines, rangeStr, qualLines }
  let sy = top, ty = top;
  rows.forEach((r, i) => {
    const w = share(r) * K; // identical on both ends — no taper, flush at source
    const y0c = sy + w / 2, y1c = ty + w / 2;
    sy += w; ty += w + gT;
    const x0 = X0, x1 = X1;
    const flat = i === 0;
    const tone = flat ? FLAT : `url(#${PATS[(i - 1) % PATS.length].id})`;
    const qual = r.qual ? String(r.qual) : "";

    if (w <= 0.4) { // degenerate band -> margin label only
      margin.push({ y0: y1c, tipX: X1 + 2, tone, nameLines: wrap(r.node, 22), rangeStr: rng(r), qualLines: qual ? wrap(qual, 26) : [] });
      return;
    }

    // sketch-style arrow ribbon with bold ink outline (constant width)
    parts.push(`<path d="${arrowRibbon(x0, y0c, w, x1, y1c, w)}" fill="${tone}"` +
               ` stroke="${INK}" stroke-width="1.6" stroke-linejoin="round"/>`);

    // label placement
    const nameLines = wrap(r.node, 20);
    const rangeStr = rng(r);
    const qualLines = qual ? wrap(qual, 26) : [];
    const n = nameLines.length, q = qualLines.length;
    const labelH = 14 + n * 13 + 11 + q * 10;
    const labelW = Math.max(
      ...nameLines.map((s) => textWidth(s, "serifItalic", 11)),
      textWidth(rangeStr, "sansBold", 11),
      ...qualLines.map((s) => textWidth(s, "sans", 9))
    );
    const cxm = (x0 + x1) / 2;
    if (flat && labelH <= w - 8 && labelW <= x1 - x0 - 14) {
      // direct on the flat band, sketch-style
      let ty = y1c - labelH / 2 + 18;
      for (const ln of nameLines) {
        parts.push(textEl(cxm, ty, ln, { size: 11, anchor: "middle", italic: true }));
        ty += 13;
      }
      parts.push(textEl(cxm, ty, rangeStr, { size: 11, anchor: "middle", weight: "bold", family: SANS }));
      ty += 11;
      for (const ln of qualLines) {
        parts.push(textEl(cxm, ty, ln, { size: 9, anchor: "middle", family: SANS, fill: MID }));
        ty += 10;
      }
    } else if (labelH <= w - 8 && labelW <= x1 - x0 - 14) {
      // patterned band: white plaque keeps text legible over the texture
      const pw = labelW + 20, ph = labelH + 6;
      const px = cxm - pw / 2, py = y1c - ph / 2;
      parts.push(`<rect x="${fmt(px)}" y="${fmt(py)}" width="${fmt(pw)}" height="${fmt(ph)}"` +
                 ` rx="3" fill="${PAT_BG}" stroke="${INK}" stroke-width="0.8"/>`);
      let ty = py + 18;
      for (const ln of nameLines) {
        parts.push(textEl(cxm, ty, ln, { size: 11, anchor: "middle", italic: true }));
        ty += 13;
      }
      parts.push(textEl(cxm, ty, rangeStr, { size: 11, anchor: "middle", weight: "bold", family: SANS }));
      ty += 11;
      for (const ln of qualLines) {
        parts.push(textEl(cxm, ty, ln, { size: 9, anchor: "middle", family: SANS, fill: MID }));
        ty += 10;
      }
    } else {
      margin.push({ y0: y1c, tipX: X1 + Math.min(22, 9 + w * 0.09), tone, nameLines, rangeStr, qualLines });
    }
  });

  // ---- margin labels: swatch-keyed blocks beside the arrow tips
  const GAP = 7;
  const blocks = margin.map((m) => {
    const h = m.nameLines.length * 12 + 12 + m.qualLines.length * 10.5 + 3;
    return { ...m, h };
  });
  let cursor = top + 4;
  for (const b of blocks) {
    const want = Math.max(b.y0, cursor + b.h / 2);
    b.cy = want;
    cursor = want + b.h / 2 + GAP;
  }
  if (blocks.length) {
    const ys = blocks.flatMap((b) => [b.y0, b.cy]);
    const railTop = Math.min(...ys), railBot = Math.max(...ys);
    if (railBot - railTop > 2)
      parts.push(`<line x1="${ELBOW}" y1="${fmt(railTop)}" x2="${ELBOW}" y2="${fmt(railBot)}"` +
                 ` stroke="${MID}" stroke-width="0.8"/>`);
    for (const b of blocks) {
      parts.push(`<line x1="${fmt(b.tipX + 2)}" y1="${fmt(b.y0)}" x2="${ELBOW}" y2="${fmt(b.y0)}"` +
                 ` stroke="${MID}" stroke-width="0.8"/>`);
      parts.push(`<line x1="${ELBOW}" y1="${fmt(b.cy)}" x2="${SWX - 3}" y2="${fmt(b.cy)}"` +
                 ` stroke="${MID}" stroke-width="0.8"/>`);
      parts.push(`<rect x="${SWX}" y="${fmt(b.cy - 4.5)}" width="9" height="9" fill="${b.tone}"` +
                 ` stroke="${INK}" stroke-width="0.8"/>`);
      let ty = b.cy - b.h / 2 + 10;
      for (const ln of b.nameLines) {
        parts.push(textEl(TX, ty, ln, { size: 10, italic: true }));
        ty += 12;
      }
      parts.push(textEl(TX, ty, b.rangeStr, { size: 10, weight: "bold", family: SANS }));
      ty += 12;
      for (const ln of b.qualLines) {
        parts.push(textEl(TX, ty, ln, { size: 8.5, italic: true, fill: MID }));
        ty += 10.5;
      }
    }
  }

  const floor = blocks.length ? blocks[blocks.length - 1].cy + blocks[blocks.length - 1].h / 2 : top + flowH;
  const height = Math.max(top + flowH, floor) + 10;
  return (`<?xml version="1.0" encoding="UTF-8"?>\n` +
          `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${fmt(height)}"` +
          ` width="${W}" height="${fmt(height)}" role="img">` +
          defs + parts.join("") + `</svg>`);
}

for (const [origin, rows] of Object.entries(job)) {
  if (!rows?.length) continue;
  try {
    writeFileSync(join(outDir, `${origin}.svg`), sankeyFor(origin, rows));
  } catch (err) {
    console.error(`skipped ${origin}: ${err?.message || err}`);
  }
}
console.log(`rendered ${Object.keys(job).length} sankey diagrams`);
