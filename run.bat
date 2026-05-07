@echo off
title Antigravity Bot Launcher
echo ------------------------------------------
echo     🚀 ANTIGRAVITY TRADING BOT 🚀
echo ------------------------------------------

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.12 or 3.13.
    pause
    exit
)

:: Install dependencies
echo [1/3] Checking dependencies...
python -m pip install -r requirements.txt --quiet

:: Ask user if they want watchdog mode
echo.
set /p choice="Enable 24/7 Watchdog (Keep-Alive) Mode? (y/n): "

if /i "%choice%"=="y" (
    echo [2/3] Starting Watchdog...
    powershell -ExecutionPolicy Bypass -File watchdog.ps1
) else (
    echo [2/3] Starting Bot normally...
    python main.py
)

pause
