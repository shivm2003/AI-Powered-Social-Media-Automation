@echo off
chcp 65001 >nul
echo =====================================================================
echo 🔄 MANVIX AI — 1-CLICK INSTANT ROLLBACK / REVERT UTILITY
echo =====================================================================
echo.
echo This tool lets you immediately revert recent changes made to your codebase.
echo Choose an option below:
echo.
echo   [1] Revert Latest Commit (Soft: Keep all files in working directory)
echo   [2] Revert Latest Commit (Hard: Reset codebase back to previous GitHub commit)
echo   [3] Revert Only Post-Share & Gallery Features
echo   [4] View Detailed Changelog
echo   [5] Cancel and Exit
echo.
set /p opt="Enter your choice (1-5): "

if "%opt%"=="1" (
    echo.
    echo [INFO] Reverting latest commit with soft reset...
    git reset --soft HEAD~1
    echo [SUCCESS] Latest commit undone! Your code changes are kept staged.
    pause
    exit /b 0
)

if "%opt%"=="2" (
    echo.
    echo [WARNING] This will discard uncommitted changes and roll back to HEAD~1!
    set /p confirm="Are you sure? (Y/N): "
    if /i "%confirm%"=="Y" (
        git reset --hard HEAD~1
        echo [SUCCESS] Codebase completely reverted to previous state.
    ) else (
        echo [INFO] Revert cancelled.
    )
    pause
    exit /b 0
)

if "%opt%"=="3" (
    echo.
    echo [INFO] Reverting post sharer files...
    git checkout origin/main -- automation/telegram/poller.py automation/telegram/bot.py automation/db_campaigns.py
    if exist automation\social\post_sharer.py del /f automation\social\post_sharer.py
    echo [SUCCESS] Post share features reverted to origin/main!
    pause
    exit /b 0
)

if "%opt%"=="4" (
    if exist CHANGELOG_FEATURES.md (
        start notepad.exe CHANGELOG_FEATURES.md
    ) else (
        echo [INFO] CHANGELOG_FEATURES.md not found.
    )
    exit /b 0
)

echo.
echo [INFO] No changes made. Exiting.
exit /b 0
