---
description: View accumulated limitations / optimization targets
allowed-tools: Read, Bash(python3 .claude/skills/dev-loop/scripts/devtool.py:*), Bash(python .claude/skills/dev-loop/scripts/devtool.py:*)
---

Run `python3 .claude/skills/dev-loop/scripts/devtool.py devlog limitations` and `… devlog optimization` (`python …` if `python3` isn't available) and show the two sections **separately**.

```
Limitations / Improvements  (read by A on the next /dev)
1. ...
2. ...

Optimization Targets  (read by E on /dev-optimize)
1. ...
```

If an item has linked spec IDs (`F-xxx`, etc.), show them too.

Then add just one line:

- If there are limitations — note that the top item can be run directly as the next `/dev` request
- If 3 or more optimization targets have piled up — suggest `/dev-optimize`

**Do not change anything here. Only read and show.** Do not start a loop.
