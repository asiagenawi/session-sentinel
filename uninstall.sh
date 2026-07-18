#!/bin/bash
# claude-powernap uninstaller. --purge also deletes state/checkpoints/logs.
set -euo pipefail
POWERNAP_DIR="$HOME/.claude/claude-powernap"
SETTINGS="$HOME/.claude/settings.json"
PLIST="$HOME/Library/LaunchAgents/com.claude-powernap.watcher.plist"

if [ "$(uname)" = "Darwin" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
else
    systemctl --user disable --now claude-powernap.timer 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/claude-powernap.service" \
          "$HOME/.config/systemd/user/claude-powernap.timer"
    systemctl --user daemon-reload 2>/dev/null || true
fi
rm -f "$HOME/.local/bin/claude-powernap"

python3 "$(cd "$(dirname "$0")" && pwd)/scripts/hooks_config.py" unregister "$SETTINGS"

if [ "${1:-}" = "--purge" ]; then
    rm -rf "$POWERNAP_DIR"
    echo "purged $POWERNAP_DIR"
else
    rm -f "$POWERNAP_DIR"/*.py
    echo "kept config/state/checkpoints in $POWERNAP_DIR (use --purge to delete)"
fi
echo "claude-powernap uninstalled"
