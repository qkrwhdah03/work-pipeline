# Research Pipeline Install Kit

Two Claude Code commands for the literature: find the key papers on a topic, and analyze one paper in depth. Design: `research-pipeline.pdf`.

## Install

Pass the folder you do research in (a paper project, a reading-notes folder, …).

**Windows (PowerShell)**

```powershell
.\install.ps1 C:\path\to\my-research
```

**macOS / Linux / Git Bash**

```bash
./install.sh /path/to/my-research
```

Safe to re-run to update. Saved lists and analyses in `.research/` are never touched, and only the research marker block in `CLAUDE.md` is replaced.

## Use

```
/research-list-paper 3D Gaussian Splatting, since 2023
/research-summary-paper https://arxiv.org/abs/2308.04079
```

| Command | Gives you | Saved to |
| --- | --- | --- |
| `/research-list-paper <topic>` | 10–15 key papers (foundational + recent) with venue, year, paper and code links, and a short summary each | `.research/lists/` |
| `/research-summary-paper <paper>` | where the paper fits, its claims, the evidence for each, and its limitations | `.research/papers/` |

Options go in plain words after the topic: `since 2023`, `top 10`, `foundational only`. A paper can be a title, arXiv ID or URL, DOI, or a local PDF path.

Results are written in the language you ask in.

## Optional: API keys

Everything works without keys. Semantic Scholar is often rate-limited without one; if you have keys, set them as environment variables and they'll be used:

- `SEMANTIC_SCHOLAR_API_KEY`
- `OPENALEX_API_KEY`

## What gets installed

```
<folder>/
├── CLAUDE.md                     research block (commands, language, integrity rules)
├── .claude/commands/             research-list-paper.md, research-summary-paper.md
├── .claude/skills/research-sources/
└── .research/lists/, .research/papers/
```
