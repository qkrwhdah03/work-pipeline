---
name: dev-loop
description: Dev loop reference for this project — the .dev/context spec system and boundary rules, order/result file formats, 04-devlog routing, commit convention, and the doc-update checklist. Use when running a /dev or /dev-optimize loop, or when editing .dev/context/ docs directly. Do not use for general coding questions or work outside the loop.
user-invocable: false
---

# Dev Loop Reference

## Loop

```
read context → order(A) → execute(B) → evaluate(C) → limitations·record(D) → wait
                                      └ E · optimization is a separate loop (/dev-optimize)
```

Three principles explain every other design decision.

1. **Limitations become the next order.** The loop's final output is not code but a list of unresolved items.
2. **Docs are the state.** `.dev/context/` is itself the project's state. Updating docs is not extra work; it is what closes the loop.
3. **Context isolation is token efficiency.** Instructions are split into files so each agent reads only its own.

## Script

`scripts/devtool.py` (Python 3, standard library only) does the loop's bookkeeping. Run it from the project root as `python3 .claude/skills/dev-loop/scripts/devtool.py <command>` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run).

| Command | Does |
| --- | --- |
| `preflight [--no-loop]` | git repo + clean working tree check; creates `.dev/loops/<LOOP_ID>/` and prints the ID |
| `devlog [limitations\|optimization\|log\|all] [--count]` | prints 04-devlog sections, or just their item counts |
| `prune-loops [--keep 10]` | deletes the oldest loop folders |
| `test [--loop LOOP_ID] -- <test command>` | runs the tests; prints exit code, summary and failure lines only; full log to `.dev/loops/<LOOP_ID>/test.log` |

Always run tests through `test` — raw test output is the biggest token cost in a loop.

## Spec Doc Boundary Rules

| Doc | Question | Changes when |
| --- | --- | --- |
| `01-features` | What can it do | What the user wants changes |
| `02-design` | How does it look | The way it looks changes |
| `03-architecture` | How does it work | The implementation approach changes |

**"It happens" is a feature, "it looks like this" is design, "it's built this way" is architecture.**

Items that span docs are split and written into each side. Do not cram them into one doc.

**Cross-references required**: `F-012 ↔ D-07 ↔ U-23`. Without them, the three docs age separately and drift apart.

Examples for borderline calls:

- "Lock after 3 failed logins" → **feature** (F). The lock message text and placement → **design** (D). Where the counter is stored → **architecture** (U).
- "Spinner on the button while loading" → **design** (D). The fact that a loading state exists is itself a state transition of the **feature** (F).
- "Retry API calls 3 times" → **feature** if visible to the user, **architecture** if not.

## 04-devlog Routing

```markdown
## Limitations / Improvements        ← consumed by A (behavior-changing)
- Token refresh not implemented (F-031)

## Optimization Targets            ← consumed by E (behavior-preserving)
- parseConfig() is 180 lines with 4 responsibilities
```

**When unsure, route it up (to A).** A taking one more look is cheaper than E overstepping.

Rule of thumb: **if not a single line of existing tests changes, it's E; if tests must change, it's A.**

## order / result Formats

Use `.dev/templates/order-B.md`, `order-C.md`, and `result.md` as-is.

Key constraint: **order-B and order-C do not reference each other.** B and C never read each other's files, so each must be self-sufficient, and public interface signatures are written **identically** in both. If these diverge, the whole loop diverges.

## Failure Handoff Format

This is all that gets passed to B.

```
- `test name` — one or two lines of assertion diff — `path/file.ts:120`
```

Full logs, stack traces, build output, and lists of passing tests are **never** passed on.

## Doc-Update Checklist (D only)

- [ ] One-line match verdict — order-B's design intent vs. the actual diff
- [ ] 01-features — if behavior changed, update/add the F item
- [ ] 02-design — if what's visible changed, update/add the D item
- [ ] 03-architecture — if modules, interfaces, or dependencies changed, update/add the U item
- [ ] Link cross-reference IDs (`F ↔ D ↔ U`)
- [ ] 04-devlog `## Limitations / Improvements` — unresolved items left by this loop
- [ ] 04-devlog `## Optimization Targets` — structural issues noticed (record only; do not invoke E)
- [ ] 04-devlog `## Loop Log` — add one line
- [ ] Delete lines for resolved existing limitations + note the resolving loop ID
- [ ] Commit message includes all of **Intent / Design / Changes / Tests / Limits / loop ID**
- [ ] Delete `.dev/loops/` entries beyond the latest 10

## Commit Convention

**One loop = one commit.** Code + tests + docs as a single unit.

```
feat(auth): add social login

Intent: reduce new-signup drop-off (request: "add social login")
Design: abstracted behind an AuthProvider interface; OAuth providers are extensible
Changes: F-031 new / D-12 modified / U-08 new
Tests: 7 added, all passing
Limits: token refresh not implemented -> devlog#14

loop: 2026-10-21-001
```

Never omit `Intent`. With no approval gate, **this is the only place where what A intended can be traced after the fact.**

`refactor(...)` is an E-only prefix.

## Early Adoption

**The first 3–5 loops are not automatic.** If `01~03` are empty, A has no context to read and re-scans the entire codebase every time. For an existing project, spend the first loop on **"reverse-documenting the current state."**

**A being silently wrong is the only real risk.** Mistakes by B, C, and D surface through tests or diffs, but if A misreads the intent you get "a perfectly implemented wrong feature" — and the tests pass too. So A asks back when unsure, and D leaves a match verdict at the end of every loop.
