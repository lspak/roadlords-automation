"""
ADB (Android Debug Bridge) utilities for device control.
"""
import logging
import subprocess
import shlex
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class ADBUtils:
    """Utility class for ADB operations."""

    def __init__(self, device_id: Optional[str] = None):
        """
        Initialize ADBUtils.

        Args:
            device_id: Specific device ID (for multiple connected devices)
        """
        self.device_id = device_id

    def _build_command(self, *args) -> List[str]:
        """Build ADB command with optional device targeting."""
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(args)
        return cmd

    def _execute(self, *args, timeout: int = 30) -> Tuple[str, str, int]:
        """
        Execute ADB command.

        Args:
            *args: Command arguments
            timeout: Command timeout in seconds

        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        cmd = self._build_command(*args)
        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return '', 'Command timed out', 1

    def shell(self, command: str, timeout: int = 30) -> str:
        """
        Execute shell command on device.

        Args:
            command: Shell command to execute
            timeout: Command timeout

        Returns:
            Command output
        """
        stdout, stderr, code = self._execute('shell', command, timeout=timeout)
        if code != 0:
            logger.warning(f"Shell command failed: {stderr}")
        return stdout

    def get_current_activity(self) -> str:
        """Get currently focused activity."""
        output = self.shell('dumpsys activity activities | grep mResumedActivity')
        # Parse activity name from output
        if 'mResumedActivity' in output:
            parts = output.split()
            for part in parts:
                if '/' in part:
                    return part
        return ''

    def get_device_info(self) -> dict:
        """Get device information."""
        return {
            'model': self.shell('getprop ro.product.model'),
            'android_version': self.shell('getprop ro.build.version.release'),
            'sdk_version': self.shell('getprop ro.build.version.sdk'),
            'manufacturer': self.shell('getprop ro.product.manufacturer'),
        }

    def set_mock_location(
        self,
        latitude: float,
        longitude: float,
        altitude: float = 0,
        speed: float = 0,
        bearing: float = 0
    ) -> bool:
        """
        Set mock location via Appium Settings app.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            altitude: Altitude in meters
            speed: Speed in m/s
            bearing: Bearing/heading in degrees

        Returns:
            True if successful
        """
        cmd = (
            f'am start-foreground-service '
            f'-n io.appium.settings/.LocationService '
            f'--es latitude {latitude} '
            f'--es longitude {longitude} '
            f'--es altitude {altitude}'
        )

        if speed > 0:
            cmd += f' --es speed {speed}'
        if bearing > 0:
            cmd += f' --es bearing {bearing}'

        output = self.shell(cmd)
        success = 'Error' not in output
        if success:
            logger.info(f"Mock location set: {latitude}, {longitude}")
        else:
            logger.error(f"Failed to set mock location: {output}")
        return success

    def stop_mock_location(self) -> bool:
        """Stop mock location service."""
        output = self.shell('am stopservice io.appium.settings/.LocationService')
        logger.info("Mock location service stopped")
        return 'Stopping' in output or 'Service' in output

    def enable_mock_location_app(self, package: str = 'io.appium.settings') -> bool:
        """
        Enable app as mock location provider.

        Args:
            package: Package name of mock location app

        Returns:
            True if successful
        """
        output = self.shell(
            f'appops set {package} android:mock_location allow'
        )
        return 'Error' not in output

    def send_key_event(self, keycode: int) -> None:
        """
        Send key event to device.

        Args:
            keycode: Android keycode (e.g., 4 for BACK)
        """
        self.shell(f'input keyevent {keycode}')

    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        self.shell(f'input tap {x} {y}')

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Swipe gesture."""
        self.shell(f'input swipe {x1} {y1} {x2} {y2} {duration_ms}')

    def toggle_wifi(self, enable: bool) -> None:
        """Toggle WiFi on/off."""
        state = 'enable' if enable else 'disable'
        self.shell(f'svc wifi {state}')
        logger.info(f"WiFi {'enabled' if enable else 'disabled'}")

    def toggle_mobile_data(self, enable: bool) -> None:
        """Toggle mobile data on/off."""
        state = 'enable' if enable else 'disable'
        self.shell(f'svc data {state}')
        logger.info(f"Mobile data {'enabled' if enable else 'disabled'}")

    def toggle_airplane_mode(self, enable: bool) -> None:
        """Toggle airplane mode."""
        value = '1' if enable else '0'
        self.shell(f'settings put global airplane_mode_on {value}')
        self.shell('am broadcast -a android.intent.action.AIRPLANE_MODE')
        logger.info(f"Airplane mode {'enabled' if enable else 'disabled'}")

    def clear_app_data(self, package: str) -> None:
        """Clear app data and cache."""
        self.shell(f'pm clear {package}')
        logger.info(f"App data cleared: {package}")

    def force_stop_app(self, package: str) -> None:
        """Force stop application."""
        self.shell(f'am force-stop {package}')
        logger.info(f"App force stopped: {package}")

    def is_app_installed(self, package: str) -> bool:
        """Check if app is installed."""
        output = self.shell(f'pm list packages | grep {package}')
        return package in output

    def get_connected_devices(self) -> List[str]:
        """Get list of connected device IDs."""
        stdout, _, _ = self._execute('devices')
        devices = []
        for line in stdout.split('\n')[1:]:  # Skip header
            if '\tdevice' in line:
                devices.append(line.split('\t')[0])
        return devices


# Emulator-specific commands
class EmulatorUtils(ADBUtils):
    """Extended ADB utils for Android Emulator."""

    def __init__(self, emulator_port: int = 5554):
        """
        Initialize EmulatorUtils.

        Args:
            emulator_port: Emulator console port (default 5554)
        """
        super().__init__(device_id=f'emulator-{emulator_port}')
        self.port = emulator_port

    def geo_fix(
        self,
        longitude: float,
        latitude: float,
        altitude: float = 0
    ) -> bool:
        """
        Set GPS location via emulator console.

        Note: For emulator, longitude comes before latitude!

        Args:
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            altitude: Altitude in meters

        Returns:
            True if successful
        """
        stdout, stderr, code = self._execute(
            'emu', 'geo', 'fix',
            str(longitude), str(latitude), str(altitude)
        )
        success = code == 0
        if success:
            logger.info(f"Emulator geo fix: {latitude}, {longitude}")
        return success
