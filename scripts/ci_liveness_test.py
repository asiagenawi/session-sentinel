#!/usr/bin/env python3
"""CI check: Windows liveness detection (rename-test) on an open vs closed file."""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "claude-powernap"))
from fallback_watch import transcript_holders

path = Path.home() / ".claude" / "projects" / "-test" / "ci-test.jsonl"
assert path.exists(), f"fixture missing: {path}"

holders = transcript_holders(path)
assert holders == [], f"expected no holders on closed file, got {holders}"

child = subprocess.Popen([sys.executable, "-c",
                          f"f = open(r'{path}', 'a'); import time; time.sleep(60)"])
try:
    time.sleep(3)
    holders = transcript_holders(path)
    assert holders, "expected holders while a child process holds the file open"
finally:
    child.kill()
print("liveness check OK")
