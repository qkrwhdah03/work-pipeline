# work-pipeline Structure

A collection of work pipelines for Claude Code (bundles of agents, commands and skills). One pipeline is one folder.

## Global rules

These apply to every pipeline in this repository.

**Language: the kit is English, usage follows the user's language.**

- Everything in this repository is written in English — docs, skills, agents, commands, templates, scripts, and the structural headings the pipelines look up.
- What a pipeline produces while in use — reports to the user, context document content, order · result files, commit messages — is written in the user's language (the language of their request).
- Identifiers the pipeline depends on stay in English even in the user's output: structural headings, STATUS codes, commit field names, trailers, spec IDs.
- Each pipeline states this in a `### Language` section of its CLAUDE snippet, so it takes effect in the installed project.

**Token efficiency: mechanical work goes in scripts.**

Anything deterministic a pipeline does on every run — fetching and parsing pages or APIs, git checks, ID and folder bookkeeping, running tests and condensing their output — lives in a script shipped with the kit. Claude calls the script instead of re-deriving the same steps each run.

- One entry script per skill: `skills/<skill>/scripts/<name>tool.py`, with subcommands (`devtool.py preflight`, `researchtool.py meta …`).
- Python 3 standard library only — nothing to install.
- Print only what the next step needs, as compact plain text. Bulky data (full text, full logs) goes to a file; print its path and a short outline so Claude reads only the part it needs.
- Fail loudly: one `ERROR: …` line and a non-zero exit.
- Commands say how to run it: `python3 <script> …`, or `python <script> …` where `python3` isn't available (Windows).

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
| Script | `skills/<skill>/scripts/<name>tool.py` | `skills/dev-loop/scripts/devtool.py` |
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
| [dev](dev/docs/design.md) | Takes one development request around a full loop: design → implement → test → document → commit. Optimization runs as a separate loop | `/dev` `/dev-optimize` `/dev-limitations` | `dev-loop` | `dev-a-architect` … `dev-e-optimizer` |
| [research](research/docs/design.md) | Finds the key papers on a topic from trusted venues, and analyzes one paper: big picture, claims, evidence, limitations | `/research-list-paper` `/research-summary-paper` | `research-sources` | — |
