---
name: research-figures
description: How to build paper figures and paper-style (booktabs) tables as editable PPTX + PDF with figuretool.py — the JSON spec format, print sizes, style rules, and the build → preview → fix loop. Read this before running /research-figure or /research-table.
---

# Research Figures & Tables

Figures and tables are written as a **JSON spec**, built by `scripts/figuretool.py` into an editable `.pptx` (real PowerPoint shapes and tables, not a picture), a `.pdf` for LaTeX, and a `.png` preview. Keep the spec — later changes ("thicker arrows", "swap columns") are edits to the spec plus a rebuild.

Run: `python3 .claude/skills/research-figures/scripts/figuretool.py build <spec.json>` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run). `… check` tells you whether a PDF converter is available (PowerPoint on Windows, or LibreOffice).

## Build loop

1. Write the spec.
2. `build` it. It prints the `.pptx`, `.pdf` and `.png` paths, the canvas size, and `warning:` lines — fix every one before looking further:
   - **text that wraps or overflows** its box (widths come from Arial glyph metrics, so take them literally);
   - **elbow arrows** whose last segment is too short for the arrowhead, or with a diagonal segment;
   - **overlaps**: two shapes overlapping (a shape fully inside another — a panel or background — is fine), two pieces of text colliding, text crossing the edge of a shape, an arrow or line running through a shape or text it doesn't connect. Elements in a figure must not overlap unless that is the point (overlapping Gaussians, a splat drawn over a tile grid): mark those with `"overlap": true` on the element, or on a `group` / `repeat` to cover everything inside;
   - **canvas problems** when the size is fixed (content cut off, or unused margins).
3. **Read the `.png` preview** and check: text overflowing or clipped, overlapping elements, arrows that miss their targets, uneven spacing or misalignment, labels that are too small.
4. Fix the spec and rebuild — at most 3 rounds. Report anything you couldn't fix.

## Print sizes

Design at the size it will be printed, so font sizes are real.

| Use | Width |
| --- | --- |
| Single column (CVPR / ICCV / ECCV / NeurIPS-style two-column papers) | 3.25 in |
| Full width, two-column papers | 6.875 in |
| ACM (SIGGRAPH / TOG) single · double column | 3.33 in · 7.0 in |
| Single-column papers (NeurIPS, ICLR, ICML main text) | 5.5 in |

**Margins are minimal on all four sides.** With `"size": "auto"` (the default) the canvas is cropped to the ink — shapes, lines, arrowheads and the text itself, not oversized text boxes — plus `margin` (default 0.03 in) on every side, wherever the elements were placed. When the width must be exact (full width at 6.875 in), use `"size": [6.875, "auto"]`: the height is still cropped and the content is centered horizontally; a warning says if it is cut off or leaves wide side margins. `"size": [w, h]` fixes both.

PowerPoint can't store a slide under 1 in on a side, so a very small figure is saved proportionally enlarged; `build` then prints the real width to use in `\includegraphics`.

## Style rules

**Figures**
- Sans-serif text (`Arial`, the default), **at least 7 pt at print size**, 8–9 pt for main labels. One font throughout.
- A small, consistent palette — one color per concept, reused everywhere it appears. Light fills with a darker border of the same hue. Colorblind-safe pairs: blue `#2F5597` / orange `#C55A11` / green `#548235` / purple `#7030A0`; fills `#DCE8F5` / `#FBE5D6` / `#E2F0D9` / `#E8E0F0`; neutral `#F2F2F2` / `#404040`.
- No shadows, 3D effects, gradients or clip art. Thin lines (0.75–1 pt), arrows 1 pt.
- Read left → right (or top → bottom); align boxes on a grid; equal gaps.
- **Line breaks are yours.** Text never breaks a word, and a `text` element never wraps at all — it breaks only at `\n`. Put each `\n` where a reader would pause (`"appended to the keys / values\nof every attention layer"`), and make the box wide enough for the longest line.
- **Arrows.** Straight when the two ends line up; otherwise an orthogonal elbow — `via` points that share x or y with their neighbours, never a diagonal segment — drawn as one line that turns at a right angle and ends in the arrowhead. Keep the segment carrying the arrowhead at least 0.12 in long so the turn is visible, and end the tip on the target's edge (use an anchor like `"kc.bottom"`).
- **Sub-figure labels** `(a)`, `(b)`, …: give each panel its own `group` with `"label": "(a) Token positions from depth"`. The script centers the label **under** the panel and puts the labels of panels in the same row on one baseline. Use another position only with a concrete reason, and say it in the report — e.g. `"label_pos": "above"` when a shared legend or axis sits under the panels, or letters over the corner of photos in an image grid (place those as `text`). Keep labels short enough to fit under their panel; the long description belongs in the LaTeX caption.
- Every element earns its place — if the caption would explain it, the figure needs it; otherwise cut it.

