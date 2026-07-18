# Security

## What this tool touches

- **Reads** Claude Code's OAuth token — macOS: read-only Keychain lookup via
  `security find-generic-password`; Linux/Windows: reads
  `~/.claude/.credentials.json`. The token is used in memory for one request
  and never written anywhere.
- **One outbound HTTPS request** to `api.anthropic.com` (the usage endpoint) —
  the only network traffic the tool ever makes. Disable with
  `endpoint_enabled: false` for fully-offline operation.
- **Edits** `~/.claude/settings.json` to register three hooks (a timestamped
  backup is written first; `uninstall` reverses the edit).
- **Reads** your local Claude Code transcripts (`~/.claude/projects/`) for
  token math and limit detection. Nothing from them leaves your machine.
- **Schedules** the fallback watcher via launchd / systemd user timer /
  Task Scheduler, running as your user.

## Supply chain

Python 3 standard library only — no pip packages, no npm, no curl|bash. What
you clone is what runs; it's ~600 lines of Python you can read first.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository
(Security → Report a vulnerability). Best-effort response from a single
maintainer.
