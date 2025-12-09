# GPS Mock - Roadlords Test Tool

Minimal Android application for GPS mocking, controlled via ADB.

## Build

```bash
cd android-gps-mock
./gradlew assembleDebug
```

APK will be at: `app/build/outputs/apk/debug/app-debug.apk`

## Installation

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Set as Mock Location App

1. Open Developer Options on device
2. Find "Select mock location app"
3. Select "GPS Mock"

## First Launch - Permissions

After installation, grant permissions:
```bash
adb shell pm grant com.roadlords.gpsmock android.permission.ACCESS_FINE_LOCATION
adb shell pm grant com.roadlords.gpsmock android.permission.ACCESS_COARSE_LOCATION
```

## Usage via ADB

**IMPORTANT:** On Android 12+ you need to launch the app first so the service can run in background:
```bash
adb shell am start -n com.roadlords.gpsmock/.MainActivity
```

### Set static position:
```bash
adb shell am broadcast -n com.roadlords.gpsmock/.CommandReceiver \
  -a com.roadlords.gpsmock.SET \
  --ef lat 48.1516 --ef lon 17.1093
```

### Start GPX route:
```bash
adb shell am broadcast -n com.roadlords.gpsmock/.CommandReceiver \
  -a com.roadlords.gpsmock.START \
  -e gpx "/sdcard/Download/route.gpx" \
  --ef speed 80.0
```

### Stop:
```bash
adb shell am broadcast -n com.roadlords.gpsmock/.CommandReceiver \
  -a com.roadlords.gpsmock.STOP
```

## Python Integration

Use `GPSMockController` from the main project:

```python
from src.gps.gps_mock_controller import GPSMockController

# Create controller
gps = GPSMockController()

# Start service (required on Android 12+)
gps.start_service()

# Set static position
gps.set_location(48.1486, 17.1077)  # Bratislava

# Start GPX route
gps.push_gpx_file("local_route.gpx", "/sdcard/Download/route.gpx")
gps.play_gpx_route("/sdcard/Download/route.gpx", speed_kmh=90)

# Or simulate smooth movement from Python
waypoints = [(48.1486, 17.1077), (48.2082, 16.3738)]
gps.simulate_route_smooth(waypoints, speed_kmh=80)

# Stop
gps.stop()
```
