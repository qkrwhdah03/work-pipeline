---
description: Optimization loop — behavior-preserving refactors of the devlog's optimization targets (multiple items allowed)
argument-hint: [target items (all if omitted)]
allowed-tools: Task, Read, Glob, Grep, Bash(python3 .claude/skills/dev-loop/scripts/devtool.py:*), Bash(python .claude/skills/dev-loop/scripts/devtool.py:*)
---

Optimization targets: **$ARGUMENTS** (if empty, E processes all of `## Optimization Targets` in `04-devlog.md`, starting with the narrowest impact)

## Preflight

`DT` below means `python3 .claude/skills/dev-loop/scripts/devtool.py` (`python …` if `python3` isn't available), run from the project root.

1. `DT preflight --no-loop` — **stop on `ERROR`** (not a git repo, or the working tree is not clean). E must roll back on failure, so a clean tree is a precondition.
2. Confirm the main dev loop is not running. E and the main loop touch the same code, so **never run them at the same time.**
3. `DT devlog optimization --count` — if it is 0, stop and say so.

## Run

Call `Task` with `subagent_type: dev-e-optimizer`. Pass: `Target: $ARGUMENTS` (or `Target: all`).

There is no limit on the number. E processes the target items in order, **one at a time**: refactor → test → commit (or roll back). If one item is rolled back, the remaining items still proceed.

## Report

```
Optimization · done <n> / rolled back <n> / handed off <n>

[1] <STATUS>  <devlog item>
    Changes  <file list>
    Tests    all <n> existing passing / 0 tests modified
    Commit   <sha> <title>
[2] ...
```

- `ROLLED_BACK` → state the cause for that item. Do not retry.
- `HANDED_OFF` → state that the item needs test changes and so was handed off to A, and add that A will read it on the next `/dev`.
