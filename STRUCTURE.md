# work-pipeline Structure

A collection of work pipelines for Claude Code (bundles of agents, commands and skills). One pipeline is one folder.

## Global rules

These apply to every pipeline in this repository.

**Language: the kit and what goes into the repository are English; everything else follows the user's language.**

- Everything in this repository is written in English — docs, skills, agents, commands, templates, scripts, and the structural headings the pipelines look up.
- The rule of thumb: **what goes public, in the repository and its version history, is English; what the user reads is in the user's language.**
- English, whatever language the request is in: code comments, context documents (`.dev/context/`), `CLAUDE.md`, and commit messages (subject and body). The pipeline translates the request and its own notes; it doesn't mix languages in these.
- The user's language (the language of their request): replies and reports to the user, gitignored scratch files (`.dev/loops/` order · result files), and material written for the user to read in `.research/` (paper lists, summaries).
- Identifiers the pipeline depends on stay in English even in the user's output: structural headings, STATUS codes, commit field names, trailers, spec IDs.
- Each pipeline states this in a `### Language` section of its CLAUDE snippet, so it takes effect in the installed project.

**Cross-platform: every pipeline works on Windows, macOS and Linux.**

- Ship both installers — `install.ps1` (Windows) and `install.sh` (macOS, Linux, Git Bash) — with the same behavior. `.sh` files are LF (enforced by `.gitattributes`).
- Scripts use only the Python standard library and portable calls: `os.path` / `pathlib` for paths, no hard-coded `/` or `\`, no shell-specific syntax, UTF-8 for every file read and written, and stdout set to UTF-8 (Windows consoles default to another code page).
- Commands give the interpreter per OS: `python3 …` on macOS / Linux, `python …` on Windows. Allow both in `allowed-tools`.
- File names a pipeline creates must be valid on all three systems: no `<>:"/\|?*`, no trailing dot or space.
- User folders are found per OS, not assumed (e.g. Downloads: the Windows registry entry, then XDG, then `~/Downloads`).
- When a feature needs an outside program (PowerPoint, LibreOffice, Chrome), support what each OS has — e.g. PowerPoint on Windows, LibreOffice on macOS / Linux — and when none is present, still produce the main output and say in one line what is missing.
- Shell commands a pipeline runs for the user (test commands, build commands) come from the project's own settings, never hard-coded for one OS.

**Token efficiency: mechanical work goes in scripts.**

Anything deterministic a pipeline does on every run — fetching and parsing pages or APIs, git checks, ID and folder bookkeeping, running tests and condensing their output — lives in a script shipped with the kit. Claude calls the script instead of re-deriving the same steps each run.

