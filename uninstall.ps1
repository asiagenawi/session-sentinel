# claude-powernap uninstaller (native Windows). -Purge also deletes state/checkpoints.
param([switch]$Purge)
$ErrorActionPreference = "SilentlyContinue"

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PowernapDir = Join-Path $env:USERPROFILE ".claude\claude-powernap"
$Settings = Join-Path $env:USERPROFILE ".claude\settings.json"

schtasks /delete /f /tn "claude-powernap-watcher" | Out-Null
Remove-Item (Join-Path $env:USERPROFILE ".local\bin\claude-powernap.cmd") -Force

$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($Py) { & $Py (Join-Path $RepoDir "scripts\hooks_config.py") unregister $Settings }

if ($Purge) {
    Remove-Item $PowernapDir -Recurse -Force
    Write-Host "purged $PowernapDir"
} else {
    Remove-Item (Join-Path $PowernapDir "*.py") -Force
    Write-Host "kept config/state/checkpoints in $PowernapDir (use -Purge to delete)"
}
Write-Host "claude-powernap uninstalled"
