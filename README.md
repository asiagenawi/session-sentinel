# session-sentinel

Keep long-running Claude Code automations alive across the subscription's
5-hour session limit — **proactively**. Instead of dying mid-task at the hard
limit, your session is warned at ~90% usage, checkpoints its own work,
schedules its own resumption for the moment the window resets, and continues
in the **same open terminal session**. A background watcher catches the cases
where the limit is hit anyway.

Free, local, dependency-free (Python 3 stdlib only). macOS, Linux (incl.
WSL), and native Windows (experimental).

## How it works

1. **Monitor** — a Claude Code hook (`PostToolUse`/`UserPromptSubmit`/`Stop`)
   checks your 5-hour window at most every 2 minutes. Usage comes from the
   same endpoint Claude Code's `/usage` screen uses (exact %, exact reset
   time), with a fully-local transcript-based estimate as fallback.
2. **Pause protocol** — at the threshold (default 90%) the hook injects a
   warning into the live session. Claude then: stops starting new work, writes
   a checkpoint file (`~/.claude/session-sentinel/checkpoints/<session>.md`),
   creates a one-shot scheduled task for reset time + 3 min, announces the
   pause, and idles.
3. **Self-resume** — the scheduled task fires inside the still-open session at
   reset; Claude reads its checkpoint and continues. No human action needed.
4. **Fallback watcher** — a launchd job (every 2 min) spots sessions whose
   transcript ends in a rate-limit error. After the reset it resumes them
   *visibly*: if the original `claude` process is dead it opens a new
   Terminal/iTerm2 window with `claude --resume <id>` and the continue-prompt
   pre-submitted; if the process is still alive it just sends a macOS
   notification (never injects into or forks a live session); headless resume
   only as a last resort when no GUI is available.

## Install

```bash
git clone https://github.com/asiagenawi/session-sentinel.git && cd session-sentinel
./install.sh        # macOS / Linux / WSL
```

Native Windows (PowerShell 7 recommended):

```powershell
git clone https://github.com/asiagenawi/session-sentinel.git; cd session-sentinel
.\install.ps1
```

Idempotent; re-run to upgrade. It copies scripts to
`~/.claude/session-sentinel/`, merges three hook entries into
`~/.claude/settings.json` (backup saved first), loads the launchd watcher, and
puts the `claude-sentinel` CLI in `~/.local/bin`.

The first usage check may trigger a macOS Keychain prompt (the monitor reads
Claude Code's own OAuth token to query usage) — click "Always Allow".

## Toggle

```bash
claude-sentinel on       # enable everything
claude-sentinel off      # disable everything (hooks stay registered but exit instantly)
claude-sentinel status   # enabled? watcher? current 5h + weekly usage
claude-sentinel log      # recent sentinel activity
```

## Configure — `~/.claude/session-sentinel/config.json`

| key | default | meaning |
|---|---|---|
| `enabled` | `true` | master switch (what `on`/`off` flips) |
| `threshold_pct` | `90` | warn/pause threshold for the 5h window |
| `check_interval_s` | `120` | min seconds between usage checks |
| `endpoint_enabled` | `true` | `false` = fully local estimation only |
| `terminal_app` | `Terminal` | macOS: `Terminal`/`iTerm2`; Linux: terminal binary name (auto-detected if unset) |
| `resume_grace_min` | `3` | schedule resume this long after reset |
| `headless_resume_extra_args` | `[]` | extra flags for last-resort headless resume |
| `local_budget_weighted_tokens` | `null` | manual budget for local estimation |

## Caveats

- **Undocumented endpoint**: the exact-usage source is the endpoint Claude
  Code's own `/usage` uses; it isn't a published API and could change or be
  restricted at any time. The tool degrades to local estimation automatically.
  Set `endpoint_enabled: false` if you'd rather never call it.
- **Local estimate is approximate**: token-weighted guess, self-calibrated
  from past limit hits; keep the threshold conservative when relying on it.
- The paused session must stay open (that's the point); the scheduled-task
  resume relies on Claude Code's native scheduled-tasks feature.
- **Platforms**: macOS uses Keychain + launchd + osascript. Linux uses
  `~/.claude/.credentials.json` + a systemd user timer + `notify-send` and
  auto-detects your terminal emulator (gnome-terminal, konsole, kitty,
  alacritty, xterm, …; set `terminal_app` to a binary name to override).
  Headless Linux servers work too — the watcher just falls straight to
  headless resume. Run `loginctl enable-linger $USER` if you want the watcher
  active while logged out.
- **Windows (experimental)**: token from `~/.claude/.credentials.json`, watcher
  via Task Scheduler (every 2 min, `pythonw` so no console flash), toast
  notifications, resume in Windows Terminal (`wt`) or a new cmd window.
  Liveness detection is deliberately conservative (rename-test + claude.exe
  check): when in doubt it notifies instead of auto-resuming, so it never
  forks a live session — worst case you click instead of it being automatic.
  Exercised by CI on real Windows runners; interactive behavior (window spawn,
  toasts) is less battle-tested than macOS/Linux — issues welcome. WSL users:
  just use `./install.sh` inside WSL instead.

## Uninstall

```bash
./uninstall.sh          # removes hooks, watcher, CLI; keeps config/checkpoints
./uninstall.sh --purge  # removes everything
```

Windows: `.\uninstall.ps1` (or `.\uninstall.ps1 -Purge`).
