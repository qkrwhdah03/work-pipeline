---
description: View accumulated limitations / optimization targets
allowed-tools: Read, Bash, Glob, Grep
---

Read `.dev/context/04-devlog.md` and show the two sections **separately**.

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
