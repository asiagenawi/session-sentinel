"""Shared logic for session-sentinel: config, state, usage sources, block math."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
SENTINEL_DIR = Path(os.environ.get("SENTINEL_HOME", HOME / ".claude" / "session-sentinel"))
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude"))
PROJECTS_DIR = CLAUDE_DIR / "projects"
CONFIG_PATH = SENTINEL_DIR / "config.json"
STATE_PATH = SENTINEL_DIR / "state.json"
CHECKPOINT_DIR = SENTINEL_DIR / "checkpoints"
LOG_PATH = SENTINEL_DIR / "sentinel.log"

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
KEYCHAIN_SERVICE_PREFIX = "Claude Code-credentials"
IS_MAC = sys.platform == "darwin"
CREDENTIALS_FILE = CLAUDE_DIR / ".credentials.json"  # Linux/WSL token location

DEFAULT_CONFIG = {
    "enabled": True,
    "threshold_pct": 90,
    "check_interval_s": 120,
    "endpoint_enabled": True,
    "terminal_app": "Terminal",          # or "iTerm2"
    "resume_grace_min": 3,               # schedule resume this many min after reset
    "headless_resume_extra_args": [],    # e.g. ["--dangerously-skip-permissions"]
    "local_budget_weighted_tokens": None,  # override for local estimation budget
    "token_weights": {"input": 1.0, "output": 3.0, "cache_creation": 1.0, "cache_read": 0.1},
}


def log(msg):
    SENTINEL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    with open(LOG_PATH, "a") as f:
        f.write(f"{ts} {msg}\n")


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(load_json(CONFIG_PATH, {}))
    return cfg


def load_state():
    return load_json(STATE_PATH, {})


def save_state(state):
    SENTINEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    tmp.replace(STATE_PATH)


# ---------------------------------------------------------------- keychain

def _keychain_services():
    """All 'Claude Code-credentials*' service names in the login keychain."""
    try:
        out = subprocess.run(["security", "dump-keychain"], capture_output=True,
                             text=True, timeout=20).stdout
    except Exception:
        return [KEYCHAIN_SERVICE_PREFIX]
    names = set(re.findall(r'"svce"<blob>="(Claude Code-credentials[^"]*)"', out))
    return sorted(names) or [KEYCHAIN_SERVICE_PREFIX]


def get_oauth_token(state):
    """Freshest unexpired OAuth access token (Keychain on macOS, file elsewhere)."""
    if not IS_MAC:
        try:
            with open(CREDENTIALS_FILE) as f:
                oauth = json.load(f).get("claudeAiOauth", {})
            tok, exp = oauth.get("accessToken"), oauth.get("expiresAt", 0)
            return tok if tok and exp > time.time() * 1000 + 60_000 else None
        except (OSError, json.JSONDecodeError):
            return None
    candidates = []
    cached = state.get("keychain_service")
    services = _keychain_services()
    if cached in services:
        services.remove(cached)
        services.insert(0, cached)
    now_ms = time.time() * 1000
    for svc in services:
        try:
            raw = subprocess.run(
                ["security", "find-generic-password", "-s", svc, "-w"],
                capture_output=True, text=True, timeout=10).stdout.strip()
            oauth = json.loads(raw).get("claudeAiOauth", {})
            tok, exp = oauth.get("accessToken"), oauth.get("expiresAt", 0)
            if tok and exp > now_ms + 60_000:
                candidates.append((exp, svc, tok))
        except Exception:
            continue
    if not candidates:
        return None
    exp, svc, tok = max(candidates)
    state["keychain_service"] = svc
    return tok


# ---------------------------------------------------------------- endpoint

def get_usage_from_endpoint(state):
    """Query the OAuth usage endpoint. Returns usage dict or None.

    NOTE: undocumented endpoint (same one Claude Code's /usage uses). May
    change without notice; callers must tolerate None and fall back.
    """
    token = get_oauth_token(state)
    if not token:
        return None
    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        "Content-Type": "application/json",
        "User-Agent": "claude-cli/2.1.214 (external, cli)",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        log(f"endpoint error: {e}")
        return None
    usage = {"source": "endpoint"}
    # Preferred: limits[] array; fallback: five_hour/seven_day objects.
    for lim in data.get("limits") or []:
        if lim.get("kind") == "session":
            usage["pct"] = lim.get("percent")
            usage["resets_at"] = lim.get("resets_at")
        elif lim.get("kind") == "weekly_all":
            usage["weekly_pct"] = lim.get("percent")
            usage["weekly_resets_at"] = lim.get("resets_at")
    if "pct" not in usage:
        fh = data.get("five_hour") or {}
        usage["pct"] = fh.get("utilization")
        usage["resets_at"] = fh.get("resets_at")
        sd = data.get("seven_day") or {}
        usage["weekly_pct"] = sd.get("utilization")
        usage["weekly_resets_at"] = sd.get("resets_at")
    return usage if usage.get("pct") is not None else None


# ---------------------------------------------------------------- local estimate

def _iter_transcript_events(max_age_h):
    """Yield (ts_epoch, weighted_tokens_or_0, is_rate_limit) from recent transcripts."""
    cfg = load_config()
    w = cfg["token_weights"]
    cutoff = time.time() - max_age_h * 3600
    if not PROJECTS_DIR.is_dir():
        return
    for jsonl in PROJECTS_DIR.glob("*/*.jsonl"):
        try:
            if jsonl.stat().st_mtime < cutoff:
                continue
            with open(jsonl, errors="replace") as f:
                for line in f:
                    if '"timestamp"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = rec.get("timestamp")
                    if not ts:
                        continue
                    try:
                        ep = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                    except ValueError:
                        continue
                    if ep < cutoff:
                        continue
                    u = (rec.get("message") or {}).get("usage") or {}
                    weighted = (u.get("input_tokens", 0) * w["input"]
                                + u.get("output_tokens", 0) * w["output"]
                                + u.get("cache_creation_input_tokens", 0) * w["cache_creation"]
                                + u.get("cache_read_input_tokens", 0) * w["cache_read"])
                    is_rl = ((rec.get("error") == "rate_limit" or rec.get("apiErrorStatus") == 429)
                             and "resets" in line and "not your usage limit" not in line)
                    yield ep, weighted, is_rl
        except OSError:
            continue


def _blocks(events):
    """Group sorted (ts, tokens, is_rl) events into 5h blocks (ccusage algorithm)."""
    blocks = []
    for ep, tok, is_rl in events:
        if not blocks or ep >= blocks[-1]["start"] + 5 * 3600:
            start = ep - (ep % 3600)  # floor to hour
            blocks.append({"start": start, "tokens": 0.0, "hit_limit": False})
        blocks[-1]["tokens"] += tok
        blocks[-1]["hit_limit"] = blocks[-1]["hit_limit"] or is_rl
    return blocks


def get_usage_local(state):
    """Estimate 5h-window usage from transcripts. Approximate; may return pct=None."""
    cfg = load_config()
    now = time.time()
    events = sorted(_iter_transcript_events(max_age_h=26))
    blocks = _blocks(events)
    current = blocks[-1] if blocks and now < blocks[-1]["start"] + 5 * 3600 else None

    # Budget preference: explicit config > endpoint-calibrated > limit-hit heuristic.
    budget = cfg.get("local_budget_weighted_tokens") or state.get("calibrated_budget")
    if not budget:
        # A block that ended in a rate-limit hit reached ~100% of the budget.
        cal_events = sorted(_iter_transcript_events(max_age_h=14 * 24))
        hits = [b["tokens"] for b in _blocks(cal_events) if b["hit_limit"]]
        if hits:
            budget = state["calibrated_budget"] = max(hits)

    if current is None:
        return {"source": "local", "pct": 0.0, "resets_at": None,
                "weekly_pct": None, "weekly_resets_at": None}
    resets_at = datetime.fromtimestamp(current["start"] + 5 * 3600,
                                       tz=timezone.utc).isoformat()
    pct = round(current["tokens"] / budget * 100, 1) if budget else None
    return {"source": "local", "pct": pct, "resets_at": resets_at,
            "weekly_pct": None, "weekly_resets_at": None}


def get_usage(state, cfg=None):
    cfg = cfg or load_config()
    usage = get_usage_from_endpoint(state) if cfg.get("endpoint_enabled") else None
    if usage is None:
        return get_usage_local(state)
    # Continuously calibrate the local fallback budget against endpoint truth
    # (at most every 6h, and only when the window is meaningfully used).
    if usage.get("pct", 0) >= 20 and time.time() - state.get("calibration_ts", 0) > 6 * 3600:
        events = sorted(_iter_transcript_events(max_age_h=26))
        blocks = _blocks(events)
        if blocks and time.time() < blocks[-1]["start"] + 5 * 3600 and blocks[-1]["tokens"]:
            state["calibrated_budget"] = blocks[-1]["tokens"] / (usage["pct"] / 100)
            state["calibration_ts"] = time.time()
            log(f"calibrated local budget={int(state['calibrated_budget'])} from endpoint pct={usage['pct']}")
    return usage


# ---------------------------------------------------------------- misc

def fmt_local(iso_ts):
    if not iso_ts:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%Y-%m-%d %I:%M%p %Z")
    except ValueError:
        return iso_ts
