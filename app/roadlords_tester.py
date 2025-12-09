#!/usr/bin/env python3
"""
Roadlords Test Runner - Simple GUI for running E2E tests.

Double-click to run, connect your phone, and click "Run Test".
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import os
import sys
import time
import webbrowser
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
TEST_FILE = PROJECT_ROOT / "tests" / "e2e" / "test_navigation_route_following.py"
REPORTS_DIR = PROJECT_ROOT / "reports" / "e2e"


class RoadlordsTestRunner:
    def __init__(self, root):
        self.root = root
        self.root.title("Roadlords Test Runner")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        # Status variables
        self.device_connected = False
        self.appium_running = False
        self.test_running = False
        self.latest_report = None

        self.setup_ui()
        self.check_status()

    def setup_ui(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(main_frame, text="Roadlords E2E Test Runner", font=("Helvetica", 18, "bold"))
        title.pack(pady=(0, 15))

        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # Device status
        device_row = ttk.Frame(status_frame)
        device_row.pack(fill=tk.X, pady=2)
        ttk.Label(device_row, text="Android Device:").pack(side=tk.LEFT)
        self.device_status = ttk.Label(device_row, text="Checking...", foreground="gray")
        self.device_status.pack(side=tk.LEFT, padx=(10, 0))

        # Appium status
        appium_row = ttk.Frame(status_frame)
        appium_row.pack(fill=tk.X, pady=2)
        ttk.Label(appium_row, text="Appium Server:").pack(side=tk.LEFT)
        self.appium_status = ttk.Label(appium_row, text="Checking...", foreground="gray")
        self.appium_status.pack(side=tk.LEFT, padx=(10, 0))

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        # Refresh button
        self.refresh_btn = ttk.Button(button_frame, text="Refresh Status", command=self.check_status)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Start Appium button
        self.appium_btn = ttk.Button(button_frame, text="Start Appium", command=self.start_appium)
        self.appium_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Run test button
        self.run_btn = ttk.Button(button_frame, text="Run Test", command=self.run_test, state=tk.DISABLED)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Open report button
        self.report_btn = ttk.Button(button_frame, text="Open Last Report", command=self.open_report, state=tk.DISABLED)
        self.report_btn.pack(side=tk.LEFT)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))

        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Courier", 11))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure tags for colored output
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")

    def log(self, message, tag="info"):
        """Add message to log with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)

    def check_status(self):
        """Check device and Appium status."""
        self.log("Checking status...")

        # Check device in background
        threading.Thread(target=self._check_device, daemon=True).start()
        threading.Thread(target=self._check_appium, daemon=True).start()

    def _check_device(self):
        """Check if Android device is connected."""
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split("\n")
            # Filter out header and empty lines
            devices = [l for l in lines[1:] if l.strip() and "device" in l and "offline" not in l]

            if devices:
                device_id = devices[0].split()[0]
                self.device_connected = True
                self.root.after(0, lambda: self.device_status.config(
                    text=f"Connected ({device_id})", foreground="green"))
                self.root.after(0, lambda: self.log(f"Device found: {device_id}", "success"))
            else:
                self.device_connected = False
                self.root.after(0, lambda: self.device_status.config(
                    text="Not connected", foreground="red"))
                self.root.after(0, lambda: self.log("No device connected. Please connect your Android phone.", "warning"))
        except Exception as e:
            self.device_connected = False
            self.root.after(0, lambda: self.device_status.config(
                text="Error checking", foreground="red"))
            self.root.after(0, lambda: self.log(f"Error checking device: {e}", "error"))

        self.root.after(0, self._update_buttons)

    def _check_appium(self):
        """Check if Appium server is running."""
        try:
            result = subprocess.run(["pgrep", "-f", "appium"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.appium_running = True
                self.root.after(0, lambda: self.appium_status.config(
                    text="Running", foreground="green"))
                self.root.after(0, lambda: self.log("Appium server is running", "success"))
            else:
                self.appium_running = False
                self.root.after(0, lambda: self.appium_status.config(
                    text="Not running", foreground="red"))
                self.root.after(0, lambda: self.log("Appium not running. Click 'Start Appium' to start.", "warning"))
        except Exception as e:
            self.appium_running = False
            self.root.after(0, lambda: self.appium_status.config(
                text="Error checking", foreground="red"))

        self.root.after(0, self._update_buttons)

    def _update_buttons(self):
        """Update button states based on status."""
        if self.test_running:
            self.run_btn.config(state=tk.DISABLED)
            self.appium_btn.config(state=tk.DISABLED)
        else:
            if self.device_connected and self.appium_running:
                self.run_btn.config(state=tk.NORMAL)
            else:
                self.run_btn.config(state=tk.DISABLED)
            self.appium_btn.config(state=tk.NORMAL)

        # Check for existing reports
        if REPORTS_DIR.exists():
            reports = list(REPORTS_DIR.glob("stress_report_*.html"))
            if reports:
                self.latest_report = max(reports, key=lambda p: p.stat().st_mtime)
                self.report_btn.config(state=tk.NORMAL)

    def start_appium(self):
        """Start Appium server."""
        self.log("Starting Appium server...")

        def _start():
            try:
                # Kill existing appium
                subprocess.run(["pkill", "-f", "appium"], capture_output=True)
                time.sleep(1)

                # Start appium in background
                subprocess.Popen(
                    ["appium", "--allow-insecure", "chromedriver_autodownload"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

                # Wait for startup
                time.sleep(3)
                self.root.after(0, lambda: self.log("Appium started!", "success"))
                self.root.after(0, self.check_status)

            except Exception as e:
                self.root.after(0, lambda: self.log(f"Failed to start Appium: {e}", "error"))

        threading.Thread(target=_start, daemon=True).start()

    def run_test(self):
        """Run the E2E test."""
        if self.test_running:
            return

        self.test_running = True
        self.run_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self.log("=" * 50)
        self.log("Starting E2E test...", "info")
        self.log("=" * 50)

        def _run():
            try:
                # Change to project directory
                os.chdir(PROJECT_ROOT)

                # Activate venv and run test
                env = os.environ.copy()
                venv_python = PROJECT_ROOT / "venv" / "bin" / "python"

                if venv_python.exists():
                    python_cmd = str(venv_python)
                else:
                    python_cmd = sys.executable

                process = subprocess.Popen(
                    [python_cmd, str(TEST_FILE)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(PROJECT_ROOT)
                )

                # Read output line by line
                for line in iter(process.stdout.readline, ''):
                    if line:
                        line = line.rstrip()
                        # Determine tag based on content
                        if "ERROR" in line or "FAILED" in line:
                            tag = "error"
                        elif "ARRIVED" in line or "SUCCESS" in line or "PASS" in line:
                            tag = "success"
                        elif "WARNING" in line:
                            tag = "warning"
                        else:
                            tag = "info"
                        self.root.after(0, lambda l=line, t=tag: self.log(l, t))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log("=" * 50, "success"))
                    self.root.after(0, lambda: self.log("TEST COMPLETED SUCCESSFULLY!", "success"))
                    self.root.after(0, lambda: self.log("=" * 50, "success"))
                else:
                    self.root.after(0, lambda: self.log("=" * 50, "error"))
                    self.root.after(0, lambda: self.log(f"TEST FAILED (exit code: {process.returncode})", "error"))
                    self.root.after(0, lambda: self.log("=" * 50, "error"))

            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error running test: {e}", "error"))
            finally:
                self.root.after(0, self._test_finished)

        threading.Thread(target=_run, daemon=True).start()

    def _test_finished(self):
        """Called when test finishes."""
        self.test_running = False
        self.progress.stop()
        self._update_buttons()

        # Find and open latest report
        if REPORTS_DIR.exists():
            reports = list(REPORTS_DIR.glob("stress_report_*.html"))
            if reports:
                self.latest_report = max(reports, key=lambda p: p.stat().st_mtime)
                self.report_btn.config(state=tk.NORMAL)

                # Ask to open report
                self.log(f"Report saved: {self.latest_report.name}")
                self.log("Opening report...", "success")
                self.open_report()

    def open_report(self):
        """Open the latest report in browser."""
        if self.latest_report and self.latest_report.exists():
            webbrowser.open(f"file://{self.latest_report}")
            self.log(f"Opened report: {self.latest_report.name}", "success")
        else:
            self.log("No report found", "warning")


def main():
    root = tk.Tk()

    # Set app icon (optional)
    try:
        # For macOS, we could set the icon here
        pass
    except:
        pass

    app = RoadlordsTestRunner(root)
    root.mainloop()


if __name__ == "__main__":
    main()