- One entry script per skill: `skills/<skill>/scripts/<name>tool.py`, with subcommands (`devtool.py preflight`, `researchtool.py meta …`). When a pipeline has scripts in more than one skill, name the others after their topic (`research-figures/scripts/figuretool.py`).
- Python 3 standard library only — nothing to install.
- Print only what the next step needs, as compact plain text. Bulky data (full text, full logs) goes to a file; print its path and a short outline so Claude reads only the part it needs.
- Fail loudly: one `ERROR: …` line and a non-zero exit.
- Commands say how to run it: `python3 <script> …` on macOS / Linux, `python <script> …` on Windows (where `python3` is usually a Microsoft Store stub that doesn't run).

**Visibility: only commands are user-facing.**

The user starts a pipeline through its commands. Skills are internal references that commands and agents load, so they stay out of the `/` menu where they would look like commands.

- Every skill's frontmatter has `user-invocable: false`. Claude can still load it (the Skill tool, or a command that says to read it); it just isn't listed for the user to type.
- Anything the user should be able to run directly is a command (`commands/<name>-….md`), not a skill.
- Never set `disable-model-invocation: true` on a pipeline skill — that does the opposite and hides it from Claude.

**Context budget: what is always loaded stays minimal.**

A pipeline's `CLAUDE.md` block is read in every session — research, chat, unrelated work — and again by every subagent it spawns, so each line there is paid many times over.

- The block holds only what must apply in every session: when the pipeline runs (and when it must not), rules that also bind work outside its commands (e.g. language), and one line naming the skill that holds the rest. Aim for ~400 tokens or less.
- Everything else — boundaries, permissions, retry limits, formats, checklists — lives in the pipeline's skill or agent files, read only when a command runs. Don't repeat a rule in both places.
- Files that a pipeline re-reads on every run and that grow with use (context docs, logs) need a way to stay small without losing meaning — a compaction step with a deterministic check, like `/dev-optimize-memory`.

**Permissions: pre-approve narrowly.**

A command's `allowed-tools` lists exactly what it needs, so it runs without repeated approval prompts but can't do more than its job.

- Allow the pipeline's own scripts by path — `Bash(python3 .claude/skills/<skill>/scripts/<name>tool.py:*)` and the same with `python` — and specific commands it needs (e.g. `Bash(git status:*)`), never bare `Bash`.
- Read-only tools (`Read`, `Glob`, `Grep`) and the tools the job is about (`WebSearch`, `WebFetch`, `Task`, `Write`) are listed by name.
- Agents list only the tools their role needs in `tools:`.

## Layout

```
work-pipeline/
├── STRUCTURE.md              this document — layout, rules, pipeline list
├── tools/
│   └── build.py              builds the distributables (zip · PDF)
│
└── <name>/                   one pipeline (e.g. dev)
    ├── docs/
    │   ├── design.md         design doc — why it works this way (source)
    │   └── install.md        install guide — shipped as README.md inside the kit zip (source)
    ├── kit/                  install kit source — edit here
    │   ├── install.sh        macOS / Linux / Git Bash
    │   ├── install.ps1       Windows
    │   └── template/         files copied into the target project
    │       ├── CLAUDE.snippet.md      CLAUDE.md marker block
    │       ├── CLAUDE.project.md      project section, used when CLAUDE.md is created
    │       ├── claude/                → <project>/.claude/
    │       │   ├── agents/
    │       │   ├── commands/
    │       │   └── skills/
    │       └── <name>/ etc.           → <project>/.<name>/ etc. (context documents)
    └── dist/                 build output — never edit by hand
        ├── <name>-pipeline-kit.zip
        └── <name>-pipeline.pdf
```

**Only `docs/` and `kit/` are source.** `dist/` can be regenerated at any time, so don't edit it by hand.

## Build

```bash
python tools/build.py dev      # one pipeline
python tools/build.py --all    # all of them
```

- `kit/` + `docs/install.md` → `dist/<name>-pipeline-kit.zip` (top-level folder in the zip: `<name>-pipeline-kit/`)
- `docs/design.md` → `dist/<name>-pipeline.pdf` (headless Chrome/Edge, renders mermaid diagrams, needs internet)

Re-run the build after editing `docs/` or `kit/`.

## Installing into a project / updating

You can install straight from `kit/` without going through the zip.

```bash
./dev/kit/install.sh /path/to/project
```

Installing must be safe to re-run. Updating uses the same command.

## Naming

`<name>` is the pipeline name: one short lowercase word (`dev`, `review`, …). It is the folder name and the prefix for everything the pipeline installs. Words are joined with `-`, all lowercase.

| What | Pattern | dev example |
| --- | --- | --- |
| Pipeline folder | `<name>/` | `dev/` |
| Main command | `/<name>` | `/dev` |
| Other commands | `/<name>-<verb or noun>` | `/dev-optimize`, `/dev-limitations` |
| Command file | `commands/<command without />.md` | `commands/dev-optimize.md` |
| Agent | `<name>-<role letter>-<role>` — letters in run order | `dev-a-architect`, `dev-e-optimizer` |
| Skill | `<name>-<topic>` | `dev-loop` |
| Script | `skills/<skill>/scripts/<name>tool.py` (more skills: `<topic>tool.py`) | `skills/dev-loop/scripts/devtool.py` |
| Project data folder | `.<name>/` | `.dev/` |
| CLAUDE.md markers | `<!-- <NAME>-PIPELINE:BEGIN -->` … `<!-- <NAME>-PIPELINE:END -->` | `DEV-PIPELINE` |
| Built files | `<name>-pipeline-kit.zip`, `<name>-pipeline.pdf` | `dev-pipeline-kit.zip` |

- An agent's or skill's `name:` in frontmatter must equal its file or folder name.
- Context documents inside `.<name>/context/` are numbered `NN-<topic>.md` (`00-project.md`, `04-devlog.md`).
- **Renaming is a breaking change.** When you rename a command, agent or skill, make the installers delete the old file (see the install script rules below), and update every reference: kit, docs, README.md, this file.

## Rules for a new pipeline

1. **Follow the naming rules above.**
2. **Keep commands, agents and skills inside your own prefix.** Never ship an unprefixed name — several pipelines must be installable in one project without collisions.
3. **Touch only your own marker block in CLAUDE.md.** `<!-- <NAME>-PIPELINE:BEGIN -->` … `<!-- <NAME>-PIPELINE:END -->`. Content outside the block and other pipelines' blocks are preserved.
4. **Install script rules**
   - Always overwrite your own files under `.claude/`.
   - Preserve context documents the user has built up (e.g. `.dev/context/`) if they already exist.
   - Delete files that were renamed or removed (e.g. the old `optimize.md` in `dev`).
   - Ship both `install.sh` and `install.ps1`, and keep their behavior in sync.
5. **Follow the global rules above**, including the `### Language` section in the CLAUDE snippet.
6. **The first `# Title` line of `docs/design.md` becomes the PDF title.**
7. **README.md gets one table row per pipeline** — name (linked to its design doc), one-line description, commands. Details belong in the pipeline's own `docs/`, so the README stays short as pipelines are added.

## Pipelines

| Name | What it does | Commands | Skills | Agents |
| --- | --- | --- | --- | --- |
| [dev](dev/docs/design.md) | Takes one development request around a full loop: design → implement → test → document → commit; refactoring and context compaction follow automatically when due | `/dev` `/dev-optimize` `/dev-optimize-memory` `/dev-limitations` | `dev-loop` | `dev-a-architect` … `dev-f-compactor` |
| [research](research/docs/design.md) | Finds the key papers on a topic from trusted venues, and analyzes one paper: big picture, claims, evidence, limitations; downloads PDFs; makes paper figures and booktabs tables as PPTX + PDF | `/research-list-paper` `/research-summary-paper` `/research-download-paper` `/research-figure` `/research-table` | `research-sources` `research-figures` | — |
