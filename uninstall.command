#!/bin/bash
# ================================================
# Roadlords Automation - Uninstall Script (Mac)
# Removes all installed tools
# ================================================

echo ""
echo "========================================"
echo "  Roadlords Automation - Uninstall"
echo "========================================"
echo ""
echo "This will remove:"
echo "  • Appium + UiAutomator2 driver"
echo "  • Android Platform Tools (ADB)"
echo "  • Node.js"
echo "  • Python 3"
echo "  • Homebrew (optional)"
echo ""
echo "WARNING: This may affect other projects using these tools!"
echo ""
read -p "Are you sure? (y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""

# Remove Appium
echo "[1/6] Removing Appium..."
if command -v appium &> /dev/null; then
    npm uninstall -g appium 2>/dev/null
    rm -rf ~/.appium 2>/dev/null
    echo "   ✅ Appium removed"
else
    echo "   (not installed)"
fi

# Remove ADB
echo ""
echo "[2/6] Removing Android Platform Tools..."
if command -v brew &> /dev/null; then
    brew uninstall --cask android-platform-tools 2>/dev/null
    echo "   ✅ ADB removed"
else
    echo "   (Homebrew not found)"
fi

# Remove Node.js
echo ""
echo "[3/6] Removing Node.js..."
if command -v brew &> /dev/null; then
    brew uninstall node 2>/dev/null
    echo "   ✅ Node.js removed"
else
    echo "   (Homebrew not found)"
fi

# Remove Python
echo ""
echo "[4/6] Removing Python..."
if command -v brew &> /dev/null; then
    brew uninstall python 2>/dev/null
    echo "   ✅ Python removed"
else
    echo "   (Homebrew not found)"
fi

# Remove local venv
echo ""
echo "[5/6] Removing local virtual environment..."
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -d "$DIR/venv" ]; then
    rm -rf "$DIR/venv"
    echo "   ✅ venv removed"
else
    echo "   (not found)"
fi

# Homebrew (optional)
echo ""
echo "[6/6] Homebrew..."
read -p "Remove Homebrew too? This affects ALL brew packages! (y/N): " remove_brew

if [[ "$remove_brew" == "y" || "$remove_brew" == "Y" ]]; then
    echo "   Removing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"
    echo "   ✅ Homebrew removed"
else
    echo "   (keeping Homebrew)"
fi

echo ""
echo "========================================"
echo "  Uninstall Complete!"
echo "========================================"
echo ""
echo "You can now delete the roadlords-automation folder."
echo ""
read -p "Press Enter to close..."
