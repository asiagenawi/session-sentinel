#!/bin/bash
# session-sentinel uninstaller. --purge also deletes state/checkpoints/logs.
set -euo pipefail
SENTINEL_DIR="$HOME/.claude/session-sentinel"
SETTINGS="$HOME/.claude/settings.json"
PLIST="$HOME/Library/LaunchAgents/com.session-sentinel.watcher.plist"

launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST" "$HOME/.local/bin/claude-sentinel"

python3 - "$SETTINGS" <<'PY'
import json, sys
path = sys.argv[1]
try:
    with open(path) as f:
        settings = json.load(f)
except (OSError, json.JSONDecodeError):
    sys.exit(0)
hooks = settings.get("hooks", {})
for event in list(hooks):
    hooks[event] = [e for e in hooks[event]
                    if not any("session-sentinel" in h.get("command", "")
                               for h in e.get("hooks", []))]
    if not hooks[event]:
        del hooks[event]
if not hooks:
    settings.pop("hooks", None)
with open(path, "w") as f:
    json.dump(settings, f, indent=2)
print("hooks removed from", path)
PY

if [ "${1:-}" = "--purge" ]; then
    rm -rf "$SENTINEL_DIR"
    echo "purged $SENTINEL_DIR"
else
    rm -f "$SENTINEL_DIR"/*.py
    echo "kept config/state/checkpoints in $SENTINEL_DIR (use --purge to delete)"
fi
echo "session-sentinel uninstalled"
