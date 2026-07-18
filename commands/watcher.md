---
description: Set up the powernap fallback watcher (one-time; plugins can't schedule OS tasks themselves)
---

The powernap plugin's hooks are already active, but the fallback watcher — the
background job that rescues sessions which hard-hit the limit or miss their
wake-up alarm — runs outside Claude Code (launchd / systemd user timer / Task
Scheduler), which a plugin cannot register on its own. Set it up now:

1. Run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/src/claude_powernap/cli.py" watcher-setup
```

(Use `python` if `python3` is not found.)

2. Show the user the output. If it reports a launchd/systemd/Task Scheduler
   registration, confirm the watcher is live and explain in one sentence what
   it does. If it prints a WARNING about neither launchd nor systemd being
   available, relay the suggested crontab line instead.

This is one-time; to undo it later run the same command with
`watcher-remove`.
