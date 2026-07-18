---
description: Turn claude-powernap monitoring off
---

Run this command and show the user its output:

```
python3 "${CLAUDE_PLUGIN_ROOT}/src/claude_powernap/cli.py" off
```

(Use `python` if `python3` is not found.) Note: this stops usage checks and
disables the fallback watcher; the plugin's hooks remain registered but exit
instantly.
