#!/usr/bin/env python3
"""Register/unregister session-sentinel hooks in Claude Code settings.json.

Usage:
  hooks_config.py register   <settings.json> <hook-command>
  hooks_config.py unregister <settings.json>

Idempotent; merges without touching unrelated settings. 'session-sentinel'
in a hook's command string marks it as ours.
"""
import json
import shutil
import sys


def load(path):
    try:
        with open(path) as f:
            return json.load(f), True
    except (OSError, json.JSONDecodeError):
        return {}, False


def register(path, cmd):
    settings, existed = load(path)
    if existed:
        shutil.copy(path, path + ".sentinel-backup")
    hooks = settings.setdefault("hooks", {})

    def ensure(event, matcher):
        entries = hooks.setdefault(event, [])
        if any("session-sentinel" in h.get("command", "")
               for e in entries for h in e.get("hooks", [])):
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
    print(f"hooks registered in {path}" + (" (backup saved)" if existed else ""))


def unregister(path):
    settings, existed = load(path)
    if not existed:
        return
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
    print(f"hooks removed from {path}")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("register", "unregister"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "register":
        register(sys.argv[2], sys.argv[3])
    else:
        unregister(sys.argv[2])
