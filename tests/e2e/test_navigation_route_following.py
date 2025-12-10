"""
E2E Navigation Test: Pifflova 2 to Sustekova 5 (Bratislava)

Automated test for Roadlords truck GPS navigation app that:
1. Sets GPS to starting position via GPS Mock Android app
2. Opens search, enters destination address
3. Starts turn-by-turn navigation
4. Records video, monitors memory usage
5. Plays GPS movement along route until arrival
6. Generates HTML report with metrics

Requirements:
- Appium server running on localhost:4723
- GPS Mock Android app installed (com.roadlords.gpsmock)
- Roadlords app installed (com.roadlords.android)
- Device connected via ADB

Usage:
    python tests/e2e/test_bratislava_svidnik.py
"""

import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.memory_monitor import MemoryMonitor
from src.utils.video_recorder import VideoRecorder
from src.utils.report_generator import generate_report_from_test_data
from src.utils.ui_verifier import UIVerifier
from src.gps import GPSMockController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

APPIUM_SERVER = "http://localhost:4723"
DEVICE_UDID = "SCAIOC641923K8V"

# Route: Pifflova 2 to Sustekova 5 (local route in Bratislava ~4km)
START_LAT = 48.1270
START_LON = 17.1072
DESTINATION = "Sustekova 5, Bratislava"
GPX_FILE = Path(__file__).parent.parent.parent / "src/data/routes/pifflova_sustekova_petrzalka.gpx"

# App packages
ROADLORDS_PACKAGE = "com.roadlords.android"
GPS_MOCK_PACKAGE = "com.roadlords.gpsmock"

# Test timing
TOTAL_DRIVE_TIME = 120  # Max navigation duration (seconds)
BASELINE_SECONDS = 20   # Initial baseline period
GPS_SPEED_KMH = 50.0    # GPS playback speed

# UI Verification: None, "capture", or "verify"
# Auto-switches to "capture" if baseline doesn't exist
UI_VERIFY_MODE = "verify"

def get_ui_verify_mode():
    """Auto-detect UI verify mode - use capture if no baseline exists"""
    baseline_file = Path(__file__).parent.parent.parent / "reports/ui_baseline/baseline.json"
    if UI_VERIFY_MODE == "verify" and not baseline_file.exists():
        print("⚠️  No baseline found - switching to 'capture' mode for first run")
        return "capture"
    return UI_VERIFY_MODE


# =============================================================================
# Roadlords App Automation
# =============================================================================

