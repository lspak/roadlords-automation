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

# Set ANDROID_HOME for Appium (required!)
echo ""
echo "📦 Setting up ANDROID_HOME..."

# Find where ADB actually is
ADB_PATH=$(which adb 2>/dev/null)
if [ -n "$ADB_PATH" ]; then
    # ADB is at e.g. /opt/homebrew/bin/adb
    # We need ANDROID_HOME to be parent of a 'platform-tools' folder containing adb
    # So we create a symlink structure that Appium expects

    ADB_DIR=$(dirname "$ADB_PATH")

    # Create a fake Android SDK structure for Appium
    ANDROID_HOME_PATH="$HOME/.android-sdk"
    mkdir -p "$ANDROID_HOME_PATH/platform-tools"

    # Symlink adb to the expected location
    if [ ! -L "$ANDROID_HOME_PATH/platform-tools/adb" ]; then
        ln -sf "$ADB_PATH" "$ANDROID_HOME_PATH/platform-tools/adb"
    fi

    # Also link other platform-tools binaries if they exist
    for tool in fastboot; do
        TOOL_PATH=$(which $tool 2>/dev/null)
        if [ -n "$TOOL_PATH" ] && [ ! -L "$ANDROID_HOME_PATH/platform-tools/$tool" ]; then
            ln -sf "$TOOL_PATH" "$ANDROID_HOME_PATH/platform-tools/$tool"
        fi
    done

    echo "   Created Android SDK structure at $ANDROID_HOME_PATH"
else
    echo "   ⚠️  ADB not found - install with: brew install --cask android-platform-tools"
    ANDROID_HOME_PATH=""
fi

# Add to shell profile
if [ -n "$ANDROID_HOME_PATH" ]; then
    SHELL_PROFILE="$HOME/.zprofile"
    if [[ "$SHELL" == *"bash"* ]]; then
        SHELL_PROFILE="$HOME/.bash_profile"
    fi

    # Remove old ANDROID_HOME entries first
    if [ -f "$SHELL_PROFILE" ]; then
        grep -v "ANDROID_HOME" "$SHELL_PROFILE" | grep -v "# Android SDK for Appium" > "$SHELL_PROFILE.tmp" 2>/dev/null
        mv "$SHELL_PROFILE.tmp" "$SHELL_PROFILE" 2>/dev/null
    fi

    echo "" >> "$SHELL_PROFILE"
    echo "# Android SDK for Appium" >> "$SHELL_PROFILE"
    echo "export ANDROID_HOME=\"$ANDROID_HOME_PATH\"" >> "$SHELL_PROFILE"
    echo "   ✅ Added ANDROID_HOME to $SHELL_PROFILE"

    # Also export for current session
    export ANDROID_HOME="$ANDROID_HOME_PATH"
fi

# ============================================
# 5. Install Java 17 (required for building GPS Mock APK)
# ============================================
echo ""
echo "📦 Checking Java 17..."
if ! /opt/homebrew/opt/openjdk@17/bin/java -version &> /dev/null && ! /usr/local/opt/openjdk@17/bin/java -version &> /dev/null; then
    echo "   Installing Java 17..."
    brew install openjdk@17
else
    echo "   ✅ Java 17 already installed"
fi

# Find Java 17 path
if [ -d "/opt/homebrew/opt/openjdk@17" ]; then
    JAVA17_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
elif [ -d "/usr/local/opt/openjdk@17" ]; then
    JAVA17_HOME="/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
fi

# ============================================
# 6. Build GPS Mock APK (if needed)
# ============================================
echo ""
echo "📦 Building GPS Mock APK..."
if [ -f "android-gps-mock/gradlew" ] && [ -n "$JAVA17_HOME" ]; then
    cd android-gps-mock
    JAVA_HOME="$JAVA17_HOME" ./gradlew assembleDebug --quiet 2>/dev/null || echo "   ⚠️  Build failed - using pre-built APK"
    if [ -f "app/build/outputs/apk/debug/app-debug.apk" ]; then
        cp app/build/outputs/apk/debug/app-debug.apk gps-mock.apk
        echo "   ✅ GPS Mock APK built successfully"
    fi
    cd ..
else
    echo "   Using pre-built GPS Mock APK"
fi

# ============================================
# 7. Install Appium
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
# 8. Install Appium UiAutomator2 driver
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
# 9. Create Python virtual environment
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
# 10. Install GPS Mock APK (if device connected)
# ============================================
echo ""
echo "📱 Checking for connected Android device..."
if adb devices 2>/dev/null | grep -q "device$"; then
    DEVICE=$(adb devices | grep "device$" | head -1 | cut -f1)
    echo "   Found device: $DEVICE"

    if [ -f "android-gps-mock/gps-mock.apk" ]; then
        echo "   Installing GPS Mock app..."
        adb install -r android-gps-mock/gps-mock.apk 2>/dev/null || echo "   (Already installed or install failed)"

        # Enable notifications for GPS Mock (required on Android 13+)
        echo "   Enabling GPS Mock notifications..."
        adb shell cmd appops set com.roadlords.gpsmock POST_NOTIFICATIONS allow 2>/dev/null || true
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
echo "⚠️  IMPORTANT: Manual configuration required!"
echo ""
echo "Before running tests, you MUST:"
echo ""
echo "  1. Set GPS Mock as mock location provider:"
echo "     Settings → Developer Options → Select mock location app → GPS Mock"
echo "     (This cannot be automated due to Android security)"
echo ""
echo "  2. Reboot your device:"
echo "     adb reboot"
echo "     (Required to clear GPS provider state on first setup)"
echo ""
echo "  3. After reboot, you're ready to test!"
echo "     Double-click 'Run Roadlords Test.command'"
echo ""
echo "Troubleshooting: See README.md ## Troubleshooting section"
echo ""
read -p "Press Enter to close..."
