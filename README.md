# work-pipeline

Installable work pipelines for [Claude Code](https://claude.com/claude-code) — bundles of subagents, slash commands and skills that you drop into a project.

## Pipelines

Each pipeline is one folder. Its design doc explains how it works.

| Pipeline | What it does | Commands |
| --- | --- | --- |
| [dev](dev/docs/design.md) | Takes one development request through design → code → test → docs → commit, keeping spec docs and unresolved items for the next request | `/dev` `/dev-optimize` `/dev-optimize-memory` `/dev-limitations` |
| [research](research/docs/design.md) | Finds the key papers on a topic from trusted venues, and analyzes a single paper — claims, evidence, limitations — with every citation verified, downloads papers as PDFs, and makes paper figures and tables (PPTX + PDF) | `/research-list-paper` `/research-summary-paper` `/research-download-paper` `/research-figure` `/research-table` |

## Install

```bash
git clone https://github.com/qkrwhdah03/work-pipeline.git
./work-pipeline/<pipeline>/kit/install.sh /path/to/your-project   # e.g. dev
```

On Windows: `.\work-pipeline\<pipeline>\kit\install.ps1 C:\path\to\your-project`

Re-run the same command to update. Your project's context docs and the rest of its `CLAUDE.md` are kept.

Then open Claude Code in that project and use the pipeline's commands (for dev: `/dev <your request>`).

## Language

Pipeline files are in English, and so is what a pipeline commits to your repository — code comments, context docs, commit messages. Replies and research notes are in **your** language.

## Layout

```
<pipeline>/
├── docs/    design doc + install guide
├── kit/     install scripts + files copied into your project
└── dist/    built zip and PDF  (python tools/build.py <pipeline>)
```

Details and rules for adding a pipeline: [STRUCTURE.md](STRUCTURE.md)
