#!/usr/bin/env python3
"""Paper figures and tables as editable PPTX + PDF. Python 3 standard library only.

    figuretool.py build <spec.json> [--out BASENAME] [--no-pdf]
        spec -> BASENAME.pptx, BASENAME.pdf and BASENAME.png (preview)
    figuretool.py check
        which PDF converter is available (PowerPoint on Windows / macOS, or LibreOffice)

The spec format is described in the research-figures skill (SKILL.md). Units are inches.
Errors print one "ERROR: ..." line and exit 1.
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from xml.sax.saxutils import escape

EMU = 914400  # per inch
NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
SHAPES = {"rect": "rect", "round": "roundRect", "ellipse": "ellipse", "diamond": "diamond",
          "trapezoid": "trapezoid", "triangle": "triangle", "chevron": "chevron", "pentagon": "homePlate",
          "parallelogram": "parallelogram", "hexagon": "hexagon", "cylinder": "can", "none": "rect"}
DASH = {"solid": None, "dash": "dash", "dot": "sysDot", "dashdot": "dashDot"}


def die(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def emu(v):
    return int(round(float(v) * EMU))


def hexcolor(c, default="000000"):
    c = (c or default).lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", c):
        die("bad color: %r (use #RRGGBB)" % c)
    return c.upper()


# ------------------------------------------------------------------ text

RUN = re.compile(r"(\{size:[0-9.]+\|.+?\}|\*\*.+?\*\*|__.+?__|\^\{.+?\}|_\{.+?\}|\*[^*\s][^*]*?\*)")


def runs_xml(text, size, color, bold=False, italic=False, font=None):
    """Inline markup: **bold**, __underline__, *italic*, ^{superscript}, _{subscript}, {size:11|bigger}."""
    out = []
    for part in RUN.split(text):
        if not part:
            continue
        b, i, u, base, sz = bold, italic, False, 0, size
        ms = re.fullmatch(r"\{size:([0-9.]+)\|(.+)\}", part)
        if ms:
            sz, part = float(ms.group(1)), ms.group(2)
            out.append(runs_xml(part, sz, color, bold, italic, font))
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            part, b = part[2:-2], True
        elif part.startswith("__") and part.endswith("__") and len(part) > 4:
            part, u = part[2:-2], True
        elif part.startswith("^{") and part.endswith("}"):
            part, base = part[2:-1], 30000
        elif part.startswith("_{") and part.endswith("}"):
            part, base = part[2:-1], -25000
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, i = part[1:-1], True
        attrs = 'lang="en-US" sz="%d" b="%d" i="%d"' % (int(size * 100), b, i)
        if u:
            attrs += ' u="sng"'
        if base:
            attrs += ' baseline="%d"' % base
        f = ('<a:latin typeface="%s"/><a:ea typeface="%s"/><a:cs typeface="%s"/>' % ((escape(font),) * 3)) if font else ""
        out.append('<a:r><a:rPr %s dirty="0"><a:solidFill><a:srgbClr val="%s"/></a:solidFill>%s</a:rPr>'
                   '<a:t>%s</a:t></a:r>' % (attrs, color, f, escape(part)))
    return "".join(out)


def paragraphs_xml(text, size, color, align="ctr", bold=False, italic=False, font=None, spacing=None):
    algn = {"left": "l", "l": "l", "center": "ctr", "c": "ctr", "ctr": "ctr", "right": "r", "r": "r"}.get(align, "ctr")
    sp = '<a:lnSpc><a:spcPct val="%d"/></a:lnSpc>' % int(spacing * 100000) if spacing else ""
    paras = []
    for line in str(text).split("\n"):
        paras.append('<a:p><a:pPr algn="%s">%s</a:pPr>%s<a:endParaRPr lang="en-US" sz="%d"/></a:p>'
                     % (algn, sp, runs_xml(line, size, color, bold, italic, font), int(size * 100)))
    return "".join(paras)


# ------------------------------------------------------------------ shapes

class Slide:
    def __init__(self, spec):
        self.spec = spec
        self.font = spec.get("font", "Arial")
        self.size = float(spec.get("fontsize", 9))
        self.items, self.boxes, self.images, self.nid = [], {}, [], 2
        self.extent = [0.0, 0.0]  # right-most x, bottom-most y — for "size": "auto"
        self.warnings = []

    def grow(self, x2, y2):
        self.extent = [max(self.extent[0], x2), max(self.extent[1], y2)]

    def next_id(self):
        self.nid += 1
        return self.nid

    def anchor(self, ref):
        """[x, y] or "id.side" with side in left/right/top/bottom/center (+ optional offset like right+0.1)."""
        if isinstance(ref, (list, tuple)):
            return float(ref[0]), float(ref[1])
        m = re.fullmatch(r"([\w-]+)\.(left|right|top|bottom|center)(?:@([0-9.]+))?", str(ref))
        if not m or m.group(1) not in self.boxes:
            die("unknown anchor %r — use [x, y] or '<id>.left|right|top|bottom|center' of an earlier element" % ref)
        x, y, w, h = self.boxes[m.group(1)]
        t = float(m.group(3)) if m.group(3) else 0.5  # position along the side, 0..1
        return {"left": (x, y + h * t), "right": (x + w, y + h * t), "top": (x + w * t, y),
                "bottom": (x + w * t, y + h), "center": (x + w / 2, y + h / 2)}[m.group(2)]

    def line_xml(self, color, lw, dash, head_start=None, head_end=None):
        if color is None:
            return "<a:ln><a:noFill/></a:ln>"
        d = '<a:prstDash val="%s"/>' % DASH[dash] if DASH.get(dash) else ""
        hs = '<a:headEnd type="%s" w="med" len="med"/>' % head_start if head_start else ""
        he = '<a:tailEnd type="%s" w="med" len="med"/>' % head_end if head_end else ""
        return '<a:ln w="%d"><a:solidFill><a:srgbClr val="%s"/></a:solidFill>%s<a:round/>%s%s</a:ln>' % (
            int(float(lw) * 12700), hexcolor(color), d, hs, he)

    def box(self, e, text_only=False):
        x, y, w, h = (float(e[k]) for k in ("x", "y", "w", "h"))
        if e.get("id"):
            self.boxes[e["id"]] = (x, y, w, h)
        self.grow(x + w, y + h)
        geom = SHAPES.get(e.get("shape", "rect"))
        if geom is None:
            die("unknown shape %r (use %s)" % (e.get("shape"), ", ".join(SHAPES)))
        fill = e.get("fill")
        alpha = '<a:alpha val="%d"/>' % int(float(e["fill_alpha"]) * 100000) if "fill_alpha" in e else ""
        fill_xml = '<a:solidFill><a:srgbClr val="%s">%s</a:srgbClr></a:solidFill>' % (hexcolor(fill), alpha) if fill and not text_only else "<a:noFill/>"
        if text_only:
            border = None
        elif "line" in e:
            border = None if e["line"] in (None, "none") else e["line"]
        else:
            border = "#404040"
        ln = self.line_xml(border, e.get("lw", 0.75), e.get("dash", "solid"))
        adj = '<a:avLst><a:gd name="adj" fmla="val %d"/></a:avLst>' % int(float(e["radius"]) * 100000) \
            if geom == "roundRect" and "radius" in e else "<a:avLst/>"
        rot = ' rot="%d"' % int(float(e["rotate"]) * 60000) if e.get("rotate") else ""
        va = {"top": "t", "middle": "ctr", "center": "ctr", "bottom": "b"}.get(e.get("valign", "middle"), "ctr")
        inset = emu(e.get("pad", 0.04))
        text = e.get("text", "")
        body = paragraphs_xml(text, float(e.get("size", self.size)), hexcolor(e.get("color"), "000000"),
                              e.get("align", "center"), e.get("bold", False), e.get("italic", False),
                              e.get("font", self.font), e.get("spacing"))
        self.check_fit(e, text, w, h, text_only)
        sid = self.next_id()
        self.items.append(
            '<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm%s><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="%s">%s</a:prstGeom>%s%s</p:spPr>'
            '<p:txBody><a:bodyPr wrap="square" lIns="%d" tIns="%d" rIns="%d" bIns="%d" anchor="%s" rtlCol="0">'
            '<a:noAutofit/></a:bodyPr><a:lstStyle/>%s</p:txBody></p:sp>' % (
                sid, escape(e.get("id", "Shape %d" % sid)), rot, emu(x), emu(y), emu(w), emu(h), geom, adj,
                fill_xml, ln, inset, inset, inset, inset, va, body))

    def check_fit(self, e, text, w, h, text_only):
        """Rough text-fit estimate — warns before the preview has to show it. Errs on the quiet side:
        average glyph ~0.48 em; flags only clear overruns."""
        if not text or e.get("_internal"):
            return
        size = float(e.get("size", self.size))
        pad = float(e.get("pad", 0.04))
        lines = [MARKUP_ALL.sub(lambda m: next((g for g in m.groups() if g), ""), l)
                 for l in str(text).split("\n")]
        widest = max(len(l) for l in lines) * size * 0.48 / 72
        tall = len(lines) * size * 1.2 / 72
        name = e.get("id") or (lines[0][:24] + "…")
        if widest > (w - 2 * pad) * 1.1:
            self.warnings.append("%s: text ~%.2f in wide in a %.2f in box — likely wraps (widen, shrink size, or reduce pad)" % (name, widest, w - 2 * pad))
        if not text_only and len(lines) > 1 and tall > (h - 2 * pad) * 1.1:
            self.warnings.append("%s: %d lines need ~%.2f in, box is %.2f in tall — likely overflows" % (name, len(lines), tall, h - 2 * pad))

    def segment(self, p1, p2, e, head_start=None, head_end=None):
        (x1, y1), (x2, y2) = p1, p2
        self.grow(max(x1, x2), max(y1, y2))
        flip = (' flipH="1"' if x2 < x1 else "") + (' flipV="1"' if y2 < y1 else "")
        sid = self.next_id()
        self.items.append(
            '<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="%d" name="Line %d"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
            '<p:spPr><a:xfrm%s><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="line"><a:avLst/></a:prstGeom>%s</p:spPr></p:cxnSp>' % (
                sid, sid, flip, emu(min(x1, x2)), emu(min(y1, y2)), emu(abs(x2 - x1)), emu(abs(y2 - y1)),
                self.line_xml(e.get("color", "#333333"), e.get("lw", 1), e.get("dash", "solid"), head_start, head_end)))

    def arrow(self, e):
        pts = [self.anchor(e["from"])] + [self.anchor(p) for p in e.get("via", [])] + [self.anchor(e["to"])]
        head = e.get("head", "end")
        kind = "triangle"
        for i in range(len(pts) - 1):
            first, last = i == 0, i == len(pts) - 2
            self.segment(pts[i], pts[i + 1], e,
                         kind if first and head in ("start", "both") else None,
                         kind if last and head in ("end", "both") else None)
        if e.get("label"):
            (x1, y1), (x2, y2) = pts[len(pts) // 2 - 1 if len(pts) > 2 else 0], pts[len(pts) // 2 if len(pts) > 2 else 1]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            lw, lh = float(e.get("label_w", 1.0)), float(e.get("label_h", 0.2))
            dx, dy = e.get("label_offset", [0, -0.12])
            self.box({"x": mx - lw / 2 + dx, "y": my - lh / 2 + dy, "w": lw, "h": lh, "text": e["label"],
                      "size": e.get("label_size", self.size - 1), "italic": e.get("label_italic", False),
                      "color": e.get("label_color", "#333333")}, text_only=True)

    def image(self, e, base_dir):
        path = os.path.join(base_dir, e["path"]) if not os.path.isabs(e["path"]) else e["path"]
        if not os.path.isfile(path):
            die("image not found: " + path)
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext not in ("png", "jpg", "jpeg"):
            die("images must be PNG or JPEG: " + path)
        x, y = float(e["x"]), float(e["y"])
        w, h = e.get("w"), e.get("h")
        if w is None or h is None:
            pw, ph = image_size(path)
            if w is None and h is None:
                die("image needs w or h: " + path)
            w = float(w) if w is not None else float(h) * pw / ph
            h = float(h) if h is not None else float(w) * ph / pw
        if e.get("id"):
            self.boxes[e["id"]] = (x, y, float(w), float(h))
        self.grow(x + float(w), y + float(h))
        rid = "rIdImg%d" % (len(self.images) + 1)
        self.images.append((rid, path, "jpeg" if ext == "jpg" else ext))
        sid = self.next_id()
        self.items.append(
            '<p:pic><p:nvPicPr><p:cNvPr id="%d" name="Picture %d"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            '<p:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>%s</p:spPr></p:pic>'
            % (sid, sid, rid, emu(x), emu(y), emu(w), emu(h),
               self.line_xml(e.get("line"), e.get("lw", 0.5), "solid") if e.get("line") else ""))

    # -------------------------------------------------------------- table

    def table(self, e):
        """Paper-style (booktabs) table: top/bottom rules, a rule under the header, no vertical lines."""
        cols = e["columns"]
        n = len(cols)
        rows = e.get("rows", [])
        font = e.get("font", self.font)
        size = float(e.get("size", self.size))
        x, y = float(e.get("x", 0)), float(e.get("y", 0))
        widths = [float(v) for v in e.get("col_widths", [])] or [float(e.get("w", 3.25)) / n] * n
        if len(widths) != n:
            die("col_widths must have one entry per column (%d)" % n)
        align = e.get("align") or (["l"] + ["c"] * (n - 1))
        row_h = float(e.get("row_h", size / 72 * 1.75))
        heavy, light = float(e.get("heavy", 1.0)), float(e.get("light", 0.5))

        grid = []  # (cells, kind) — kind: group | header | body ; cells = [(text, span, align)]
        if e.get("header_groups"):
            cells, col = [], 0
            for g in sorted(e["header_groups"], key=lambda g: g["span"][0]):
                a0, a1 = g["span"]
                while col < a0:
                    cells.append(("", 1, "c")); col += 1
                cells.append((g["text"], a1 - a0 + 1, "c")); col = a1 + 1
            while col < n:
                cells.append(("", 1, "c")); col += 1
            grid.append((cells, "group"))
        grid.append(([(c, 1, align[i]) for i, c in enumerate(cols)], "header"))
        body_rows = [r for r in rows if not (r == "midrule" or isinstance(r, dict))]
        for r in body_rows:
            if len(r) != n:
                die("row has %d cells, expected %d: %r" % (len(r), n, r))
        body_rows = mark_best(format_decimals([[str(c) for c in r] for r in body_rows], e.get("decimals")),
                              e.get("best"), e.get("second", True))
        mid_after, it = set(), iter(body_rows)
        for r in rows:
            if r == "midrule" or (isinstance(r, dict) and r.get("rule")):
                mid_after.add(len(grid) - 1)
                continue
            grid.append(([(c, 1, align[i]) for i, c in enumerate(next(it))], "body"))
        header_last = 1 if e.get("header_groups") else 0

        def border(side, w):
            tag = {"top": "lnT", "bottom": "lnB", "left": "lnL", "right": "lnR"}[side]
            if not w:
                return "<a:%s w=\"0\"><a:noFill/></a:%s>" % (tag, tag)
            return '<a:%s w="%d"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:%s>' % (tag, int(w * 12700), tag)

        group_spans = []
        if e.get("header_groups"):
            group_spans = [tuple(g["span"]) for g in e["header_groups"] if g.get("rule", True)]
        trs = []
        for ri, (cells, kind) in enumerate(grid):
            tcs, col = [], 0
            for text, span, al in cells:
                for k in range(span):
                    c = col + k
                    top = heavy if ri == 0 else 0
                    bottom = 0
                    if ri == header_last:
                        bottom = light
                    if ri in mid_after:
                        bottom = light
                    if ri == len(grid) - 1:
                        bottom = heavy
                    lr = 0
                    # Group headers are not merged: PowerPoint draws a merged cell's border under its first
                    # column only. The rule goes on every spanned cell and the label is overlaid afterwards.
                    span_attr = ""
                    bold = kind in ("header", "group") and e.get("bold_header", False)
                    body = paragraphs_xml("" if kind == "group" else text, size, "000000", al, bold, False, font)
                    tcs.append('<a:tc%s><a:txBody><a:bodyPr/><a:lstStyle/>%s</a:txBody>'
                               '<a:tcPr marL="%d" marR="%d" marT="%d" marB="%d" anchor="ctr">%s%s%s%s<a:noFill/></a:tcPr></a:tc>'
                               % (span_attr, body, emu(0.04), emu(0.04), emu(0.01), emu(0.01),
                                  border("left", lr), border("right", lr), border("top", top), border("bottom", bottom)))
                col += span
            trs.append('<a:tr h="%d">%s</a:tr>' % (emu(row_h), "".join(tcs)))
        total_w, total_h = sum(widths), row_h * len(grid)
        self.grow(x + total_w, y + total_h)
        if e.get("id"):
            self.boxes[e["id"]] = (x, y, total_w, total_h)
        sid = self.next_id()
        self.items.append(
            '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="%d" name="Table %d"/><p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
            '<p:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></p:xfrm>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
            '<a:tbl><a:tblPr firstRow="0" bandRow="0"/><a:tblGrid>%s</a:tblGrid>%s</a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
            % (sid, sid, emu(x), emu(y), emu(total_w), emu(total_h),
               "".join('<a:gridCol w="%d"/>' % emu(w) for w in widths), "".join(trs)))
        if e.get("header_groups"):
            trim = 0.04  # like booktabs \cmidrule(lr): a gap between neighbouring group rules
            for g in e["header_groups"]:
                a0, a1 = g["span"]
                gx, gw = x + sum(widths[:a0]), sum(widths[a0:a1 + 1])
                self.box({"x": gx, "y": y, "w": gw, "h": row_h, "text": g["text"], "size": size,
                          "font": font, "bold": e.get("bold_header", False), "pad": 0.01, "_internal": True}, text_only=True)
                if g.get("rule", True):
                    self.segment((gx + trim, y + row_h), (gx + gw - trim, y + row_h),
                                 {"color": "#000000", "lw": light})
        ny = y + total_h + 0.04
        if e.get("caption"):
            # Papers put table captions above; the caption box is placed above the table.
            ch = float(e.get("caption_h", 0.3))
            self.box({"x": x, "y": y - ch - 0.04, "w": total_w, "h": ch, "text": e["caption"], "size": size,
                      "font": font, "align": "left", "valign": "bottom", "_internal": True}, text_only=True)
        for note in e.get("notes", []):
            nh = float(e.get("note_h", (size - 1) / 72 * 1.5))
            self.box({"x": x, "y": ny, "w": total_w, "h": nh, "text": note, "size": float(e.get("note_size", size - 1)),
                      "font": font, "align": "left", "valign": "top", "pad": 0.02, "_internal": True}, text_only=True)
            ny += nh

    def xml(self):
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld %s><p:cSld><p:spTree>'
                '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
                '%s</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>' % (NS, "".join(self.items)))


NUM = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?)")
MARKUP = re.compile(r"\*\*|__|\^\{[^}]*\}|_\{[^}]*\}")
MARKUP_ALL = re.compile(r"\{size:[0-9.]+\|([^}]*)\}|\*\*|__|\^\{([^}]*)\}|_\{([^}]*)\}|\*")


def cell_value(text):
    m = NUM.match(MARKUP.sub("", text))
    return float(m.group(1)) if m else None


def format_decimals(rows, decimals):
    """Round plain numeric cells to a fixed number of decimals per column (null = leave as is)."""
    if not decimals:
        return rows
    out = []
    for r in rows:
        row = list(r)
        for c, d in enumerate(decimals):
            if d is None or c >= len(row):
                continue
            m = re.fullmatch(r"\s*([-+]?\d+(?:\.\d+)?)(.*)", row[c])
            if m:
                row[c] = ("%." + str(int(d)) + "f") % float(m.group(1)) + m.group(2)
        out.append(row)
    return out


def mark_best(rows, best, second=True):
    """best: per column "max", "min" or null. Bolds the best value and underlines the second best
    (ties share the mark). Cells that already carry ** or __ are left alone."""
    if not best:
        return rows
    rows = [list(r) for r in rows]
    for c, how in enumerate(best):
        if how not in ("max", "min"):
            continue
        vals = sorted({v for v in (cell_value(r[c]) for r in rows) if v is not None}, reverse=(how == "max"))
        marks = {vals[0]: "**"} if vals else {}
        if second and len(vals) > 1:
            marks[vals[1]] = "__"
        for r in rows:
            v = cell_value(r[c])
            if v in marks and "**" not in r[c] and "__" not in r[c]:
                m = re.match(r"([-+]?\d+(?:\.\d+)?)(.*)", r[c].strip())
                r[c] = marks[v] + m.group(1) + marks[v] + m.group(2) if m else r[c]
    return rows


def image_size(path):
    with open(path, "rb") as f:
        head = f.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        f.seek(2)
        while True:
            marker, = struct.unpack(">H", f.read(2))
            length, = struct.unpack(">H", f.read(2))
            if marker in (0xFFC0, 0xFFC1, 0xFFC2):
                f.read(1)
                h, w = struct.unpack(">HH", f.read(4))
                return w, h
            f.seek(length - 2, 1)


# ------------------------------------------------------------------ package

THEME = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Paper">'
         '<a:themeElements><a:clrScheme name="Paper"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
         '<a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F3F4F6"/></a:lt2>'
         + "".join('<a:accent%d><a:srgbClr val="%s"/></a:accent%d>' % (i, c, i) for i, c in
                   enumerate(["2F5597", "C55A11", "548235", "7030A0", "BF9000", "2E75B6"], 1))
         + '<a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme>'
         '<a:fontScheme name="Paper"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
         '<a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
         '<a:fmtScheme name="Paper"><a:fillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3 + '</a:fillStyleLst>'
         '<a:lnStyleLst>' + '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>' * 3 + '</a:lnStyleLst>'
         '<a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 + '</a:effectStyleLst>'
         '<a:bgFillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3 + '</a:bgFillStyleLst>'
         '</a:fmtScheme></a:themeElements></a:theme>')

MASTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster %s><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree>'
          '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>'
          '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
          '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>' % NS)

LAYOUT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout %s type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>'
          '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>'
          '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>' % NS)


def rels(items):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/%s" Target="%s"/>' % i for i in items)
            + "</Relationships>")


def write_pptx(slide, w, h, out):
    R = "officeDocument/2006/relationships/"
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="png" ContentType="image/png"/><Default Extension="jpeg" ContentType="image/jpeg"/>'
          '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
          '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
          '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
          '<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
          '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
          '</Types>')
    pres = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation %s saveSubsetFonts="1">'
            '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
            '<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>'
            '<p:sldSz cx="%d" cy="%d"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>' % (NS, emu(w), emu(h)))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels([("rId1", R + "officeDocument", "ppt/presentation.xml")]))
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", rels([
            ("rId1", R + "slideMaster", "slideMasters/slideMaster1.xml"),
            ("rId2", R + "slide", "slides/slide1.xml"),
            ("rId3", R + "theme", "theme/theme1.xml")]))
        z.writestr("ppt/slideMasters/slideMaster1.xml", MASTER)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels([
            ("rId1", R + "slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", R + "theme", "../theme/theme1.xml")]))
        z.writestr("ppt/slideLayouts/slideLayout1.xml", LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", rels([
            ("rId1", R + "slideMaster", "../slideMasters/slideMaster1.xml")]))
        z.writestr("ppt/theme/theme1.xml", THEME)
        z.writestr("ppt/slides/slide1.xml", slide.xml())
        srels = [("rId1", R + "slideLayout", "../slideLayouts/slideLayout1.xml")]
        for i, (rid, path, ext) in enumerate(slide.images, 1):
            name = "image%d.%s" % (i, ext)
            z.write(path, "ppt/media/" + name)
            srels.append((rid, R + "image", "../media/" + name))
        z.writestr("ppt/slides/_rels/slide1.xml.rels", rels(srels))


# ------------------------------------------------------------------ conversion

def converter():
    if os.name == "nt" and shutil.which("powershell"):
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "try { $p = New-Object -ComObject PowerPoint.Application; 'ok' } catch { 'no' }"],
                           capture_output=True, text=True)
        if "ok" in r.stdout:
            return "powerpoint-win"
    if sys.platform == "darwin" and os.path.isdir("/Applications/Microsoft PowerPoint.app"):
        return "powerpoint-mac"
    for exe in ("soffice", "libreoffice", r"C:\Program Files\LibreOffice\program\soffice.exe",
                "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if shutil.which(exe) or os.path.isfile(exe):
            return "libreoffice:" + (shutil.which(exe) or exe)
    return None


def convert(pptx, pdf, png, w_in, h_in):
    kind = converter()
    if kind == "powerpoint-win":
        ps = ("$ErrorActionPreference='Stop'; $pp = New-Object -ComObject PowerPoint.Application; "
              "$d = $pp.Presentations.Open('{src}', $true, $false, $false); "
              "$d.SaveAs('{pdf}', 32); "
              "$d.Slides.Item(1).Export('{png}', 'PNG', {pw}, {ph}); "
              "$d.Close()").format(src=pptx.replace("'", "''"), pdf=pdf.replace("'", "''"), png=png.replace("'", "''"),
                                   pw=int(w_in * 200), ph=int(h_in * 200))
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(pdf):
            return "PowerPoint conversion failed: " + (r.stderr or r.stdout).strip().splitlines()[-1:][0] if (r.stderr or r.stdout).strip() else "PowerPoint conversion failed"
        return None
    if kind and kind.startswith("libreoffice:"):
        exe, outdir = kind.split(":", 1)[1], os.path.dirname(pdf) or "."
        r = subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", outdir, pptx], capture_output=True, text=True)
        if not os.path.isfile(pdf):
            return "LibreOffice conversion failed: " + r.stderr.strip()[-200:]
        subprocess.run([exe, "--headless", "--convert-to", "png", "--outdir", outdir, pptx], capture_output=True)
        return None
    if kind == "powerpoint-mac":
        return "PowerPoint for Mac found, but automatic export isn't supported — open the .pptx and use File > Export > PDF."
    return "no PDF converter found (needs PowerPoint on Windows, or LibreOffice). The .pptx was saved."


# ------------------------------------------------------------------ commands

def shift(e, dx, dy):
    """Copy of an element moved by (dx, dy): x/y and [x, y] points; "id.side" anchors are left alone."""
    e = dict(e)
    if "x" in e:
        e["x"] = float(e["x"]) + dx
    if "y" in e:
        e["y"] = float(e["y"]) + dy
    for k in ("from", "to"):
        if isinstance(e.get(k), list):
            e[k] = [float(e[k][0]) + dx, float(e[k][1]) + dy]
    if e.get("via"):
        e["via"] = [[float(p[0]) + dx, float(p[1]) + dy] if isinstance(p, list) else p for p in e["via"]]
    return e


def fill_index(v, i):
    if isinstance(v, str):
        return v.replace("{i}", str(i)).replace("{n}", str(i + 1))
    if isinstance(v, list):
        return [fill_index(x, i) for x in v]
    if isinstance(v, dict):
        return {k: fill_index(x, i) for k, x in v.items()}
    return v


def draw(s, elements, base_dir, dx, dy):
    for e in elements:
        t = e.get("type", "box")
        if t == "group":
            # local coordinates: children are placed relative to the group's x, y
            draw(s, e.get("elements", []), base_dir, dx + float(e.get("x", 0)), dy + float(e.get("y", 0)))
            continue
        if t == "repeat":
            # copies of "element" (or "elements"), the k-th moved by k*(dx, dy); "{i}" (0-based) and "{n}" (1-based) are filled in
            items = e.get("elements") or [e["element"]]
            for k in range(int(e["count"])):
                draw(s, [fill_index(x, k) for x in items], base_dir,
                     dx + k * float(e.get("dx", 0)), dy + k * float(e.get("dy", 0)))
            continue
        e = shift(e, dx, dy)
        if t == "box":
            s.box(e)
        elif t == "text":
            s.box(e, text_only=True)
        elif t == "arrow":
            s.arrow(e)
        elif t == "line":
            s.arrow(dict(e, head=e.get("head", "none")))
        elif t == "image":
            s.image(e, base_dir)
        elif t == "table":
            s.table(e)
        else:
            die("unknown element type %r (box, text, arrow, line, image, table, group, repeat)" % t)


def cmd_build(a):
    try:
        with open(a.spec, encoding="utf-8") as f:
            spec = json.load(f)
    except (OSError, ValueError) as e:
        die("cannot read spec: %s" % e)
    auto = spec.get("size", "auto") == "auto"
    s = Slide(spec)
    base_dir = os.path.dirname(os.path.abspath(a.spec))
    draw(s, spec.get("elements", []), base_dir, 0.0, 0.0)
    if auto:
        m = float(spec.get("margin", 0.05))
        w, h = s.extent[0] + m, s.extent[1] + m
    else:
        w, h = (float(v) for v in spec["size"])
    out = os.path.abspath(a.out or os.path.splitext(a.spec)[0])
    pptx, pdf, png = out + ".pptx", out + ".pdf", out + ".png"
    for p in (pdf, png):
        if os.path.exists(p):
            os.remove(p)
    write_pptx(s, w, h, pptx)
    print("pptx: %s · %.2f x %.2f in" % (pptx, w, h))
    for warn in s.warnings[:20]:
        print("warning: " + warn)
    if a.no_pdf:
        return
    err = convert(pptx, pdf, png, w, h)
    if err:
        print("pdf: not created — " + err)
        return
    print("pdf: %s" % pdf)
    if os.path.isfile(png):
        print("preview: %s  (read this image to check the layout)" % png)


def cmd_check(a):
    kind = converter()
    print("pdf converter: " + (kind or "none — install LibreOffice, or use PowerPoint on Windows"))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("build"); s.add_argument("spec"); s.add_argument("--out"); s.add_argument("--no-pdf", action="store_true")
    sub.add_parser("check")
    a = ap.parse_args()
    {"build": cmd_build, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
