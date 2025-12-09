@echo off
REM ================================================
REM Roadlords Automation - Uninstall Script (Windows)
REM Run as Administrator!
REM ================================================

echo.
echo ========================================
echo   Roadlords Automation - Uninstall
echo ========================================
echo.
echo This will remove:
echo   - Appium + UiAutomator2 driver
echo   - Android Platform Tools (ADB)
echo   - Node.js
echo   - Python 3
echo   - Chocolatey (optional)
echo.
echo WARNING: This may affect other projects!
echo.
set /p confirm="Are you sure? (y/N): "
if /i not "%confirm%"=="y" (
    echo Cancelled.
    pause
    exit /b 0
)

REM Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: Run as Administrator!
    pause
    exit /b 1
)

echo.

REM Remove Appium
echo [1/6] Removing Appium...
where appium >nul 2>&1
if %errorLevel% equ 0 (
    call npm uninstall -g appium 2>nul
    rmdir /s /q "%USERPROFILE%\.appium" 2>nul
    echo    Done
) else (
    echo    (not installed)
)

REM Remove ADB
echo.
echo [2/6] Removing ADB...
where choco >nul 2>&1
if %errorLevel% equ 0 (
    choco uninstall adb -y 2>nul
    echo    Done
) else (
    echo    (Chocolatey not found)
)

REM Remove Node.js
echo.
echo [3/6] Removing Node.js...
where choco >nul 2>&1
if %errorLevel% equ 0 (
    choco uninstall nodejs -y 2>nul
    echo    Done
) else (
    echo    (Chocolatey not found)
)

REM Remove Python
echo.
echo [4/6] Removing Python...
where choco >nul 2>&1
if %errorLevel% equ 0 (
    choco uninstall python -y 2>nul
    echo    Done
) else (
    echo    (Chocolatey not found)
)

REM Remove local venv
echo.
echo [5/6] Removing local virtual environment...
if exist "%~dp0venv" (
    rmdir /s /q "%~dp0venv"
    echo    Done
) else (
    echo    (not found)
)

REM Chocolatey (optional)
echo.
echo [6/6] Chocolatey...
set /p remove_choco="Remove Chocolatey too? This affects ALL choco packages! (y/N): "
if /i "%remove_choco%"=="y" (
    echo    Removing Chocolatey...
    rmdir /s /q "%ALLUSERSPROFILE%\chocolatey" 2>nul
    echo    Done - you may need to remove Chocolatey from PATH manually
) else (
    echo    (keeping Chocolatey)
)

echo.
echo ========================================
echo   Uninstall Complete!
echo ========================================
echo.
echo You can now delete the roadlords-automation folder.
echo.
pause
