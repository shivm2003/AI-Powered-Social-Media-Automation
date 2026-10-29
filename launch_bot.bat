@echo off
title Manvxi AI - Telegram Bot Daemon
echo ==============================================================================
echo   Manvxi AI - Telegram Poller Daemon
echo ==============================================================================
echo.
echo Starting Telegram bot background polling listener...
echo Bot: @shiv2003_bot
echo.

set PYTHONIOENCODING=utf-8
python -c "import psutil; [p.kill() for p in psutil.process_iter(['pid', 'name', 'cmdline']) if 'python' in (p.info['name'] or '').lower() and any('poller.py' in str(arg).lower() for arg in (p.info.get('cmdline') or []))]" 2>nul
python "%~dp0automation\telegram\poller.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The bot poller stopped with an error code %ERRORLEVEL%.
    pause
)
