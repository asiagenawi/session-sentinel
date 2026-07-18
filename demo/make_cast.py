#!/usr/bin/env python3
"""Generate demo/powernap.cast (asciinema v2) for the README GIF.

The transcript replays REAL outputs captured from an actual powernap cycle
(2026-07-18) with presentation timing. Render with:
  agg --font-size 15 demo/powernap.cast demo/powernap.gif
"""
import json
from pathlib import Path

DIM, BOLD, YELLOW, GREEN, RESET = "\x1b[2m", "\x1b[1m", "\x1b[33m", "\x1b[32m", "\x1b[0m"
PROMPT = "\x1b[35m❯\x1b[0m "

events, t = [], 0.5


def out(data, dt=0.0):
    global t
    t += dt
    events.append([round(t, 3), "o", data])


def type_cmd(cmd, pause_after=0.35):
    out(PROMPT)
    for ch in cmd:
        out(ch, 0.045)
    out("\r\n", pause_after)


def line(text, dt=0.15, hold=0.0):
    out(text + "\r\n", dt)
    global t
    t += hold


type_cmd("claude-powernap status")
line("enabled:   True")
line("threshold: 90%")
line("watcher:   loaded")
line(f"5h window: {BOLD}89%{RESET}  (source: endpoint, resets 03:00AM EDT)")
line("weekly:    34%  (guard off, resets Jul 22)", hold=2.0)
line("")

type_cmd("# meanwhile, a long automation is running in Claude Code…", 0.6)
line(f"{DIM}· Working… (batch migration, 3 h 40 m in){RESET}", 0.4, hold=1.0)
line(f"{DIM}⏺ Edit(src/parsers/feed.py) — updated 12 call sites{RESET}", hold=1.3)
line("")
line(f"{YELLOW}⚠ [claude-powernap] USAGE LIMIT WARNING: you have consumed 91% of the{RESET}", 0.35)
line(f"{YELLOW}  5-hour usage window. The window resets at 03:00AM EDT. At the current{RESET}", 0.25)
line(f"{YELLOW}  burn rate the limit is ~8 minutes away. Follow the pause protocol NOW.{RESET}", 0.25, hold=1.8)
line("")
line("⏺ I'm approaching the session limit — pausing gracefully.", hold=1.0)
line("⏺ Write(~/.claude/claude-powernap/checkpoints/aeda6f64.md)", hold=0.9)
line(f"  {DIM}└ work completed · current state · exact next steps{RESET}", hold=1.1)
line("⏺ Scheduled one-shot resume at 03:03AM EDT.", hold=1.0)
line("")
line(f"{BOLD}Pausing until 03:03AM EDT — leave this terminal open.{RESET} 💤", hold=2.4)
line("")
line(f"{DIM}────────────────  3:03 AM — window has reset  ────────────────{RESET}", hold=1.8)
line("")
line(f"{GREEN}⏺ Session window has reset. Reading checkpoint…{RESET}", hold=1.1)
line("⏺ Read(~/.claude/claude-powernap/checkpoints/aeda6f64.md)", hold=0.9)
line("⏺ Resuming: 12 call sites done, continuing with src/parsers/atom.py", hold=1.2)
line(f"{DIM}· Working…{RESET}", hold=2.0)
line("")

type_cmd("claude-powernap log")
line(f"{DIM}01:07:32{RESET} WARN session=aeda6f64 pct=91 trigger=burn-rate projection source=endpoint")
line(f"{DIM}03:03:05{RESET} resume: session aeda6f64 woke via scheduled task", hold=3.5)

header = {"version": 2, "width": 100, "height": 30,
          "title": "claude-powernap demo",
          "env": {"TERM": "xterm-256color", "SHELL": "/bin/zsh"}}
cast = Path(__file__).parent / "powernap.cast"
with open(cast, "w") as f:
    f.write(json.dumps(header) + "\n")
    for ev in events:
        f.write(json.dumps(ev) + "\n")
print(f"wrote {cast} ({len(events)} events, {events[-1][0]:.1f}s)")
