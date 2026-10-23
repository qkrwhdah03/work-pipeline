---
description: Compact the .dev/context docs — same meaning, fewer tokens for every later loop (F)
argument-hint: (no arguments)
allowed-tools: Task, Read, Bash(python3 .claude/skills/dev-loop/scripts/devtool.py:*), Bash(python .claude/skills/dev-loop/scripts/devtool.py:*)
---

Compact the project's dev context now. `/dev` also does this on its own when the context grows past its budget; this command runs it on demand.

Reply in the user's language.

## Preflight

`DT` below means `python3 .claude/skills/dev-loop/scripts/devtool.py` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run), run from the project root.

1. `DT preflight --no-loop` — **stop on `ERROR`**. F checks its result against HEAD and rolls back with git, so a clean tree is a precondition.
2. Confirm no `/dev` or `/dev-optimize` loop is running — they write the same docs.
3. `DT memory` — if `context: missing`/no files, stop and say so.

## Run

Call `Task` with `subagent_type: dev-f-compactor`. Pass: `Trigger: manual` (compact even if under budget).

## Report

```
Memory · <COMPACTED | NO_CHANGE>
Tokens   ~<before> -> ~<after> (<-n%>)   ← paid by A and D on every /dev
Commit   <sha> <title>                   ← NO_CHANGE: the reason
```
