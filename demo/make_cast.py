#!/usr/bin/env python3
"""Generate demo/powernap.cast (asciinema v2) for the README GIF.

Styled after the Claude Code TUI; the powernap outputs replay REAL events
from an actual cycle (2026-07-18) with presentation timing. Render with:
  agg --font-size 15 --theme monokai --last-frame-duration 4 demo/powernap.cast demo/powernap.gif
"""
import json
from pathlib import Path

DIM, BOLD, RESET = "\x1b[2m", "\x1b[1m", "\x1b[0m"
YELLOW, GREEN, ORANGE, CYAN = "\x1b[33m", "\x1b[32m", "\x1b[38;5;209m", "\x1b[36m"
W = 96

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
line(f"{DIM}│   /help for help · cwd: ~/Brevy/atlas{' ' * (W - 41)}│{RESET}")
line(f"{DIM}╰{'─' * (W - 2)}╯{RESET}", hold=1.0)
line()

# ── the long automation ───────────────────────────────────────────────────
typed(f"{DIM}>{RESET} ", "run the overnight batch migration across all 437 articles", 0.9)
line()
line("⏺ Starting the migration. I'll work through the parsers in order.", hold=1.1)
line()
line(f"⏺ {BOLD}Update{RESET}(src/parsers/feed.py)")
line(f"  {DIM}⎿  Updated 12 call sites{RESET}", hold=1.2)
line()
line(f"{ORANGE}✻{RESET} {DIM}Working… (3h 40m elapsed · esc to interrupt){RESET}", hold=1.6)
line()

# ── the warning lands ─────────────────────────────────────────────────────
line(f"{YELLOW}⚠ [claude-powernap] USAGE LIMIT WARNING: 91% of the 5-hour window consumed.{RESET}", 0.3)
line(f"{YELLOW}  Resets 03:00AM EDT — at the current burn rate the limit is ~8 minutes away.{RESET}", 0.2, hold=1.8)
line()
line("⏺ I'm approaching the session limit — pausing gracefully instead of dying", 0.25)
line("  mid-task.", hold=0.9)
line()
line(f"⏺ {BOLD}Write{RESET}(~/.claude/claude-powernap/checkpoints/aeda6f64.md)")
line(f"  {DIM}⎿  Wrote 41 lines — work completed · current state · exact next steps{RESET}", hold=1.2)
line()
line(f"⏺ {BOLD}Scheduled task{RESET}(one-shot · 03:03AM EDT · \"resume from checkpoint\")", hold=1.1)
line()
line(f"⏺ {BOLD}Pausing until 03:03AM EDT — leave this terminal open.{RESET} 💤", hold=2.6)
line()

# ── the reset ─────────────────────────────────────────────────────────────
line(f"{DIM}{'─' * 34}  3:03 AM  {'─' * 34}{RESET}", hold=1.6)
line()
line(f"{DIM}>{RESET} {DIM}Session window has reset. Read the checkpoint and continue the work.{RESET}", 0.3, hold=1.3)
line()
line(f"⏺ {BOLD}Read{RESET}(~/.claude/claude-powernap/checkpoints/aeda6f64.md)")
line(f"  {DIM}⎿  41 lines{RESET}", hold=1.0)
line()
line(f"⏺ {GREEN}Back from the powernap.{RESET} 12 call sites done — continuing with", 0.25)
line("  src/parsers/atom.py.", hold=1.1)
line()
line(f"⏺ {BOLD}Update{RESET}(src/parsers/atom.py)")
line(f"  {DIM}⎿  Updated 9 call sites{RESET}", hold=1.0)
line()
line(f"{ORANGE}✻{RESET} {DIM}Working…{RESET}", hold=1.8)
line()

# ── idle input box ────────────────────────────────────────────────────────
line(f"{DIM}╭{'─' * (W - 2)}╮{RESET}")
line(f"{DIM}│{RESET} > {' ' * (W - 6)}{DIM}│{RESET}")
line(f"{DIM}╰{'─' * (W - 2)}╯{RESET}")
line(f"  {DIM}? for shortcuts{RESET}", hold=3.0)

header = {"version": 2, "width": 100, "height": 42,
          "title": "claude-powernap demo",
          "env": {"TERM": "xterm-256color", "SHELL": "/bin/zsh"}}
cast = Path(__file__).parent / "powernap.cast"
with open(cast, "w") as f:
    f.write(json.dumps(header) + "\n")
    for ev in events:
        f.write(json.dumps(ev) + "\n")
print(f"wrote {cast} ({len(events)} events, {events[-1][0]:.1f}s)")
