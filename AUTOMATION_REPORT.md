# Roadlords - Automated GPS Navigation Testing

## Summary

This document describes a complete approach to automated testing of the Roadlords mobile application (truck GPS navigation). We created a functional prototype that demonstrates end-to-end testing capabilities for navigation scenarios including GPS location simulation.

**Demo test:** Navigation from Bratislava to Vienna with realistic truck driving simulation.

---

## 1. Solution Architecture

### Technologies Used

| Technology | Purpose |
|------------|---------|
| **Appium 2.x** | Mobile app automation framework |
| **UiAutomator2** | Android driver (supports Jetpack Compose) |
| **Python + pytest** | Test framework and scripting |
| **ADB (Android Debug Bridge)** | Device communication, GPS commands |
| **GPX files** | Route definitions for GPS simulation |

### Project Structure

```
roadlords-automation/
├── tests/
│   └── e2e/
│       └── test_bratislava_svidnik.py    # Main demo test
├── src/
│   ├── data/routes/
│   │   └── pifflova_sustekova_petrzalka.gpx  # GPS route
│   ├── gps/                               # GPS utilities
│   └── utils/                             # Utility modules
├── android-gps-mock/                      # Android app for GPS mocking
└── config/
    └── capabilities/                      # Appium configurations
```

---

## 2. How Automation Works

### 2.1 Connecting to the App (Appium)

```python
from appium import webdriver
from appium.options.android import UiAutomator2Options

options = UiAutomator2Options()
options.platform_name = "Android"
options.device_name = "DEVICE_UDID"
options.app_package = "com.roadlords.android"
options.app_activity = "com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity"
options.no_reset = True  # Preserves app state

driver = webdriver.Remote("http://localhost:4723", options=options)
```

### 2.2 UI Element Interaction

Roadlords uses **Jetpack Compose**, which complicates element identification (missing resource-id). Solutions:

1. **Accessibility ID** (content-desc):
   ```python
   driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Search")
   ```

2. **XPath with text**:
   ```python
   driver.find_element(AppiumBy.XPATH, "//*[contains(@text, 'Vienna')]")
   ```

3. **Coordinate fallback** (when element has no identifier):
   ```python
   # W3C Actions API for coordinate tap
   actions = ActionChains(driver)
   actions.w3c_actions.pointer_action.move_to_location(x, y)
   actions.w3c_actions.pointer_action.click()
   actions.perform()
   ```

### 2.3 GPS Simulation

For stable GPS simulation, we created a **custom Android application** (`android-gps-mock`) that:
- Receives commands via ADB broadcast
- Sets mock location via Android API
- Plays GPX files with configurable speed

```python
class GPSMockController:
    def set_location(self, lat: float, lon: float):
        """Sets static GPS position."""
        subprocess.run([
            "adb", "shell", "am", "broadcast",
            "-n", "com.roadlords.gpsmock/.CommandReceiver",
            "-a", "com.roadlords.gpsmock.SET",
            "--ef", "lat", str(lat),
            "--ef", "lon", str(lon)
        ])

    def play_gpx(self, gpx_path: str, speed_kmh: float = 80.0):
        """Starts GPX route playback."""
        subprocess.run([
            "adb", "shell", "am", "broadcast",
            "-n", "com.roadlords.gpsmock/.CommandReceiver",
            "-a", "com.roadlords.gpsmock.START",
            "-e", "gpx", gpx_path,
            "--ef", "speed", str(speed_kmh)
        ])
```

---

## 3. Testing Procedure

### Typical E2E Navigation Test:

```
1. Set GPS to starting position
2. Launch Roadlords application
3. Open search
4. Enter destination
5. Select search result
6. Click "Get Directions" / "Route"
7. Dismiss warning dialog (if displayed)
8. Click green navigation start button
9. Start GPS movement along route
10. Verify navigation instructions / app behavior
```

### Key Points for Your Tests:

- **Restart app before each test** for clean state
- **Wait for map to load** (5+ seconds)
- **Handle various dialogs** (permissions, warnings)
- **Use timeouts** for unstable elements

---

## 4. GPS Coordinates - Your Options

Since you're developing the application, you have several advantages:

### Option A: Export from App (Recommended)
Add a debug build feature to **export calculated route as GPX**:
```kotlin
// In app after route calculation
fun exportRouteToGpx(route: Route): File {
    val gpx = GpxWriter.fromCoordinates(route.coordinates)
    return File(cacheDir, "route.gpx").apply { writeText(gpx) }
}
```
This is the most reliable method - you get exactly the coordinates the app uses.

### Option B: Direct Routing API
If you have access to the same routing API (Sygic/custom), you can:
```python
response = requests.get("https://your-routing-api.com/route", params={
    "from": "48.1486,17.1077",
    "to": "48.2082,16.3738",
    "truck_height": 4.0,
    "truck_weight": 40000
})
gpx_content = convert_to_gpx(response.json()["coordinates"])
```

