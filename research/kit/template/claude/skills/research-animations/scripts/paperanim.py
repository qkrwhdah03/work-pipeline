"""Paper-style building blocks for Manim scenes. animtool.py puts this folder on PYTHONPATH, so a scene does:

    from manim import *
    from paperanim import *

    class Overview(Scene):
        def construct(self):
            paper_style(self)
            ...

Colors match the research-figures palette, so an animation and the paper's figures read as one set.
"""
import os
import re
import shutil
import tempfile

from manim import (DOWN, LEFT, RIGHT, UP, WHITE, Arrow, MarkupText, MathTex, RoundedRectangle, Square, SVGMobject,
                   Text, VGroup, config)

# research-figures palette: dark = lines / text, light = fills
BLUE_D, ORANGE_D, GREEN_D, PURPLE_D = "#2F5597", "#C55A11", "#548235", "#7030A0"
BLUE_L, ORANGE_L, GREEN_L, PURPLE_L = "#DCE8F5", "#FBE5D6", "#E2F0D9", "#E8E0F0"
GRAY_L, INK = "#F2F2F2", "#404040"


SANS = ("Arial", "Helvetica", "Helvetica Neue", "Liberation Sans", "DejaVu Sans", "Noto Sans")


def sans_font():
    """The first sans font this machine has — Pango's own default is a serif."""
    try:
        import manimpango
        have = set(manimpango.list_fonts())
        return next((f for f in SANS if f in have), "Sans")
    except Exception:
        return "Sans"


def paper_style(scene=None):
    """White background, dark ink, one sans font, thin strokes — call first in construct()."""
    config.background_color = WHITE
    if scene is not None:
        scene.camera.background_color = WHITE
    font = sans_font()
    Text.set_default(color=INK, font=font)
    MarkupText.set_default(color=INK, font=font)
    MathTex.set_default(color=INK)
    Arrow.set_default(color=INK, stroke_width=3, buff=0.08, max_tip_length_to_length_ratio=0.15)


def label(text, size=28, color=INK, **kw):
    return Text(text, font_size=size, color=color, **kw)


def box(text="", fill=GRAY_L, line=INK, w=2.2, h=0.9, size=28, bold=False, markup=False):
    """Rounded box with a centered label — the animated twin of a figure `box`.
    markup=True takes Pango markup: "Token <i>x</i><sub>i</sub>"."""
    r = RoundedRectangle(width=w, height=h, corner_radius=0.12, fill_color=fill, fill_opacity=1,
                         stroke_color=line, stroke_width=2)
    if not text:
        return VGroup(r)
    t = (MarkupText if markup else Text)(text, font_size=size, color=INK, weight="BOLD" if bold else "NORMAL")
    if t.width > w - 0.2:
        t.scale_to_fit_width(w - 0.2)
    return VGroup(r, t.move_to(r))


def token_row(n, fill=GRAY_L, line=INK, side=0.38, gap=0.1):
    """n square tokens in a row. Arrows attach to row[0].get_left() / row[-1].get_right(), never across a token."""
    return VGroup(*[Square(side_length=side, fill_color=fill, fill_opacity=1, stroke_color=line, stroke_width=2)
                    for _ in range(n)]).arrange(RIGHT, buff=gap)


def connect(a, b, color=INK, **kw):
    """Arrow from a's right edge to b's left edge (or bottom → top when b is below a)."""
    if abs(a.get_center()[0] - b.get_center()[0]) < 0.1:
        return Arrow(a.get_bottom(), b.get_top(), color=color, **kw) if a.get_center()[1] > b.get_center()[1] \
            else Arrow(a.get_top(), b.get_bottom(), color=color, **kw)
    return Arrow(a.get_right(), b.get_left(), color=color, **kw) if a.get_center()[0] < b.get_center()[0] \
        else Arrow(a.get_left(), b.get_right(), color=color, **kw)


def has_latex():
    return bool(shutil.which("latex") and shutil.which("dvisvgm"))


def formula(tex, size=36, color=INK):
    """Math that works everywhere: MathTex with LaTeX + dvisvgm, else matplotlib mathtext, else plain text."""
    if has_latex():
        return MathTex(tex, font_size=size, color=color)
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, "$%s$" % tex, fontsize=size / 2, color=color)
        path = os.path.join(tempfile.mkdtemp(), "formula.svg")
        fig.savefig(path, transparent=True, bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        m = SVGMobject(path)
        return m.scale_to_fit_height(size / 72 * 0.45)
    except Exception:
        return MarkupText(tex_to_markup(tex), font_size=size, color=color)


GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "theta": "θ", "lambda": "λ", "mu": "μ",
         "pi": "π", "sigma": "σ", "phi": "φ", "omega": "ω", "Sigma": "Σ", "Delta": "Δ", "cdot": "·", "times": "×",
         "in": "∈", "leq": "≤", "geq": "≥", "approx": "≈", "rightarrow": "→", "to": "→", "sum": "∑", "infty": "∞"}


def tex_to_markup(tex):
    """Simple TeX -> Pango markup: sub/superscripts, Greek and common symbols, single letters in italics."""
    s = re.sub(r"\\[,;:!]|\\ ", " ", tex)  # TeX spacing commands
    s = re.sub(r"\\(\w+)", lambda m: GREEK.get(m.group(1), m.group(1)), s)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"_\{([^}]*)\}|_(\w)", lambda m: "<sub>%s</sub>" % (m.group(1) or m.group(2)), s)
    s = re.sub(r"\^\{([^}]*)\}|\^(\w)", lambda m: "<sup>%s</sup>" % (m.group(1) or m.group(2)), s)
    return re.sub(r"(?<![\w<>/])([A-Za-z])(?![\w>])", r"<i>\1</i>", s)


__all__ = ["BLUE_D", "ORANGE_D", "GREEN_D", "PURPLE_D", "BLUE_L", "ORANGE_L", "GREEN_L", "PURPLE_L", "GRAY_L", "INK",
           "paper_style", "label", "box", "token_row", "connect", "formula", "has_latex", "UP", "DOWN", "LEFT", "RIGHT"]