**Tables** (booktabs)
- Serif text matching the paper body (`Times New Roman`), 8–9 pt.
- Heavy rule on top and bottom, light rule under the header, no vertical lines. Light `midrule` only to separate groups of rows (e.g. baselines vs. ours).
- Metric headers carry direction: `PSNR↑`, `LPIPS↓`.
- Per column: **best in bold**, __second best underlined__ — set `best` and let the script compute it rather than marking cells by hand (say so in a note if the paper doesn't already). Same number of decimals within a column — set `decimals`.
- Text column left-aligned, numbers centered (or right-aligned).
- Footnote markers in this order: `*`, `†`, `‡`, `§`, assigned by first appearance reading the table top to bottom, left to right — as superscripts on the cell (`Ours^{*}`), explained in `notes` in the same order.
- Missing values: `–`. Never invent a number.
- No caption by default — in a paper the caption is LaTeX. Add `caption` only if asked.

## Spec format

```json
{
  "size": "auto",            // or [width, "auto"] or [width, height] in inches
  "margin": 0.03,            // empty space kept on each side
  "font": "Arial",           // default font
  "fontsize": 8,             // default point size
  "elements": [ ... ]        // drawn in order; later elements are on top
}
```

The `//` comments above are explanations only — a real spec is plain JSON. Coordinates and sizes are in **inches** from the top-left corner.

**Text markup** (any `text`, table cells, notes): `**bold**`, `__underline__`, `*italic*`, `^{superscript}`, `_{subscript}`, `{size:10|larger text}`, `\n` for a new line.

| Element | Fields |
| --- | --- |
| `box` | `id`, `x`, `y`, `w`, `h`, `text`, `shape` (`rect` `round` `ellipse` `diamond` `parallelogram` `hexagon` `cylinder` `trapezoid` `triangle` `chevron` `pentagon`), `fill`, `fill_alpha` (0–1), `line` (color or `"none"`; default dark gray), `lw` (pt), `dash` (`solid` `dash` `dot` `dashdot`), `radius` (0–0.5, for `round`), `size`, `bold`, `italic`, `color`, `font`, `align` (`left` `center` `right`), `valign` (`top` `middle` `bottom`), `pad` (inner margin, default 0.04 in — lower it for narrow boxes), `rotate` (degrees) |
| `text` | same as `box`, no fill or border. Never wraps — lines break only at `\n` |
| `arrow` | `from`, `to` — `[x, y]` or `"<id>.left\|right\|top\|bottom\|center"` (add `@0.25` to pick a point along that side, 0–1), `via` (list of points for elbow arrows), `head` (`end` `start` `both` `none`), `color`, `lw`, `dash`, `label`, `label_offset` `[dx, dy]`, `label_size`, `label_w`, `label_h` |
| `line` | same as `arrow`, without arrowheads by default |
| `group` | `x`, `y`, `elements` — children use coordinates relative to the group (e.g. one panel of a multi-panel figure). `label` adds a sub-figure label centered under the panel (`label_pos` `"above"` to put it over it, `label_size`, `label_bold`, `label_gap` default 0.06 in) |
| `repeat` | `count`, `dx`, `dy`, `element` (or `elements`) — copy *k* is shifted by *k*·(`dx`, `dy`); `{i}` (from 0) and `{n}` (from 1) in any string are filled in, e.g. `"id": "pt{i}"`. Nest two repeats for a grid. |
| `image` | `path` (PNG / JPEG, relative to the spec), `x`, `y`, `w` and/or `h` (aspect kept if one is given), `id`, `line` |
| `table` | `x`, `y`, `columns`, `rows` (lists of cell strings, or the string `"midrule"`), `col_widths` (or `w`), `align` (per column: `l` `c` `r`), `header_groups` (`[{"text": "Mip-NeRF360", "span": [1, 3]}]` — column indices, 0-based, inclusive), `best` (per column `"max"`, `"min"` or `null` — the script bolds the best and underlines the second best, ties share the mark; cells you already marked are left alone), `second` (default `true`), `decimals` (per column, e.g. `[null, 2, 3]`), `notes` (lines under the table; several short notes can share a line), `font`, `size`, `row_h`, `bold_header`, `caption` |

An element's `id` can be used as an arrow anchor only after the element is defined. Any element, group or repeat takes `"overlap": true` to mark an intended overlap.

**Example — pipeline overview**

```json
{"font": "Arial", "fontsize": 8, "elements": [
  {"type": "box", "id": "in",  "x": 0.1, "y": 0.4, "w": 1.0, "h": 0.6, "text": "Input\nimages", "shape": "round", "fill": "#F2F2F2"},
  {"type": "box", "id": "enc", "x": 1.6, "y": 0.4, "w": 1.2, "h": 0.6, "text": "**Encoder**", "shape": "round", "fill": "#DCE8F5", "line": "#2F5597"},
  {"type": "arrow", "from": "in.right", "to": "enc.left"},
  {"type": "arrow", "from": "enc.bottom", "via": [[2.2, 1.3], [0.6, 1.3]], "to": "in.bottom", "dash": "dash", "label": "feedback", "label_offset": [0, 0.12]}
]}
```

**Example — two panels with sub-figure labels**

```json
{"size": [6.875, "auto"], "font": "Arial", "fontsize": 8, "elements": [
  {"type": "group", "x": 0, "y": 0, "label": "(a) Token positions from depth", "elements": [ ... ]},
  {"type": "group", "x": 2.5, "y": 0, "label": "(b) 3D RoPE attention with a camera token", "elements": [
    {"type": "box", "id": "cam", "x": 1.1, "y": 0.7, "w": 1.05, "h": 0.45, "text": "**Camera token**"},
    {"type": "box", "id": "kc", "x": 4.1, "y": 0.0, "w": 0.22, "h": 0.5, "fill": "#FBE5D6", "line": "#C55A11"},
    {"type": "arrow", "from": "cam.right", "via": [[4.21, 0.925]], "to": "kc.bottom", "color": "#C55A11"}
  ]}
]}
```

The elbow runs right from the camera token, turns up at x = 4.21 (the center of `kc`) and rises 0.43 in into `kc.bottom` — long enough for the line to show before the arrowhead. Both labels land centered under their panels, on one baseline.

**Example — results table**

```json
{"font": "Times New Roman", "fontsize": 8, "elements": [
  {"type": "table", "x": 0.05, "y": 0.05, "col_widths": [1.1, 0.55, 0.55, 0.55],
   "header_groups": [{"text": "Mip-NeRF360", "span": [1, 3]}],
   "columns": ["Method", "PSNR↑", "SSIM↑", "LPIPS↓"], "align": ["l", "c", "c", "c"],
   "rows": [["Mip-NeRF360", "**27.69**", "0.792", "0.237"], "midrule", ["Ours^{*}", "__27.21__", "**0.815**", "**0.214**"]],
   "notes": ["* Trained for 30K iterations."]}
]}
```

## Data plots

For a chart of numbers (bars, lines, scatter), draw it with matplotlib if it's installed: a short script under the output folder that saves a PNG at 300 dpi at the print size, then place it with an `image` element (add titles or callouts as `text` elements if useful). Without matplotlib, simple bar charts can be drawn with `box` elements. Plotted numbers follow the same rule as tables: only data the user gave or numbers verified from a paper, with the source noted.
