#!/usr/bin/env python3
"""CI check: the watcher spots a napping session whose resume alarm died."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

POWERNAP = Path.home() / ".claude" / "claude-powernap"
sys.path.insert(0, str(POWERNAP))
from powernap_common import PROJECTS_DIR, state_lock  # honors CLAUDE_CONFIG_DIR

PROJECTS = PROJECTS_DIR / "-test"
SESSION = "rescue-test-session"
CLI = POWERNAP / "cli.py"

# A LIVE watcher (launchd/schtasks, loaded by the install step) would race us:
# it can consume or clobber the fixture between our write and the dry-run.
# `off` unloads it; a straggler run exits immediately on enabled=False.
subprocess.run([sys.executable, str(CLI), "off"], capture_output=True, timeout=60)
try:
    PROJECTS.mkdir(parents=True, exist_ok=True)
    jsonl = PROJECTS / f"{SESSION}.jsonl"
    jsonl.write_text(json.dumps({"type": "assistant", "sessionId": SESSION,
                                 "cwd": str(Path.home())}) + "\n")
    two_hours_ago = time.time() - 2 * 3600
    os.utime(jsonl, (two_hours_ago, two_hours_ago))

    state_path = POWERNAP / "state.json"
    with state_lock(timeout=15) as acquired:
        assert acquired, "could not acquire state lock for fixture write"
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        state.setdefault("paused", {})[SESSION] = {
            "paused_at": time.time() - 3 * 3600,
            "resets_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }
        state.setdefault("resumed", {}).pop(SESSION, None)
        POWERNAP.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state))

    out = subprocess.run([sys.executable, str(POWERNAP / "fallback_watch.py"),
                          "--dry-run"], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert "missed its alarm" in out.stdout, \
        f"rescue not detected: {out.stdout!r} {out.stderr!r}"

    # cleanup so later CI steps see clean state
    with state_lock(timeout=15):
        state = json.loads(state_path.read_text())
        state.get("paused", {}).pop(SESSION, None)
        state_path.write_text(json.dumps(state))
    jsonl.unlink()
finally:
    subprocess.run([sys.executable, str(CLI), "on"], capture_output=True, timeout=60)
print("rescue test OK")
