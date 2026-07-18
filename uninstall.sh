#!/bin/bash
# session-sentinel uninstaller. --purge also deletes state/checkpoints/logs.
set -euo pipefail
SENTINEL_DIR="$HOME/.claude/session-sentinel"
SETTINGS="$HOME/.claude/settings.json"
PLIST="$HOME/Library/LaunchAgents/com.session-sentinel.watcher.plist"

if [ "$(uname)" = "Darwin" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
else
    systemctl --user disable --now session-sentinel.timer 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/session-sentinel.service" \
          "$HOME/.config/systemd/user/session-sentinel.timer"
    systemctl --user daemon-reload 2>/dev/null || true
fi
rm -f "$HOME/.local/bin/claude-sentinel"

python3 "$(cd "$(dirname "$0")" && pwd)/scripts/hooks_config.py" unregister "$SETTINGS"

if [ "${1:-}" = "--purge" ]; then
    rm -rf "$SENTINEL_DIR"
    echo "purged $SENTINEL_DIR"
else
    rm -f "$SENTINEL_DIR"/*.py
    echo "kept config/state/checkpoints in $SENTINEL_DIR (use --purge to delete)"
fi
echo "session-sentinel uninstalled"
