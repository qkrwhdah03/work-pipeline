---
description: Find the key papers on a topic — trusted venues, verified links, slide-ready citations, BibTeX links, short summaries
argument-hint: <topic or keywords> [e.g. "since 2023", "top 10", "foundational only"]
allowed-tools: WebSearch, WebFetch, Read, Write, Glob, Grep, Bash(python3 .claude/skills/research-sources/scripts/researchtool.py:*), Bash(python .claude/skills/research-sources/scripts/researchtool.py:*)
---

Topic: **$ARGUMENTS**

Build a list of the papers someone needs to understand this topic — both where it came from and where it is now.

## 0. Rules

Read `.claude/skills/research-sources/SKILL.md` first and follow it throughout: trusted venues, arXiv-only criteria, and **verify every field before it appears in the output.**

Do lookups with the skill's script instead of hand-written requests — `RT` below means `python3 .claude/skills/research-sources/scripts/researchtool.py` (`python …` if `python3` isn't available).

Write the output in the user's language (the language of their request). Paper titles, venue names and author names stay as published.

## 1. Scope

- Restate the topic in one line, including the sub-area it belongs to.
- Read options from the request: time range ("since 2023"), count ("top 10"), focus ("foundational only", "recent only"). Defaults: **10–15 papers**, covering both foundational and recent work.
- Only if the topic splits into clearly different fields (e.g. "diffusion" in generative models vs. physics), ask one short question. Otherwise proceed and state your interpretation.

## 2. Search

Cast a wide net, then narrow.

- WebSearch with several phrasings of the topic, plus the field's established terms for it.
- Venue-targeted WebSearch (e.g. `site:openaccess.thecvf.com`, `site:openreview.net`) for recent tier-1 work.
- `RT search "<query>" --since <year>` for a second, citation-ranked view.
- **Recent surveys** on the topic — their taxonomy and reference lists point to the canonical papers. Use them to find papers; don't list a survey unless it is itself a key reference, and label it `(survey)`.
- From the clearly seminal paper(s): `RT cites <arXiv id or DOI> --n 15` for the influential follow-ups.

Keep a candidate pool larger than the final list.

## 3. Select

Rank candidates by: relevance to the topic → venue tier → influence relative to age. Aim for:

- **Foundational** — papers that introduced the problem or method family, or that later work builds on and compares against.
- **Recent** — strongest work from roughly the last two years, showing where the field is heading.

Split the count roughly half and half, leaning toward whichever the request emphasizes. If a time range is given, "foundational" means the papers that defined the topic **within that range** (e.g. the first wave right after the range starts), and the overview says so.

Prefer one paper per idea; skip incremental variants unless they became the standard baseline.

## 4. Verify

For every selected paper, run the skill's **full check** with the script:

1. `RT meta <arXiv id | DOI | "title">` — title, authors, arXiv comment / journal_ref, Crossref venue, OpenAlex venue + citations, and the exact abstract.
2. The venue page — for CVPR / ICCV / WACV get it with `RT venue-url "<title>" <CONF><YEAR>` (don't guess CVF URLs); otherwise take it from the `meta` output or WebSearch. Then `RT page <venue page URL>` confirms the paper there and lists GitHub links on it.
3. `RT github <owner/repo> --paper "<title>" --paper <arXiv id> --page <project page>` — the repo exists, and the paper or its project page points to it.
4. `RT bibtex <venue page URL> <DOI> <arXiv id>` — the first of these that shows the BibTeX (pass what you have, best first).

Drop any paper you can't verify and count it. Note any detail that rests on a weaker source for the source note.

## 5. Summarize

Use the exact abstract from `RT meta` — and the introduction or conclusion (`RT fulltext <arXiv id>`, then read only those lines) when the abstract is vague. For each paper write **2–3 sentences**: what problem it tackles and how it solves it, or what it claims. Concrete, no hype words ("novel", "state-of-the-art") unless you say against what.

## 6. Output

```
# <topic>

<date> · <n> papers · scope: <the tier-1 venues in scope for this topic>
> <your interpretation of the topic, the time range and how the count was split>

## Overview
<one paragraph: how the topic developed — the founding idea, the main branches, and the current trend. Refer to papers by short name.>

## Foundational

| # | Citation | Links | Summary |
| --- | --- | --- | --- |
| 1 | Kerbl et al., 3D Gaussian Splatting for Real-Time Radiance Field Rendering (SIGGRAPH 2023) | [Paper](<link>) · [Code](<link>) · [BibTeX](<link>) | **<why it's key, a few words>** (<citations, e.g. ~830>) — <2–3 sentence summary> |

## Recent

| # | Citation | Links | Summary |
| --- | --- | --- | --- |
| 7 | ... | | |

---
- Not verified, dropped: <n>
- Strong candidates not selected (count limit): <short names, venue year>
- Source notes: <citation source and date; anything resting on a weaker source>
```

**Citation cell** — plain text meant to be pasted onto a slide as is, no markdown:
`<First author's last name> et al., <Title> (<Venue> <Year>)`
- One author: `<Last name>, <Title> (…)`. Two authors: `<Last name> and <Last name>, <Title> (…)`.
- Venue as people say it: `CVPR`, `ICCV`, `ECCV`, `NeurIPS`, `ICML`, `ICLR`, `SIGGRAPH`, `SIGGRAPH Asia`, `TPAMI`, `IJCV`, `TVCG`, `3DV`, …  A TOG paper uses the conference it was presented at if confirmed, otherwise `ACM TOG`. Workshops: `CVPR Workshops`.
- arXiv-only: `(arXiv <year>)`, and the reason it's included goes at the start of the Summary cell.

**Links cell** — `[Paper]` (accessible link), `[Code]` (official) or `Code: —`, `[BibTeX]` (from `RT bibtex`) or `BibTeX: —`.

Number papers continuously across both sections (1, 2, … n) and order by year within each section. **For 6 papers or fewer**, use a single table instead of two sections — say "foundational" or "recent" in each paper's key phrase — and keep only the footer lines that apply. Keep each cell on one line — no line breaks, and escape any `|` inside a cell as `\|`. Citation counts come from the source named in the source notes.

## 7. Save

Save the result to `.research/lists/<YYYY-MM-DD>-<topic-slug>.md` (create the folder if needed), then show it in full in the chat and give the file path.
