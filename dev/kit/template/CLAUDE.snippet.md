<!-- DEV-PIPELINE:BEGIN (This block is managed by the install script. You may edit it, but reinstalling overwrites it) -->
## Dev Loop

Development work in this project goes through `/dev`: design (A) → code (B) ∥ tests (C) → record and commit (D), then optimization (E) and memory compaction (F) when due. `/dev-optimize` and `/dev-optimize-memory` run E and F on demand. Loop rules — doc boundaries, devlog routing, permissions, retries, commit format — are in the `dev-loop` skill and the agent files; read them only when running a loop.

### When It Runs

- **Only on an explicit `/dev`.** Never start the loop yourself; it doesn't step into questions, exploration, debugging talk or chat.
- Asked for a code change without `/dev`: ask in one line whether to run it through `/dev`; if not, do it as usual. Typo or comment fixes, temporary debug output and "just do it quickly" tasks are never loop work.

### Language

Everything committed is in **English**, whatever language the request is in: `.dev/context/` docs, `CLAUDE.md`, code comments, commit messages. Translate; don't mix languages. Only what isn't committed follows the user's language: replies, and the gitignored `.dev/loops/` order · result files. Identifiers the pipeline looks up stay English everywhere: structural headings, STATUS codes, commit field names, the `loop:` trailer, spec IDs.
<!-- DEV-PIPELINE:END -->
