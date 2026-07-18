#!/usr/bin/env python3
"""claude-powernap — proactive 5-hour-limit pause-and-resume for Claude Code.

Commands:
  setup    install: deploy hook files, register hooks, schedule the watcher
  remove   uninstall (add --purge to also delete config/state/checkpoints)
  on       enable monitoring + watcher
  off      disable monitoring + watcher
  status   enabled state, watcher state, live usage
  log      tail the powernap log
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from .powernap_common import (CONFIG_PATH, LOG_PATH, POWERNAP_DIR, CLAUDE_DIR,
                                  fmt_local, load_config, load_state, save_state,
                                  state_lock, get_usage)
    from . import hooks_config
except ImportError:  # running as a flat deployed script
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from powernap_common import (CONFIG_PATH, LOG_PATH, POWERNAP_DIR, CLAUDE_DIR,
                                 fmt_local, load_config, load_state, save_state,
                                 state_lock, get_usage)
    import hooks_config

PKG_DIR = Path(__file__).resolve().parent
IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"
ASSETS = PKG_DIR / "assets"
PLIST = Path.home() / "Library" / "LaunchAgents" / "com.claude-powernap.watcher.plist"
LABEL = "com.claude-powernap.watcher"
TIMER = "claude-powernap.timer"
WIN_TASK = "claude-powernap-watcher"
BIN_DIR = Path.home() / ".local" / "bin"
DEPLOY_FILES = ["powernap_common.py", "usage_check.py", "fallback_watch.py",
                "hooks_config.py", "cli.py"]


def _stable_python():
    """Interpreter path safe to embed in hooks/shims/scheduled jobs.

    Under `uvx`, sys.executable lives in uv's cache and can be garbage-
    collected later — silently killing every hook. Prefer a system python
    whenever the current interpreter looks ephemeral.
    """
    exe = sys.executable
    markers = ("/uv/", "\\uv\\", "uv/archive", "Caches/uv", ".cache/uv",
               "/tmp/", "\\Temp\\", "pip-build-env")
    if not any(m in exe for m in markers):
        return exe
    for cand in ("python3", "python"):
        found = shutil.which(cand)
        if found and not any(m in found for m in markers):
            return found
    print(f"WARNING: only found an ephemeral interpreter ({exe}); hooks may "
          f"break if its environment is cleaned up. Install with pipx or pip "
          f"for a stable interpreter.")
    return exe


# ─────────────────────────────────────────────────────────── setup / remove

def _schedule_watcher():
    watcher = POWERNAP_DIR / "fallback_watch.py"
    if IS_MAC:
        tpl = (ASSETS / "com.claude-powernap.watcher.plist.template").read_text()
        PLIST.parent.mkdir(parents=True, exist_ok=True)
        PLIST.write_text(tpl.replace("__HOME__", str(Path.home())))
        subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
        subprocess.run(["launchctl", "load", "-w", str(PLIST)], check=True,
                       capture_output=True)
        return f"launchd: {LABEL}"
    if IS_WIN:
        py = _stable_python()
        pyw = py.replace("python.exe", "pythonw.exe")
        if not Path(pyw).exists():
            pyw = py
        tr = f'"{pyw}" "{watcher}"'
        subprocess.run(["schtasks", "/create", "/f", "/tn", WIN_TASK,
                        "/sc", "minute", "/mo", "2", "/tr", tr], check=True,
                       capture_output=True)
        return f"Task Scheduler: {WIN_TASK} (every 2 min)"
    ok = subprocess.run(["systemctl", "--user", "show-environment"],
                        capture_output=True)
    if ok.returncode == 0:
        unit_dir = Path.home() / ".config" / "systemd" / "user"
        unit_dir.mkdir(parents=True, exist_ok=True)
        for unit in ("claude-powernap.service", "claude-powernap.timer"):
            shutil.copy(ASSETS / unit, unit_dir / unit)
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        subprocess.run(["systemctl", "--user", "enable", "--now", TIMER],
                       check=True, capture_output=True)
        return (f"systemd user timer: {TIMER} "
                f"('loginctl enable-linger' keeps it active while logged out)")
    return (f"WARNING: no launchd/systemd — schedule manually, e.g. crontab: "
            f"*/2 * * * * {sys.executable} {watcher}")


def _unschedule_watcher():
    if IS_MAC:
        subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
        PLIST.unlink(missing_ok=True)
    elif IS_WIN:
        subprocess.run(["schtasks", "/delete", "/f", "/tn", WIN_TASK],
                       capture_output=True)
    else:
        subprocess.run(["systemctl", "--user", "disable", "--now", TIMER],
                       capture_output=True)
        unit_dir = Path.home() / ".config" / "systemd" / "user"
        for unit in ("claude-powernap.service", "claude-powernap.timer"):
            (unit_dir / unit).unlink(missing_ok=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)


def _write_cli_shim():
    """PATH entry for clone/uvx users; pip installs also get the entry point."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    target = POWERNAP_DIR / "cli.py"
    py = _stable_python()
    if IS_WIN:
        shim = BIN_DIR / "claude-powernap.cmd"
        shim.write_text(f'@echo off\r\n"{py}" "{target}" %*\r\n')
    else:
        shim = BIN_DIR / "claude-powernap"
        shim.write_text(f'#!/bin/sh\nexec "{py}" "{target}" "$@"\n')
        shim.chmod(0o755)
    return shim


