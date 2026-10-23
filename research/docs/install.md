# Research Pipeline Install Kit

Claude Code commands for the literature: find the key papers on a topic, analyze one paper in depth, download papers as PDFs, and make paper figures and results tables. Design: `research-pipeline.pdf`.

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

Add `--with-animation` (Windows: `-WithAnimation`) to set up Manim for `/research-animation` right away — otherwise it is offered on first use. It goes into its own environment in your user cache (~0.5 GB, once per machine), not into your Python.

Safe to re-run to update. Saved lists and analyses in `.research/` are never touched, and only the research marker block in `CLAUDE.md` is replaced.

## Use

```
/research-list-paper 3D Gaussian Splatting, since 2023
/research-summary-paper https://arxiv.org/abs/2308.04079
/research-download-paper SplaTAM
/research-figure overview of our pipeline: images → SfM → 3D Gaussians → rasterizer
/research-table <paste your results>  — Ours was trained without depth prior
/research-animation depth becomes 3D points, which set the RoPE angles inside the ViT
```

| Command | Gives you | Saved to |
| --- | --- | --- |
| `/research-list-paper <topic>` | 10–15 key papers (foundational + recent) in a table: slide-ready citation, paper · code · BibTeX links, and a short summary each | `.research/lists/` |
| `/research-summary-paper <paper>` | where the paper fits, its claims, the evidence for each, and its limitations | `.research/papers/` |
| `/research-download-paper <paper>` | the PDF, named `<year>. <title> (<venue>).pdf`, a `.txt` beside it (citation, links, BibTeX), and `index.txt` + `references.bib` for the whole folder | `.research/pdfs/`, or a folder you name (`… to ~/papers`) |
| `/research-figure <description>` | a paper figure: editable PPTX, PDF for LaTeX, PNG preview | `.research/figures/` |
| `/research-table <data>` | a booktabs results table with notes under it: PPTX, PDF, PNG | `.research/tables/` |
| `/research-animation <description>` | a short talk animation: MP4 (1080p), GIF, and the editable `scene.py` | `.research/animations/` |

Options go in plain words after the topic: `since 2023`, `top 10`, `foundational only`. A paper can be a title, arXiv ID or URL, DOI, or a local PDF path.

Results are written in the language you ask in.

PDF export of figures and tables uses PowerPoint (Windows) or LibreOffice. Without either, the `.pptx` is still created.

## Optional: API keys

Everything works without keys. Semantic Scholar is often rate-limited without one; if you have keys, set them as environment variables and they'll be used:

- `SEMANTIC_SCHOLAR_API_KEY`
- `OPENALEX_API_KEY`

## What gets installed

```
<folder>/
├── CLAUDE.md                     research block (commands, language, integrity rules)
├── .claude/commands/             research-list-paper.md, research-summary-paper.md, research-download-paper.md, research-figure.md, research-animation.md, research-table.md
├── .claude/skills/research-sources/   (+ scripts/researchtool.py)
├── .claude/skills/research-figures/   (+ scripts/figuretool.py)
├── .claude/skills/research-animations/   (+ scripts/animtool.py, paperanim.py)
└── .research/lists/, papers/, pdfs/, figures/, tables/, animations/   (pdfs/ and the render cache are added to .gitignore)
```
