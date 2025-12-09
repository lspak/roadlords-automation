"""
Custom wait utilities for Appium tests.
"""
import logging
from typing import Callable, TypeVar, Optional

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement

logger = logging.getLogger(__name__)
T = TypeVar('T')


class WaitUtils:
    """Utility class for various wait operations."""

    def __init__(self, driver: WebDriver, default_timeout: int = 30):
        """
        Initialize WaitUtils.

        Args:
            driver: Appium WebDriver instance
            default_timeout: Default wait timeout in seconds
        """
        self.driver = driver
        self.default_timeout = default_timeout

    def wait_for_element(
        self,
        locator: tuple,
        timeout: Optional[int] = None,
        condition: str = 'visible'
    ) -> WebElement:
        """
        Wait for element with specified condition.

        Args:
            locator: Tuple of (By, value)
            timeout: Wait timeout
            condition: 'visible', 'clickable', 'present'

        Returns:
            WebElement when found

        Raises:
            TimeoutException: If element not found within timeout
        """
        timeout = timeout or self.default_timeout

        conditions = {
            'visible': EC.visibility_of_element_located,
            'clickable': EC.element_to_be_clickable,
            'present': EC.presence_of_element_located
        }

        if condition not in conditions:
            raise ValueError(f"Unknown condition: {condition}")

        logger.debug(f"Waiting for element {locator} to be {condition}")

        return WebDriverWait(self.driver, timeout).until(
            conditions[condition](locator)
        )

    def wait_for_element_gone(
        self,
        locator: tuple,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait until element is no longer visible.

        Args:
            locator: Tuple of (By, value)
            timeout: Wait timeout

        Returns:
            True when element is gone
        """
        timeout = timeout or self.default_timeout

        logger.debug(f"Waiting for element {locator} to disappear")

        return WebDriverWait(self.driver, timeout).until(
            EC.invisibility_of_element_located(locator)
        )

    def wait_for_text(
        self,
        locator: tuple,
        text: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait until element contains specified text.

        Args:
            locator: Tuple of (By, value)
            text: Expected text (partial match)
            timeout: Wait timeout

        Returns:
            True when text is present
        """
        timeout = timeout or self.default_timeout

        logger.debug(f"Waiting for text '{text}' in element {locator}")

        return WebDriverWait(self.driver, timeout).until(
            EC.text_to_be_present_in_element(locator, text)
        )

    def wait_for_activity(
        self,
        activity: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait until specified activity is in foreground.

        Args:
            activity: Activity name (can be partial)
            timeout: Wait timeout

        Returns:
            True when activity is active
        """
        timeout = timeout or self.default_timeout

        def activity_is_current(driver):
            current = driver.current_activity
            return activity in current if current else False

        logger.debug(f"Waiting for activity: {activity}")

        return WebDriverWait(self.driver, timeout).until(activity_is_current)

    def wait_for_condition(
        self,
        condition: Callable[[WebDriver], T],
        timeout: Optional[int] = None,
        poll_frequency: float = 0.5
    ) -> T:
        """
        Wait for custom condition.

        Args:
            condition: Callable that returns truthy value when condition is met
            timeout: Wait timeout
            poll_frequency: How often to check condition

        Returns:
            Result of condition when met
        """
        timeout = timeout or self.default_timeout

        return WebDriverWait(
            self.driver,
            timeout,
            poll_frequency=poll_frequency
        ).until(condition)

    def is_element_present(
        self,
        locator: tuple,
        timeout: int = 3
    ) -> bool:
        """
        Check if element is present (with short timeout).

        Args:
            locator: Tuple of (By, value)
            timeout: Short timeout for check

        Returns:
            True if element exists, False otherwise
        """
        try:
            self.wait_for_element(locator, timeout=timeout, condition='present')
            return True
        except TimeoutException:
            return False

    def wait_for_toast(
        self,
        text: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for Android Toast message.

        Args:
            text: Expected toast text (partial match)
            timeout: Wait timeout

        Returns:
            True if toast with text appears
        """
        timeout = timeout or 10

        toast_locator = (
            By.XPATH,
            f"//android.widget.Toast[contains(@text, '{text}')]"
        )

        try:
            self.wait_for_element(toast_locator, timeout=timeout, condition='present')
            logger.debug(f"Toast found: {text}")
            return True
        except TimeoutException:
            logger.debug(f"Toast not found: {text}")
            return False