### Option C: OSRM (Open Source Routing Machine)
For approximate routes (without truck restrictions):
```python
from src.tools.gpx_generator import generate_gpx_route
generate_gpx_route("Bratislava", "Vienna", "bratislava_vienna.gpx")
```
Disadvantage: OSRM doesn't know truck restrictions (bridges, tunnels, weight limits).

### Option D: Intercept from App
Using **mitmproxy** to capture app API calls. More complex but works without app modifications.

---

## 5. Running Tests - Platforms

### 5.1 Local Device (Development)

```bash
# Start Appium server
appium

# Run test
python tests/e2e/test_bratislava_svidnik.py
```

**Requirements:**
- Android device with enabled Developer Options
- USB debugging enabled
- GPS Mock app installed and set as Mock location app

### 5.2 BrowserStack (Cloud - Parallel Tests)

BrowserStack App Automate supports:
- 25+ Android devices in parallel
- Various OS versions (Android 10-14)
- GPS mocking via their API

```yaml
# config/capabilities/browserstack.yaml
browserstack:
  userName: "YOUR_USERNAME"
  accessKey: "YOUR_ACCESS_KEY"
  app: "bs://APP_ID"
  device: "Samsung Galaxy S23"
  os_version: "13.0"
  gpsLocation: "48.1486,17.1077"  # BrowserStack GPS mock
```

```python
# Using BrowserStack
driver = webdriver.Remote(
    "https://hub.browserstack.com/wd/hub",
    options=browserstack_options
)
```

**Advantages:**
- Real devices
- Parallelization (20+ tests at once)
- Various device/OS combinations
- Integrated GPS mocking

**Disadvantages:**
- Cost (~$400/month for 5 parallel sessions)
- Latency (cloud vs local)

### 5.3 Emulator (CI/CD)

```yaml
# config/capabilities/emulator.yaml
emulator:
  avd: "Pixel_6_API_33"
  platformVersion: "13"
  automationName: "UiAutomator2"
```

```bash
# Start emulator
emulator -avd Pixel_6_API_33

# Set GPS in emulator
adb emu geo fix 17.1077 48.1486
```

**Advantages:**
- Free
- Fast for CI/CD
- Full GPS control

**Disadvantages:**
- Not a real device
- Slower map rendering
- Some sensors unavailable

### 5.4 Mobile Device Farm (Enterprise)

For your own device farm, we recommend:
- **STF (Smartphone Test Farm)** - open source
- **OpenSTF** - self-hosted solution
- **AWS Device Farm** - AWS managed

These solutions enable:
- Parallel tests on physical devices
- Own infrastructure
- Full device control

---

## 6. CI/CD Integration

### GitHub Actions Example:

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Android Emulator
        uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 33
          script: pytest tests/e2e/ --platform=emulator
```

### For BrowserStack:

```yaml
name: BrowserStack Tests
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Upload app to BrowserStack
        run: |
          curl -u "$BS_USER:$BS_KEY" -X POST \
            "https://api-cloud.browserstack.com/app-automate/upload" \
            -F "file=@app.apk"

      - name: Run tests
        env:
          BROWSERSTACK_USER: ${{ secrets.BS_USER }}
          BROWSERSTACK_KEY: ${{ secrets.BS_KEY }}
        run: pytest tests/e2e/ --platform=browserstack --parallel=5
```

---

## 7. Recommended Extensions

### 7.1 Screenshot on Failure
```python
@pytest.fixture(autouse=True)
def screenshot_on_failure(request, driver):
    yield
    if request.node.rep_call.failed:
        driver.save_screenshot(f"reports/failures/{request.node.name}.png")
```

### 7.2 Allure Reporting
```bash
pytest tests/ --alluredir=reports/allure
allure serve reports/allure
```

### 7.3 Video Recording
BrowserStack and STF support video recording automatically.

---

## 8. What We Need from You

Based on this demonstration, please send us **specific test scenarios** you want to automate. For example:

1. **Navigation Scenarios:**
   - Navigation with specific truck parameters (height, weight, ADR)
   - Route change during navigation (rerouting)
   - Navigation through restricted sections (tunnels, bridges)

2. **Offline Scenarios:**
   - Navigation without internet connection
   - Map downloading for offline use

3. **Truck Profiles:**
   - Switching between vehicle profiles
   - Verification of restrictions for different vehicle types

4. **Edge Cases:**
   - Behavior on GPS signal loss
   - Response to speed limit violations
   - Behavior on low battery

**The more specific the scenario, the better we can automate it.**

---

## Contact

For further questions or technical consultation, please contact us.

---

*This document was created as part of the Roadlords application automation analysis.*
