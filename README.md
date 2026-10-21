# work-pipeline

Installable work pipelines for [Claude Code](https://claude.com/claude-code) — bundles of subagents, slash commands and skills that you drop into a project.

## Pipelines

| Pipeline | What it does |
| --- | --- |
| [dev](#dev) | Takes one development request through design → code → test → docs → commit |

### dev

Turns a development request into a full, documented change — then stops and waits for the next one.

An architect agent reads the project's spec docs and turns your request into a design. A coder and a tester work from that design in parallel. A recorder updates the docs, writes down what's still unresolved, and commits. Next time, the architect starts from those leftovers, so the design stays consistent and context isn't lost between requests.

| You type | Does |
| --- | --- |
| `/dev <request>` | Run one loop for the request |
| `/dev-limitations` | Show unresolved items and refactoring candidates |
| `/dev-optimize` | Refactor the recorded candidates without changing behavior |

Used internally (you don't call these): skill `dev-loop`, agents `dev-a-architect` → `dev-b-coder` · `dev-c-tester` → `dev-d-recorder`, plus `dev-e-optimizer`.

Full design: [dev/docs/design.md](dev/docs/design.md)

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
