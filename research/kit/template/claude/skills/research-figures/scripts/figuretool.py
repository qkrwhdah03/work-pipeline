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
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from xml.sax.saxutils import escape

EMU = 914400  # per inch
SCALE = 1.0   # set by build when the canvas must be enlarged (PowerPoint needs at least 1 in per side)
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
    return int(round(float(v) * EMU * SCALE))


def hexcolor(c, default="000000"):
    c = (c or default).lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", c):
        die("bad color: %r (use #RRGGBB)" % c)
    return c.upper()


# ------------------------------------------------------------------ text

RUN = re.compile(r"(\{size:[0-9.]+\|.+?\}|\*\*.+?\*\*|__.+?__|\^\{.+?\}|_\{.+?\}|\*[^*\s][^*]*?\*)")

# Arial / Helvetica advance widths (1/1000 em) for ASCII 32..126 — Liberation Sans shares them.
ARIAL = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
         556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
         1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
         667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
         333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
         556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]


def char_em(ch):
    o = ord(ch)
    if 32 <= o <= 126:
        return ARIAL[o - 32] / 1000
    if o >= 0x1100 and (o <= 0x11FF or 0x2E80 <= o <= 0xD7AF or 0xF900 <= o <= 0xFFDC):
        return 1.0  # CJK / Hangul
    return 0.6


def text_width(line, size, bold=False):
    """Width in inches of one line of marked-up text in Arial (close for other sans fonts)."""
    w = 0.0
    for part in RUN.split(line):
        if not part:
            continue
        b, k, sz = bold, 1.0, size
        ms = re.fullmatch(r"\{size:([0-9.]+)\|(.+)\}", part)
        if ms:
            w += text_width(ms.group(2), float(ms.group(1)), bold)
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            w += text_width(part[2:-2], size, True)
            continue
        elif part.startswith("__") and part.endswith("__") and len(part) > 4:
            w += text_width(part[2:-2], size, bold)
            continue
        elif part[:2] in ("^{", "_{") and part.endswith("}"):
            part, k = part[2:-1], 0.67  # super/subscripts are drawn at about 2/3 size
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            w += text_width(part[1:-1], size, bold)
            continue
        w += sum(char_em(c) for c in part) * (1.07 if b else 1.0) * k * sz / 72
    return w


def runs_xml(text, size, color, bold=False, italic=False, font=None, underline=False):
    """Inline markup: **bold**, __underline__, *italic*, ^{superscript}, _{subscript}, {size:11|bigger}.
    Bold / underline / italic may contain other markup (*x_{i}*)."""
    out = []
    for part in RUN.split(text):
        if not part:
            continue
        b, i, u, base, sz = bold, italic, underline, 0, size
        ms = re.fullmatch(r"\{size:([0-9.]+)\|(.+)\}", part)
        if ms:
            sz, part = float(ms.group(1)), ms.group(2)
            out.append(runs_xml(part, sz, color, bold, italic, font, underline))
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append(runs_xml(part[2:-2], size, color, True, italic, font, underline))
            continue
        elif part.startswith("__") and part.endswith("__") and len(part) > 4:
            out.append(runs_xml(part[2:-2], size, color, bold, italic, font, True))
            continue
        elif part.startswith("^{") and part.endswith("}"):
            part, base = part[2:-1], 30000
        elif part.startswith("_{") and part.endswith("}"):
            part, base = part[2:-1], -25000
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append(runs_xml(part[1:-1], size, color, bold, True, font, underline))
            continue
        attrs = 'lang="en-US" sz="%d" b="%d" i="%d"' % (int(size * 100 * SCALE), b, i)
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
        # latinLnBrk="0": never break an English word in half (Korean / Japanese / Chinese Office does by default)
        paras.append('<a:p><a:pPr algn="%s" latinLnBrk="0">%s</a:pPr>%s<a:endParaRPr lang="en-US" sz="%d"/></a:p>'
                     % (algn, sp, runs_xml(line, size, color, bold, italic, font), int(size * 100 * SCALE)))
    return "".join(paras)


# ------------------------------------------------------------------ shapes

