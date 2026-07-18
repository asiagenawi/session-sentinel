# claude-powernap installer (native Windows). Idempotent.
# Thin wrapper: all logic lives in the package CLI (`claude-powernap setup`).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:PYTHONPATH = "src"
python -m claude_powernap setup
