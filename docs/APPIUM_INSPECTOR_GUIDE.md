# Appium Inspector Guide

## Connecting to Roadlords

### 1. Start Appium Server
```bash
appium
```

### 2. Open Appium Inspector

### 3. Set Desired Capabilities

**Remote Host:** `localhost`
**Remote Port:** `4723`
**Remote Path:** `/`

**Capabilities (JSON):**
```json
{
  "platformName": "Android",
  "appium:automationName": "UiAutomator2",
  "appium:deviceName": "ASUSAI2501C",
  "appium:udid": "SCAIOC641923K8V",
  "appium:appPackage": "com.roadlords.android",
  "appium:appActivity": "com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity",
  "appium:noReset": true,
  "appium:autoGrantPermissions": true
}
```

### 4. Click "Start Session"

---

## Mapping UI Elements

### What to Look For:

For each screen (Home, Navigation, Settings, etc.) map:

#### 1. Resource ID (ideal)
```
resource-id="com.roadlords.android:id/btn_search"
↓
SEARCH_BUTTON = (By.ID, "com.roadlords.android:id/btn_search")
```

#### 2. Content-desc (if ID missing)
```
content-desc="Search for destination"
↓
SEARCH_BUTTON = (By.ACCESSIBILITY_ID, "Search for destination")
```

#### 3. Text (if ID and desc missing)
```
text="Search"
↓
SEARCH_BUTTON = (By.XPATH, "//android.widget.TextView[@text='Search']/..")
```

#### 4. Class + index (last resort)
```
class="android.widget.ImageButton" index="2"
↓
MENU_BUTTON = (By.XPATH, "//android.widget.ImageButton[2]")
```

---

## Page Objects to Update

### Home Page (`src/pages/home_page.py`)
Elements to map:
- [ ] Search button/input
- [ ] Menu button
- [ ] Map view
- [ ] Current location button
- [ ] Zoom controls
- [ ] Navigation start FAB

### Navigation Page (`src/pages/navigation_page.py`)
Elements to map:
- [ ] Current instruction text
- [ ] Distance to turn
- [ ] ETA
- [ ] Remaining distance/time
- [ ] Current speed display
- [ ] Speed limit display
- [ ] Stop navigation button
- [ ] Mute button

### Truck Profile Page (`src/pages/truck_profile_page.py`)
Elements to map:
- [ ] Profile name input
- [ ] Height input (m)
- [ ] Width input (m)
- [ ] Length input (m)
- [ ] Weight input (kg)
- [ ] Axle count selector
- [ ] Hazmat toggle
- [ ] Save button
- [ ] Delete button

### Settings Page (`src/pages/settings_page.py`)
Elements to map:
- [ ] Offline maps button
- [ ] Language selector
- [ ] Units selector
- [ ] Voice guidance toggle

---

## Record Format

For each element create a record:

```python
# Home Page - Search Button
# Inspector: resource-id="com.roadlords.android:id/search_box"
# Location: Top center of screen
# Type: EditText
SEARCH_INPUT = (By.ID, "com.roadlords.android:id/search_box")

# Alternative if no ID:
# SEARCH_INPUT = (By.XPATH, "//android.widget.EditText[@content-desc='Search']")
```

---

## Tips

1. **Jetpack Compose UI** - Roadlords uses Compose, which often lacks resource-ids
   - Prefer `content-desc` or `text` locators
   - Use parent/child XPath relations

2. **Dynamic elements** - Navigation data changes
   - Map the container, not the specific value
   - `//android.widget.TextView[contains(@resource-id, 'eta')]`

3. **Scrollable lists** - Truck profiles, settings
   - Use `UiScrollable` for scrolling
   - Map list item template

4. **Modal dialogs** - Permissions, confirmations
   - Map "Allow", "OK", "Cancel" buttons
   - Store in `handle_dialog()` helpers

---

## Checklist

After mapping each screen:

- [ ] Screenshot of screen saved to `docs/screenshots/`
- [ ] All interactive elements have a locator
- [ ] Locators tested in Inspector (Tap Test)
- [ ] Page Object updated with real IDs
- [ ] Alternative locators documented
- [ ] Test written for given screen

---

## Workflow

```
1. Appium Inspector → Find element
2. Copy resource-id / content-desc / xpath
3. Update Page Object
4. Commit: "Update HomePage locators from Inspector"
5. Run smoke test: pytest tests/smoke/test_app_launch.py -v
6. Fix if test fails
7. Continue with next element
```
