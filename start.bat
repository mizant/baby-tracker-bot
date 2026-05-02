@echo off
echo ======================================
echo   Baby Tracker Bot - Quick Start
echo ======================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Python found!
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/4] Creating virtual environment...
    python -m venv venv
) else (
    echo [2/4] Virtual environment already exists
)

echo.

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [4/4] Installing dependencies...
pip install -r requirements.txt

echo.
echo ======================================
echo   Setup Complete!
echo ======================================
echo.
echo Next steps:
echo 1. Edit the .env file with your bot credentials:
echo    - BOT_TOKEN (from @BotFather)
echo    - ADMIN_IDS (your Telegram IDs)
echo    - TIMEZONE (default: Europe/Warsaw)
echo.
echo 2. Run the bot:
echo    python -m app.main
echo.
pause
