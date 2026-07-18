# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [0.3.0] - 2026-07-18

### Added
- **PyPI packaging**: installable via `pip install claude-powernap` /
  `uvx claude-powernap setup`; new `setup` / `remove` CLI subcommands replace
  the platform installer scripts (install.sh/.ps1 remain as thin wrappers).
- **Claude Code plugin**: the repo is its own marketplace —
  `/plugin marketplace add asiagenawi/claude-powernap` then
  `/plugin install powernap@claude-powernap`. Hooks activate with no file
  deployment; `/powernap:watcher` schedules the OS-level fallback watcher;
  `/powernap:status` and `/powernap:toggle` included
  (`watcher-setup`/`watcher-remove` CLI subcommands back them).
- `claude-powernap version` command.
- CI: package build + wheel install + entry-point smoke test job; PyPI
  publish workflow on GitHub releases (trusted publishing).

### Changed
- Repo restructured to a src-layout Python package (`src/claude_powernap/`);
  install logic consolidated into one cross-platform code path.

## [0.2.0] - 2026-07-18

### Added
- **Burn-rate prediction**: warnings also fire when the recent burn rate
  projects the limit within `safety_margin_min` minutes — catches fast
  (subagent-heavy) burns the static threshold misses.
- **Adaptive check cadence**: 30s above 80% usage, every hook event above 90%.
- **Pause ledger + rescue**: every pause is recorded; the watcher resumes
  napping sessions whose in-session alarm died (sleep/reboot/crash).
- **Weekly guard** (opt-in, `weekly_guard: true`): warn/pause on the weekly
  window; pauses without scheduling a resume since weekly resets are days out.
- **Account-switch detection**: per-account cached state clears automatically
  on `/login` to a different account.
- **Cross-platform state locking**: concurrent sessions can no longer race
  state.json (fcntl/msvcrt; 12-process CI test).

## [0.1.0] - 2026-07-18

Initial release.

### Added
- Usage monitor hook (`PostToolUse`/`UserPromptSubmit`/`Stop`): warns the live
  session at a configurable threshold (default 90%) of the 5-hour window,
  with the pause-checkpoint-reschedule protocol injected into context.
- Hybrid usage source: exact numbers from the OAuth usage endpoint with
  automatic fallback to local transcript estimation, continuously calibrated
  against endpoint truth.
- Fallback watcher: detects sessions that hard-hit the limit, waits for the
  reset, and resumes them visibly (new terminal window) — with a
  never-fork-a-live-session guarantee; notifies instead when in doubt.
- `claude-powernap on|off|status|log` CLI.
- Platforms: macOS (Keychain/launchd/osascript), Linux incl. WSL
  (credentials file/systemd user timer/notify-send, terminal auto-detect),
  native Windows experimental (Task Scheduler/toasts/wt).
- CI: full install→monitor→hook→watcher→uninstall cycle on macOS, Ubuntu,
  and Windows runners.
