#!/usr/bin/env python3
"""CI check: state_lock serializes concurrent read-modify-write across processes.

Spawns N processes that each do a locked load->increment->save on a counter.
Without the lock this loses updates; with it the final count must be exactly N.
"""
import json
import subprocess
import sys
from pathlib import Path

POWERNAP = Path.home() / ".claude" / "claude-powernap"
N = 12

WORKER = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from powernap_common import state_lock, load_state, save_state
with state_lock(timeout=30) as acquired:
    assert acquired, "worker failed to acquire lock within 30s"
    st = load_state()
    st["counter"] = st.get("counter", 0) + 1
    save_state(st)
"""

state_path = POWERNAP / "state.json"
st = json.loads(state_path.read_text()) if state_path.exists() else {}
st["counter"] = 0
POWERNAP.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(st))

procs = [subprocess.Popen([sys.executable, "-c", WORKER, str(POWERNAP)])
         for _ in range(N)]
for p in procs:
    assert p.wait(timeout=120) == 0, "worker crashed"

final = json.loads(state_path.read_text())["counter"]
assert final == N, f"lost updates: expected {N}, got {final}"
print(f"lock test OK ({N}/{N} increments survived)")
