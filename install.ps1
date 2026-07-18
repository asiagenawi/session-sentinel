# claude-powernap installer (native Windows). Idempotent — re-run to upgrade.
$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PowernapDir = Join-Path $env:USERPROFILE ".claude\claude-powernap"
$Settings = Join-Path $env:USERPROFILE ".claude\settings.json"
$BinDir = Join-Path $env:USERPROFILE ".local\bin"
$TaskName = "claude-powernap-watcher"

Write-Host "== claude-powernap install (Windows) =="

$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) { Write-Error "python not found on PATH — install Python 3 first"; exit 1 }
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Warning "'claude' not on PATH — fallback resume needs it"
}

# 1. Files
New-Item -ItemType Directory -Force -Path (Join-Path $PowernapDir "checkpoints") | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
Copy-Item (Join-Path $RepoDir "powernap\powernap_common.py") $PowernapDir -Force
Copy-Item (Join-Path $RepoDir "powernap\usage_check.py") $PowernapDir -Force
Copy-Item (Join-Path $RepoDir "powernap\fallback_watch.py") $PowernapDir -Force
$Cfg = Join-Path $PowernapDir "config.json"
if (-not (Test-Path $Cfg)) { Copy-Item (Join-Path $RepoDir "powernap\config.default.json") $Cfg }
Copy-Item (Join-Path $RepoDir "bin\claude-powernap") (Join-Path $PowernapDir "claude_powernap_cli.py") -Force
Write-Host "installed files -> $PowernapDir"

# 2. CLI shim + user PATH
$UsageScript = Join-Path $PowernapDir "usage_check.py"
$CliScript = Join-Path $PowernapDir "claude_powernap_cli.py"
"@echo off`r`n""$Py"" ""$CliScript"" %*" | Set-Content (Join-Path $BinDir "claude-powernap.cmd") -Encoding ascii
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    Write-Host "added $BinDir to user PATH (new shells only)"
}

# 3. Hooks (absolute paths — cmd.exe does not expand ~)
& $Py (Join-Path $RepoDir "scripts\hooks_config.py") register $Settings "`"$Py`" `"$UsageScript`""

# 4. Fallback watcher via Task Scheduler (pythonw = no console flash)
$Pyw = $Py -replace "python\.exe$", "pythonw.exe"
if (-not (Test-Path $Pyw)) { $Pyw = $Py }
$Tr = '"{0}" "{1}"' -f $Pyw, (Join-Path $PowernapDir "fallback_watch.py")
schtasks /create /f /tn $TaskName /sc minute /mo 2 /tr $Tr | Out-Null
Write-Host "fallback watcher scheduled (Task Scheduler: $TaskName, every 2 min)"

Write-Host ""
Write-Host "Done. Commands:  claude-powernap status | on | off | log"
