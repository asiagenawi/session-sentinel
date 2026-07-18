#!/bin/bash
# claude-powernap installer (macOS). Idempotent — safe to re-run to upgrade.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
POWERNAP_DIR="$HOME/.claude/claude-powernap"
SETTINGS="$HOME/.claude/settings.json"
PLIST_DST="$HOME/Library/LaunchAgents/com.claude-powernap.watcher.plist"
BIN_DIR="$HOME/.local/bin"

echo "== claude-powernap install =="

command -v python3 >/dev/null || { echo "ERROR: python3 required"; exit 1; }
command -v claude  >/dev/null || echo "WARNING: 'claude' not on PATH — fallback resume needs it"

# 1. Files
mkdir -p "$POWERNAP_DIR/checkpoints" "$BIN_DIR" "$HOME/Library/LaunchAgents"
cp "$REPO_DIR/powernap/powernap_common.py" "$REPO_DIR/powernap/usage_check.py" \
   "$REPO_DIR/powernap/fallback_watch.py" "$POWERNAP_DIR/"
[ -f "$POWERNAP_DIR/config.json" ] || cp "$REPO_DIR/powernap/config.default.json" "$POWERNAP_DIR/config.json"
install -m 755 "$REPO_DIR/bin/claude-powernap" "$BIN_DIR/claude-powernap"
echo "installed files -> $POWERNAP_DIR, CLI -> $BIN_DIR/claude-powernap"

# 2. Register hooks in ~/.claude/settings.json (merge, never clobber)
python3 "$REPO_DIR/scripts/hooks_config.py" register "$SETTINGS" \
    "python3 ~/.claude/claude-powernap/usage_check.py"

# 3. fallback watcher (launchd on macOS, systemd user timer on Linux)
if [ "$(uname)" = "Darwin" ]; then
    sed "s|__HOME__|$HOME|g" "$REPO_DIR/launchd/com.claude-powernap.watcher.plist.template" > "$PLIST_DST"
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    launchctl load -w "$PLIST_DST"
    echo "fallback watcher loaded (launchd: com.claude-powernap.watcher)"
elif command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
    mkdir -p "$HOME/.config/systemd/user"
    cp "$REPO_DIR/systemd/claude-powernap.service" "$REPO_DIR/systemd/claude-powernap.timer" \
       "$HOME/.config/systemd/user/"
    systemctl --user daemon-reload
    systemctl --user enable --now claude-powernap.timer
    echo "fallback watcher loaded (systemd user timer: claude-powernap.timer)"
    echo "NOTE: for the watcher to run while logged out: loginctl enable-linger $USER"
else
    echo "WARNING: no launchd/systemd — fallback watcher not scheduled."
    echo "Add to crontab manually: */2 * * * * python3 $POWERNAP_DIR/fallback_watch.py"
fi

echo
echo "Done. Commands:  claude-powernap status | on | off | log"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "NOTE: add $BIN_DIR to your PATH";; esac
