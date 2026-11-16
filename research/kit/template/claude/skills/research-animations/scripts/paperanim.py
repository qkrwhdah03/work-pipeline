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
    if t.height > h - 0.15:  # several lines in a short box: shrink to fit the height too
        t.scale_to_fit_height(h - 0.15)
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
        # Size it like text: measure the formula against an "x" set by the same renderer, then match that "x"
        # to the height of an "x" in Manim Text at this font size — so tall formulas (fractions, sums) stay
        # proportionally taller instead of being squeezed into one fixed height.
        fig = plt.figure(figsize=(1, 1))
        r = fig.canvas.get_renderer()
        hx = fig.text(0, 0, "$x$", fontsize=size).get_window_extent(renderer=r).height
        fig.clear()
        t = fig.text(0, 0, "$%s$" % tex, fontsize=size, color=color)
        hf = t.get_window_extent(renderer=r).height
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "formula.svg")
        try:
            fig.savefig(path, transparent=True, bbox_inches="tight", pad_inches=0)
            plt.close(fig)
            m = SVGMobject(path)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        ref = Text("x", font_size=size).height
        return m.set_color(color).scale_to_fit_height(ref * hf / hx if hx > 0 else ref)
    except Exception:
        return MarkupText(tex_to_markup(tex), font_size=size, color=color)


GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ",
         "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
         "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ",
         "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
         "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
         "cdot": "·", "times": "×", "div": "÷", "pm": "±", "mp": "∓", "in": "∈", "notin": "∉", "leq": "≤", "le": "≤",
         "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠", "approx": "≈", "sim": "∼", "equiv": "≡", "propto": "∝",
         "rightarrow": "→", "to": "→", "leftarrow": "←", "Rightarrow": "⇒", "Leftarrow": "⇐", "mapsto": "↦",
         "leftrightarrow": "↔", "sum": "∑", "prod": "∏", "int": "∫", "infty": "∞", "partial": "∂", "nabla": "∇",
         "forall": "∀", "exists": "∃", "cap": "∩", "cup": "∪", "subset": "⊂", "subseteq": "⊆", "emptyset": "∅",
         "circ": "∘", "odot": "⊙", "oplus": "⊕", "otimes": "⊗", "top": "⊤", "ell": "ℓ", "cdots": "⋯", "ldots": "…",
         "dots": "…", "langle": "⟨", "rangle": "⟩", "mid": "|", "|": "‖", "lVert": "‖", "rVert": "‖"}
ACCENT = {"hat": "̂", "widehat": "̂", "bar": "̅", "overline": "̅", "tilde": "̃",
          "widetilde": "̃", "vec": "⃗", "dot": "̇", "ddot": "̈"}
GROUP = r"\{([^{}]*)\}"


def tex_to_markup(tex):
    """Simple TeX -> Pango markup: \\frac as a/b, \\sqrt, accents, bold / upright text, sub/superscripts,
    Greek and common symbols, single letters in italics. Unknown commands keep their name (\\log -> log)."""
    keep = []  # upright segments (\text, \mathrm, \mathbf, operator names), put back after the italics pass

    def esc(x):
        return x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def protect(markup):
        keep.append(markup)
        return "\x03%d\x04" % (len(keep) - 1)

    def plain(x):  # text of a group with symbols replaced and braces dropped
        x = re.sub(r"\\([A-Za-z]+|[|{}])", lambda m: GREEK.get(m.group(1), m.group(1)), x)
        return x.replace("{", "").replace("}", "")

    def wrap(x):  # parentheses around a fraction part unless it is a single term
        return x if re.fullmatch(r"[^\s+\-*/=<>,]+", x) else "(%s)" % x

    s = re.sub(r"\\[,;:!> ]|~|\\quad|\\qquad", " ", tex)  # spacing commands
    s = re.sub(r"\\(?:left|right|big|Big|bigg|Bigg)(?![A-Za-z])\\?", "", s)  # sizing: keep the delimiter
    for _ in range(10):  # innermost groups first, so nesting (\frac{\hat{x}}{2}) works
        before = s
        s = re.sub(r"\\[dt]?frac" + GROUP + GROUP, lambda m: "%s/%s" % (wrap(m.group(1)), wrap(m.group(2))), s)
        s = re.sub(r"\\sqrt" + GROUP, lambda m: "√" + wrap(m.group(1)), s)
        s = re.sub(r"\\(%s)" % "|".join(ACCENT) + GROUP, lambda m: m.group(2) + ACCENT[m.group(1)], s)
        s = re.sub(r"\\(?:mathbf|boldsymbol|bm|textbf)" + GROUP, lambda m: protect("<b>%s</b>" % esc(plain(m.group(1)))), s)
        s = re.sub(r"\\(?:text|textrm|mathrm|operatorname|mathsf|mathcal|mathbb|mathit)" + GROUP,
                   lambda m: protect(esc(plain(m.group(1)))), s)
        if s == before:
            break
    s = re.sub(r"\\([A-Za-z]+|[|{}&%$#_])", lambda m: GREEK.get(m.group(1)) or protect(esc(m.group(1))), s)
    s = esc(s)
    for _ in range(10):  # innermost sub/superscript groups first
        before = s
        s = re.sub(r"_\{([^{}]*)\}", r"<sub>\1</sub>", s)
        s = re.sub(r"\^\{([^{}]*)\}", r"<sup>\1</sup>", s)
        if s == before:
            break
    s = re.sub(r"_(\x03\d+\x04|[^\s{}<\x03])", r"<sub>\1</sub>", s)
    s = re.sub(r"\^(\x03\d+\x04|[^\s{}<\x03])", r"<sup>\1</sup>", s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"(?<![\w</&])([A-Za-z])(?![\w>])", r"<i>\1</i>", s)  # single letters are variables
    return re.sub(r"\x03(\d+)\x04", lambda m: keep[int(m.group(1))], s)


__all__ = ["BLUE_D", "ORANGE_D", "GREEN_D", "PURPLE_D", "BLUE_L", "ORANGE_L", "GREEN_L", "PURPLE_L", "GRAY_L", "INK",
           "paper_style", "label", "box", "token_row", "connect", "formula", "has_latex", "UP", "DOWN", "LEFT", "RIGHT"]
