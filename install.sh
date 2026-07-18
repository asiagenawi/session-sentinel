#!/bin/bash
# session-sentinel installer (macOS). Idempotent — safe to re-run to upgrade.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SENTINEL_DIR="$HOME/.claude/session-sentinel"
SETTINGS="$HOME/.claude/settings.json"
PLIST_DST="$HOME/Library/LaunchAgents/com.session-sentinel.watcher.plist"
BIN_DIR="$HOME/.local/bin"

echo "== session-sentinel install =="

command -v python3 >/dev/null || { echo "ERROR: python3 required"; exit 1; }
command -v claude  >/dev/null || echo "WARNING: 'claude' not on PATH — fallback resume needs it"

# 1. Files
mkdir -p "$SENTINEL_DIR/checkpoints" "$BIN_DIR" "$HOME/Library/LaunchAgents"
cp "$REPO_DIR/sentinel/sentinel_common.py" "$REPO_DIR/sentinel/usage_check.py" \
   "$REPO_DIR/sentinel/fallback_watch.py" "$SENTINEL_DIR/"
[ -f "$SENTINEL_DIR/config.json" ] || cp "$REPO_DIR/sentinel/config.default.json" "$SENTINEL_DIR/config.json"
install -m 755 "$REPO_DIR/bin/claude-sentinel" "$BIN_DIR/claude-sentinel"
echo "installed files -> $SENTINEL_DIR, CLI -> $BIN_DIR/claude-sentinel"

# 2. Register hooks in ~/.claude/settings.json (merge, never clobber)
python3 - "$SETTINGS" <<'PY'
import json, sys, time, shutil, os
path = sys.argv[1]
cmd = "python3 ~/.claude/session-sentinel/usage_check.py"
try:
    with open(path) as f:
        settings = json.load(f)
    shutil.copy(path, path + f".sentinel-backup")
except (OSError, json.JSONDecodeError):
    settings = {}
hooks = settings.setdefault("hooks", {})
def ensure(event, matcher):
    entries = hooks.setdefault(event, [])
    for e in entries:
        for h in e.get("hooks", []):
            if "session-sentinel" in h.get("command", ""):
                return
    entry = {"hooks": [{"type": "command", "command": cmd}]}
    if matcher is not None:
        entry["matcher"] = matcher
    entries.append(entry)
ensure("PostToolUse", "*")
ensure("UserPromptSubmit", None)
ensure("Stop", None)
with open(path, "w") as f:
    json.dump(settings, f, indent=2)
print("hooks registered in", path, "(backup: settings.json.sentinel-backup)")
PY

# 3. launchd fallback watcher
sed "s|__HOME__|$HOME|g" "$REPO_DIR/launchd/com.session-sentinel.watcher.plist.template" > "$PLIST_DST"
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load -w "$PLIST_DST"
echo "fallback watcher loaded (launchd: com.session-sentinel.watcher)"

echo
echo "Done. Commands:  claude-sentinel status | on | off | log"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "NOTE: add $BIN_DIR to your PATH";; esac
