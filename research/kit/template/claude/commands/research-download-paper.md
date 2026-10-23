---
description: Download a paper's PDF as "<year>. <title> (<venue>).pdf" into .research/pdfs/ (or a folder you name)
argument-hint: <paper title, link, arXiv ID, DOI — or numbers from the last /research-list-paper list> [to <folder>]
allowed-tools: WebSearch, Read, Glob, Bash(python3 .claude/skills/research-sources/scripts/researchtool.py:*), Bash(python .claude/skills/research-sources/scripts/researchtool.py:*)
---

Paper(s): **$ARGUMENTS**

Save each paper's PDF named `<Year>. <Title> (<Venue>).pdf` — by default in the project's `.research/pdfs/`, or wherever the user says.

## 0. Rules

Read `.claude/skills/research-sources/SKILL.md` first. `RT` below means `python3 .claude/skills/research-sources/scripts/researchtool.py` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run).

Reply in the user's language.

**Only open, legitimate copies:** the venue's own PDF, arXiv, or an open-access link from the publisher or OpenAlex. Never use shadow libraries or anything that gets around a paywall. If no open PDF exists, say so and give the paper's link instead.

## 1. Where to save

- **Default: `.research/pdfs/`** in the project — pass nothing.
- **The user named a place** in the request ("to ~/papers", "in docs/refs", "다운로드 폴더에"): a folder → `--dir <folder>` (relative paths are from the project root; `~` works); their Downloads folder → `--downloads`. Use exactly what they named; don't move it elsewhere.

## 2. Resolve each paper

The input can be anything: a title, a link (venue page, arXiv, DOI, project page), an arXiv ID, a DOI — or several separated by `;` or new lines. If it is only numbers (e.g. `2, 5`) and `.research/lists/` has lists, take those entries from the most recent list.

For each paper, confirm from fetched sources (the skill's full check, minus code):

- **Title** exactly as published — `RT meta <arXiv id | DOI | "title">`.
- **Venue and year** of the published version. Venue as people say it, same as the slide citation in `/research-list-paper`: `CVPR`, `ICCV`, `ECCV`, `NeurIPS`, `ICML`, `ICLR`, `SIGGRAPH`, `SIGGRAPH Asia`, `TPAMI`, `3DV`, … A TOG paper uses the conference it was presented at if confirmed, otherwise `ACM TOG`. Not yet published: `arXiv` and the arXiv year.
- **The venue page** — for CVPR / ICCV / WACV use `RT venue-url "<title>" <CONF><YEAR>`.

If the input matches several papers, list them and ask which one. Don't guess.

## 3. Download

```
RT download <venue page URL> <DOI> <arXiv id> --year <Year> --title "<Title>" --venue "<Venue>" [--dir <folder> | --downloads]
```

Pass the sources best first — the venue page gives the final camera-ready PDF; arXiv is the fallback. The script finds the PDF link on each page, checks the file really is a PDF, saves it to the folder from step 1, and skips files that already exist.

## 4. Report

One line per paper:

```
✓ 2023. 3D Gaussian Splatting for Real-Time Radiance Field Rendering (SIGGRAPH).pdf — from arXiv (venue PDF is paywalled)
✗ <Title> — no open PDF; paper: <link>
```

Say where the PDF came from (venue or arXiv), and end with the folder the PDFs were saved in.
