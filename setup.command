#!/bin/bash
# ================================================
# Roadlords Automation - Full Setup Script
# Run this ONCE on a new Mac to install everything
# ================================================

set -e  # Exit on error

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo ""
echo "========================================"
echo "  🚛 Roadlords Automation Setup"
echo "========================================"
echo ""
echo "This will install all required tools:"
echo "  • Homebrew (package manager)"
echo "  • Python 3"
echo "  • Node.js"
echo "  • Android Platform Tools (ADB)"
echo "  • Appium"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."
echo ""

# ============================================
# 1. Install Homebrew (if not installed)
# ============================================
echo "📦 Checking Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "   Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add to PATH for Apple Silicon
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "   ✅ Homebrew already installed"
fi

# ============================================
# 2. Install Python 3
# ============================================
echo ""
echo "📦 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "   Installing Python 3..."
    brew install python
else
    echo "   ✅ Python 3 already installed ($(python3 --version))"
fi

# ============================================
# 3. Install Node.js
# ============================================
echo ""
echo "📦 Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "   Installing Node.js..."
    brew install node
else
    echo "   ✅ Node.js already installed ($(node --version))"
fi

# ============================================
# 4. Install Android Platform Tools (ADB)
# ============================================
echo ""
echo "📦 Checking ADB..."
if ! command -v adb &> /dev/null; then
    echo "   Installing Android Platform Tools..."
    brew install --cask android-platform-tools
else
    echo "   ✅ ADB already installed"
fi

# ============================================
# 5. Install Appium
# ============================================
echo ""
echo "📦 Checking Appium..."
if ! command -v appium &> /dev/null; then
    echo "   Installing Appium globally..."
    npm install -g appium
else
    echo "   ✅ Appium already installed ($(appium --version))"
fi

# ============================================
# 6. Install Appium UiAutomator2 driver
# ============================================
echo ""
echo "📦 Checking Appium UiAutomator2 driver..."
if ! appium driver list --installed 2>/dev/null | grep -q "uiautomator2"; then
    echo "   Installing UiAutomator2 driver..."
    appium driver install uiautomator2
else
    echo "   ✅ UiAutomator2 driver already installed"
fi

# ============================================
# 7. Create Python virtual environment
# ============================================
echo ""
echo "📦 Setting up Python environment..."
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "   Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q flask

touch venv/.installed

# ============================================
# 8. Install GPS Mock APK (if device connected)
# ============================================
echo ""
echo "📱 Checking for connected Android device..."
if adb devices 2>/dev/null | grep -q "device$"; then
    DEVICE=$(adb devices | grep "device$" | head -1 | cut -f1)
    echo "   Found device: $DEVICE"

    if [ -f "android-gps-mock/gps-mock.apk" ]; then
        echo "   Installing GPS Mock app..."
        adb install -r android-gps-mock/gps-mock.apk 2>/dev/null || echo "   (Already installed or install failed)"
    fi
else
    echo "   ⚠️  No device connected - connect device later and install GPS Mock manually"
    echo "      Run: adb install android-gps-mock/gps-mock.apk"
fi

# ============================================
# Done!
# ============================================
echo ""
echo "========================================"
echo "  ✅ Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Connect your Android phone via USB"
echo "  2. Enable USB debugging on phone"
echo "  3. Set GPS Mock as mock location app:"
echo "     Settings → Developer Options → Mock location app → GPS Mock"
echo "  4. Double-click 'Run Roadlords Test.command' to start testing"
echo ""
read -p "Press Enter to close..."
