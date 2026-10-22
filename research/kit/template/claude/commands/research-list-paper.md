---
description: Find the key papers on a topic — trusted venues, verified links, one-paragraph summaries
argument-hint: <topic or keywords> [e.g. "since 2023", "top 10", "foundational only"]
allowed-tools: WebSearch, WebFetch, Bash, Read, Write, Glob, Grep
---

Topic: **$ARGUMENTS**

Build a list of the papers someone needs to understand this topic — both where it came from and where it is now.

## 0. Rules

Read `.claude/skills/research-sources/SKILL.md` first and follow it throughout: trusted venues, arXiv-only criteria, and **verify every field before it appears in the output.**

Write the output in the user's language (the language of their request). Paper titles, venue names and author names stay as published.

## 1. Scope

- Restate the topic in one line, including the sub-area it belongs to.
- Read options from the request: time range ("since 2023"), count ("top 10"), focus ("foundational only", "recent only"). Defaults: **10–15 papers**, covering both foundational and recent work.
- Only if the topic splits into clearly different fields (e.g. "diffusion" in generative models vs. physics), ask one short question. Otherwise proceed and state your interpretation.

## 2. Search

Cast a wide net, then narrow.

- Several phrasings of the topic, plus the field's established terms for it.
- Venue-targeted searches (e.g. `site:openaccess.thecvf.com`, `site:openreview.net`) for recent tier-1 work.
- **Recent surveys** on the topic — their taxonomy and reference lists point to the canonical papers. Use them to find papers; don't list a survey unless it is itself a key reference, and label it `(survey)`.
- From the clearly seminal paper(s), look at what cites them (OpenAlex / Semantic Scholar) to find the influential follow-ups.

Keep a candidate pool larger than the final list.

## 3. Select

Rank candidates by: relevance to the topic → venue tier → influence relative to age. Aim for:

- **Foundational** — papers that introduced the problem or method family, or that later work builds on and compares against.
- **Recent** — strongest work from roughly the last two years, showing where the field is heading.

Split the count roughly half and half, leaning toward whichever the request emphasizes. If a time range is given, "foundational" means the papers that defined the topic **within that range** (e.g. the first wave right after the range starts), and the overview says so.

Prefer one paper per idea; skip incremental variants unless they became the standard baseline.

## 4. Verify

For every selected paper, run the skill's **full check**: exact title, venue + year (published version over arXiv), an accessible link, official code or `—`. Drop any paper you can't verify and count it. Note any detail that rests on a weaker source for the source note.

## 5. Summarize

Read at least the abstract — and the introduction or conclusion when the abstract is vague — from the paper itself, as exact text (see "How to fetch" in the skill). For each paper write **2–3 sentences**: what problem it tackles and how it solves it, or what it claims. Concrete, no hype words ("novel", "state-of-the-art") unless you say against what.

## 6. Output

```
# <topic>

<date> · <n> papers · scope: <the tier-1 venues in scope for this topic>
> <your interpretation of the topic, the time range and how the count was split>

## Overview
<one paragraph: how the topic developed — the founding idea, the main branches, and the current trend. Refer to papers by short name.>

## Foundational

| # | Title | Venue | Links | Summary |
| --- | --- | --- | --- | --- |
| 1 | <Title> | <Venue> <Year> | [Paper](<link>) · [Code](<link>) | **<why it's key, a few words>** (<citations, e.g. ~830>) — <2–3 sentence summary> |

## Recent

| # | Title | Venue | Links | Summary |
| --- | --- | --- | --- | --- |
| 1 | ... | | | |

---
- Not verified, dropped: <n>
- Strong candidates not selected (count limit): <short names, venue year>
- Source notes: <citation source and date; anything resting on a weaker source>
```

Order papers by year within each section. In the Venue cell, mark arXiv-only papers `arXiv <year> (preprint — <reason>)`. Write `Code: —` in the Links cell when there is no official code. Keep each cell on one line — no line breaks, and escape any `|` inside a cell as `\|`. Citation counts come from the source named in the source notes.

## 7. Save

Save the result to `.research/lists/<YYYY-MM-DD>-<topic-slug>.md` (create the folder if needed), then show it in full in the chat and give the file path.
