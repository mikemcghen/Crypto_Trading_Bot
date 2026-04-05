@echo off
REM Market Structure Trading Bot - Scheduled Task Runner
REM This script is designed to be called by Windows Task Scheduler
REM
REM Setup Instructions:
REM 1. Open Task Scheduler (taskschd.msc)
REM 2. Create Basic Task > Give it a name
REM 3. Trigger: Daily, then set to repeat every 1 hour (or your preferred interval)
REM 4. Action: Start a Program
REM    - Program/script: C:\Users\mcghe\OneDrive\Documents\GitHub\Crypto_Trading_Bot\scripts\run_scheduled.bat
REM    - Start in: C:\Users\mcghe\OneDrive\Documents\GitHub\Crypto_Trading_Bot
REM 5. Finish and test with "Run" option

REM Change to project directory
cd /d "C:\Users\mcghe\OneDrive\Documents\GitHub\Crypto_Trading_Bot"

REM Set log file path
set LOG_DIR=logs
set LOG_FILE=%LOG_DIR%\scheduled_run_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log

REM Create logs directory if it doesn't exist
if not exist %LOG_DIR% mkdir %LOG_DIR%

REM Log start time
echo. >> %LOG_FILE%
echo ====================================================== >> %LOG_FILE%
echo Scheduled run started at %date% %time% >> %LOG_FILE%
echo ====================================================== >> %LOG_FILE%

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run analysis mode (change to --trade for actual paper trading)
python main_market_structure.py --analyze >> %LOG_FILE% 2>&1

REM Log end time
echo. >> %LOG_FILE%
echo Run completed at %time% >> %LOG_FILE%
echo ====================================================== >> %LOG_FILE%

REM Optional: Uncomment the line below to run in trade mode instead
REM python main_market_structure.py --trade --dry-run >> %LOG_FILE% 2>&1
