#!/bin/bash
# ================================================
# Roadlords Test Runner
# Double-click to start
# ================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo ""
echo "========================================"
echo "  🚛 Roadlords Test Runner"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found!"
    echo ""
    echo "Install Python from: https://www.python.org/downloads/"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

# Check/create venv
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "📦 Installing dependencies..."
    pip install -q -r requirements.txt
    pip install -q flask
    touch venv/.installed
fi

# Check ADB
if ! command -v adb &> /dev/null; then
    echo "⚠️  ADB not found in PATH"
    echo "   Install Android Platform Tools"
    echo ""
fi

# Check Appium
if ! command -v appium &> /dev/null; then
    echo "⚠️  Appium not found in PATH"
    echo "   Install: npm install -g appium"
    echo ""
fi

echo "🚀 Starting web interface..."
echo ""
echo "   Opening http://localhost:5050 in your browser"
echo "   Press Ctrl+C to stop"
echo ""

python3 app/roadlords_tester_web.py
