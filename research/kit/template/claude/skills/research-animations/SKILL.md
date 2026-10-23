---
name: research-animations
description: How to make short paper / talk animations with Manim — setup, the paperanim helpers, scene rules, and the draft → steps.png → fix → final loop with animtool.py. Read this before running /research-animation.
user-invocable: false
---

# Research Animations

An animation is a Manim scene file (`scene.py`) — that file is the spec. `scripts/animtool.py` renders it from a pipeline-owned Manim environment and turns the result into **one review image**, `steps.png`: the last frame of every `play()`, in order (steps that change nothing, like `wait`, are dropped). Claude can't watch video, so `steps.png` is what gets checked — one image per round, not a frame dump.

`AT` below means `python3 .claude/skills/research-animations/scripts/animtool.py` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run).

## Setup — once per machine

`AT check` says whether Manim is usable. If not, **ask the user once** ("Manim isn't installed; set it up now? one time, about 0.5 GB, a few minutes — it goes into its own environment and doesn't touch your Python") and on yes run `AT setup`. It uses micromamba + conda-forge (Manim with cairo, pango and ffmpeg, no compiler, no admin rights) on Windows, macOS and Linux, downloading micromamba if needed; pip into a venv is the fallback. The environment lives in `~/.cache/research-pipeline/manim/` (Windows: `%LOCALAPPDATA%\research-pipeline\manim\`) and is shared by all projects. `MANIM_PYTHON=<python with manim>` uses an existing install instead.

LaTeX is optional and never installed automatically: `formula()` uses `MathTex` when LaTeX + dvisvgm exist, otherwise matplotlib or Pango markup — sub/superscripts, Greek and common symbols all work.

## Build loop

1. Write `scene.py`. One `Scene` class, `from manim import *` and `from paperanim import *`, `paper_style(self)` first.
2. `AT render scene.py` — 480p draft. Output: duration, step count, `steps.png`. On a failure it prints the error and the `scene.py` line only; open `render.log` only if that isn't enough.
3. **Read `steps.png`** and fix: overlaps, text too small or cut off at the frame edge, arrows that miss or cross shapes, uneven spacing, a step that shows nothing new. Edit `scene.py` in place — don't rewrite it whole.
4. Repeat 2–3, **at most 3 rounds**. Manim caches unchanged steps, so re-renders are fast.
5. `AT render scene.py --final` — 1080p30 MP4 + GIF (960 px, 12 fps) for slides. Only once, at the end.

## Scene rules

- **One message per animation.** 10–30 s, 4–8 steps. Each `play()` adds one idea; the order follows the explanation you'd give out loud.
- **Pacing:** `run_time` 0.6–1.5 s per step, `self.wait(0.5–1)` after a step the viewer must read. End with `self.wait(1)` on the complete picture.
- **Layout:** the frame is 14.2 × 8 units; use ~80% of it — content clustered in a corner reads as tiny on a slide. Align on a grid (`arrange`, `next_to(..., buff=0.6)`), equal gaps, left → right flow.
- **Text:** `font_size` ≥ 28 for labels, ≥ 36 for the key term. No sentences on screen — the talk says them.
- **Color:** the figure palette (`BLUE_D`/`BLUE_L`, `ORANGE_D`/`ORANGE_L`, `GREEN_D`/`GREEN_L`, `PURPLE_D`/`PURPLE_L`, `GRAY_L`, `INK`), one color per concept, the same as in the paper's figures.
- **Arrows** attach to the facing edges (`connect(a, b)`, or `Arrow(row[-1].get_right(), ...)`), never across a shape.
- **Motion carries meaning:** `Transform` when one thing becomes another (depth → 3D points), `Indicate` / color change to point at something, `FadeOut` what is no longer needed. No decorative spinning or bouncing.

## paperanim helpers

| Helper | Does |
| --- | --- |
| `paper_style(self)` | white background, dark ink, the first sans font the machine has, thin strokes |
| `box(text, fill, line, w=2.2, h=0.9, size=28, bold=False)` | rounded box with a centered label (text shrinks to fit) |
| `token_row(n, fill, line, side=0.38, gap=0.1)` | n square tokens in a row |
| `connect(a, b, color=INK)` | arrow between facing edges of two mobjects |
| `label(text, size=28, color=INK)` | plain text |
| `formula(tex, size=36)` | math that renders with or without LaTeX |

## 3D

Use `class Name(ThreeDScene)` when depth or geometry is the point (back-projection, camera rays, point clouds); stay 2D for pipelines and data flow — 3D costs render time and legibility.

```python
self.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES)
axes = ThreeDAxes(x_range=[-3, 3], y_range=[-3, 3], z_range=[0, 4], x_length=5, y_length=5, z_length=3.5, axis_config={"color": INK})
Dot3D(axes.c2p(x, y, z), color=BLUE_D); Line3D(a, b); Prism(dimensions=[1, 1, 2]); Surface(lambda u, v: axes.c2p(u, v, f(u, v)), u_range=[-2, 2], v_range=[-2, 2])
self.add_fixed_in_frame_mobjects(title); title.to_corner(UL)   # labels that must not rotate with the camera
self.move_camera(theta=20 * DEGREES, run_time=2)                # each camera move is one step in steps.png
```

## Manim in brief

```python
a.next_to(b, RIGHT, buff=0.6); VGroup(a, b, c).arrange(RIGHT, buff=0.8); a.move_to(ORIGIN).shift(UP * 2)
self.play(FadeIn(a), Create(shape), Write(text), GrowArrow(arrow), run_time=1)
self.play(Transform(a, b)); self.play(ReplacementTransform(a, b)); self.play(Indicate(a, color=ORANGE_D))
self.play(a.animate.shift(RIGHT * 2).set_fill(ORANGE_L)); self.play(LaggedStart(*[FadeIn(t) for t in row], lag_ratio=0.2))
self.play(FadeOut(a)); self.wait(1)
```

`Rectangle`, `RoundedRectangle`, `Square`, `Circle`, `Dot`, `Line`, `DashedLine`, `Arrow`, `CurvedArrow`, `Brace(a, DOWN)`, `SurroundingRectangle(a)`, `Text`, `MarkupText` (`<sub>`, `<sup>`, `<i>`, `<b>`), `ImageMobject(path).scale_to_fit_width(4)` for a picture.

## Integrity

Only what the user described or a verified source supports — no invented numbers, results or claims on screen, same as figures.
