# Roadlords Automation

Automated E2E testing framework for Roadlords truck GPS navigation app.

## Features

- **GPS Simulation**: Custom GPS Mock Android app for stable location mocking
- **Memory Monitoring**: Real-time memory tracking during navigation
- **Video Recording**: Screen capture during test execution
- **UI Verification**: Visual regression testing with SSIM comparison
- **HTML Reports**: Detailed reports with memory graphs, video, and screenshots

## Quick Start

```bash
# 1. Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Start Appium server
appium

# 3. Run E2E test
python tests/e2e/test_bratislava_svidnik.py
```

## Project Structure

```
roadlords-automation/
├── tests/
│   ├── e2e/
│   │   └── test_bratislava_svidnik.py    # Main E2E navigation test
│   └── conftest.py                        # Pytest fixtures
├── src/
│   ├── gps/
│   │   └── gps_mock_controller.py        # GPS Mock app controller
│   ├── utils/
│   │   ├── memory_monitor.py             # Memory tracking
│   │   ├── video_recorder.py             # Screen recording
│   │   ├── ui_verifier.py                # Visual regression
│   │   ├── report_generator.py           # HTML report generation
│   │   ├── driver_factory.py             # Appium driver setup
│   │   ├── wait_utils.py                 # Custom wait utilities
│   │   └── adb_utils.py                  # ADB utilities
│   └── data/routes/
│       └── pifflova_sustekova_petrzalka.gpx  # Test route
├── android-gps-mock/                      # GPS Mock Android app source
├── config/
│   ├── config.yaml                        # Main configuration
│   └── capabilities/                      # Appium capabilities
├── reports/                               # Generated reports
└── docs/                                  # Documentation
```

## Requirements

- Python 3.11+
- Appium 2.x
- Android device with Developer Options enabled
- GPS Mock app installed (from `android-gps-mock/`)

## GPS Mock App Setup

The GPS Mock app provides stable GPS simulation via ADB broadcasts.

```bash
# Build and install
cd android-gps-mock
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk

# Enable as mock location provider
# Settings → Developer options → Select mock location app → GPS Mock
```

## Test Configuration

Edit `tests/e2e/test_bratislava_svidnik.py` to configure:

```python
DEVICE_UDID = "your-device-id"    # ADB device ID
START_LAT = 48.1270               # Starting latitude
START_LON = 17.1072               # Starting longitude
DESTINATION = "Sustekova 5"       # Search destination
GPS_SPEED_KMH = 50.0              # GPS playback speed
```

## UI Verification

Run in capture mode to create baseline:
```python
UI_VERIFY_MODE = "capture"
```

Run in verify mode to compare against baseline:
```python
UI_VERIFY_MODE = "verify"
```

## Generated Reports

Reports are saved to `reports/e2e/`:
- `stress_report_*.html` - Interactive HTML report with memory graph
- `videos/` - Screen recordings
- `screenshots/` - Navigation screenshots
- `memory_*.csv` - Raw memory data

## Documentation

- [AUTOMATION_REPORT.md](./AUTOMATION_REPORT.md) - Detailed automation guide
- [CLAUDE.md](./CLAUDE.md) - AI assistant instructions
