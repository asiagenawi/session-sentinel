#!/usr/bin/env python3
"""Claude Code hook: warn the live session when the 5h usage window nears its limit.

Registered as PostToolUse / UserPromptSubmit / Stop hook. Reads hook JSON on
stdin; at/above threshold emits hookSpecificOutput.additionalContext with the
pause-and-self-resume protocol. Silent otherwise.

Flags: --debug (print usage, no throttle)  --force-local (skip endpoint)
"""
import json
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from sentinel_common import (CHECKPOINT_DIR, fmt_local, load_config, load_state,
                             log, save_state, get_usage, get_usage_local)


def build_warning(pct, resets_iso, session_id, cfg, source):
    resume_at = "the reset time"
    try:
        dt = datetime.fromisoformat(resets_iso.replace("Z", "+00:00"))
        resume_at = (dt + timedelta(minutes=cfg["resume_grace_min"])).astimezone() \
            .strftime("%Y-%m-%d %H:%M %Z")
    except (ValueError, AttributeError):
        pass
    ckpt = CHECKPOINT_DIR / f"{session_id or 'unknown-session'}.md"
    approx = " (approximate local estimate)" if source == "local" else ""
    return (
        f"[session-sentinel] USAGE LIMIT WARNING: you have consumed {pct}% of the "
        f"5-hour usage window{approx}. The window resets at {fmt_local(resets_iso)}. "
        f"To avoid dying mid-task, follow this pause protocol NOW:\n"
        f"1. Do NOT start new work. Finish or safely stop the current step only.\n"
        f"2. Write a checkpoint file to {ckpt} covering: work completed, current "
        f"state, and exact next steps so you can resume cold.\n"
        f"3. Create a ONE-SHOT scheduled task (scheduled-tasks / cron capability) "
        f"firing at {resume_at} with this prompt: 'Session window has reset. Read "
        f"{ckpt} and continue the work from where it left off.'\n"
        f"4. Tell the user you are pausing until {resume_at}, then END your turn "
        f"and idle. Do not keep working past this warning.\n"
        f"If you cannot create scheduled tasks, still write the checkpoint, then "
        f"tell the user to send any message after {resume_at} to resume."
    )


def main():
    argv = sys.argv[1:]
    debug = "--debug" in argv
    force_local = "--force-local" in argv

    cfg = load_config()
    if not cfg.get("enabled") and not debug:
        return

    hook_input = {}
    if not sys.stdin.isatty():
        try:
            hook_input = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            hook_input = {}
    session_id = hook_input.get("session_id", "")
    event = hook_input.get("hook_event_name", "PostToolUse")

    state = load_state()
    now = time.time()
    if not debug and now - state.get("last_check", 0) < cfg["check_interval_s"]:
        return
    state["last_check"] = now

    usage = get_usage_local(state) if force_local else get_usage(state, cfg)
    state.update({"last_pct": usage.get("pct"), "last_source": usage["source"],
                  "last_resets_at": usage.get("resets_at"),
                  "last_weekly_pct": usage.get("weekly_pct")})

    if debug:
        print(json.dumps(usage, indent=2))
        save_state(state)
        return

    pct, resets = usage.get("pct"), usage.get("resets_at")
    warned = state.setdefault("warned", {})
    # One warning per session per window (keyed by reset time).
    warn_key = f"{session_id}:{resets}"
    if (pct is not None and pct >= cfg["threshold_pct"]
            and warn_key not in warned):
        warned[warn_key] = now
        # Drop stale warn entries (> 24h).
        for k in [k for k, v in warned.items() if now - v > 86400]:
            del warned[k]
        log(f"WARN session={session_id} pct={pct} source={usage['source']} resets={resets}")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": build_warning(pct, resets, session_id, cfg,
                                               usage["source"]),
        }}))
    save_state(state)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the user's session over a monitor bug
        log(f"usage_check error: {e!r}")
        sys.exit(0)