def setup():
    print("== claude-powernap setup ==")
    if not shutil.which("claude"):
        print("WARNING: 'claude' not on PATH — fallback resume needs it")
    # 1. Deploy flat copies so hooks/watcher never depend on pip/venv location.
    (POWERNAP_DIR / "checkpoints").mkdir(parents=True, exist_ok=True)
    for name in DEPLOY_FILES:
        shutil.copy(PKG_DIR / name, POWERNAP_DIR / name)
    shutil.copytree(ASSETS, POWERNAP_DIR / "assets", dirs_exist_ok=True)
    if not CONFIG_PATH.exists():
        shutil.copy(ASSETS / "config.default.json", CONFIG_PATH)
    print(f"files -> {POWERNAP_DIR}")
    # 2. Hooks (merged into settings.json, backup written first).
    hook_cmd = f'"{_stable_python()}" "{POWERNAP_DIR / "usage_check.py"}"'
    hooks_config.register(str(CLAUDE_DIR / "settings.json"), hook_cmd)
    # 3. Watcher.
    print(f"watcher: {_schedule_watcher()}")
    # 4. CLI shim.
    print(f"cli: {_write_cli_shim()}")
    if not IS_WIN and str(BIN_DIR) not in os.environ.get("PATH", ""):
        print(f"NOTE: add {BIN_DIR} to your PATH")
    print("\nDone. Commands:  claude-powernap status | on | off | log")


def remove(purge=False):
    _unschedule_watcher()
    hooks_config.unregister(str(CLAUDE_DIR / "settings.json"))
    for shim in (BIN_DIR / "claude-powernap", BIN_DIR / "claude-powernap.cmd"):
        shim.unlink(missing_ok=True)
    if purge:
        shutil.rmtree(POWERNAP_DIR, ignore_errors=True)
        print(f"purged {POWERNAP_DIR}")
    else:
        for name in DEPLOY_FILES:
            (POWERNAP_DIR / name).unlink(missing_ok=True)
        print(f"kept config/state/checkpoints in {POWERNAP_DIR} (--purge deletes)")
    print("claude-powernap removed")


# ─────────────────────────────────────────────────────────── toggle / status

def set_watcher(value):
    if IS_MAC:
        if PLIST.exists():
            action = ["load", "-w", str(PLIST)] if value else ["unload", "-w", str(PLIST)]
            subprocess.run(["launchctl", *action], capture_output=True)
    elif IS_WIN:
        flag = "/enable" if value else "/disable"
        subprocess.run(["schtasks", "/change", "/tn", WIN_TASK, flag],
                       capture_output=True)
    else:
        action = ["enable", "--now", TIMER] if value else ["disable", "--now", TIMER]
        subprocess.run(["systemctl", "--user", *action], capture_output=True)


def set_enabled(value):
    cfg = load_config()
    cfg["enabled"] = value
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    set_watcher(value)
    print(f"claude-powernap {'ON — monitoring all Claude Code sessions' if value else 'OFF'}")


def watcher_loaded():
    if IS_MAC:
        r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        return LABEL in r.stdout
    if IS_WIN:
        r = subprocess.run(["schtasks", "/query", "/tn", WIN_TASK, "/fo", "LIST"],
                           capture_output=True, text=True)
        return r.returncode == 0 and "disabled" not in r.stdout.lower()
    r = subprocess.run(["systemctl", "--user", "is-active", TIMER],
                       capture_output=True, text=True)
    return r.stdout.strip() == "active"


def status():
    cfg = load_config()
    state = load_state()
    print(f"enabled:   {cfg.get('enabled')}")
    print(f"threshold: {cfg.get('threshold_pct')}%")
    print(f"watcher:   {'loaded' if watcher_loaded() else 'not loaded'}")
    with state_lock() as acquired:
        usage = get_usage(state, cfg)
        if acquired:  # display-only caller: never clobber state unlocked
            save_state(state)
    pct = usage.get("pct")
    print(f"5h window: {pct if pct is not None else 'unknown'}%"
          f"  (source: {usage['source']}, resets {fmt_local(usage.get('resets_at'))})")
    if usage.get("weekly_pct") is not None:
        guard = "guard on" if cfg.get("weekly_guard") else "guard off"
        print(f"weekly:    {usage['weekly_pct']}%  ({guard}, resets {fmt_local(usage.get('weekly_resets_at'))})")
    if state.get("warned"):
        print(f"warned:    {len(state['warned'])} session-window(s)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "setup":
        setup()
    elif cmd in ("remove", "uninstall"):
        remove(purge=any(a.lower() in ("--purge", "-purge") for a in sys.argv[2:]))
    elif cmd == "watcher-setup":   # used by the plugin's /powernap:watcher command
        # Deploy the files the scheduled job runs — plugin installs never ran
        # setup(), and the job must not depend on the plugin dir's lifetime.
        POWERNAP_DIR.mkdir(parents=True, exist_ok=True)
        for name in DEPLOY_FILES:  # full set: watcher-remove must survive /plugin uninstall
            shutil.copy(PKG_DIR / name, POWERNAP_DIR / name)
        print(f"watcher: {_schedule_watcher()}")
        print(f"undo anytime: python3 {POWERNAP_DIR / 'cli.py'} watcher-remove")
    elif cmd == "watcher-remove":
        _unschedule_watcher()
        print("watcher unscheduled")
    elif cmd == "on":
        set_enabled(True)
    elif cmd == "off":
        set_enabled(False)
    elif cmd == "status":
        status()
    elif cmd == "log":
        try:
            with open(LOG_PATH, errors="replace") as f:
                print("".join(f.readlines()[-40:]), end="")
        except OSError:
            print("(no log yet)")
    elif cmd in ("--version", "version"):
        try:
            from . import __version__
        except ImportError:
            __version__ = "unknown (deployed copy)"
        print(__version__)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
