"""
Memory monitoring utilities for Android apps via ADB.

Tracks memory usage over time, detects leaks, and generates reports.
"""
import logging
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Callable

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Single memory measurement."""
    timestamp: datetime
    total_pss_kb: int  # Proportional Set Size (most accurate for app memory)
    java_heap_kb: int
    native_heap_kb: int
    code_kb: int
    stack_kb: int
    graphics_kb: int
    private_other_kb: int
    system_kb: int

    @property
    def total_pss_mb(self) -> float:
        return self.total_pss_kb / 1024

    @property
    def java_heap_mb(self) -> float:
        return self.java_heap_kb / 1024

    @property
    def native_heap_mb(self) -> float:
        return self.native_heap_kb / 1024

    def __str__(self) -> str:
        return (
            f"PSS: {self.total_pss_mb:.1f}MB | "
            f"Java: {self.java_heap_mb:.1f}MB | "
            f"Native: {self.native_heap_mb:.1f}MB"
        )


@dataclass
class MemoryReport:
    """Summary report of memory monitoring session."""
    package: str
    duration_seconds: float
    snapshots: List[MemorySnapshot] = field(default_factory=list)
    events: List[Dict] = field(default_factory=list)  # Tagged events (recompute, etc.)

    @property
    def min_pss_mb(self) -> float:
        if not self.snapshots:
            return 0
        return min(s.total_pss_mb for s in self.snapshots)

    @property
    def max_pss_mb(self) -> float:
        if not self.snapshots:
            return 0
        return max(s.total_pss_mb for s in self.snapshots)

    @property
    def avg_pss_mb(self) -> float:
        if not self.snapshots:
            return 0
        return sum(s.total_pss_mb for s in self.snapshots) / len(self.snapshots)

    @property
    def memory_growth_mb(self) -> float:
        """Memory growth from first to last snapshot."""
        if len(self.snapshots) < 2:
            return 0
        return self.snapshots[-1].total_pss_mb - self.snapshots[0].total_pss_mb

    @property
    def memory_growth_percent(self) -> float:
        """Percentage memory growth."""
        if len(self.snapshots) < 2 or self.snapshots[0].total_pss_mb == 0:
            return 0
        return (self.memory_growth_mb / self.snapshots[0].total_pss_mb) * 100

    def to_csv(self, path: Path) -> None:
        """Export snapshots to CSV."""
        with open(path, 'w') as f:
            f.write("timestamp,total_pss_kb,java_heap_kb,native_heap_kb,code_kb,graphics_kb\n")
            for s in self.snapshots:
                f.write(
                    f"{s.timestamp.isoformat()},{s.total_pss_kb},{s.java_heap_kb},"
                    f"{s.native_heap_kb},{s.code_kb},{s.graphics_kb}\n"
                )
        logger.info(f"Memory report saved to: {path}")

    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            "=" * 50,
            f"MEMORY REPORT: {self.package}",
            "=" * 50,
            f"Duration: {self.duration_seconds:.1f}s",
            f"Samples: {len(self.snapshots)}",
            f"",
            f"PSS Memory:",
            f"  Min: {self.min_pss_mb:.1f} MB",
            f"  Max: {self.max_pss_mb:.1f} MB",
            f"  Avg: {self.avg_pss_mb:.1f} MB",
            f"  Growth: {self.memory_growth_mb:+.1f} MB ({self.memory_growth_percent:+.1f}%)",
            f"",
        ]

        if self.events:
            lines.append(f"Events: {len(self.events)}")
            for event in self.events[-10:]:  # Last 10 events
                lines.append(f"  [{event['timestamp']}] {event['type']}: {event.get('details', '')}")

        lines.append("=" * 50)
        return "\n".join(lines)


class MemoryMonitor:
    """
    Continuous memory monitoring for Android apps.

    Usage:
        monitor = MemoryMonitor("com.roadlords.android", device_id="...")
        monitor.start(interval_seconds=2)

        # ... run your test ...

        report = monitor.stop()
        print(report.summary())
    """

    def __init__(self, package: str, device_id: Optional[str] = None):
        """
        Initialize memory monitor.

        Args:
            package: Android package name to monitor
            device_id: ADB device ID (optional if only one device)
        """
        self.package = package
        self.device_id = device_id
        self._snapshots: List[MemorySnapshot] = []
        self._events: List[Dict] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[datetime] = None
        self._on_snapshot: Optional[Callable[[MemorySnapshot], None]] = None

    def _adb_cmd(self, *args) -> str:
        """Execute ADB command."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout

    def get_memory_info(self) -> Optional[MemorySnapshot]:
        """
        Get current memory info for package.

        Returns:
            MemorySnapshot or None if failed
        """
        try:
            output = self._adb_cmd("shell", "dumpsys", "meminfo", self.package)
            return self._parse_meminfo(output)
        except Exception as e:
            logger.warning(f"Failed to get memory info: {e}")
            return None

    def _parse_meminfo(self, output: str) -> Optional[MemorySnapshot]:
        """Parse dumpsys meminfo output."""
        if not output or "No process found" in output:
            return None

        # Parse the summary table
        # Example line: "  TOTAL PSS:   123456"
        patterns = {
            'total_pss': r'TOTAL\s+PSS:\s+(\d+)',
            'total_rss': r'TOTAL\s+RSS:\s+(\d+)',
            'java_heap': r'Java Heap:\s+(\d+)',
            'native_heap': r'Native Heap:\s+(\d+)',
            'code': r'Code:\s+(\d+)',
            'stack': r'Stack:\s+(\d+)',
            'graphics': r'Graphics:\s+(\d+)',
            'private_other': r'Private Other:\s+(\d+)',
            'system': r'System:\s+(\d+)',
        }

        values = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            values[key] = int(match.group(1)) if match else 0

        # Fallback: try to parse from TOTAL line in table format
        # "  TOTAL   12345   12345   12345   12345   12345   12345"
        if values['total_pss'] == 0:
            total_match = re.search(r'TOTAL\s+(\d+)', output)
            if total_match:
                values['total_pss'] = int(total_match.group(1))

        return MemorySnapshot(
            timestamp=datetime.now(),
            total_pss_kb=values['total_pss'],
            java_heap_kb=values['java_heap'],
            native_heap_kb=values['native_heap'],
            code_kb=values['code'],
            stack_kb=values['stack'],
            graphics_kb=values['graphics'],
            private_other_kb=values['private_other'],
            system_kb=values['system'],
        )

    def start(self, interval_seconds: float = 2.0, on_snapshot: Optional[Callable] = None) -> None:
        """
        Start continuous memory monitoring in background thread.

        Args:
            interval_seconds: How often to sample memory
            on_snapshot: Optional callback for each snapshot
        """
        if self._running:
            logger.warning("Monitor already running")
            return

        self._running = True
        self._start_time = datetime.now()
        self._snapshots = []
        self._events = []
        self._on_snapshot = on_snapshot

        def monitor_loop():
            while self._running:
                snapshot = self.get_memory_info()
                if snapshot:
                    self._snapshots.append(snapshot)
                    logger.debug(f"Memory: {snapshot}")
                    if self._on_snapshot:
                        self._on_snapshot(snapshot)
                time.sleep(interval_seconds)

        self._thread = threading.Thread(target=monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Memory monitoring started for {self.package}")

    def stop(self) -> MemoryReport:
        """
        Stop monitoring and return report.

        Returns:
            MemoryReport with all collected data
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

        duration = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0

        report = MemoryReport(
            package=self.package,
            duration_seconds=duration,
            snapshots=self._snapshots.copy(),
            events=self._events.copy(),
        )

        logger.info(f"Memory monitoring stopped. Collected {len(self._snapshots)} samples.")
        return report

    def add_event(self, event_type: str, details: str = "") -> None:
        """
        Add tagged event (e.g., recompute detected).

        Args:
            event_type: Type of event (e.g., "recompute", "memory_warning")
            details: Optional details
        """
        self._events.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details,
            "memory_mb": self._snapshots[-1].total_pss_mb if self._snapshots else 0
        })
        logger.info(f"Event: {event_type} - {details}")

    def snapshot_now(self) -> Optional[MemorySnapshot]:
        """Take immediate snapshot (useful for before/after comparisons)."""
        snapshot = self.get_memory_info()
        if snapshot:
            self._snapshots.append(snapshot)
        return snapshot


class LogcatMonitor:
    """
    Monitor logcat for specific patterns (e.g., route recompute).

    Usage:
        logcat = LogcatMonitor(device_id="...", patterns=["recompute", "recalculate"])
        logcat.start()

        # ... run test ...

        matches = logcat.stop()
        print(f"Found {len(matches)} recompute events")
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        patterns: Optional[List[str]] = None,
        package_filter: Optional[str] = None
    ):
        """
        Initialize logcat monitor.

        Args:
            device_id: ADB device ID
            patterns: Regex patterns to match (case-insensitive)
            package_filter: Filter logs by package (e.g., "com.roadlords")
        """
        self.device_id = device_id
        self.patterns = patterns or ["recompute", "recalculate", "reroute", "route.*calc"]
        self.package_filter = package_filter
        self._matches: List[Dict] = []
        self._running = False
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._on_match: Optional[Callable[[Dict], None]] = None

    def start(self, on_match: Optional[Callable[[Dict], None]] = None) -> None:
        """
        Start monitoring logcat.

        Args:
            on_match: Callback when pattern matches
        """
        if self._running:
            return

        self._running = True
        self._matches = []
        self._on_match = on_match

        # Clear logcat first
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["logcat", "-c"])
        subprocess.run(cmd, capture_output=True)

        # Start logcat process
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["logcat", "-v", "time"])

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        def read_loop():
            compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]

            while self._running and self._process.poll() is None:
                line = self._process.stdout.readline()
                if not line:
                    continue

                # Optional package filter
                if self.package_filter and self.package_filter not in line:
                    continue

                # Check patterns
                for pattern in compiled_patterns:
                    if pattern.search(line):
                        match = {
                            "timestamp": datetime.now().isoformat(),
                            "pattern": pattern.pattern,
                            "line": line.strip()[:200]  # Truncate long lines
                        }
                        self._matches.append(match)
                        logger.info(f"Logcat match: {pattern.pattern}")

                        if self._on_match:
                            self._on_match(match)
                        break

        self._thread = threading.Thread(target=read_loop, daemon=True)
        self._thread.start()
        logger.info("Logcat monitoring started")

    def stop(self) -> List[Dict]:
        """
        Stop monitoring and return matches.

        Returns:
            List of matched log entries
        """
        self._running = False

        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)

        if self._thread:
            self._thread.join(timeout=5)

        logger.info(f"Logcat monitoring stopped. Found {len(self._matches)} matches.")
        return self._matches.copy()

    @property
    def match_count(self) -> int:
        """Get current number of matches."""
        return len(self._matches)
