---
description: Download a paper's PDF to the Downloads folder as "<year>. <title> (<venue>).pdf"
argument-hint: <paper title, link, arXiv ID, DOI — or numbers from the last /research-list-paper list>
allowed-tools: WebSearch, Read, Glob, Bash(python3 .claude/skills/research-sources/scripts/researchtool.py:*), Bash(python .claude/skills/research-sources/scripts/researchtool.py:*)
---

Paper(s): **$ARGUMENTS**

Save each paper's PDF to the user's Downloads folder, named `<Year>. <Title> (<Venue>).pdf`.

## 0. Rules

Read `.claude/skills/research-sources/SKILL.md` first. `RT` below means `python3 .claude/skills/research-sources/scripts/researchtool.py` (`python …` if `python3` isn't available).

Reply in the user's language.

**Only open, legitimate copies:** the venue's own PDF, arXiv, or an open-access link from the publisher or OpenAlex. Never use shadow libraries or anything that gets around a paywall. If no open PDF exists, say so and give the paper's link instead.

## 1. Resolve each paper

The input can be anything: a title, a link (venue page, arXiv, DOI, project page), an arXiv ID, a DOI — or several separated by `;` or new lines. If it is only numbers (e.g. `2, 5`) and `.research/lists/` has lists, take those entries from the most recent list.

For each paper, confirm from fetched sources (the skill's full check, minus code):

- **Title** exactly as published — `RT meta <arXiv id | DOI | "title">`.
- **Venue and year** of the published version. Venue as people say it, same as the slide citation in `/research-list-paper`: `CVPR`, `ICCV`, `ECCV`, `NeurIPS`, `ICML`, `ICLR`, `SIGGRAPH`, `SIGGRAPH Asia`, `TPAMI`, `3DV`, … A TOG paper uses the conference it was presented at if confirmed, otherwise `ACM TOG`. Not yet published: `arXiv` and the arXiv year.
- **The venue page** — for CVPR / ICCV / WACV use `RT venue-url "<title>" <CONF><YEAR>`.

If the input matches several papers, list them and ask which one. Don't guess.

## 2. Download

```
RT download <venue page URL> <DOI> <arXiv id> --year <Year> --title "<Title>" --venue "<Venue>"
```

Pass the sources best first — the venue page gives the final camera-ready PDF; arXiv is the fallback. The script finds the PDF link on each page, checks the file really is a PDF, saves it to the Downloads folder, and skips files that already exist.

## 3. Report

One line per paper:

```
✓ 2023. 3D Gaussian Splatting for Real-Time Radiance Field Rendering (SIGGRAPH).pdf — from arXiv (venue PDF is paywalled)
✗ <Title> — no open PDF; paper: <link>
```

Say where the PDF came from (venue or arXiv), and end with the Downloads folder path.
