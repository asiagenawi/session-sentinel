# claude-powernap

[![CI](https://github.com/asiagenawi/claude-powernap/actions/workflows/ci.yml/badge.svg)](https://github.com/asiagenawi/claude-powernap/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/asiagenawi/claude-powernap)](https://github.com/asiagenawi/claude-powernap/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)
![Deps](https://img.shields.io/badge/deps-stdlib%20only-brightgreen)

**Your Claude Code session sees the usage limit coming, saves its work, and
resumes itself when the window resets. You do nothing.**

## The problem

You kick off a long Claude Code automation — a big refactor, a batch
migration, an overnight research run. You check back three hours later and
find it died 40 minutes in:

```
You've hit your session limit · resets 3:00am
```

Everything since the last commit is in limbo. The context that session had
built up is sitting frozen mid-thought. And the limit reset hours ago — the
session just had no way to know, no way to save itself, and no way to come
back. Your subscription's 5-hour window reset while your automation sat
dead in a terminal.

## The idea

A session that's *about* to hit the limit still has tokens left. That's
enough budget to do something smarter than die:

1. **A hook watches your usage** (checked at most every 2 min, zero workflow
   changes). It knows your exact window percentage and reset time — the same
   numbers Claude Code's own `/usage` screen shows.
2. **At 90%, the session itself gets warned** — the hook injects a message
   into the live conversation: *"you're at 91%, window resets at 3:00am,
   pause now."*
3. **Claude wraps up gracefully**: finishes the current step, writes a
   checkpoint file (what's done, what's in flight, exact next steps), and
   schedules a one-shot task for just after the reset. Then it idles.
4. **At reset, the session wakes itself** — same terminal, same context,
   reads its checkpoint, keeps going.

If the estimate is ever wrong and a session hard-hits the wall anyway, a
background watcher catches that too: after the reset it reopens the session
in a visible terminal window with the "continue from your checkpoint" prompt
already submitted. If the original window is still open, you get a
notification instead — it will never fork a live session.

## How it compares

| | warns before the limit | session saves its work | resumes automatically | needs tmux |
|---|---|---|---|---|
| **claude-powernap** | ✅ | ✅ | ✅ same session | no |
| usage monitors (ccusage, claude-monitor) | ⚠️ warns *you*, not the session | ❌ | ❌ | — |
| auto-retriers (unsnooze, claude-auto-retry, …) | ❌ reacts after death | ❌ dies mid-thought | ✅ | mostly yes |

Free, local, no dependencies (Python 3 stdlib only). macOS, Linux (incl.
WSL), native Windows (experimental).

## Install

```bash
git clone https://github.com/asiagenawi/claude-powernap.git && cd claude-powernap
./install.sh        # macOS / Linux / WSL
```

Native Windows (PowerShell 7 recommended):

```powershell
git clone https://github.com/asiagenawi/claude-powernap.git; cd claude-powernap
.\install.ps1
```

That's the whole setup. Every Claude Code session on the machine is covered —
no per-project config, no special launcher, no flags to remember. Start your
long automations exactly the way you already do.

The installer is deliberately boring and inspectable: it copies a few Python
files to `~/.claude/claude-powernap/`, merges three hook entries into
`~/.claude/settings.json` (backing it up first), and schedules the fallback
watcher (launchd / systemd user timer / Task Scheduler). `uninstall.sh`
reverses all of it.

On macOS the first usage check may trigger one Keychain prompt — the monitor
reads Claude Code's own OAuth token to ask Anthropic for your real usage
numbers (see Caveats). Click "Always Allow".

## Toggle

```bash
claude-powernap on       # enable everything
claude-powernap off      # disable everything
claude-powernap status   # current 5h + weekly usage, watcher state
claude-powernap log      # what the watcher and monitor have been doing
```

## Configure — `~/.claude/claude-powernap/config.json`

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

## Caveats (read these — they're the honest part)

- **Usage numbers come from an undocumented endpoint** — the same one Claude
  Code's own `/usage` screen calls, authenticated with the OAuth token Claude
  Code already stores on your machine. Nothing leaves your machine except
  that one HTTPS request to Anthropic. It isn't a published API and could
  change or be restricted at any time; the tool automatically degrades to
  local estimation if it fails. Worth naming plainly: Anthropic's consumer
  terms scope OAuth tokens to Claude Code itself, so a script making this
  query — even the identical read-only call `/usage` makes, the same pattern
  ccusage-class tools use — sits in a ToS gray area. Set
  `endpoint_enabled: false` if you'd rather avoid it entirely — everything
  still works, just with an approximate percentage (self-calibrated,
  conservative threshold recommended).
- The paused session must stay open — that's the point. The self-resume uses
  Claude Code's native scheduled-tasks feature.
- **Platforms**: macOS uses Keychain + launchd + osascript. Linux uses
  `~/.claude/.credentials.json` + a systemd user timer + `notify-send`, and
  auto-detects your terminal emulator. Headless Linux servers work — the
  watcher falls through to headless resume. Run `loginctl enable-linger
  $USER` to keep the watcher active while logged out.
- **Windows (experimental)**: token from `~/.claude/.credentials.json`,
  watcher via Task Scheduler (`pythonw`, no console flash), toast
  notifications, resume in Windows Terminal or a new cmd window. Liveness
  detection is deliberately conservative (rename-test + claude.exe check):
  when in doubt it notifies you instead of auto-resuming, so it never forks
  a live session — worst case is one click instead of full automation.
  Exercised by CI on real Windows runners; interactive behavior is less
  battle-tested than macOS/Linux. WSL users: use `./install.sh` inside WSL.

## Uninstall

```bash
./uninstall.sh          # removes hooks, watcher, CLI; keeps config/checkpoints
./uninstall.sh --purge  # removes everything
```

Windows: `.\uninstall.ps1` (or `.\uninstall.ps1 -Purge`).

## License

MIT
