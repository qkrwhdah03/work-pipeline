# work-pipeline

Installable work pipelines for [Claude Code](https://claude.com/claude-code) — bundles of subagents, slash commands and skills that you drop into a project.

## Pipelines

| Pipeline | What it does | Commands | Skills | Agents |
| --- | --- | --- | --- | --- |
| [dev](dev/docs/design.md) | Runs one dev request through design → code → test → docs → commit, then stops. Refactoring runs as a separate loop. | `/dev` `/dev-optimize` `/dev-limitations` | `dev-loop` | `dev-a-architect` … `dev-e-optimizer` |

Commands are what you type. Skills and agents are used by the pipeline itself — you don't call them.

## Install

```bash
git clone https://github.com/qkrwhdah03/work-pipeline.git
./work-pipeline/dev/kit/install.sh /path/to/your-project
```

On Windows: `.\work-pipeline\dev\kit\install.ps1 C:\path\to\your-project`

Re-run the same command to update. Your project's context docs and the rest of its `CLAUDE.md` are kept.

Then open Claude Code in that project and run `/dev <your request>`.

## Language

Pipeline files are in English. When you use a pipeline, it reports and writes docs in **your** language.

## Layout

```
<pipeline>/
├── docs/    design doc + install guide
├── kit/     install scripts + files copied into your project
└── dist/    built zip and PDF  (python tools/build.py <pipeline>)
```

Details and rules for adding a pipeline: [STRUCTURE.md](STRUCTURE.md)
