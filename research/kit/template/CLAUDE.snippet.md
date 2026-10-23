<!-- RESEARCH-PIPELINE:BEGIN (This block is managed by the install script. You may edit it, but reinstalling overwrites it) -->
## Research Pipeline

| Command | Does | Saves to |
| --- | --- | --- |
| `/research-list-paper <topic>` | Finds the key papers on a topic — foundational and recent, from trusted venues | `.research/lists/` |
| `/research-summary-paper <paper>` | Analyzes one paper — big picture, claims, evidence, limitations | `.research/papers/` |
| `/research-download-paper <paper>` | Saves the paper's PDF as `<year>. <title> (<venue>).pdf` — venue PDF first, arXiv as fallback, open copies only | Downloads folder |
| `/research-figure <description>` | Designs a paper figure that conveys the description — editable PPTX + PDF + PNG preview | `.research/figures/` |
| `/research-table <data>` | Lays out results as a booktabs table with notes (`*`, `†`) under it — editable PPTX + PDF + PNG preview | `.research/tables/` |

Source and verification rules live in `.claude/skills/research-sources/SKILL.md`; figure and table rules in `.claude/skills/research-figures/SKILL.md`. Each command reads the ones it needs first.

### Language

The pipeline's own files (skills, commands) are in English. **Everything produced while using it follows the user's language** — the language of the request: summaries, analyses and reports. Paper titles, venue names, method and dataset names, and author names stay as published.

### Integrity

- Never cite a paper, venue, year, link, code repo or number that wasn't confirmed from a fetched source. Leave it out instead.
- Keep what a paper says (attributed, with section / table references) apart from your own assessment (labeled as yours).
<!-- RESEARCH-PIPELINE:END -->