class Slide:
    def __init__(self, spec):
        self.spec = spec
        self.font = spec.get("font", "Arial")
        self.size = float(spec.get("fontsize", 9))
        self.items, self.boxes, self.images, self.nid = [], {}, [], 2
        self.bounds = None  # ink bounds [x1, y1, x2, y2] — for cropping the canvas
        self.warnings = []
        self.shapes, self.texts, self.segments = [], [], []  # for the overlap check
        self.panels = []  # groups with a sub-figure "label", placed after everything is drawn

    def grow(self, x1, y1, x2, y2):
        b = self.bounds
        self.bounds = [x1, y1, x2, y2] if b is None else [min(b[0], x1), min(b[1], y1), max(b[2], x2), max(b[3], y2)]

    def text_ink(self, e, text, x, y, w, h, text_only):
        """Estimated rectangle the text itself covers inside its box. Text-only elements never wrap
        (lines break only at \\n), so their ink may stick out of the box; box text wraps inside it."""
        size = float(e.get("size", self.size))
        pad = float(e.get("pad", 0.04))
        lines = str(text).split("\n")
        inner = max(w - 2 * pad, 0.01)
        widths = [text_width(l, size, e.get("bold", False)) for l in lines]
        if text_only:
            n, tw = len(lines), max(widths)
        else:
            n = sum(int(-(-wl // inner)) if wl > inner else 1 for wl in widths)  # wrapped line count
            tw = min(max(widths), inner)
        th = n * size * 1.22 / 72
        al = e.get("align", "center")
        tx = x + pad if al in ("left", "l") else x + w - pad - tw if al in ("right", "r") else x + (w - tw) / 2
        va = e.get("valign", "middle")
        ty = y + pad if va == "top" else y + h - pad - th if va == "bottom" else y + (h - th) / 2
        return (tx, ty, tx + tw, ty + th)

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
            int(float(lw) * 12700 * SCALE), hexcolor(color), d, hs, he)

    def box(self, e, text_only=False):
        x, y, w, h = (float(e[k]) for k in ("x", "y", "w", "h"))
        if e.get("id"):
            self.boxes[e["id"]] = (x, y, w, h)
        text = e.get("text", "")
        name = e.get("id") or str(text).split("\n")[0][:28] or "%s at (%.2f, %.2f)" % (e.get("shape", "rect"), x, y)
        if text_only:
            if text:
                ink = self.text_ink(e, text, x, y, w, h, True)
                self.grow(*ink)
                if not e.get("_internal"):
                    self.texts.append({"name": name, "ink": ink,
                                       "ok": e.get("overlap", False), "owner": e.get("_owner")})
        else:
            r = rotated_bbox(x, y, w, h, float(e.get("rotate", 0) or 0))
            lw = float(e.get("lw", 0.75)) / 72 / 2
            self.grow(r[0] - lw, r[1] - lw, r[2] + lw, r[3] + lw)
            self.shapes.append({"name": name, "id": e.get("id"), "rect": r, "ok": e.get("overlap", False)})
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
        body = paragraphs_xml(text, float(e.get("size", self.size)), hexcolor(e.get("color"), "000000"),
                              e.get("align", "center"), e.get("bold", False), e.get("italic", False),
                              e.get("font", self.font), e.get("spacing"))
        self.check_fit(e, text, w, h, text_only)
        sid = self.next_id()
        self.items.append(
            '<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm%s><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="%s">%s</a:prstGeom>%s%s</p:spPr>'
            '<p:txBody><a:bodyPr wrap="%s" lIns="%d" tIns="%d" rIns="%d" bIns="%d" anchor="%s" rtlCol="0">'
            '<a:noAutofit/></a:bodyPr><a:lstStyle/>%s</p:txBody></p:sp>' % (
                sid, escape(e.get("id", "Shape %d" % sid)), rot, emu(x), emu(y), emu(w), emu(h), geom, adj,
                fill_xml, ln, "none" if text_only else "square", inset, inset, inset, inset, va, body))

    def check_fit(self, e, text, w, h, text_only):
        """Text-fit check from Arial glyph widths — warns before the preview has to show it."""
        if not text or e.get("_internal"):
            return
        size = float(e.get("size", self.size))
        pad = float(e.get("pad", 0.04))
        lines = str(text).split("\n")
        widest = max(text_width(l, size, e.get("bold", False)) for l in lines)
        tall = len(lines) * size * 1.2 / 72
        name = e.get("id") or (MARKUP_ALL.sub(lambda m: next((g for g in m.groups() if g), ""), lines[0])[:24] + "…")
        if widest * 1.03 > w - 2 * pad:  # ~3% headroom: renderers differ a little in kerning
            what = "sticks out of its box (text elements never wrap; break lines with \\n or widen it)" if text_only \
                else "wraps inside the box (widen it, shrink size, reduce pad, or break lines yourself with \\n)"
            self.warnings.append("%s: text ~%.2f in wide, box has %.2f in — %s" % (name, widest, w - 2 * pad, what))
        if not text_only and len(lines) > 1 and tall > (h - 2 * pad) * 1.1:
            self.warnings.append("%s: %d lines need ~%.2f in, box is %.2f in tall — likely overflows" % (name, len(lines), tall, h - 2 * pad))

    def segment(self, p1, p2, e, head_start=None, head_end=None, ends=(), owner=None):
        (x1, y1), (x2, y2) = p1, p2
        g = float(e.get("lw", 1)) / 72 * (3.5 if head_start or head_end else 0.5)  # arrowheads stick out
        self.grow(min(x1, x2) - g, min(y1, y2) - g, max(x1, x2) + g, max(y1, y2) + g)
        if not e.get("_internal"):
            self.segments.append({"p1": p1, "p2": p2, "ends": set(ends), "ok": e.get("overlap", False), "owner": owner})
        flip = (' flipH="1"' if x2 < x1 else "") + (' flipV="1"' if y2 < y1 else "")
        sid = self.next_id()
        self.items.append(
            '<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="%d" name="Line %d"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
            '<p:spPr><a:xfrm%s><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="line"><a:avLst/></a:prstGeom>%s</p:spPr></p:cxnSp>' % (
                sid, sid, flip, emu(min(x1, x2)), emu(min(y1, y2)), emu(abs(x2 - x1)), emu(abs(y2 - y1)),
                self.line_xml(e.get("color", "#333333"), e.get("lw", 1), e.get("dash", "solid"), head_start, head_end)))

    def polyline(self, pts, e, head_start=None, head_end=None, ends=(), owner=None):
        """Elbow arrow / bent line as ONE freeform path, so corners join cleanly and the head sits on the path end."""
        hs = float(e.get("lw", 1)) / 72 * 3.5
        for i, (p1, p2) in enumerate(zip(pts, pts[1:])):
            g = hs if (i == 0 and head_start) or (i == len(pts) - 2 and head_end) else float(e.get("lw", 1)) / 72 * 0.5
            self.grow(min(p1[0], p2[0]) - g, min(p1[1], p2[1]) - g, max(p1[0], p2[0]) + g, max(p1[1], p2[1]) + g)
            if not e.get("_internal"):
                self.segments.append({"p1": p1, "p2": p2, "ends": set(ends), "ok": e.get("overlap", False), "owner": owner})
        x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
        pw, ph = max(emu(max(p[0] for p in pts) - x0), 1), max(emu(max(p[1] for p in pts) - y0), 1)
        path = "".join('<a:%s><a:pt x="%d" y="%d"/></a:%s>' % (t, emu(p[0] - x0), emu(p[1] - y0), t)
                       for t, p in zip(["moveTo"] + ["lnTo"] * (len(pts) - 1), pts))
        ln = self.line_xml(e.get("color", "#333333"), e.get("lw", 1), e.get("dash", "solid"), head_start, head_end)
        ln = ln.replace("<a:round/>", '<a:miter lim="800000"/>')  # crisp right-angle corners
        sid = self.next_id()
        self.items.append(
            '<p:sp><p:nvSpPr><p:cNvPr id="%d" name="Connector %d"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="r" b="b"/>'
            '<a:pathLst><a:path w="%d" h="%d" fill="none">%s</a:path></a:pathLst></a:custGeom>'
            '<a:noFill/>%s</p:spPr></p:sp>' % (sid, sid, emu(x0), emu(y0), pw, ph, pw, ph, path, ln))

    def arrow(self, e):
        pts = [self.anchor(e["from"])] + [self.anchor(p) for p in e.get("via", [])] + [self.anchor(e["to"])]
        head = e.get("head", "end")
        kind = "triangle"
        ends = [str(r).split(".")[0] for r in (e["from"], e["to"]) if isinstance(r, str)]
        owner = id(e)
        hs = kind if head in ("start", "both") else None
        he = kind if head in ("end", "both") else None
        if not e.get("_internal"):
            # An arrowhead needs room: on a final segment shorter than ~0.12 in the bend vanishes and
            # only a floating triangle is left.
            name = "arrow %s → %s" % tuple(r if isinstance(r, str) else "[%.2f, %.2f]" % tuple(map(float, r))
                                            for r in (e["from"], e["to"]))
            for seg, on in (((pts[-2], pts[-1]), he), ((pts[0], pts[1]), hs)):
                L = math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
                if on and len(pts) > 2 and L < 0.12:
                    self.warnings.append("%s: the segment with the arrowhead is only %.2f in — move the bend so it is at least 0.12 in, "
                                         "or the turn won't show" % (name, L))
            if any(math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-3 for a, b in zip(pts, pts[1:])):
                self.warnings.append("%s: two consecutive points are the same — drop the duplicate via point" % name)
            if any(abs(a[0] - b[0]) > 0.005 and abs(a[1] - b[1]) > 0.005 for a, b in zip(pts, pts[1:])) and len(pts) > 2:
                self.warnings.append("%s: an elbow segment is diagonal — via points should share x or y with their neighbours" % name)
        if len(pts) > 2:
            self.polyline(pts, e, hs, he, ends, owner)
        else:
            self.segment(pts[0], pts[1], e, hs, he, ends, owner)
        if e.get("label"):
            (x1, y1), (x2, y2) = pts[len(pts) // 2 - 1 if len(pts) > 2 else 0], pts[len(pts) // 2 if len(pts) > 2 else 1]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            lw, lh = float(e.get("label_w", 1.0)), float(e.get("label_h", 0.2))
            dx, dy = e.get("label_offset", [0, -0.12])
            self.box({"x": mx - lw / 2 + dx, "y": my - lh / 2 + dy, "w": lw, "h": lh, "text": e["label"],
                      "size": e.get("label_size", self.size - 1), "italic": e.get("label_italic", False),
                      "color": e.get("label_color", "#333333"), "_owner": owner,
                      "overlap": e.get("overlap", False)}, text_only=True)

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
        self.grow(x, y, x + float(w), y + float(h))
        self.shapes.append({"name": e.get("id") or os.path.basename(path), "id": e.get("id"),
                            "rect": (x, y, x + float(w), y + float(h)), "ok": e.get("overlap", False)})
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
            return '<a:%s w="%d"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:%s>' % (tag, int(w * 12700 * SCALE), tag)

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
        self.grow(x, y, x + total_w, y + total_h)
        self.shapes.append({"name": e.get("id") or "table", "id": e.get("id"),
                            "rect": (x, y, x + total_w, y + total_h), "ok": e.get("overlap", False)})
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
                                 {"color": "#000000", "lw": light, "_internal": True})
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


def rotated_bbox(x, y, w, h, deg):
    if not deg:
        return (x, y, x + w, y + h)
    t = math.radians(deg)
    c, s_ = abs(math.cos(t)), abs(math.sin(t))
    bw, bh = w * c + h * s_, w * s_ + h * c
    cx, cy = x + w / 2, y + h / 2
    return (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)


def inter(a, b, tol=0.01):
    """True when rectangles a and b (x1, y1, x2, y2) overlap by more than tol in both directions."""
    return min(a[2], b[2]) - max(a[0], b[0]) > tol and min(a[3], b[3]) - max(a[1], b[1]) > tol


def contains(a, b, tol=0.01):
    return a[0] - tol <= b[0] and a[1] - tol <= b[1] and b[2] <= a[2] + tol and b[3] <= a[3] + tol


def shrink(r, d):
    return (r[0] + d, r[1] + d, r[2] - d, r[3] - d)


def seg_hits(p1, p2, r):
    """Liang-Barsky: does segment p1-p2 pass through the inside of rectangle r?"""
    (x1, y1), (x2, y2) = p1, p2
    if r[2] <= r[0] or r[3] <= r[1]:
        return False
    dx, dy, t0, t1 = x2 - x1, y2 - y1, 0.0, 1.0
    for p, q in ((-dx, x1 - r[0]), (dx, r[2] - x1), (-dy, y1 - r[1]), (dy, r[3] - y1)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return t1 - t0 > 1e-6


def seg_dist(px, py, p1, p2):
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def near(p, r, tol=0.03):
    return r[0] - tol <= p[0] <= r[2] + tol and r[1] - tol <= p[1] <= r[3] + tol


def check_overlaps(s):
    """Warnings for shapes, labels and arrows that collide. A shape fully inside another (a panel or
    background) is fine, and so is text fully inside a shape. Mark intended overlaps with "overlap": true."""
    out = []
    sh = s.shapes
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i], sh[j]
            if a["ok"] or b["ok"] or not inter(a["rect"], b["rect"]):
                continue
            if contains(a["rect"], b["rect"]) or contains(b["rect"], a["rect"]):
                continue
            out.append("overlap: %s and %s" % (a["name"], b["name"]))
    tx = [t for t in s.texts if not t["ok"]]
    for i in range(len(tx)):
        for j in range(i + 1, len(tx)):
            if inter(tx[i]["ink"], tx[j]["ink"]):
                out.append("overlap: text %r and text %r" % (tx[i]["name"], tx[j]["name"]))
    for t in tx:
        for b in sh:
            if b["ok"] or not inter(t["ink"], b["rect"]):
                continue
            if not contains(b["rect"], t["ink"]):
                out.append("overlap: text %r crosses the edge of %s" % (t["name"], b["name"]))
    for g in s.segments:
        if g["ok"]:
            continue
        for b in sh:
            if b["ok"] or (b["id"] and b["id"] in g["ends"]):
                continue
            r = b["rect"]
            inner = shrink(r, 0.02)
            if near(g["p1"], r) or near(g["p2"], r):
                # Starting or ending on the edge and leaving outward is fine (coordinates instead of an anchor);
                # running across the shape is not — e.g. an arrow drawn from the last token's LEFT edge, over the token.
                if seg_hits(g["p1"], g["p2"], inner):
                    out.append("overlap: an arrow/line %s %s and runs across it — attach it to the facing edge instead: "
                               "give the shape an id (in a repeat: \"tok{i}\") and use \"<id>.right\" etc."
                               % ("starts on" if near(g["p1"], r) else "ends on", b["name"]))
                continue
            if contains(r, (min(g["p1"][0], g["p2"][0]), min(g["p1"][1], g["p2"][1]),
                            max(g["p1"][0], g["p2"][0]), max(g["p1"][1], g["p2"][1]))):
                continue  # runs inside a panel or background
            if max(r[2] - r[0], r[3] - r[1]) <= 0.15 and \
                    seg_dist((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, g["p1"], g["p2"]) < 0.02:
                continue  # a small marker placed on the line (sample points on a ray)
            if seg_hits(g["p1"], g["p2"], shrink(r, 0.02)):
                out.append("overlap: an arrow/line crosses %s" % b["name"])
        for t in tx:
            if seg_hits(g["p1"], g["p2"], shrink(t["ink"], 0.01)):
                out.append("overlap: an arrow/line crosses text %r" % t["name"])
    seen, uniq = set(), []
    for w in out:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    return uniq


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


def draw(s, elements, base_dir, dx, dy, overlap=False):
    for e in elements:
        t = e.get("type", "box")
        ov = overlap or e.get("overlap", False)  # set on a group / repeat, it covers everything inside
        if t == "group":
            # local coordinates: children are placed relative to the group's x, y
            outer, s.bounds = s.bounds, None
            draw(s, e.get("elements", []), base_dir, dx + float(e.get("x", 0)), dy + float(e.get("y", 0)), ov)
            inner = s.bounds
            s.bounds = outer
            if inner:
                s.grow(*inner)
                if e.get("label"):
                    s.panels.append({"e": e, "ink": inner, "ok": ov})
            continue
        if t == "repeat":
            # copies of "element" (or "elements"), the k-th moved by k*(dx, dy); "{i}" (0-based) and "{n}" (1-based) are filled in
            items = e.get("elements") or [e["element"]]
            for k in range(int(e["count"])):
                draw(s, [fill_index(x, k) for x in items], base_dir,
                     dx + k * float(e.get("dx", 0)), dy + k * float(e.get("dy", 0)), ov)
            continue
        e = shift(e, dx, dy)
        if ov:
            e["overlap"] = True
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


def place_panel_labels(s):
    """Sub-figure labels ("(a) ...") from a group's "label": centered under the panel's ink, and on one
    shared baseline for panels in the same row. "label_pos": "above" puts them over the panel instead."""
    rows = []
    for p in sorted(s.panels, key=lambda p: p["ink"][1]):
        for r in rows:  # same row = vertical extents overlap
            if min(p["ink"][3], max(q["ink"][3] for q in r)) > max(p["ink"][1], min(q["ink"][1] for q in r)):
                r.append(p)
                break
        else:
            rows.append([p])
    for r in rows:
        bottom, top = max(q["ink"][3] for q in r), min(q["ink"][1] for q in r)
        for p in r:
            e, (x1, _, x2, _) = p["e"], p["ink"]
            size = float(e.get("label_size", s.size))
            gap = float(e.get("label_gap", 0.06))
            tw = text_width(e["label"], size, e.get("label_bold", False))
            w, h = tw * 1.06 + 0.04, size * 1.22 / 72 + 0.04
            y = top - gap - h if e.get("label_pos") == "above" else bottom + gap
            if tw > x2 - x1 + 0.01:
                s.warnings.append("panel label %r (%.2f in) is wider than its panel (%.2f in) — shorten it"
                                  % (e["label"], tw, x2 - x1))
            s.box({"x": (x1 + x2) / 2 - w / 2, "y": y, "w": w, "h": h, "text": e["label"], "size": size,
                   "bold": e.get("label_bold", False), "pad": 0.02, "overlap": p["ok"]}, text_only=True)


def cmd_build(a):
    try:
        with open(a.spec, encoding="utf-8") as f:
            spec = json.load(f)
    except (OSError, ValueError) as e:
        die("cannot read spec: %s" % e)
    base_dir = os.path.dirname(os.path.abspath(a.spec))
    size = spec.get("size", "auto")
    m = float(spec.get("margin", 0.03))
    probe = Slide(spec)  # first pass: measure the ink bounds
    draw(probe, spec.get("elements", []), base_dir, 0.0, 0.0)
    place_panel_labels(probe)
    if probe.bounds is None:
        die("the spec has no elements")
    bx1, by1, bx2, by2 = probe.bounds
    cw, ch = bx2 - bx1, by2 - by1
    notes = []
    fixed_w = "auto" if size == "auto" else size[0]
    fixed_h = "auto" if size == "auto" else size[1]
    if fixed_w == "auto":
        w, dx = cw + 2 * m, m - bx1
    else:
        # Fixed width: center the content, so any spare width becomes equal side margins.
        w = float(fixed_w)
        dx = (w - cw) / 2 - bx1
        if cw > w + 0.01:
            notes.append("content is %.2f in wide but the canvas is %.2f in - it will be cut off; shrink or move elements" % (cw, w))
        elif w - cw - 2 * m > 0.1:
            notes.append("content is %.2f in wide on a %.2f in canvas - %.2f in of side margins; widen or spread the elements" % (cw, w, w - cw))
    if fixed_h == "auto":
        h, dy = ch + 2 * m, m - by1
    else:
        h = float(fixed_h)
        dy = (h - ch) / 2 - by1
        if ch > h + 0.01:
            notes.append("content is %.2f in tall but the canvas is %.2f in - it will be cut off" % (ch, h))
        elif h - ch - 2 * m > 0.1:
            notes.append('%.2f in of empty top/bottom margins; use "size": [%s, "auto"] to crop them' % (h - ch, fixed_w))
    # PowerPoint rejects slides under 1 in on a side, so small figures are drawn enlarged — every
    # coordinate, font size and line width alike. Placed at the intended width, they print at true size.
    global SCALE
    SCALE = max(1.0, 1.0 / min(w, h))
    s = Slide(spec)  # second pass: draw with the content moved to the margins
    draw(s, spec.get("elements", []), base_dir, dx, dy)
    place_panel_labels(s)
    s.warnings += notes + check_overlaps(s)
    out = os.path.abspath(a.out or os.path.splitext(a.spec)[0])
    pptx, pdf, png = out + ".pptx", out + ".pdf", out + ".png"
    for p in (pdf, png):
        if os.path.exists(p):
            os.remove(p)
    write_pptx(s, w, h, pptx)
    print("pptx: %s · %.2f x %.2f in" % (pptx, w, h))
    if SCALE > 1:
        print("note: stored %.2fx larger (PowerPoint needs at least 1 in per side); place it at its real size, "
              "e.g. \\includegraphics[width=%.2fin]{...}" % (SCALE, w))
    for warn in s.warnings[:25]:
        print("warning: " + warn)
    if len(s.warnings) > 25:
        print("warning: ... and %d more" % (len(s.warnings) - 25))
    if a.no_pdf:
        return
    err = convert(pptx, pdf, png, w * SCALE, h * SCALE)
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
