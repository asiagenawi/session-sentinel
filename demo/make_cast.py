#!/usr/bin/env python3
"""Generate demo/powernap.cast (asciinema v2) for the README GIF.

Styled after the Claude Code TUI. An illustrative mock-up of a real cycle:
powernap lines are condensed from usage_check.build_warning()'s actual
output (timestamps in fmt_local()'s format; resume shown as the scheduled
user-turn prompt the hook dictates), and the '⧉ context injected' banner
visualizes an injection the real TUI does not render. Render with:
  agg --font-size 15 --theme monokai --last-frame-duration 4 demo/powernap.cast demo/powernap.gif
"""
import json
from pathlib import Path

DIM, BOLD, RESET = "\x1b[2m", "\x1b[1m", "\x1b[0m"
YELLOW, GREEN, ORANGE = "\x1b[33m", "\x1b[32m", "\x1b[38;5;209m"
DIMYEL = "\x1b[2;33m"
W = 96
SID = "aeda6f64-430f-45f1-9691-84fdfa937f47"
CKPT = f"~/.claude/claude-powernap/checkpoints/{SID}.md"

events, t = [], 0.4


def out(data, dt=0.0):
    global t
    t += dt
    events.append([round(t, 3), "o", data])


def line(text="", dt=0.12, hold=0.0):
    global t
    out(text + "\r\n", dt)
    t += hold


def typed(prefix, text, hold=0.5):
    out(prefix)
    for ch in text:
        out(ch, 0.035)
    out("\r\n", 0.15)
    global t
    t += hold


# ── Claude Code welcome banner ────────────────────────────────────────────
line(f"{DIM}╭{'─' * (W - 2)}╮{RESET}")
line(f"{DIM}│{RESET} {ORANGE}✳{RESET} {BOLD}Welcome to Claude Code!{RESET}{' ' * (W - 28)}{DIM}│{RESET}")
line(f"{DIM}│{' ' * (W - 2)}│{RESET}")
line(f"{DIM}│   /help for help · cwd: ~/projects/acme-api{' ' * (W - 47)}│{RESET}")
line(f"{DIM}╰{'─' * (W - 2)}╯{RESET}", hold=1.0)
line()

# ── the long automation ───────────────────────────────────────────────────
typed(f"{DIM}>{RESET} ", "migrate every API handler to the new auth middleware, run the tests as you go", 0.9)
line()
line("⏺ There are 214 handlers across src/api/. I'll migrate them module by", 0.25)
line("  module, running each module's tests before moving on.", hold=1.1)
line()
line(f"⏺ {BOLD}Update{RESET}(src/api/billing/invoices.py)")
line(f"  {DIM}⎿  Updated 11 handlers{RESET}", hold=0.9)
line()
line(f"⏺ {BOLD}Bash{RESET}(pytest tests/api/billing -q)")
line(f"  {DIM}⎿  148 passed in 12.4s{RESET}", hold=1.1)
line()
line(f"{ORANGE}✻{RESET} {DIM}Working… (esc to interrupt · 3h 40m · ↓ 61.2k tokens){RESET}", hold=1.7)
line()

# ── the warning lands (context injection — the model sees it, styled dim) ─
line(f"{DIMYEL}⧉ context injected by claude-powernap hook:{RESET}", 0.3)
line(f"{YELLOW}  USAGE LIMIT WARNING: you have consumed 91% of the 5-hour usage window.{RESET}", 0.25)
line(f"{YELLOW}  The window resets at 2026-07-18 03:00AM EDT. At the current burn rate the{RESET}", 0.2)
line(f"{YELLOW}  limit is ~8 minutes away. To avoid dying mid-task, follow this pause{RESET}", 0.2)
line(f"{YELLOW}  protocol NOW: 1. Do NOT start new work. 2. Write a checkpoint file.{RESET}", 0.2)
line(f"{YELLOW}  3. SCHEDULE YOUR OWN WAKE-UP — create a one-shot scheduled task firing{RESET}", 0.2)
line(f"{YELLOW}  at 03:03AM EDT; without it the session sits idle after the reset.{RESET}", 0.2)
line(f"{YELLOW}  4. Tell the user you are pausing, then end your turn and idle.{RESET}", 0.2, hold=2.4)
line()
line("⏺ I'm at 91% of the session window — pausing gracefully instead of dying", 0.25)
line("  mid-migration. Billing module is done and green; checkpointing here.", hold=1.1)
line()
line(f"⏺ {BOLD}Write{RESET}({CKPT})")
line(f"  {DIM}⎿  Wrote 38 lines — completed: billing (11/214) · next: src/api/orders/{RESET}", hold=1.2)
line()
line(f"⏺ {BOLD}CronCreate{RESET}(one-shot · \"3 3 18 7 *\")")
line(f"  {DIM}⎿  Scheduled one-shot task f903accf. It will fire once then auto-delete.{RESET}", hold=1.2)
line()
line(f"⏺ {BOLD}Pausing until 2026-07-18 03:03AM EDT — leave this terminal open.{RESET} 💤", hold=2.6)
line()

# ── the reset: resume arrives as the scheduled user-turn prompt ───────────
line(f"{DIM}{'─' * 35}  3:03 AM  {'─' * 35}{RESET}", hold=1.6)
line()
line(f"{DIM}>{RESET} {DIM}Session window has reset. Read {CKPT}{RESET}", 0.3)
line(f"  {DIM}and continue the work from where it left off.{RESET}", 0.15, hold=1.3)
line()
line(f"⏺ {BOLD}Read{RESET}({CKPT})")
line(f"  {DIM}⎿  38 lines{RESET}", hold=1.0)
line()
line(f"⏺ {GREEN}Back from the powernap with a fresh window.{RESET} Billing is done (11/214);", 0.25)
line("  continuing with src/api/orders/.", hold=1.1)
line()
line(f"⏺ {BOLD}Update{RESET}(src/api/orders/checkout.py)")
line(f"  {DIM}⎿  Updated 9 handlers{RESET}", hold=1.0)
line()
line(f"{ORANGE}✻{RESET} {DIM}Working… (esc to interrupt · 2m 10s · ↓ 4.1k tokens){RESET}", hold=1.8)
line()

# ── idle input box ────────────────────────────────────────────────────────
line(f"{DIM}╭{'─' * (W - 2)}╮{RESET}")
line(f"{DIM}│{RESET} > {' ' * (W - 6)}{DIM}│{RESET}")
line(f"{DIM}╰{'─' * (W - 2)}╯{RESET}")
line(f"  {DIM}? for shortcuts{RESET}", hold=3.0)

header = {"version": 2, "width": 100, "height": 46,
          "title": "claude-powernap demo",
          "env": {"TERM": "xterm-256color", "SHELL": "/bin/zsh"}}
cast = Path(__file__).parent / "powernap.cast"
with open(cast, "w") as f:
    f.write(json.dumps(header) + "\n")
    for ev in events:
        f.write(json.dumps(ev) + "\n")
print(f"wrote {cast} ({len(events)} events, {events[-1][0]:.1f}s)")
