"""
GPS Mock Controller - Python wrapper for our custom GPS Mock Android app.

Usage:
    from src.gps.gps_mock_controller import GPSMockController

    gps = GPSMockController()
    gps.start_service()  # Must be called first
    gps.set_location(48.1486, 17.1077)  # Bratislava
    gps.play_gpx_route("/sdcard/Download/route.gpx", speed_kmh=90)
    gps.stop()
"""

import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
import xml.etree.ElementTree as ET
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)


class GPSMockController:
    """Controller for GPS Mock Android app via ADB broadcasts."""

    PACKAGE = "com.roadlords.gpsmock"
    RECEIVER = f"{PACKAGE}/.CommandReceiver"
    MAIN_ACTIVITY = f"{PACKAGE}/.MainActivity"

    ACTION_START = f"{PACKAGE}.START"
    ACTION_STOP = f"{PACKAGE}.STOP"
    ACTION_SET = f"{PACKAGE}.SET"

    def __init__(self, device_id: Optional[str] = None):
        """
        Initialize GPS Mock Controller.

        Args:
            device_id: Optional ADB device ID. If None, uses first connected device.
        """
        self.device_id = device_id
        self._service_started = False

    def _adb_cmd(self, *args) -> str:
        """Execute ADB command and return output."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"ADB command failed: {' '.join(cmd)}\n{result.stderr}")
        # Return both stdout and stderr (adb push outputs to stderr)
        return result.stdout + result.stderr

    def _broadcast(self, action: str, **extras) -> bool:
        """Send broadcast to GPS Mock receiver."""
        args = ["shell", "am", "broadcast", "-n", self.RECEIVER, "-a", action]

        for key, value in extras.items():
            if isinstance(value, float):
                args.extend(["--ef", key, str(value)])
            elif isinstance(value, int):
                args.extend(["--ei", key, str(value)])
            elif isinstance(value, str):
                args.extend(["-e", key, value])

        output = self._adb_cmd(*args)
        return "Broadcast completed" in output

    def start_service(self) -> bool:
        """
        Start GPS Mock service by launching MainActivity.
        Must be called before sending location commands on Android 12+.

        Returns:
            True if service started successfully.
        """
        logger.info("Starting GPS Mock service...")

        # Launch MainActivity to get foreground exemption
        output = self._adb_cmd("shell", "am", "start", "-n", self.MAIN_ACTIVITY)

        if "Error" in output:
            logger.error(f"Failed to start GPS Mock: {output}")
            return False

        # Wait for service to initialize
        time.sleep(1)
        self._service_started = True
        logger.info("GPS Mock service started")
        return True

    def set_location(self, lat: float, lon: float) -> bool:
        """
        Set static GPS location.

        Args:
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.

        Returns:
            True if location was set successfully.
        """
        if not self._service_started:
            self.start_service()

        logger.info(f"Setting GPS location to: {lat}, {lon}")
        return self._broadcast(self.ACTION_SET, lat=lat, lon=lon)

    def play_gpx_route(self, gpx_path: str, speed_kmh: float = 80.0) -> bool:
        """
        Start GPX route playback.

        Args:
            gpx_path: Path to GPX file on device (e.g., /sdcard/Download/route.gpx)
            speed_kmh: Playback speed in km/h.

        Returns:
            True if playback started successfully.
        """
        if not self._service_started:
            self.start_service()

        logger.info(f"Starting GPX playback: {gpx_path} at {speed_kmh} km/h")
        return self._broadcast(self.ACTION_START, gpx=gpx_path, speed=speed_kmh)

    def stop(self) -> bool:
        """Stop GPS mock playback."""
        logger.info("Stopping GPS Mock")
        return self._broadcast(self.ACTION_STOP)

    def push_gpx_file(self, local_path: str, remote_path: str = "/sdcard/Download/route.gpx") -> bool:
        """
        Push local GPX file to device.

        Args:
            local_path: Path to local GPX file.
            remote_path: Destination path on device.

        Returns:
            True if file was pushed successfully.
        """
        output = self._adb_cmd("push", local_path, remote_path)
        success = "pushed" in output.lower() or "transferred" in output.lower()
        if success:
            logger.info(f"Pushed GPX file to {remote_path}")
        else:
            logger.error(f"Failed to push GPX: {output}")
        return success

    def simulate_route_smooth(
        self,
        waypoints: list[Tuple[float, float]],
        speed_kmh: float = 80.0,
        update_interval: float = 0.5
    ):
        """
        Simulate smooth movement along waypoints using Python control.
        This provides more control than the built-in GPX playback.

        Args:
            waypoints: List of (lat, lon) tuples.
            speed_kmh: Speed in km/h.
            update_interval: How often to update position (seconds).
        """
        if not self._service_started:
            self.start_service()

        speed_ms = speed_kmh / 3.6  # Convert to m/s
        distance_per_update = speed_ms * update_interval

        for i in range(len(waypoints) - 1):
            from_point = waypoints[i]
            to_point = waypoints[i + 1]

            segment_distance = self._haversine_distance(*from_point, *to_point)
            steps = max(1, int(segment_distance / distance_per_update))

            for step in range(steps):
                fraction = step / steps
                lat = from_point[0] + (to_point[0] - from_point[0]) * fraction
                lon = from_point[1] + (to_point[1] - from_point[1]) * fraction

                self.set_location(lat, lon)
                time.sleep(update_interval)

        # Set final position
        if waypoints:
            self.set_location(*waypoints[-1])

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters."""
        R = 6371000  # Earth radius in meters

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    @staticmethod
    def parse_gpx(gpx_path: str) -> list[Tuple[float, float]]:
        """
        Parse GPX file and return list of waypoints.

        Args:
            gpx_path: Path to local GPX file.

        Returns:
            List of (lat, lon) tuples.
        """
        tree = ET.parse(gpx_path)
        root = tree.getroot()

        # Handle GPX namespace
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}

        waypoints = []

        # Try with namespace
        for trkpt in root.findall('.//gpx:trkpt', ns):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            waypoints.append((lat, lon))

        # Try without namespace if empty
        if not waypoints:
            for trkpt in root.findall('.//trkpt'):
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                waypoints.append((lat, lon))

        return waypoints


# Convenience functions for quick usage
def set_gps_location(lat: float, lon: float, device_id: Optional[str] = None):
    """Quick function to set GPS location."""
    gps = GPSMockController(device_id)
    gps.start_service()
    gps.set_location(lat, lon)


def play_gps_route(gpx_path: str, speed_kmh: float = 80.0, device_id: Optional[str] = None):
    """Quick function to play GPX route."""
    gps = GPSMockController(device_id)
    gps.start_service()
    gps.play_gpx_route(gpx_path, speed_kmh)


if __name__ == "__main__":
    # Test the controller
    logging.basicConfig(level=logging.INFO)

    controller = GPSMockController()

    print("Starting GPS Mock service...")
    controller.start_service()

    print("Setting location to Bratislava...")
    controller.set_location(48.1486, 17.1077)

    print("Waiting 5 seconds...")
    time.sleep(5)

    print("Moving to Vienna...")
    controller.set_location(48.2082, 16.3738)

    print("Done!")
