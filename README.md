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

This will install all dependencies (Python, Node, Appium, ADB).

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

## Uninstall

**Mac:**
```bash
./uninstall.command
```

**Windows:**
```bash
uninstall.bat
```
