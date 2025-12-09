@echo off
REM ================================================
REM Roadlords Automation - Windows Setup Script
REM Run as Administrator!
REM ================================================

echo.
echo ========================================
echo   Roadlords Automation Setup (Windows)
echo ========================================
echo.
echo This will install: Python, Node.js, ADB, Appium
echo.
echo NOTE: Run as Administrator!
echo.
pause

REM Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Run as Administrator!
    pause
    exit /b 1
)

REM Install Chocolatey
echo.
echo [1/6] Installing Chocolatey...
where choco >nul 2>&1
if %errorLevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
    SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
) else (
    echo    Already installed
)

REM Install Python
echo.
echo [2/6] Installing Python...
where python >nul 2>&1
if %errorLevel% neq 0 (
    choco install python -y
) else (
    echo    Already installed
)

REM Install Node.js
echo.
echo [3/6] Installing Node.js...
where node >nul 2>&1
if %errorLevel% neq 0 (
    choco install nodejs -y
) else (
    echo    Already installed
)

REM Install ADB
echo.
echo [4/6] Installing ADB...
where adb >nul 2>&1
if %errorLevel% neq 0 (
    choco install adb -y
) else (
    echo    Already installed
)

call refreshenv >nul 2>&1

REM Install Appium
echo.
echo [5/6] Installing Appium...
where appium >nul 2>&1
if %errorLevel% neq 0 (
    call npm install -g appium
    call appium driver install uiautomator2
) else (
    echo    Already installed
)

REM Setup Python venv
echo.
echo [6/6] Setting up Python...
cd /d "%~dp0"
if not exist "venv" python -m venv venv
call venv\Scripts\activate.bat
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q flask
echo. > venv\.installed

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next: Double-click "Run Roadlords Test.bat"
echo.
pause
