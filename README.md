# Roadlords Automation

Automated E2E testing framework for Roadlords truck GPS navigation app.

## Features

- **GPS Simulation**: Custom GPS Mock Android app for stable location mocking
- **Memory Monitoring**: Real-time memory tracking during navigation
- **Video Recording**: Screen capture during test execution
- **UI Verification**: Visual regression testing with SSIM comparison
- **HTML Reports**: Detailed reports with memory graphs, video, and screenshots
- **Web GUI**: Simple interface for running tests

## Quick Start

### Option 1: Auto-install (Recommended)

**Mac:**
```bash
./setup.command
```

**Windows:**
```bash
setup.bat
```

This will install all dependencies (Python, Node, Appium, ADB, GPS Mock APK).

**⚠️ IMPORTANT: After setup, you MUST manually configure the device:**

1. **Enable GPS Mock as mock location provider:**
   - Go to: **Settings → Developer Options → Select mock location app → GPS Mock**
   - This cannot be automated due to Android security restrictions

2. **Reboot your device:**
   ```bash
   adb reboot
   ```
   - Required to clear GPS provider state on first setup

3. **Enable GPS Mock notifications (Android 13+):**
   - When GPS Mock app starts for the first time, allow notification permission
   - Or manually: **Settings → Apps → GPS Mock → Notifications → Enable**
   - Required for foreground service to work reliably

4. **Ready to test!** Now you can run tests normally.

### Option 2: Manual Setup

```bash
# 1. Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Start Appium server
appium

# 3. Run E2E test
pytest tests/e2e/ -v
```

## Running Tests

### With Web GUI

**Mac:**
```bash
./Run\ Roadlords\ Test.command
```

**Windows:**
```bash
Run Roadlords Test.bat
```

Opens a browser interface where you can start Appium and run tests.

### From Command Line

```bash
pytest tests/e2e/test_navigation_route_following.py -v
```

## Project Structure

```
roadlords-automation/
├── tests/
│   ├── e2e/
│   │   └── test_navigation_route_following.py  # Main E2E navigation test
│   └── conftest.py                              # Pytest fixtures
├── src/
│   ├── gps/
│   │   └── gps_mock_controller.py              # GPS Mock app controller
│   ├── utils/
│   │   ├── memory_monitor.py                   # Memory tracking
│   │   ├── video_recorder.py                   # Screen recording
│   │   ├── ui_verifier.py                      # Visual regression
│   │   ├── report_generator.py                 # HTML report generation
│   │   └── driver_factory.py                   # Appium driver setup
│   └── data/routes/                            # GPX route files
├── android-gps-mock/                           # GPS Mock Android app source
├── app/
│   └── roadlords_tester_web.py                 # Web GUI
├── config/                                     # Configuration files
├── setup.command / setup.bat                   # Auto-install scripts
├── uninstall.command / uninstall.bat           # Uninstall scripts
└── docs/                                       # Documentation
```

## Requirements

- Python 3.11+
- Node.js 18+
- Appium 2.x
- Android device with Developer Options enabled
- GPS Mock app installed

## GPS Mock App Setup

```bash
# Install pre-built APK
adb install android-gps-mock/gps-mock.apk

# Enable as mock location provider
# Settings → Developer options → Select mock location app → GPS Mock
```

## Generated Reports

Reports are saved to `reports/e2e/`:
- `stress_report_*.html` - Interactive HTML report with memory graph and video
- Screenshots comparison (baseline vs actual)

## Documentation

- [AUTOMATION_GUIDE.md](./AUTOMATION_GUIDE.md) - Complete guide with architecture, scaling, CI/CD
- [SETUP.md](./SETUP.md) - Quick start guide
- [docs/APPIUM_INSPECTOR_GUIDE.md](./docs/APPIUM_INSPECTOR_GUIDE.md) - Element inspection guide

## Troubleshooting

### GPS Mock not working

**Symptom:** Test runs but GPS location doesn't change, car doesn't move on map.

**Diagnostic commands:**
```bash
# 1. Check if GPS Mock is set as mock location provider
adb shell settings get secure mock_location_app
# Should return: com.roadlords.gpsmock

# 2. Check if GPS Mock service is running
adb shell "ps -A | grep gpsmock"
# Should show process running

# 3. Test GPS Mock manually
adb shell am start -n com.roadlords.gpsmock/.MainActivity
sleep 2
adb shell am broadcast -a com.roadlords.gpsmock.SET --ef lat 48.127 --ef lon 17.1072 -n com.roadlords.gpsmock/.CommandReceiver
adb shell dumpsys location | grep "last mock location"
# Should show coordinates, not "null"

# 4. Check for errors in logcat
adb logcat -d | grep -i gpsmock | tail -30
```

**Common errors and fixes:**

| Error in logcat | Problem | Solution |
|----------------|---------|----------|
| `not allowed to perform MOCK_LOCATION` | GPS Mock not set as mock location provider | Settings → Developer Options → Select mock location app → GPS Mock |
| `gps provider is not a test provider` | GPS provider in wrong state | Reboot device: `adb reboot` |
| `Background start not allowed` | Service not running | First run: `adb shell am start -n com.roadlords.gpsmock/.MainActivity` |
| `ForegroundServiceStartNotAllowedException` | Notifications blocked (Android 13+) | Settings → Apps → GPS Mock → Notifications → Enable |
| `last mock location=null` | Service running but not sending locations | Force stop and restart: `adb shell am force-stop com.roadlords.gpsmock` then start MainActivity |

**If all else fails:**
1. Uninstall GPS Mock: `adb uninstall com.roadlords.gpsmock`
2. Reboot device: `adb reboot`
3. Reinstall: `adb install -r android-gps-mock/gps-mock.apk`
4. Set as mock location provider again
5. Reboot device again

### Appium not starting

**Check Appium logs:**
```bash
cat ~/.appium-server.log
```

**Common issues:**
- Node.js not in PATH: Restart terminal after setup
- Port 4723 already in use: Kill existing Appium: `pkill -f appium`
- ANDROID_HOME not set: Run setup.command again or manually set in shell profile
- **GUI won't start Appium** (port appears busy but no process found): Restart your computer to clear zombie sockets

### Test fails immediately

**Check device connection:**
```bash
adb devices
# Should show your device with "device" status
```

**Check Developer Options enabled:**
- USB debugging must be ON
- Allow USB debugging dialog must be accepted on device

## Uninstall

**Mac:**
```bash
./uninstall.command
```

**Windows:**
```bash
uninstall.bat
```
