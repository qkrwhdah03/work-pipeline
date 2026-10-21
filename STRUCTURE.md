# work-pipeline Structure

A collection of work pipelines for Claude Code (bundles of agents, commands and skills). One pipeline is one folder.

## Global rules

These apply to every pipeline in this repository.

**Language: the kit is English, usage follows the user's language.**

- Everything in this repository is written in English — docs, skills, agents, commands, templates, scripts, and the structural headings the pipelines look up.
- What a pipeline produces while in use — reports to the user, context document content, order · result files, commit messages — is written in the user's language (the language of their request).
- Identifiers the pipeline depends on stay in English even in the user's output: structural headings, STATUS codes, commit field names, trailers, spec IDs.
- Each pipeline states this in a `### Language` section of its CLAUDE snippet, so it takes effect in the installed project.

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

## Rules for a new pipeline

1. **Folder name = pipeline name = prefix.** One lowercase word (`dev`, `review`, …).
2. **Prefix every command, agent and skill name.** Like `/dev`, `/dev-optimize`, `dev-a-architect`. That way several pipelines can be installed in one project without collisions.
3. **Touch only your own marker block in CLAUDE.md.** `<!-- <NAME>-PIPELINE:BEGIN -->` … `<!-- <NAME>-PIPELINE:END -->`. Content outside the block and other pipelines' blocks are preserved.
4. **Install script rules**
   - Always overwrite your own files under `.claude/`.
   - Preserve context documents the user has built up (e.g. `.dev/context/`) if they already exist.
   - Delete files that were renamed or removed (e.g. the old `optimize.md` in `dev`).
   - Ship both `install.sh` and `install.ps1`, and keep their behavior in sync.
5. **Follow the global rules above**, including the `### Language` section in the CLAUDE snippet.
6. **The first `# Title` line of `docs/design.md` becomes the PDF title.**

## Pipelines

| Name | What it does | Commands | Installed in |
| --- | --- | --- | --- |
| [dev](dev/docs/design.md) | Takes one development request around a full loop: design → implement → test → document → commit. Optimization runs as a separate loop | `/dev` `/dev-optimize` `/dev-limitations` | `asset-manager` |
