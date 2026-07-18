#!/usr/bin/env python3
"""CI check: garbage local budgets can never produce wild >150% warnings.

Regression for the 2026-07-18 field incident: leftover test/demo configs
(local_budget_weighted_tokens=1000 from CI's threshold step; 755000 plus
endpoint_enabled=false from a demo recording) made get_usage_local divide a
real multi-megatoken block by a tiny budget, emitting warnings of 339340.3%
up to 653929.7%, with negative "minutes away" projections.

Each scenario runs in a throwaway sandbox (POWERNAP_HOME + CLAUDE_CONFIG_DIR)
so the live install is never touched.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

DEPLOYED = Path.home() / ".claude" / "claude-powernap"
USAGE_CHECK = DEPLOYED / "usage_check.py"
assert USAGE_CHECK.exists(), f"deployed copy missing: {USAGE_CHECK}"

sys.path.insert(0, str(DEPLOYED))
from powernap_common import projected_minutes_to_limit  # noqa: E402
from usage_check import build_warning  # noqa: E402


def make_sandbox(budget, weighted_tokens):
    """Sandbox with a config using `budget` and one block of `weighted_tokens`."""
    root = Path(tempfile.mkdtemp(prefix="powernap-sanity-"))
    home = root / "powernap"
    claude = root / "claude"
    home.mkdir()
    (claude / "projects" / "-test").mkdir(parents=True)
    with open(home / "config.json", "w") as f:
        json.dump({"enabled": True, "threshold_pct": 0, "check_interval_s": 0,
                   "endpoint_enabled": False,
                   "local_budget_weighted_tokens": budget}, f)
    rec = {"type": "assistant", "sessionId": "sanity-test",
           "requestId": "req-sanity-1",
           "timestamp": datetime.now(timezone.utc).isoformat()
           .replace("+00:00", "Z"),
           "message": {"usage": {"input_tokens": int(weighted_tokens),
                                 "output_tokens": 0,
                                 "cache_creation_input_tokens": 0,
                                 "cache_read_input_tokens": 0}}}
    with open(claude / "projects" / "-test" / "sanity-test.jsonl", "w") as f:
        f.write(json.dumps(rec) + "\n")
    return home, claude


def run_hook(home, claude):
    env = dict(os.environ, POWERNAP_HOME=str(home), CLAUDE_CONFIG_DIR=str(claude))
    out = subprocess.run(
        [sys.executable, str(USAGE_CHECK)],
        input='{"session_id":"sanity-test","hook_event_name":"PostToolUse"}',
        capture_output=True, text=True, timeout=120, env=env)
    assert out.returncode == 0, f"hook exited {out.returncode}: {out.stderr!r}"
    return out.stdout


def assert_sane(stdout, home):
    """No >150% warning; any warning shown is clamped to <= 100%."""
    if "USAGE LIMIT WARNING" in stdout:
        m = re.search(r"consumed ([\d.]+)% of", stdout)
        assert m, f"warning without a pct: {stdout!r}"
        assert float(m.group(1)) <= 100, f"wild pct escaped: {stdout!r}"
        assert "~-" not in stdout, f"negative minutes in warning: {stdout!r}"
    state = json.loads((home / "state.json").read_text())
    proj = state.get("projected_min_to_limit")
    assert proj is None or proj >= 0, f"negative projection persisted: {proj}"
    lp = state.get("last_pct")
    assert lp is None or lp <= 100, f"wild last_pct persisted: {lp}"


# 1. Test-leftover budget (1000) + heavy real block: config sanity check must
#    ignore the budget entirely -> no estimate, no wild warning, log line.
home, claude = make_sandbox(budget=1000, weighted_tokens=5_000_000)
stdout = run_hook(home, claude)
assert "USAGE LIMIT WARNING" not in stdout, \
    f"tiny budget produced a warning: {stdout!r}"
assert_sane(stdout, home)
log_text = (home / "powernap.log").read_text()
assert "implausibly small" in log_text, f"missing diagnostic: {log_text!r}"
print("scenario 1 OK: budget=1000 ignored, no warning, diagnostic logged")

# 2. Plausible-but-wrong budget, block 5x over it: estimate must be discarded
#    (pct None) with a diagnostic naming tokens/budget/source.
home, claude = make_sandbox(budget=200_000, weighted_tokens=1_000_000)
stdout = run_hook(home, claude)
assert "USAGE LIMIT WARNING" not in stdout, \
    f">150% estimate produced a warning: {stdout!r}"
assert_sane(stdout, home)
log_text = (home / "powernap.log").read_text()
assert "local estimate unreliable" in log_text \
    and "budget_source=config" in log_text, f"missing diagnostic: {log_text!r}"
print("scenario 2 OK: 500% estimate discarded with diagnostic")

# 3. Mild overshoot (130%): clamped to 100.0, warning allowed, never negative
#    minutes.
home, claude = make_sandbox(budget=200_000, weighted_tokens=260_000)
stdout = run_hook(home, claude)
assert "USAGE LIMIT WARNING" in stdout, f"expected clamped warning: {stdout!r}"
assert "consumed 100.0% of" in stdout, f"expected clamp to 100.0: {stdout!r}"
assert_sane(stdout, home)
print("scenario 3 OK: 130% clamped to 100.0")

# 4. projected_minutes_to_limit never returns negative, even with poisoned
#    over-100 samples in state (as the incident left behind).
now = time.time()
state = {"samples": [[now - 600, 80.0], [now - 300, 95.0], [now - 60, 100.0]]}
p = projected_minutes_to_limit(state, now)
assert p == 0.0, f"expected 0 at the limit with positive rate, got {p}"
state = {"samples": [[now - 300, 110.0], [now - 60, 130.0]]}
p = projected_minutes_to_limit(state, now)
assert p is not None and p >= 0, f"negative projection: {p}"
print("scenario 4 OK: projections floored at 0")

# 5. build_warning never renders a "minutes away" clause for projected <= 0.
cfg = {"resume_grace_min": 3}
resets = datetime.now(timezone.utc).isoformat()
for proj in (0, -2.5):
    text = build_warning(100.0, resets, "sanity-test", cfg, "local", proj)
    assert "minutes away" not in text, f"rendered pace for {proj}: {text!r}"
text = build_warning(90.0, resets, "sanity-test", cfg, "local", 7.4)
assert "~7 minutes away" in text, f"positive pace missing: {text!r}"
print("scenario 5 OK: pace clause only for positive projections")

print("estimate sanity test OK")
