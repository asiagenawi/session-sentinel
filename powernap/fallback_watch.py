#!/usr/bin/env python3
"""External fallback watcher (run by launchd every ~2 min).

Detects sessions that hard-hit the 5h limit (rate-limit error is the last real
record in the transcript), waits for the window reset, then resumes VISIBLY:
  a) original claude process dead -> open a terminal window resuming the session
  b) original process still alive -> macOS notification only (never inject/fork)
  c) no GUI/terminal available     -> headless `claude -p --resume` to the log

Flags: --dry-run (report decisions, act on nothing)
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from powernap_common import (CHECKPOINT_DIR, IS_MAC, IS_WIN, PROJECTS_DIR,
                             POWERNAP_DIR, fmt_local, load_config, load_state,
                             log, save_state, state_lock)

# (binary, flags-before-command) pairs, tried in order on Linux
LINUX_TERMINALS = [
    ("x-terminal-emulator", ["-e"]), ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]), ("xfce4-terminal", ["-x"]),
    ("kitty", []), ("alacritty", ["-e"]), ("xterm", ["-e"]),
]

RESET_RE = re.compile(r"resets\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?:\s*\(([^)]+)\))?",
                      re.IGNORECASE)


def tail_records(path, n=5):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 65536))
            lines = f.read().decode(errors="replace").splitlines()[-n:]
    except OSError:
        return []
    recs = []
    for line in lines:
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return recs


def find_rate_limit(recs):
    """Return (record, reset_text) if the newest API-visible record is a 429."""
    for rec in reversed(recs):
        if rec.get("error") == "rate_limit" or rec.get("apiErrorStatus") == 429:
            content = ((rec.get("message") or {}).get("content")) or []
            text = ""
            if isinstance(content, list):
                text = " ".join(c.get("text", "") for c in content
                                if isinstance(c, dict))
            elif isinstance(content, str):
                text = content
            # Only genuine usage-limit hits: transient/server 429s say
            # "not your usage limit" and carry no "resets <time>" text.
            if "resets" not in text or "not your usage limit" in text:
                return None, None
            return rec, text
        if rec.get("type") in ("user", "assistant"):
            return None, None  # newer real activity after the error -> recovered
    return None, None


def parse_reset(text, error_ts_iso):
    """Parse 'resets 12:10am (America/Indianapolis)' relative to the error time."""
    m = RESET_RE.search(text or "")
    if not m:
        return None
    hh, mm, ampm, tzname = int(m.group(1)), int(m.group(2) or 0), m.group(3), m.group(4)
    if ampm:
        ampm = ampm.lower()
        hh = hh % 12 + (12 if ampm == "pm" else 0)
    tz = None
    if tzname:
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(tzname.strip())
        except Exception:
            tz = None
    try:
        err = datetime.fromisoformat(error_ts_iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        err = datetime.now(timezone.utc)
    err = err.astimezone(tz) if tz else err.astimezone()
    reset = err.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if reset <= err:
        reset += timedelta(days=1)
    return reset


def transcript_holders(path):
    """PIDs holding the transcript open (claude keeps its session file open).

    Windows has no lsof//proc, so the check is deliberately conservative:
    report 'alive' (a sentinel [-1]) if the transcript file is held open
    (rename-test) OR any claude.exe is running. False 'alive' just means the
    user gets a notification instead of an auto-resume — never a forked session.
    """
    if IS_WIN:
        try:
            out = subprocess.run(["tasklist"], capture_output=True, text=True,
                                 timeout=15).stdout.lower()
            if "claude.exe" in out:
                return [-1]
        except Exception:
            return [-1]
        try:
            probe = str(path) + ".livecheck"
            os.replace(str(path), probe)
            os.replace(probe, str(path))
            return []          # rename succeeded -> nothing holds it open
        except OSError:
            return [-1]        # held open (or locked) -> treat as alive
    try:
        out = subprocess.run(["lsof", "-t", str(path)], capture_output=True,
                             text=True, timeout=10)
        if out.returncode in (0, 1):  # 1 = ran fine, no holders
            return [int(p) for p in out.stdout.split()]
    except Exception:
        pass
    if IS_MAC:
        return []
    # Linux fallback when lsof is missing: scan /proc/*/fd symlinks.
    pids = []
    target = str(Path(path).resolve())
    for fd_dir in Path("/proc").glob("[0-9]*/fd"):
        try:
            for fd in fd_dir.iterdir():
                if str(fd.resolve()) == target:
                    pids.append(int(fd_dir.parent.name))
                    break
        except (OSError, PermissionError):
            continue
    return pids


def resume_prompt(session_id):
    ckpt = CHECKPOINT_DIR / f"{session_id}.md"
    return (f"You hit the session limit and were auto-resumed by claude-powernap. "
            f"Read {ckpt} if it exists, otherwise infer state from this session's "
            f"context, and continue the work.")


def open_terminal_resume(cwd, session_id, cfg):
    prompt = resume_prompt(session_id).replace('"', '\\"')
    shell_cmd = f'cd {cwd} && claude --resume {session_id} "{prompt}"'
    if IS_WIN:
        import shutil
        claude = shutil.which("claude") or "claude"
        # A batch file sidesteps cmd.exe quoting entirely.
        bat = POWERNAP_DIR / f"resume-{session_id}.cmd"
        bat.write_text(f'@echo off\r\ncd /d "{cwd}"\r\n'
                       f'"{claude}" --resume {session_id} "{resume_prompt(session_id)}"\r\n')
        if shutil.which("wt"):
            subprocess.Popen(["wt", "new-tab", "cmd", "/k", str(bat)])
        else:
            subprocess.Popen(["cmd", "/c", "start", "claude-powernap", "cmd",
                              "/k", str(bat)])
        return
    if not IS_MAC:
        import shutil
        preferred = cfg.get("terminal_app")
        terms = ([(preferred, ["-e"])] if preferred and preferred not in
                 ("Terminal", "iTerm2") else []) + LINUX_TERMINALS
        for term, flags in terms:
            if term and shutil.which(term):
                subprocess.Popen(
                    [term, *flags, "bash", "-c", f"{shell_cmd}; exec bash"],
                    start_new_session=True)
                return
        raise RuntimeError("no terminal emulator found")
    app = cfg.get("terminal_app", "Terminal")
    if app == "iTerm2":
        script = (f'tell application "iTerm2"\n activate\n'
                  f' create window with default profile\n'
                  f' tell current session of current window to write text "{shell_cmd}"\n'
                  f'end tell')
    else:
        script = (f'tell application "Terminal"\n activate\n'
                  f' do script "{shell_cmd}"\nend tell')
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True,
                       timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f"osascript failed: {r.stderr.strip()}")


WIN_TOAST_PS = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $x.GetElementsByTagName('text'); $t.Item(0).AppendChild($x.CreateTextNode($env:SS_TITLE)) | Out-Null; $t.Item(1).AppendChild($x.CreateTextNode($env:SS_MSG)) | Out-Null
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('claude-powernap').Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""


def notify(title, message):
    if IS_MAC:
        cmd = ["osascript", "-e",
               f'display notification "{message}" with title "{title}"']
        env = None
    elif IS_WIN:
        cmd = ["powershell", "-NoProfile", "-Command", WIN_TOAST_PS]
        env = {**os.environ, "SS_TITLE": title, "SS_MSG": message}
    else:
        cmd = ["notify-send", title, message]
        env = None
    try:
        subprocess.run(cmd, capture_output=True, timeout=15, env=env)
    except Exception:
        pass  # notification is best-effort everywhere


def headless_resume(cwd, session_id, cfg):
    import shutil
    claude = shutil.which("claude") or "claude"  # resolves claude.cmd on Windows
    cmd = [claude, "--resume", session_id, "-p", resume_prompt(session_id),
           *cfg.get("headless_resume_extra_args", [])]
    subprocess.Popen(cmd, cwd=cwd, stdout=open(str(CHECKPOINT_DIR.parent / "powernap.log"), "a"),
                     stderr=subprocess.STDOUT, start_new_session=True)


def session_cwd(path):
    try:
        with open(path, errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("cwd"):
                    return rec["cwd"]
    except OSError:
        pass
    return str(Path.home())


def main():
    dry = "--dry-run" in sys.argv
    cfg = load_config()
    if not cfg.get("enabled") and not dry:
        return
    with state_lock(timeout=5.0) as acquired:
        if not acquired and not dry:
            return  # a hook holds it; the timer re-runs in 2 min
        run_watch(cfg, dry)


def run_watch(cfg, dry):
    state = load_state()
    resumed = state.setdefault("resumed", {})
    notified = state.setdefault("notified", {})
    now = time.time()

    if not PROJECTS_DIR.is_dir():
        return
    for jsonl in PROJECTS_DIR.glob("*/*.jsonl"):
        try:
            mtime = jsonl.stat().st_mtime
        except OSError:
            continue
        if now - mtime > 6 * 3600:
            continue
        rec, text = find_rate_limit(tail_records(jsonl))
        if not rec:
            continue
        session_id = jsonl.stem
        reset = parse_reset(text, rec.get("timestamp"))
        if dry:
            print(f"session={session_id} limit-hit, reset={reset} "
                  f"({fmt_local(reset.isoformat()) if reset else '?'})")
            continue
        if reset is None:
            log(f"fallback: session {session_id} hit limit but reset time unparseable")
            continue
        reset_ep = reset.timestamp()
        if now < reset_ep + 120:            # not reset yet (+2 min grace)
            continue
        if now - mtime < 300:               # touched in last 5 min -> leave it be
            continue
        if session_id in resumed:
            continue

        holders = transcript_holders(jsonl)
        cwd = session_cwd(jsonl)
        if holders:
            if now - notified.get(session_id, 0) > 1800:
                notified[session_id] = now
                notify("claude-powernap",
                       f"Limit reset. Session {session_id[:8]}… is open and waiting "
                       f"— submit any prompt to continue.")
                log(f"fallback: session {session_id} alive (pids {holders}), notified user")
        else:
            resumed[session_id] = now
            try:
                open_terminal_resume(cwd, session_id, cfg)
                log(f"fallback: resumed {session_id} in {cfg.get('terminal_app')} window (cwd {cwd})")
                notify("claude-powernap", f"Auto-resumed session {session_id[:8]}… in a new window.")
            except Exception as e:
                log(f"fallback: terminal resume failed ({e!r}); going headless")
                try:
                    headless_resume(cwd, session_id, cfg)
                    log(f"fallback: headless resume launched for {session_id}")
                except Exception as e2:
                    log(f"fallback: headless resume ALSO failed: {e2!r}")
                    del resumed[session_id]
    save_state(state)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"fallback_watch error: {e!r}")
        sys.exit(0)
