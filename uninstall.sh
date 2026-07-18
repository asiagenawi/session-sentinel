#!/bin/bash
# claude-powernap uninstaller. --purge also deletes config/state/checkpoints.
set -euo pipefail
cd "$(dirname "$0")"
PYTHONPATH=src exec python3 -m claude_powernap remove "$@"
