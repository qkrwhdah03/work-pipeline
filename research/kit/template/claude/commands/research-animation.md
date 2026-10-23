---
description: Make a short paper / talk animation from a description — Manim scene → MP4 + GIF (+ step preview)
argument-hint: <what the animation should show, e.g. "depth becomes 3D points, which set the RoPE angles inside the ViT">
allowed-tools: Read, Write, Edit, Glob, Bash(python3 .claude/skills/research-animations/scripts/animtool.py:*), Bash(python .claude/skills/research-animations/scripts/animtool.py:*)
---

Animation: **$ARGUMENTS**

## 0. Rules

Read `.claude/skills/research-animations/SKILL.md` first and follow it: setup, scene rules, helpers, and the draft → `steps.png` → fix → final loop. `AT` below means `python3 .claude/skills/research-animations/scripts/animtool.py` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run).

Reply in the user's language. Text **inside** the animation is in the language of the description's labels — usually English, as in a paper.

## 1. Setup

`AT check`. If Manim isn't installed, ask the user once as the skill says, then `AT setup`. If they decline, stop and say the animation needs it.

## 2. Storyboard

- State in one sentence the message the viewer should take away.
- List the steps (4–8), one line each — what appears or changes, and why. This list is the plan for the `play()` calls; show it to the user only if the description was vague.
- If the description names a method or paper you have notes on (`.research/papers/`) or a figure already made (`.research/figures/`), reuse its names and colors so the animation matches.

## 3. Build

1. Write `.research/animations/<YYYY-MM-DD>-<slug>/scene.py`.
2. `AT render .research/animations/<…>/scene.py` → read `steps.png` → fix; at most 3 rounds (skill: Build loop).
3. `AT render .research/animations/<…>/scene.py --final`.

## 4. Report

```
Animation · <one-line message>
<duration> s · <n> steps

MP4    <path>   ← 1080p, for slides / video
GIF    <path>   ← drops into slides and docs
Scene  <path>   ← edit and re-render for changes
```

Show `steps.png`, and name choices the user may want to change (pacing, colors, wording).
