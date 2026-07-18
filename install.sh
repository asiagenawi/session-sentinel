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
python3 "$REPO_DIR/scripts/hooks_config.py" register "$SETTINGS" \
    "python3 ~/.claude/session-sentinel/usage_check.py"

# 3. fallback watcher (launchd on macOS, systemd user timer on Linux)
if [ "$(uname)" = "Darwin" ]; then
    sed "s|__HOME__|$HOME|g" "$REPO_DIR/launchd/com.session-sentinel.watcher.plist.template" > "$PLIST_DST"
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    launchctl load -w "$PLIST_DST"
    echo "fallback watcher loaded (launchd: com.session-sentinel.watcher)"
elif command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
    mkdir -p "$HOME/.config/systemd/user"
    cp "$REPO_DIR/systemd/session-sentinel.service" "$REPO_DIR/systemd/session-sentinel.timer" \
       "$HOME/.config/systemd/user/"
    systemctl --user daemon-reload
    systemctl --user enable --now session-sentinel.timer
    echo "fallback watcher loaded (systemd user timer: session-sentinel.timer)"
    echo "NOTE: for the watcher to run while logged out: loginctl enable-linger $USER"
else
    echo "WARNING: no launchd/systemd — fallback watcher not scheduled."
    echo "Add to crontab manually: */2 * * * * python3 $SENTINEL_DIR/fallback_watch.py"
fi

echo
echo "Done. Commands:  claude-sentinel status | on | off | log"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "NOTE: add $BIN_DIR to your PATH";; esac
