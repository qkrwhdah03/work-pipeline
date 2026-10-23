---
description: Lay out results as a paper-style (booktabs) table — editable PPTX + PDF (+ PNG preview), with notes under the table
argument-hint: <the data to organize — pasted values, a CSV path, or "PSNR/SSIM of X, Y, Z on Mip-NeRF360 from their papers">
allowed-tools: Read, Write, Edit, Glob, Grep, WebSearch, Bash(python3 .claude/skills/research-figures/scripts/figuretool.py:*), Bash(python .claude/skills/research-figures/scripts/figuretool.py:*), Bash(python3 .claude/skills/research-sources/scripts/researchtool.py:*), Bash(python .claude/skills/research-sources/scripts/researchtool.py:*)
---

Table: **$ARGUMENTS**

Organize this data into a table formatted the way results tables appear in papers.

## 0. Rules

Read `.claude/skills/research-figures/SKILL.md` first and follow its table rules and build loop. `FT` below means `python3 .claude/skills/research-figures/scripts/figuretool.py`, `RT` means `python3 .claude/skills/research-sources/scripts/researchtool.py` (on Windows: `python …` — there `python3` is usually a Microsoft Store stub that doesn't run).

Reply in the user's language. Text **inside** the table (headers, method names, notes) is in English unless the user asks otherwise.

**Every number comes from somewhere you can name.** Copy the user's values exactly. Numbers taken from papers must be read from the paper itself — `RT fulltext <arXiv id>` and the table it reports — never from memory or snippets. If a value isn't available, write `–`.

## 1. Collect the data

- **Pasted values or a file** (CSV, TSV, a results log, a Markdown table): read them as given. For an Excel file, ask the user to save it as CSV.
- **From papers** ("X, Y and Z on Mip-NeRF360"): read `.claude/skills/research-sources/SKILL.md` too. For each paper, find the numbers in its own results table, note `paper, Tab. n`, and check the settings match across papers (same dataset split, resolution, metric definition). Where they differ, say so in a note.

## 2. Lay out

- Rows are methods (or settings); columns are metrics, grouped by dataset with `header_groups` when there is more than one.
- Metric directions in the header (`↑` / `↓`). Same decimals within a column.
- Per column: best **bold**, second __underlined__ — set `best` per column (`"max"` / `"min"` by the metric's direction) and let the script mark them; set `decimals` per column.
- `midrule` between groups of rows (e.g. prior work vs. ours, or different input settings).
- Row-specific remarks become footnote markers on the cell (`Ours^{*}`, `NeRF^{†}`) with the explanation in `notes`. Add a note for anything the reader would otherwise misread: different training settings, numbers re-run by you vs. reported, the bold/underline convention if needed, and the source of numbers taken from papers.
- Column widths: wide enough for the longest entry; total width ≤ 3.25 in for a single-column table unless it doesn't fit, then 6.875 in.

## 3. Build

1. Write the spec to `.research/tables/<YYYY-MM-DD>-<slug>/table.json`.
2. `FT build .research/tables/<…>/table.json`
3. Read `table.png` and fix what's wrong (skill's build loop, at most 3 rounds).

## 4. Report

```
Table · <what it compares>
<rows> rows × <columns> columns · <width> × <height> in

PPTX  <path>   ← editable in PowerPoint
PDF   <path>   ← for LaTeX: \includegraphics[width=\linewidth]{<file>.pdf}
PNG   <path>
Sources  <where each group of numbers came from — "provided by the user" for pasted data, "<paper>, Tab. n" for numbers read from papers>
```

Show the preview image. If no PDF converter was found, say so — the PPTX is still complete.
