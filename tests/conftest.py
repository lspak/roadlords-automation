"""
Pytest configuration for Roadlords Automation tests.

Provides:
- Custom CLI options for platform/device selection
- Driver fixtures for Appium WebDriver
- Screenshot capture on failure
- Common test data fixtures
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Generator

import pytest
from appium.webdriver.webdriver import WebDriver

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.driver_factory import DriverFactory

logger = logging.getLogger(__name__)


# === CLI Options ===

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--platform",
        action="store",
        default=os.getenv("PLATFORM", "real_device"),
        help="Platform: emulator, real_device"
    )
    parser.addoption(
        "--device",
        action="store",
        default=os.getenv("DEVICE_UDID", ""),
        help="Device UDID for real device testing"
    )


@pytest.fixture(scope="session")
def platform(request) -> str:
    """Get target platform."""
    return request.config.getoption("--platform")


@pytest.fixture(scope="session")
def device_udid(request) -> str:
    """Get device UDID."""
    return request.config.getoption("--device")


# === Driver Fixtures ===

@pytest.fixture(scope="session")
def driver_factory() -> DriverFactory:
    """Create DriverFactory instance."""
    return DriverFactory()


@pytest.fixture(scope="function")
def driver(driver_factory: DriverFactory, platform: str) -> Generator[WebDriver, None, None]:
    """
    Create Appium driver for each test.

    Ensures clean app state before test and quits driver after.
    """
    import subprocess
    import time

    package = "com.roadlords.android"

    # Force stop app before test
    if platform in ["real_device", "emulator"]:
        try:
            subprocess.run(["adb", "shell", "am", "force-stop", package], timeout=5, check=False)
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Could not force-stop app: {e}")

    _driver = None
    try:
        _driver = driver_factory.create_driver(platform=platform)
        logger.info(f"Driver created on platform: {platform}")

        # Activate app
        if platform in ["real_device", "emulator"]:
            try:
                _driver.activate_app(package)
                time.sleep(3)
            except Exception as e:
                logger.warning(f"Could not activate app: {e}")

        yield _driver
    finally:
        if _driver:
            driver_factory.quit_driver(_driver)


# === Pytest Hooks ===

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture screenshot on test failure."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get('driver')
        if driver:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                reports_dir = Path(__file__).parent.parent / "reports" / "failures"
                reports_dir.mkdir(parents=True, exist_ok=True)

                screenshot_path = reports_dir / f"failure_{item.name}_{timestamp}.png"
                driver.save_screenshot(str(screenshot_path))
                logger.info(f"Failure screenshot: {screenshot_path}")
            except Exception as e:
                logger.error(f"Failed to capture screenshot: {e}")


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "smoke: Quick smoke tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "gps: Tests requiring GPS simulation")


# === Test Data ===

@pytest.fixture(scope="session")
def test_data() -> dict:
    """Common test data."""
    return {
        'locations': {
            'bratislava': {'lat': 48.1486, 'lon': 17.1077},
            'vienna': {'lat': 48.2082, 'lon': 16.3738},
        },
        'truck_profiles': {
            'standard': {
                'height': 4.0,
                'width': 2.55,
                'length': 16.5,
                'weight': 40000,
            }
        }
    }
