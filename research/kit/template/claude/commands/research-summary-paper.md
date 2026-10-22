---
description: Analyze one paper — where it sits in the field, its claims, the evidence behind them, and its limitations
argument-hint: <paper title, arXiv ID / URL, DOI, or path to a PDF>
allowed-tools: WebSearch, WebFetch, Bash, Read, Write, Glob, Grep
---

Paper: **$ARGUMENTS**

Explain this paper so the reader understands where it fits, how it works, what it claims, whether the evidence holds up, and what it leaves open.

## 0. Rules

Read `.claude/skills/research-sources/SKILL.md` first and follow it throughout — especially **verify before citing** and **keep "what the paper says" apart from "your assessment."**

Write in the user's language (the language of their request). Paper titles, method names, dataset and metric names, and author names stay as published.

## 1. Identify the paper

- Resolve the input to one paper and give it the skill's **full check**: title, authors, venue + year (published version over arXiv), paper link, official code.
- If the input matches several papers, list them and ask which one. Don't guess.

## 2. Get the full text

Use the first that works: a local PDF path (read it directly) → `https://arxiv.org/html/<id>` → the arXiv / venue PDF. Fetch with curl and extract the text yourself, keeping equations (e.g. the `alttext` of math elements in arXiv HTML); WebFetch only returns a paraphrase.

Read the whole paper, including appendices, and the supplementary material if it's linked. **If you cannot get the full text — or a linked supplement is unreachable — say so at the top**, and keep the analysis within what you actually read. Never reconstruct content from memory.

## 3. Place it in the field

- If `.research/lists/` has a list on a related topic, read it first.
- From the paper's related-work section: the line of work it extends, and the alternatives it argues against.
- What came after: from the works citing it (OpenAlex / Semantic Scholar, sorted by citations), pick **at most 5–10**, grouped by direction — did it become a building block, a baseline, or a dead end? These need only the skill's **light check**.

## 4. Analyze

Tie every piece of evidence to the claim it supports. Cite sections, equations, tables and figures (`Sec. 4.2`, `Tab. 3`). Copy numbers exactly.

**Method in brief** — how it works, in a short paragraph or a few steps: inputs, the core idea, outputs. Enough that the claims make sense.

**Claims** — what the authors claim, in their terms, numbered, main contribution first. When a paper states contributions rather than claims, turn each into the claim it implies. **Split compound claims** ("fast *and* high-quality *at 1080p*") into parts that can be judged separately.

**Evidence** — for each claim:
- *Assumptions*: what the method or argument takes for granted, stated or not (data distribution, known camera poses, static scenes, access to X, …).
- *Experiments*: setup (datasets, baselines, metrics), the key results with numbers, and ablations. Then judge: does this experiment actually test the claim?
- *Proof / explanation* (if any): theoretical results and their conditions, or the intuition offered. Note when an explanation is informal or post hoc. Skip for claims that rest on experiments alone.

Two checks that often find the real issues:
- **Claims vs. conditions** — compare each claim in the abstract and introduction with the conditions it was actually tested under (resolution, hardware, datasets, settings).
- **Headline vs. detail** — check that headline numbers agree with the detailed tables (e.g. a reported average against the per-scene table). This also catches your own parsing mistakes.

**Limitations**
- *Acknowledged by the authors* — briefly.
- *Gaps in the argument* (your assessment) — e.g. unsupported generalization, missing or weak baselines, metrics that don't measure the claim, confounded comparisons (different data / compute / tuning), assumptions that break in practice, results reported only where they look good.
- *Room for improvement* — concrete directions: what experiment, relaxation or extension would address each gap.

## 5. Output

```
# <Title>

<Authors (first three, then et al.)> · <Venue> <Year> · [Paper](<link>) · [Code](<link>) or Code: —
> Source notes: <citations (source, date); anything unconfirmed or unreachable — full text, supplement, project page, venue page>

## Big picture
<what came before, the gap it targets, what came after>

## Method in brief

## Claims
1. ...

## Evidence
### Claim 1 — <short name>
- Assumptions: ...
- Experiments: ...
- Proof / explanation: ...   (omit if none)
- Verdict: <supported / partly supported / not supported — and why, one line>

## Limitations
### Acknowledged by the authors
### Gaps in the argument
### Room for improvement

## Bottom line
<two or three sentences: what to take away and how much to trust it>
```

## 6. Save and report

Save to `.research/papers/<first-author-lastname><year>-<short-title-slug>.md` (create the folder if needed).

In the chat, don't paste the whole analysis. Show the header line, **Bottom line**, and the claims with their one-line verdicts, then give the file path.
