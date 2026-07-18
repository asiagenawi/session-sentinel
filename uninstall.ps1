# claude-powernap uninstaller. Pass --purge to also delete config/state.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:PYTHONPATH = "src"
python -m claude_powernap remove @args
