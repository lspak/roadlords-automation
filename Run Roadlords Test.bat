@echo off
REM Roadlords Test Runner - Windows

cd /d "%~dp0"

echo.
echo ========================================
echo   Roadlords Test Runner
echo ========================================
echo.

where python >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python not found! Run setup.bat first.
    pause
    exit /b 1
)

if not exist "venv" python -m venv venv
call venv\Scripts\activate.bat

if not exist "venv\.installed" (
    echo Installing dependencies...
    pip install -q -r requirements.txt
    pip install -q flask
    echo. > venv\.installed
)

echo Starting web interface...
echo Opening http://localhost:5050
echo.

python app\roadlords_tester_web.py
pause
