# Security

## What this tool touches

- **Reads** Claude Code's OAuth token. macOS: a `security
  find-generic-password` lookup of the cached Claude Code credentials entry;
  on a cache miss only, it runs `security dump-keychain` once to find the
  right entry name — that command lists metadata (names, not secrets) for
  the whole login keychain. Linux/Windows: reads
  `~/.claude/.credentials.json`. The token is used in memory for one request
  and never written anywhere.
- **Periodic outbound HTTPS requests** to `api.anthropic.com` (the usage
  endpoint — the same query the built-in `/usage` screen makes), at most one
  per check interval (120s normally, down to 15s near the limit). Requests
  identify themselves honestly as `claude-powernap/<version>`. This is the
  only network traffic the tool ever makes; disable with
  `endpoint_enabled: false` for fully-offline operation.
- **Edits** `~/.claude/settings.json` to register three hooks (a backup copy
  `settings.json.powernap-backup` is written first; `claude-powernap remove`
  reverses the edit).
- **Reads** your local Claude Code transcripts (`~/.claude/projects/`) for
  token math and limit detection. Nothing from them leaves your machine.
- **Schedules** the fallback watcher via launchd / systemd user timer /
  Task Scheduler, running as your user.

## Supply chain

Python 3 standard library only — no pip packages, no npm, no curl|bash. What
you clone is what runs: ~1,400 lines of Python you can read first.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository
(Security → Report a vulnerability). Best-effort response from a single
maintainer.
