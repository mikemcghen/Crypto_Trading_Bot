# Market Structure Trading Bot - Scheduled Task Runner (PowerShell)
#
# Setup Instructions for Task Scheduler:
# 1. Open Task Scheduler (taskschd.msc)
# 2. Create Basic Task > Give it a name like "Crypto Trading Bot"
# 3. Trigger:
#    - Daily, start at a time you prefer
#    - In Advanced settings: Repeat task every 1 hour (or 4 hours for less frequent)
# 4. Action: Start a Program
#    - Program/script: powershell.exe
#    - Arguments: -ExecutionPolicy Bypass -File "C:\Users\mcghe\OneDrive\Documents\GitHub\Crypto_Trading_Bot\scripts\run_scheduled.ps1"
#    - Start in: C:\Users\mcghe\OneDrive\Documents\GitHub\Crypto_Trading_Bot
# 5. Settings:
#    - Check "Run whether user is logged on or not"
#    - Check "Run with highest privileges" if needed
#
# Configuration
param(
    [ValidateSet("analyze", "trade", "dry-run")]
    [string]$Mode = "analyze"
)

$ProjectPath = "C:\Users\mcghe\OneDrive\Documents\GitHub\Crypto_Trading_Bot"
$LogDir = Join-Path $ProjectPath "logs"
$DateStr = Get-Date -Format "yyyyMMdd"
$LogFile = Join-Path $LogDir "scheduled_run_$DateStr.log"

# Create logs directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Change to project directory
Set-Location $ProjectPath

# Log start
$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value ""
Add-Content -Path $LogFile -Value "======================================================"
Add-Content -Path $LogFile -Value "Scheduled run started at $StartTime"
Add-Content -Path $LogFile -Value "Mode: $Mode"
Add-Content -Path $LogFile -Value "======================================================"

# Activate virtual environment if exists
$VenvActivate = Join-Path $ProjectPath "venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
}

# Build command based on mode
$PythonArgs = @("main_market_structure.py")
switch ($Mode) {
    "analyze" { $PythonArgs += "--analyze" }
    "trade"   { $PythonArgs += "--trade" }
    "dry-run" { $PythonArgs += "--trade", "--dry-run" }
}

# Run the bot
try {
    $Output = & python @PythonArgs 2>&1
    $Output | Add-Content -Path $LogFile
    $ExitCode = $LASTEXITCODE
}
catch {
    Add-Content -Path $LogFile -Value "ERROR: $_"
    $ExitCode = 1
}

# Log completion
$EndTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value ""
Add-Content -Path $LogFile -Value "Run completed at $EndTime (Exit code: $ExitCode)"
Add-Content -Path $LogFile -Value "======================================================"

exit $ExitCode
