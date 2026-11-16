---
description: Jot down a loose idea for later — no design, no code. /dev-brief turns the collected notes into a request brief
argument-hint: <idea, as rough as you like>  (empty: show the open notes)
allowed-tools: Read, Bash(python3 .claude/skills/dev-loop/scripts/devtool.py:*), Bash(python .claude/skills/dev-loop/scripts/devtool.py:*)
---

Idea: **$ARGUMENTS**

This only **records**. Do not design, plan, read code or change any file other than through the script. Reply in the user's language.

`DT` below means `python3 .claude/skills/dev-loop/scripts/devtool.py` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run), run from the project root.

## Empty argument

Run `DT brainstorm show` and list the open notes as `#n · one line each`. Stop.

## Record

1. Save the idea **verbatim** — the user's own words, not a rewrite. Pass it on stdin so quotes and line breaks survive:

   ```
   DT brainstorm add <<'EOF'
   <the idea exactly as given>
   EOF
   ```

   If the user's message clearly answers or refines an earlier note, keep it verbatim anyway; the brief reconciles them later.

2. Reply in at most three lines:

   ```
   Noted #<n> (<total> open) — <your one-line reading of the idea>
   ? <at most one question, only if a later brief can't be written without it>
   ```

   No question when the idea is clear enough to brief. Never a list of suggestions or a design. When the notes feel complete, add that `/dev-brief` will turn them into a brief.
