"""
Video Recorder for Android device

Records screen via ADB screenrecord with timestamp synchronization
for correlation with memory/performance data.
"""
import subprocess
import threading
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, List

logger = logging.getLogger(__name__)


class VideoRecorder:
    """Record Android screen with timestamp tracking."""

    def __init__(self, device_id: str = None, output_dir: Path = None):
        self.device_id = device_id
        self.output_dir = output_dir or Path("reports/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._recording = False
        self._process: Optional[subprocess.Popen] = None
        self._start_time: Optional[datetime] = None
        self._video_path: Optional[Path] = None
        self._remote_path = "/sdcard/test_recording.mp4"

    def _adb(self, *args, background=False) -> Union[subprocess.Popen, str]:
        """Execute ADB command."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)

        if background:
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout + result.stderr

    def start(self, max_duration: int = 180) -> datetime:
        """
        Start screen recording.

        Args:
            max_duration: Maximum recording duration in seconds (max 180 for screenrecord)

        Returns:
            Start timestamp for correlation with other data
        """
        if self._recording:
            logger.warning("Recording already in progress")
            return self._start_time

        # Clean up any existing recording
        self._adb("shell", "rm", "-f", self._remote_path)

        # Start recording in background
        # screenrecord has 180s limit, but we can chain recordings if needed
        logger.info(f"Starting video recording (max {max_duration}s)...")
        self._process = self._adb(
            "shell", "screenrecord",
            "--time-limit", str(min(max_duration, 180)),
            "--bit-rate", "4000000",  # 4 Mbps for good quality
            self._remote_path,
            background=True
        )

        self._start_time = datetime.now()
        self._recording = True
        logger.info(f"Recording started at {self._start_time.isoformat()}")

        return self._start_time

    def stop(self) -> Optional[Path]:
        """
        Stop recording and pull video from device.

        Returns:
            Path to the saved video file
        """
        if not self._recording:
            logger.warning("No recording in progress")
            return None

        logger.info("Stopping video recording...")

        # Send interrupt to stop screenrecord gracefully
        if self._process:
            # Kill screenrecord on device
            self._adb("shell", "pkill", "-INT", "screenrecord")
            time.sleep(2)  # Wait for file to be finalized

            try:
                self._process.terminate()
            except:
                pass

        self._recording = False

        # Generate output filename with timestamp
        timestamp = self._start_time.strftime("%Y%m%d_%H%M%S")
        self._video_path = self.output_dir / f"recording_{timestamp}.mp4"

        # Pull video from device
        logger.info(f"Pulling video to {self._video_path}...")
        self._adb("pull", self._remote_path, str(self._video_path))

        # Clean up remote file
        self._adb("shell", "rm", "-f", self._remote_path)

        if self._video_path.exists():
            size_mb = self._video_path.stat().st_size / (1024 * 1024)
            logger.info(f"Video saved: {self._video_path} ({size_mb:.1f} MB)")
            return self._video_path
        else:
            logger.error("Failed to pull video from device")
            return None

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time since recording started."""
        if self._start_time:
            return (datetime.now() - self._start_time).total_seconds()
        return 0.0

    @property
    def start_time(self) -> Optional[datetime]:
        return self._start_time

    @property
    def video_path(self) -> Optional[Path]:
        return self._video_path

    @property
    def is_recording(self) -> bool:
        return self._recording


class ChainedVideoRecorder:
    """
    Records video in chunks to bypass 180s screenrecord limit.
    Automatically chains multiple recordings for longer tests.
    """

    def __init__(self, device_id: str = None, output_dir: Path = None):
        self.device_id = device_id
        self.output_dir = output_dir or Path("reports/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._recording = False
        self._start_time: Optional[datetime] = None
        self._videos: List[Path] = []
        self._current_recorder: Optional[VideoRecorder] = None
        self._chain_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _chain_recordings(self, chunk_duration: int = 170):
        """Background thread to chain recordings."""
        while not self._stop_event.is_set():
            # Start a new chunk
            self._current_recorder = VideoRecorder(self.device_id, self.output_dir)
            self._current_recorder.start(max_duration=chunk_duration)

            # Wait for chunk to complete or stop signal
            for _ in range(chunk_duration):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

            # Stop current chunk
            video_path = self._current_recorder.stop()
            if video_path and video_path.exists():
                self._videos.append(video_path)

    def start(self) -> datetime:
        """Start chained recording."""
        if self._recording:
            return self._start_time

        self._start_time = datetime.now()
        self._recording = True
        self._stop_event.clear()
        self._videos = []

        # Start chaining thread
        self._chain_thread = threading.Thread(target=self._chain_recordings, daemon=True)
        self._chain_thread.start()

        logger.info(f"Chained recording started at {self._start_time.isoformat()}")
        return self._start_time

    def stop(self) -> List[Path]:
        """Stop recording and return all video chunks."""
        if not self._recording:
            return []

        self._stop_event.set()
        self._recording = False

        # Stop current recorder
        if self._current_recorder and self._current_recorder.is_recording:
            video_path = self._current_recorder.stop()
            if video_path and video_path.exists():
                self._videos.append(video_path)

        # Wait for chain thread to finish
        if self._chain_thread:
            self._chain_thread.join(timeout=5)

        logger.info(f"Recording stopped. {len(self._videos)} video chunk(s) saved.")
        return self._videos

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time since recording started."""
        if self._start_time:
            return (datetime.now() - self._start_time).total_seconds()
        return 0.0

    @property
    def start_time(self) -> Optional[datetime]:
        return self._start_time

    @property
    def videos(self) -> List[Path]:
        return self._videos
