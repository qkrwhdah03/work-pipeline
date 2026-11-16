---
description: Turn the /dev-brainstorm notes into one organized brief (.md) of ready-to-run /dev requests
argument-hint: [focus or title (optional)]
allowed-tools: Read, Write, Glob, Grep, Bash(python3 .claude/skills/dev-loop/scripts/devtool.py:*), Bash(python .claude/skills/dev-loop/scripts/devtool.py:*)
---

Focus: **$ARGUMENTS** (if empty, brief everything in the open notes)

Organize the brainstorm into a brief the user can review and hand to `/dev`. Do not design the implementation, read source code or change anything outside `.dev/brainstorm/`. Write the brief and reply in the user's language; keep the brief's `##` headings in English (A looks them up).

`DT` below means `python3 .claude/skills/dev-loop/scripts/devtool.py` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run), run from the project root.

## 1. Gather

1. `DT brainstorm show` — the open notes and the latest brief. **`notes: 0` → stop** and say to collect ideas with `/dev-brainstorm` first.
2. If the notes build on the latest brief ("in addition to…", "change the earlier…"), read that brief too and carry over what still holds.
3. For conflicts with what exists, read only `.dev/context/01-features.md` and `DT devlog limitations` (skip if missing). Nothing else.

## 2. Write the brief

`DT brainstorm next` prints the path. Write it with `.dev/templates/brief.md` as the format:

- **Every note lands somewhere** — in a request, a decision, a constraint, an open question or out of scope — with its `#n` so the user can trace it. Never drop one silently.
- A later note overrides an earlier one on the same point; record that under `## Decisions`.
- `## Requests` are ordered so each builds on the previous one. Each is **one `/dev`-sized change**: its scope fits in one line, with 1–3 acceptance hints under it. Split anything bigger.
- Anything A would have to ask (two reasonable designs, a choice the notes leave open) goes to `## Open Questions` with options — don't decide it for the user.
- Do not invent requirements. Plausible but unstated ideas go to `## Out of Scope / Later` marked `(suggestion)`.

## 3. Close the round

`DT brainstorm close <brief path>` — moves the notes to `.dev/brainstorm/archive/`, so the next `/dev-brainstorm` starts a new round.

## 4. Report

```
Brief  <path>
Goal   <one line>
Requests
  1. <one line>
  2. ...
Open questions  <n>   ← list them, if any
```

Then one line: run it with `/dev <brief path>` (request #1) or `/dev <brief path> #2`; answer open questions first, or edit the brief, if they touch that request.
