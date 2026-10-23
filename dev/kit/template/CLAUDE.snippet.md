<!-- DEV-PIPELINE:BEGIN (This block is managed by the install script. You may edit it, but reinstalling overwrites it) -->
## Dev Loop

Development work in this project goes through the `/dev` loop.

```
read context → order(A) → execute(B) → evaluate(C) → limitations·record(D) → wait
```

### Language

The pipeline's own files (skill, agents, commands, templates) are in English. **Everything that goes into the repository is in English too**, whatever language the `/dev` request is in: `.dev/context/` documents (devlog included), `CLAUDE.md`, code comments, and commit messages (subject and body). Translate the request, intent and design; don't mix languages in these.

Only what is not committed follows the user's language — the language of the `/dev` request: reports to the user, and the order · result files in `.dev/loops/` (gitignored).

Keep these in English, because the pipeline looks them up: structural headings (`## Limitations / Improvements`, `## Optimization Targets`, `## Loop Log`, `## Project Specifics`, order · result template headings), STATUS codes, commit body field names (`Intent:`, `Design:`, …), the `loop:` trailer, and spec IDs.

### When It Runs — Development Only

- **The loop runs only when `/dev` is explicitly invoked.** It does not intervene in questions, exploration, explanations, debugging consultations, or casual chat.
- If the user asks for a code change without `/dev`, **ask in one line whether to run it through `/dev`**; if they say no, handle it as usual. Never start the loop on your own.
- These are not loop work: typo/comment fixes, temporary debug output, and tasks the user explicitly marked "just do it quickly."

### Docs = State

There is no separate context store. The files in `.dev/context/` are themselves the project's state.

| File | Question | Changes when |
| --- | --- | --- |
| `.dev/context/00-project.md` | Where does it run | Accounts, repos, environments (**secrets by reference only, never values**) |
| `.dev/context/01-features.md` | What can it do | What the user wants changes |
| `.dev/context/02-design.md` | How does it look | The way it looks changes |
| `.dev/context/03-architecture.md` | How does it work | The implementation approach changes |
| `.dev/context/04-devlog.md` | What's left | Every loop |

Boundary rule: **"it happens" is a feature, "it looks like this" is design, "it's built this way" is architecture.** If an item spans docs, split it and write each part on its own side. Link cross-references in the form `F-012 ↔ D-07 ↔ U-23`.

`.dev/loops/` is volatile. It holds the inter-agent order files, and only the latest 10 are kept.

### 04-devlog Routing

`## Limitations / Improvements` → consumed by **A** on the next `/dev` (behavior-changing)
`## Optimization Targets` → consumed by **E** in `/dev-optimize` (behavior-preserving)

When unsure, route it up. A taking one more look is cheaper than E overstepping.

### Permission Boundaries

| | Role | Writes | Commits |
| --- | --- | --- | --- |
| A `dev-a-architect` | Grasp intent → translate into design, distribute work | order-B, order-C | — |
| B `dev-b-coder` | Modify code | Source code | — |
| C `dev-c-tester` | Write, run, and judge tests | Test code, result | — |
| D `dev-d-recorder` | Analyze → derive limitations, update docs | All of `.dev/context/` | ✓ |
| E `dev-e-optimizer` | Refactor | Source code, 03-architecture | ✓ |

- **B cannot modify test code.** Only C may modify tests, and C also delivers the verdict.
- **E does not touch 01-features or 02-design.**
- **Only D and E may commit.**

### Retry Limits

Max 3 attempts · pass failures on as a summary only (test name + assertion diff + file:line) · stop immediately if the same failure occurs twice in a row · **do not commit when retries are exhausted.**

### Commit Convention

**One loop = one commit.** Code + tests + docs as a single unit.

```
feat(scope): one-line summary

Intent: <underlying intent> (request: "<original wording>")
Design: <one line on the extensible design>
Changes: F-xxx new / D-xx modified
Tests: n added, all passing
Limits: <unresolved> -> devlog#n

loop: YYYY-MM-DD-NNN
```

The `refactor(...)` prefix is E-only.

### Stop Conditions

In these cases, stop the loop and report to the user. Do not proceed.

- A is not confident about the intent (it forks into multiple designs / conflicts with existing specs / the scope can't be stated in one line)
- Schema migrations, mass deletions, major dependency upgrades, breaking changes to public APIs
- The git working tree is not clean (loops are serialized)
<!-- DEV-PIPELINE:END -->
