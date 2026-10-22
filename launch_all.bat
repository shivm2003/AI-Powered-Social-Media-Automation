@echo off
title Manvxi AI - Full System Launcher
echo ==============================================================================
echo   MANVXI AI - UNIFIED FULL SYSTEM LAUNCHER
echo ==============================================================================
echo.
echo Launching:
echo   1. Google Chrome (Port 9222 Remote Debugging with Shivam Mishra Profile)
echo   2. Telegram Bot Poller Daemon (@shiv2003_bot)
echo   3. Next.js Web Application (http://localhost:3000)
echo.

cd /d "%~dp0"

:: 1. Launch Browser
start "Manvxi AI - Chrome Browser" cmd /c "launch_browser.bat"

:: 2. Launch Telegram Bot Poller Daemon
start "Manvxi AI - Telegram Bot Daemon" cmd /c "launch_bot.bat"

:: 3. Launch Web UI Dev Server
start "Manvxi AI - Web Server" cmd /c "npm run dev"

echo.
echo ==============================================================================
echo [SUCCESS] All 3 Manvxi AI systems are starting!
echo - Web Dashboard:  http://localhost:3000
echo - Telegram Bot:   @shiv2003_bot (Active & Polling)
echo - Chrome Debug:   Port 9222 (Profile: Shivam Mishra)
echo ==============================================================================
timeout /t 5
