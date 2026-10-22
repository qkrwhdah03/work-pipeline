<!-- RESEARCH-PIPELINE:BEGIN (This block is managed by the install script. You may edit it, but reinstalling overwrites it) -->
## Research Pipeline

| Command | Does | Saves to |
| --- | --- | --- |
| `/research-list-paper <topic>` | Finds the key papers on a topic — foundational and recent, from trusted venues | `.research/lists/` |
| `/research-summary-paper <paper>` | Analyzes one paper — big picture, claims, evidence, limitations | `.research/papers/` |

Source and verification rules live in `.claude/skills/research-sources/SKILL.md`. Both commands read it first.

### Language

The pipeline's own files (skill, commands) are in English. **Everything produced while using it follows the user's language** — the language of the request: summaries, analyses and reports. Paper titles, venue names, method and dataset names, and author names stay as published.

### Integrity

- Never cite a paper, venue, year, link, code repo or number that wasn't confirmed from a fetched source. Leave it out instead.
- Keep what a paper says (attributed, with section / table references) apart from your own assessment (labeled as yours).
<!-- RESEARCH-PIPELINE:END -->