class RoadlordsAutomation:
    """Automate Roadlords navigation app via Appium."""

    def __init__(self, driver: webdriver.Remote):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)

    def restart_app(self):
        """Force restart app for clean state."""
        logger.info("Restarting app...")
        try:
            self.driver.terminate_app(ROADLORDS_PACKAGE)
            time.sleep(2)
        except Exception:
            pass
        self.driver.activate_app(ROADLORDS_PACKAGE)
        time.sleep(5)

    def find_element_safe(self, by, value, timeout=10):
        """Find element with timeout, returns None if not found."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def tap_at(self, x: int, y: int):
        """Tap at screen coordinates using W3C Actions."""
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.actions import interaction
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        from selenium.webdriver.common.actions.pointer_input import PointerInput

        actions = ActionChains(self.driver)
        actions.w3c_actions = ActionBuilder(
            self.driver,
            mouse=PointerInput(interaction.POINTER_TOUCH, "touch")
        )
        actions.w3c_actions.pointer_action.move_to_location(x, y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pause(0.1)
        actions.w3c_actions.pointer_action.pointer_up()
        actions.perform()

    def wait_for_map_load(self):
        """Wait for map to load."""
        logger.info("Waiting for map...")
        time.sleep(5)

    def tap_to_show_ui(self):
        """Tap center of screen to show UI elements."""
        # Hardcoded for device screen (1440x3200) - avoids UiAutomator2 crashes
        self.tap_at(720, 1600)
        time.sleep(2)

    def handle_initial_dialogs(self):
        """Dismiss initial permission/info dialogs."""
        logger.info("Handling initial dialogs...")
        dismiss_texts = ["OK", "SKIP", "ALLOW", "GOT IT", "CONTINUE", "ACCEPT"]

        for _ in range(3):
            for text in dismiss_texts:
                try:
                    elem = self.driver.find_element(
                        AppiumBy.XPATH, f"//*[contains(@text, '{text}')]"
                    )
                    elem.click()
                    time.sleep(1)
                except Exception:
                    pass
            time.sleep(1)

    def open_search(self):
        """Open search panel."""
        logger.info("Opening search...")
        try:
            elem = self.driver.find_element(AppiumBy.XPATH, "//*[@text='Search']")
            elem.click()
            time.sleep(2)
            return True
        except Exception:
            self.tap_at(400, 120)
            time.sleep(2)
            return True

    def cancel_previous_route(self):
        """Cancel any previous route dialog ('Are you still heading to...')."""
        try:
            btn = self.driver.find_element(AppiumBy.XPATH, "//*[@text='Cancel route']")
            logger.info("Found 'Cancel route' dialog - canceling previous route")
            btn.click()
            time.sleep(2)
            return True
        except Exception:
            pass
        return False

    def clear_and_type_destination(self, destination: str):
        """Clear search field and type destination."""
        logger.info(f"Typing destination: {destination}")

        # Clear existing search
        self.tap_at(1050, 185)
        time.sleep(1)

        # Open search input
        self.tap_at(400, 185)
        time.sleep(2)

        # Type destination
        try:
            edit = self.driver.find_element(AppiumBy.CLASS_NAME, "android.widget.EditText")
            edit.send_keys(destination)
            time.sleep(1)
            subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_BACK"], check=False)
            time.sleep(2)
            return True
        except Exception as e:
            logger.warning(f"Could not type destination: {e}")
            return False

    def select_first_result(self):
        """Select first search result."""
        logger.info("Selecting first result...")
        time.sleep(2)

        # Try clickable result row
        try:
            result = self.driver.find_element(
                AppiumBy.XPATH,
                "//android.view.View[@clickable='true'][.//android.widget.TextView][1]"
            )
            result.click()
            time.sleep(3)
            return True
        except Exception:
            pass

        # Fallback to coordinate tap
        self.tap_at(639, 420)
        time.sleep(3)
        return False

    def click_route_button(self):
        """Click 'Get directions' button."""
        logger.info("Clicking Get directions...")
        time.sleep(3)

        try:
            elem = self.driver.find_element(
                AppiumBy.XPATH, "//*[contains(@text, 'Get directions')]"
            )
            loc = elem.location
            size = elem.size
            self.tap_at(loc['x'] + size['width'] // 2, loc['y'] + size['height'] // 2)
            time.sleep(4)
            return True
        except Exception:
            self.tap_at(420, 585)
            time.sleep(4)
            return False

    def dismiss_attention_dialog(self):
        """Dismiss route warning dialog if present."""
        patterns = [
            "//*[contains(@text, 'OK, got it')]",
            "//*[contains(@text, 'OK')]",
        ]
        for xpath in patterns:
            try:
                elem = self.find_element_safe(AppiumBy.XPATH, xpath, timeout=3)
                if elem:
                    elem.click()
                    time.sleep(2)
                    return True
            except Exception:
                pass
        return False

    def click_start_navigation_button(self):
        """Click green start/go button."""
        logger.info("Starting navigation...")

        patterns = [
            (AppiumBy.XPATH, "//android.widget.Button[@clickable='true']"),
            (AppiumBy.CLASS_NAME, "android.widget.Button"),
        ]

        for by, value in patterns:
            elem = self.find_element_safe(by, value, timeout=3)
            if elem:
                try:
                    elem.click()
                    time.sleep(3)
                    return True
                except Exception:
                    pass

        # Fallback - hardcoded for 1440x3200 screen
        self.tap_at(1224, 1600)  # 85% width, 50% height
        time.sleep(3)
        return False

    def capture_ui_elements(self, ui_verifier: UIVerifier, checkpoint: str):
        """Capture UI elements for verification checkpoint."""
        if not ui_verifier:
            return

        try:
            ui_verifier.capture_checkpoint(self.driver, checkpoint)

            if checkpoint == "search_opened":
                try:
                    elem = self.driver.find_element(AppiumBy.CLASS_NAME, "android.widget.EditText")
                    ui_verifier.add_element(checkpoint, "search_bar", elem)
                except Exception:
                    pass
                ui_verifier.add_region(checkpoint, "search_area", x=0, y=0, width=1440, height=500)

            elif checkpoint == "search_results":
                ui_verifier.add_region(checkpoint, "results_list", x=0, y=300, width=1440, height=800)

            elif checkpoint == "destination_selected":
                ui_verifier.add_region(checkpoint, "destination_panel", x=0, y=400, width=1440, height=800)

            elif checkpoint == "navigation_started":
                ui_verifier.add_region(checkpoint, "navigation_header", x=0, y=0, width=1440, height=300)

            elif checkpoint == "arrived":
                ui_verifier.add_region(checkpoint, "arrival_dialog", x=200, y=400, width=1040, height=600)

            logger.info(f"Captured UI: {checkpoint}")

        except Exception as e:
            logger.warning(f"Failed to capture UI for {checkpoint}: {e}")


# =============================================================================
# Driver Setup
# =============================================================================

def create_driver() -> webdriver.Remote:
    """Create Appium driver for Roadlords."""
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = DEVICE_UDID
    options.udid = DEVICE_UDID
    options.app_package = ROADLORDS_PACKAGE
    options.app_activity = "com.sygic.profi.platform.splashscreen.feature.ui.main.SplashScreenActivity"
    options.no_reset = True
    options.auto_grant_permissions = True
    options.new_command_timeout = 300
    options.app_wait_activity = "*"

    logger.info("Connecting to Appium...")
    driver = webdriver.Remote(APPIUM_SERVER, options=options)
    logger.info("Connected")

    # Force landscape orientation (test coordinates are designed for landscape)
    try:
        driver.orientation = "LANDSCAPE"
        logger.info("Set orientation to LANDSCAPE")
    except Exception as e:
        logger.warning(f"Could not set orientation: {e}")
    return driver


# =============================================================================
# Main Test
# =============================================================================

def run_test():
    """Run complete E2E navigation test with monitoring."""
    gps = GPSMockController(DEVICE_UDID)
    driver = None
    mem_monitor = None
    video_recorder = None
    ui_verifier = None

    try:
        # Initialize UI Verifier if enabled
        actual_ui_mode = get_ui_verify_mode()
        if actual_ui_mode:
            ui_baseline_dir = Path(__file__).parent.parent.parent / "reports/ui_baseline"
            ui_verifier = UIVerifier(ui_baseline_dir, mode=actual_ui_mode)
            logger.info(f"UI Verification: {actual_ui_mode}")

        # --- Step 1: Force stop Roadlords and set GPS ---
        logger.info("=" * 50)
        logger.info("STEP 1: Setting GPS to starting position")

        # Force stop Roadlords and io.appium.settings (conflicts with GPS mock)
        subprocess.run(["adb", "shell", "am", "force-stop", ROADLORDS_PACKAGE], capture_output=True)
        subprocess.run(["adb", "shell", "am", "force-stop", "io.appium.settings"], capture_output=True)
        time.sleep(1)

        # Set our GPS Mock app as the mock location provider
        subprocess.run(["adb", "shell", "settings", "put", "secure", "mock_location_app", "com.roadlords.gpsmock"], capture_output=True)

        # Start GPS mock and set position BEFORE launching app
        gps.start_service()
        gps.set_location(START_LAT, START_LON)
        time.sleep(2)
        gps.set_location(START_LAT, START_LON)
        time.sleep(2)

        # --- Step 2: Push GPX file ---
        logger.info("=" * 50)
        logger.info("STEP 2: Pushing GPX file")
        gpx_device_path = "/data/local/tmp/route.gpx"
        gps.push_gpx_file(str(GPX_FILE), gpx_device_path)

        # --- Step 3: Connect to app ---
        logger.info("=" * 50)
        logger.info("STEP 3: Connecting to Roadlords")

        # Set GPS again right before launching
        gps.set_location(START_LAT, START_LON)

        driver = create_driver()
        app = RoadlordsAutomation(driver)

        # Don't restart - app was just launched fresh
        time.sleep(3)

        # Cancel any previous route dialog first
        app.cancel_previous_route()

        # Set GPS multiple times to ensure app picks it up
        gps.set_location(START_LAT, START_LON)
        time.sleep(2)
        gps.set_location(START_LAT, START_LON)
        time.sleep(2)

        app.handle_initial_dialogs()

        # Set GPS again before map loads
        gps.set_location(START_LAT, START_LON)
        time.sleep(3)

        app.wait_for_map_load()

        # Final GPS set to ensure correct position
        gps.set_location(START_LAT, START_LON)
        time.sleep(2)

        app.tap_to_show_ui()

        # --- Step 4: Search for destination ---
        logger.info("=" * 50)
        logger.info("STEP 4: Searching for destination")
        app.open_search()

        if ui_verifier:
            app.capture_ui_elements(ui_verifier, "search_opened")

        app.clear_and_type_destination(DESTINATION)
        time.sleep(3)

        if ui_verifier:
            app.capture_ui_elements(ui_verifier, "search_results")

        # --- Step 5: Select result and start navigation ---
        logger.info("=" * 50)
        logger.info("STEP 5: Starting navigation")
        app.select_first_result()

        if ui_verifier:
            app.capture_ui_elements(ui_verifier, "destination_selected")

        app.click_route_button()
        app.dismiss_attention_dialog()
        app.click_start_navigation_button()

        if ui_verifier:
            app.capture_ui_elements(ui_verifier, "navigation_started")

        # --- Step 6: Start monitoring ---
        logger.info("=" * 50)
        logger.info("STEP 6: Starting monitoring")
        reports_dir = Path(__file__).parent.parent.parent / "reports/e2e"
        reports_dir.mkdir(parents=True, exist_ok=True)

        video_recorder = VideoRecorder(device_id=DEVICE_UDID, output_dir=reports_dir / "videos")
        video_recorder.start(max_duration=180)

        mem_monitor = MemoryMonitor(ROADLORDS_PACKAGE, DEVICE_UDID)
        mem_monitor.start(interval_seconds=1)
        time.sleep(1)

        initial_mem = mem_monitor.get_memory_info()
        logger.info(f"Initial memory: {initial_mem.total_pss_mb:.1f} MB")

        # --- Step 7: GPS navigation ---
        logger.info("=" * 50)
        logger.info("STEP 7: GPS navigation")
        logger.info(f"Starting GPX playback at {GPS_SPEED_KMH} km/h")
        gps.play_gpx_route(gpx_device_path, speed_kmh=GPS_SPEED_KMH)

        screenshots_dir = reports_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        total_elapsed = 0
        arrived = False

        for _ in range(TOTAL_DRIVE_TIME // 5):
            time.sleep(5)
            total_elapsed += 5

            current_mem = mem_monitor._snapshots[-1].total_pss_mb if mem_monitor._snapshots else 0

            # Check for arrival
            try:
                elem = driver.find_element(
                    AppiumBy.XPATH, "//*[contains(@text, 'reached your destination')]"
                )
                if elem:
                    logger.info(f"{total_elapsed}s | {current_mem:.1f} MB | ARRIVED!")
                    arrived = True
                    driver.save_screenshot(str(screenshots_dir / f"{total_elapsed}s_arrived.png"))

                    if ui_verifier:
                        app.capture_ui_elements(ui_verifier, "arrived")

                    try:
                        close_btn = driver.find_element(AppiumBy.XPATH, "//*[@text='Close']")
                        close_btn.click()
                    except Exception:
                        pass

                    driver.terminate_app(ROADLORDS_PACKAGE)
                    break
            except Exception:
                pass

            # Take screenshot every 20 seconds
            if total_elapsed % 20 == 0:
                driver.save_screenshot(str(screenshots_dir / f"{total_elapsed}s_navigation.png"))

            logger.info(f"{total_elapsed}s | {current_mem:.1f} MB | navigating...")

        # --- Step 8: Generate report ---
        logger.info("=" * 50)
        logger.info("STEP 8: Generating report")
        gps.stop()
        report = mem_monitor.stop()
        video_path = video_recorder.stop()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = reports_dir / f"memory_{timestamp}.csv"
        report.to_csv(csv_path)

        html_report = generate_report_from_test_data(
            test_name="E2E Navigation Test - Pifflova 2 to Sustekova 5 (Bratislava)",
            memory_csv_path=csv_path,
            screenshots_dir=screenshots_dir,
            initial_memory=initial_mem.total_pss_mb,
            baseline_memory=initial_mem.total_pss_mb,
            peak_memory=report.max_pss_mb,
            baseline_recomputes=0,
            total_recomputes=0,
            recompute_events=[],
            baseline_duration=BASELINE_SECONDS,
            deviation_duration=total_elapsed - BASELINE_SECONDS,
            output_dir=reports_dir,
            video_path=video_path,
            ui_verifier=ui_verifier
        )

        if ui_verifier:
            if UI_VERIFY_MODE == "capture":
                ui_verifier.save_baseline()
                logger.info("Baseline saved")
            elif UI_VERIFY_MODE == "verify":
                for checkpoint in ui_verifier.current_elements.keys():
                    ui_verifier.verify_checkpoint(checkpoint)
                summary = ui_verifier.get_summary()
                logger.info(f"UI Verification: {summary['status'].upper()}")

        logger.info("=" * 50)
        logger.info("TEST COMPLETED!")
        logger.info(f"Report: {html_report}")
        if video_path:
            logger.info(f"Video: {video_path}")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        gps.stop()
        if video_recorder and video_recorder.is_recording:
            try:
                video_recorder.stop()
            except Exception:
                pass
        if mem_monitor:
            try:
                mem_monitor.stop()
            except Exception:
                pass
        if driver:
            try:
                driver.terminate_app(ROADLORDS_PACKAGE)
            except Exception:
                pass
            driver.quit()


if __name__ == "__main__":
    run_test()
