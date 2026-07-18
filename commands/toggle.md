---
description: Turn claude-powernap monitoring on or off
argument-hint: on | off
---

Run this command with the user's argument ($ARGUMENTS — must be `on` or
`off`; if missing or anything else, ask which they want):

```
python3 "${CLAUDE_PLUGIN_ROOT}/src/claude_powernap/cli.py" $ARGUMENTS
```

(Use `python` if `python3` is not found.) Show the user the output. Note:
`off` stops usage checks and disables the fallback watcher; the plugin's
hooks remain registered but exit instantly.
