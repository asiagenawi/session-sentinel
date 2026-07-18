---
description: Show claude-powernap usage status (5h window %, weekly %, watcher state)
---

Run this command and show the user its output verbatim:

```
python3 "${CLAUDE_PLUGIN_ROOT}/src/claude_powernap/cli.py" status
```

(Use `python` instead of `python3` if the first is not found.) If the 5-hour
window is above 80%, briefly note how much runway remains before the powernap
pause protocol will trigger at the configured threshold.
