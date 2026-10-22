---
description: One dev loop iteration — design translation (A) → implementation (B) ∥ tests (C) → verdict → record and commit (D)
argument-hint: <dev request>
allowed-tools: Task, Read, Glob, Grep, Bash(python3 .claude/skills/dev-loop/scripts/devtool.py:*), Bash(python .claude/skills/dev-loop/scripts/devtool.py:*)
---

Dev request: **$ARGUMENTS**

You are the **orchestrator** of this loop. You do not read or modify code yourself. You call a subagent for each stage and pass **only the summaries** they return to the next stage. Never forward one agent's report wholesale to another agent — pass only the fields specified below.

Report progress in one line per stage. Do not spell out intermediate results at length.

---

## 0. Preflight

`DT` below means `python3 .claude/skills/dev-loop/scripts/devtool.py` (`python …` if `python3` isn't available), run from the project root.

Run `DT preflight`. It checks this is a git repo and **the working tree is clean** (this serializes loops, so E and the main loop never modify the same files at once), then creates `.dev/loops/<LOOP_ID>/` and prints `LOOP_ID: …`.

- `ERROR: …` → stop and relay it (e.g. ask the user to commit or stash, then call again).
- `context: missing` → fine; A will bootstrap.

---

## 1. A · Design translation

Call `Task` with `subagent_type: dev-a-architect`. Pass:

```
LOOP_ID: <id>
Request: $ARGUMENTS
```

Branch on A's `STATUS`.

- `NEEDS_CLARIFICATION` → **stop the loop and relay A's questions to the user verbatim.** Do not proceed on guesses. When the user answers, combine the original request + the answers and start again from step 1.
- `DESTRUCTIVE_STOP` → stop and report the details. Resume only if the user explicitly says to proceed.
- `BOOTSTRAPPED` → the context documents were just created. Stop, and tell the user to review the documents and then call `/dev` again.
- `READY` → go to step 2.

---

## 2. B · Implementation ∥ C · Test writing (concurrent)

**Call both Tasks at the same time in a single message.** C can write tests from A's acceptance criteria alone, so it does not wait for B.

- `subagent_type: dev-b-coder` — pass: `LOOP_ID: <id>` / `MODE: IMPLEMENT`
- `subagent_type: dev-c-tester` — pass: `LOOP_ID: <id>` / `MODE: WRITE`

Each reads its own order file from `.dev/loops/<LOOP_ID>/`. Do not copy the order contents into the prompt.

If B returns `STATUS: STUCK`, skip step 3 and go to step 5 (failure handling).

---

## 3. Verdict

Call `subagent_type: dev-c-tester`. Pass: `LOOP_ID: <id>` / `MODE: VERIFY`

- `PASS` → go to step 4.
- `FAIL` → apply the retry rules below.

### Retry rules — strict

1. **At most 3 times.** When exhausted, stop and go to step 5.
2. **Pass failures as summaries only.** Pass B only the `Failure Summary` C returned (test name + assertion diff + file:line). **Never pass full logs, stack traces, or build output.**
3. **Same failure twice in a row → stop immediately.** If the set of failed test names is the same as the previous attempt, do not use up all 3; go straight to step 5. Circling the same spot is not solved by retrying.
4. Call B again: `subagent_type: dev-b-coder`, `MODE: FIX`, `Attempt: n/3`, `Failure Summary: <exactly what C gave>`.
5. When B returns, run C `MODE: VERIFY` again.
6. If B raised a `TEST_DISPUTE`, pass that text to C for a ruling. On `DISPUTE_ESCALATE`, stop the loop and report to the user that A needs to redesign.

---

## 4. D · Record (on PASS)

Call `subagent_type: dev-d-recorder`. Pass:

```
LOOP_ID: <id>
OUTCOME: PASSED
Retries: <n>
```

D updates the documents and commits as **one loop = one commit**. Go to step 6.

---

## 5. Failure handling (retries exhausted / same failure twice in a row / B STUCK)

**Do not commit.** Call `subagent_type: dev-d-recorder`:

```
LOOP_ID: <id>
OUTCOME: FAILED
Reason: retries exhausted | same failure twice in a row | B STUCK
Blocked at: <C's last Failure Summary or B's STUCK report>
```

D records the cause of failure in 04-devlog. Do not touch the working tree — the user decides whether to revert. Go to step 6.

---

## 6. Report and wait

Tell the user only the following. Then **stop.** Wait for the next request. Do not continue with other work or call E.

```
Loop <LOOP_ID> · <passed | failed>

Intent    <A's one line>
Changes   <B's file count> files, <n> tests added
Verdict   <C's one line>  (<n> retries)
Match     <D's one-line match verdict>
Commit    <sha> <title>          ← on failure, 'no commit'

Limitations carried over to the next loop
- ...
```

If limitations have piled up, add one line saying they can be viewed with `/dev-limitations`. If optimization targets have piled up, **only suggest** `/dev-optimize` — do not call it yourself.
