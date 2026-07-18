# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

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
