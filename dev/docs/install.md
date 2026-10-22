# Development Pipeline Install Kit

The design doc (`dev-pipeline.pdf`) implemented as something that actually runs in Claude Code.

---

## Install

Unzip it and pass the **project folder as the argument**.

**Windows (PowerShell)**

```powershell
cd <unzipped folder>
.\install.ps1 C:\path\to\my-project
```

If blocked by the execution policy:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 C:\path\to\my-project
```

**macOS / Linux / Git Bash**

```bash
./install.sh /path/to/my-project
```

Safe to re-run. Existing documents in `.dev/context/` are preserved, and only the marker block in `CLAUDE.md` is replaced.

---

## What gets installed

```
<project>/
├── CLAUDE.md                    loop rules (marker block) + project specifics
├── .claude/
│   ├── agents/                  5 subagents A–E — the implementation of context isolation
│   │   ├── dev-a-architect.md
│   │   ├── dev-b-coder.md
│   │   ├── dev-c-tester.md
│   │   ├── dev-d-recorder.md
│   │   └── dev-e-optimizer.md
│   ├── commands/                /dev · /dev-optimize · /dev-limitations
│   ├── skills/dev-loop/         procedures · templates · doc update checklist · scripts/devtool.py
│   └── hooks.optional.json      enforce tests before commit (off by default)
└── .dev/
    ├── context/                 persistent — the project's state
    │   ├── 00-project.md
    │   ├── 01-features.md
    │   ├── 02-design.md
    │   ├── 03-architecture.md
    │   └── 04-devlog.md
    ├── loops/                   volatile — last 10 only (gitignored)
    └── templates/               order-B · order-C · result formats
```

---

## Why not a single skill

Split four ways, exactly as mapped in the design doc. **Rules go in CLAUDE.md, procedures in skills, isolation in subagents, enforcement in hooks.**

| Mechanism | Owns | Why |
| --- | --- | --- |
| **subagent** | A–E | Skills can't isolate context. If everything piles up in one conversation, tokens grow quadratically as the loop gets longer. Permission boundaries (B can't edit tests) also only hold with isolation. |
| **command** | `/dev` `/dev-optimize` `/dev-limitations` | Explicit entry points. This is the switch that makes it run "only during development". |
| **CLAUDE.md** | rules | Pins permission boundaries, commit conventions and stop conditions where they're always read. |
| **skill** | procedures · templates | Long references read **only when needed**, such as document boundary rules and update checklists. |

---

## When it runs — development only

The loop runs **only when `/dev` is called explicitly**. It stays out of questions, exploration, debugging advice and small talk.

If a code change request comes in without `/dev`, Claude just asks in one line "Run this through the loop?", and if you say no it handles it as usual.

---

## Usage

```
/dev add social login
```

One loop:

```
Preflight  check git tree is clean → create loops/2026-10-21-001/
A          read full context + limitations → grasp intent → order-B.md, order-C.md
B ∥ C      B writes code, C writes tests from acceptance criteria (C doesn't wait for B)
C          run tests → verdict → result.md
           on failure, only a summary goes to B → max 3 tries · stop at once on the same failure twice in a row
D          match check → update 01–04 → one commit per loop
Wait       stop until the next request
```

```
/dev-optimize        behavior-preserving refactor of the devlog's 'Optimization Targets' (manual only)
/dev-limitations     view accumulated limitations / optimization targets
```

---

## First run

If `.dev/context/` is empty, **the first `/dev` ends as a bootstrap.** A scans the repo, back-fills the project specifics in `CLAUDE.md` (test command, etc.) and documents `00–03` from the current code, then stops. Skim and fix those documents, then call `/dev` again.

For an existing project, don't skimp on this bootstrap loop. **The first 3–5 loops are not hands-off.** With empty context, A rescans all the code every time.

Writing just the **test command** under `## Project Specifics` in `CLAUDE.md` beforehand makes even the first loop far more accurate.

---

## Optional: enforce tests before commit (hook)

Off by default. To turn it on, merge the `hooks` block of `.claude/hooks.optional.json` into `.claude/settings.json` and replace `<TEST_COMMAND>` with the project's test command.

It also fires on commits made outside the loop, so it's better to turn it on once you're used to the loop.

---

## Model assignment

Adjust via `model` in the frontmatter of `.claude/agents/*.md`. Defaults:

| | Model | Reason |
| --- | --- | --- |
| A | `opus` | The only agent that reads the full context. **A being quietly wrong is the only real risk**, so tokens are concentrated here. |
| B · C · E | `inherit` | Follows the session model |
| D | `sonnet` | Formulaic recording work |

---

## Using it across projects

Keep this kit folder and re-run `install.ps1 <path>` for each new project. Don't install globally (`~/.claude/`) — the loop would follow every session and "development only" would break.
