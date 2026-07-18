#!/bin/bash
# claude-powernap installer (macOS / Linux / WSL). Idempotent.
# Thin wrapper: all logic lives in the package CLI (`claude-powernap setup`).
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "ERROR: python3 required"; exit 1; }
PYTHONPATH=src exec python3 -m claude_powernap setup
