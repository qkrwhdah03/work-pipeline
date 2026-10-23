<!-- RESEARCH-PIPELINE:BEGIN (This block is managed by the install script. You may edit it, but reinstalling overwrites it) -->
## Research Pipeline

`/research-list-paper`, `/research-summary-paper`, `/research-download-paper`, `/research-figure` and `/research-table` find, analyze and download papers and make figures and tables, saving under `.research/` (downloaded PDFs in `.research/pdfs/`, gitignored). Each command reads the skill it needs (`research-sources`, `research-figures`) — nothing else to load up front.

### Language

The pipeline's own files (skills, commands) are in English. **Everything produced while using it follows the user's language** — the language of the request: summaries, analyses and reports. Paper titles, venue names, method and dataset names, and author names stay as published.

### Integrity

- Never cite a paper, venue, year, link, code repo or number that wasn't confirmed from a fetched source. Leave it out instead.
- Keep what a paper says (attributed, with section / table references) apart from your own assessment (labeled as yours).
<!-- RESEARCH-PIPELINE:END -->
