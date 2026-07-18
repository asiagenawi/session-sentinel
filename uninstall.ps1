# session-sentinel uninstaller (native Windows). -Purge also deletes state/checkpoints.
param([switch]$Purge)
$ErrorActionPreference = "SilentlyContinue"

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SentinelDir = Join-Path $env:USERPROFILE ".claude\session-sentinel"
$Settings = Join-Path $env:USERPROFILE ".claude\settings.json"

schtasks /delete /f /tn "session-sentinel-watcher" | Out-Null
Remove-Item (Join-Path $env:USERPROFILE ".local\bin\claude-sentinel.cmd") -Force

$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($Py) { & $Py (Join-Path $RepoDir "scripts\hooks_config.py") unregister $Settings }

if ($Purge) {
    Remove-Item $SentinelDir -Recurse -Force
    Write-Host "purged $SentinelDir"
} else {
    Remove-Item (Join-Path $SentinelDir "*.py") -Force
    Write-Host "kept config/state/checkpoints in $SentinelDir (use -Purge to delete)"
}
Write-Host "session-sentinel uninstalled"
