@echo off
title Manvxi AI - Browser Launcher
echo ==============================================================================
echo   Manvxi AI - Unified Browser Launcher
echo ==============================================================================
echo.
echo Launching Google Chrome connected to the Automation Engine (Port 9222)...
echo The bot and your dashboard will run in the EXACT SAME BROWSER WINDOW!
echo.

set CHROME_EXE=""
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_EXE="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_EXE="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_EXE="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if %CHROME_EXE%=="" (
    echo [ERROR] Google Chrome was not found. Please install Google Chrome.
    pause
    exit /b 1
)

set PROFILE_DIR=%~dp0chrome_profiles\shared_browser
if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

start "" %CHROME_EXE% --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" --profile-directory=Default --no-first-run --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling,AutomaticTabDiscarding,FreezingOnBatterySaver http://localhost:3000

echo [SUCCESS] Chrome started with Shivam Mishra (2003shivam1990@gmail.com) on port 9222!
echo URL: http://localhost:3000
echo.
timeout /t 3 /nobreak >nul
