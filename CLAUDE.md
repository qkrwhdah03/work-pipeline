# CLAUDE.md

This repository holds installable Claude Code pipelines. Its rules are in [STRUCTURE.md](STRUCTURE.md) — read it before changing a pipeline.

The ones most often missed:

- **Docs follow the change.** In the same change, update the pipeline's `docs/design.md` and `docs/install.md`, the kit text that describes the behavior (CLAUDE snippet, skills, commands, agents), and `README.md` / the STRUCTURE.md tables when commands, agents or skills change. Then run `python tools/build.py <name>` (zip + design PDF; set `CHROME=<path>` if there's no system Chrome) and commit `dist/` with the source.
- **Everything in this repository is English**, commit messages included.
- **Always-loaded text stays minimal**: a pipeline's CLAUDE snippet holds only what every session needs; details go in its skill.
