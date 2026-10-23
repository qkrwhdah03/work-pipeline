---
description: Make a paper figure from a description — editable PPTX + PDF (+ PNG preview)
argument-hint: <what the figure should show, e.g. "overview of our pipeline: images → SfM → 3D Gaussians → rasterizer">
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python3 .claude/skills/research-figures/scripts/figuretool.py:*), Bash(python .claude/skills/research-figures/scripts/figuretool.py:*), Bash(python3 .research/figures/:*), Bash(python .research/figures/:*)
---

Figure: **$ARGUMENTS**

Design the figure that best conveys this description, as it would appear in a paper.

## 0. Rules

Read `.claude/skills/research-figures/SKILL.md` first and follow it: spec format, print sizes, style rules, and the build → preview → fix loop. `FT` below means `python3 .claude/skills/research-figures/scripts/figuretool.py` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run).

Reply in the user's language. Text **inside** the figure is in the language of the description's labels — usually English, as in a paper.

## 1. Decide what the figure must say

- State in one sentence the message a reader should take away.
- Pick the form that shows it most directly:
  - **Pipeline / overview** — stages as boxes, data flow as arrows.
  - **Concept / comparison** — side-by-side panels (ours vs. prior work, before vs. after), with short labels.
  - **Architecture** — modules, tensors and their shapes, skip connections.
  - **Data plot** — numbers over a variable (see "Data plots" in the skill).
- Pick the width: single column (3.25 in) unless the content is wide — a long pipeline or several panels → full width (6.875 in, `"size": [6.875, "auto"]`). If the description names the venue, use its sizes.
- If the description mentions a method or paper you have notes on (`.research/papers/`), read them for the correct stage names.
- Only if the description is too vague to draw (no idea what the parts are), ask one short question.

## 2. Build

1. Write the spec to `.research/figures/<YYYY-MM-DD>-<slug>/figure.json`.
2. `FT build .research/figures/<…>/figure.json`
3. Fix every `warning:` line (wrapping text, overlaps, canvas), then read `figure.png` and fix what else is wrong — skill's build loop, at most 3 rounds. Nothing may overlap unless intended and marked `"overlap": true`; margins stay minimal (`"size": "auto"`, or `[6.875, "auto"]` for full width).

Never put numbers in a figure that the user didn't give or that you didn't verify from a source.

## 3. Report

```
Figure · <one-line message>
<width> × <height> in · <form>

PPTX  <path>   ← editable in PowerPoint
PDF   <path>   ← for LaTeX: \includegraphics[width=\linewidth]{<file>.pdf}
PNG   <path>
```

Show the preview image, and name any choice the user may want to change (width, colors, wording). If no PDF converter was found, say so — the PPTX is still complete.
