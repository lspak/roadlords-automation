"""
Driver Factory for creating Appium driver instances.
Supports: Android Emulator, Real Device, BrowserStack
"""
import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

import yaml
from appium import webdriver
from appium.options.android import UiAutomator2Options
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DriverFactory:
    """Factory class for creating and managing Appium drivers."""

    PLATFORMS = {
        'emulator': 'emulator.yaml',
        'real_device': 'real_device.yaml',
        'browserstack': 'browserstack.yaml'
    }

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize DriverFactory.

        Args:
            config_dir: Path to config directory. Defaults to project config/
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / 'config'
        self.config_dir = Path(config_dir)
        self.main_config = self._load_yaml(self.config_dir / 'config.yaml')

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def _get_capabilities(self, platform: str) -> Dict[str, Any]:
        """
        Load capabilities for specified platform.

        Args:
            platform: One of 'emulator', 'real_device', 'browserstack'

        Returns:
            Dictionary of capabilities
        """
        if platform not in self.PLATFORMS:
            raise ValueError(f"Unknown platform: {platform}. "
                           f"Use one of: {list(self.PLATFORMS.keys())}")

        caps_file = self.config_dir / 'capabilities' / self.PLATFORMS[platform]
        caps = self._load_yaml(caps_file)

        # Override with environment variables
        caps = self._apply_env_overrides(caps, platform)

        return caps

    def _apply_env_overrides(self, caps: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """Apply environment variable overrides to capabilities."""

        if platform == 'real_device':
            if os.getenv('DEVICE_UDID'):
                caps['udid'] = os.getenv('DEVICE_UDID')
            if os.getenv('ANDROID_VERSION'):
                caps['platformVersion'] = os.getenv('ANDROID_VERSION')

        elif platform == 'browserstack':
            if 'bstack:options' not in caps:
                caps['bstack:options'] = {}

            bs_user = os.getenv('BROWSERSTACK_USER')
            bs_key = os.getenv('BROWSERSTACK_KEY')
            bs_app = os.getenv('BROWSERSTACK_APP_ID')

            if bs_user:
                caps['bstack:options']['userName'] = bs_user
            if bs_key:
                caps['bstack:options']['accessKey'] = bs_key
            if bs_app:
                caps['app'] = bs_app

            # Build info from CI
            build_name = os.getenv('BUILD_NAME', 'local')
            caps['bstack:options']['buildName'] = build_name

        return caps

    def _get_appium_url(self, platform: str) -> str:
        """Get Appium server URL based on platform."""
        if platform == 'browserstack':
            return "https://hub-cloud.browserstack.com/wd/hub"

        host = os.getenv('APPIUM_HOST', self.main_config['appium']['host'])
        port = os.getenv('APPIUM_PORT', self.main_config['appium']['port'])
        base_path = self.main_config['appium'].get('base_path', '')

        return f"http://{host}:{port}{base_path}"

    def create_driver(
        self,
        platform: Optional[str] = None,
        additional_caps: Optional[Dict[str, Any]] = None
    ) -> webdriver.Remote:
        """
        Create and return an Appium driver instance.

        Args:
            platform: Target platform. Defaults to PLATFORM env var or 'emulator'
            additional_caps: Additional capabilities to merge

        Returns:
            Configured Appium WebDriver instance
        """
        if platform is None:
            platform = os.getenv('PLATFORM', 'emulator')

        logger.info(f"Creating driver for platform: {platform}")

        caps = self._get_capabilities(platform)

        # Merge additional capabilities
        if additional_caps:
            caps.update(additional_caps)

        # Create options object
        options = UiAutomator2Options()
        options.load_capabilities(caps)

        # Get server URL
        server_url = self._get_appium_url(platform)
        logger.info(f"Connecting to Appium server: {server_url}")

        # Create driver
        driver = webdriver.Remote(
            command_executor=server_url,
            options=options
        )

        # Set implicit wait from config
        implicit_wait = self.main_config['timeouts'].get('implicit_wait', 10)
        driver.implicitly_wait(implicit_wait)

        logger.info(f"Driver created successfully. Session ID: {driver.session_id}")

        return driver

    @staticmethod
    def quit_driver(driver: webdriver.Remote) -> None:
        """Safely quit the driver."""
        if driver:
            try:
                driver.quit()
                logger.info("Driver quit successfully")
            except Exception as e:
                logger.warning(f"Error quitting driver: {e}")
