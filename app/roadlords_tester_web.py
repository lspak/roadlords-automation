#!/usr/bin/env python3
"""
Roadlords Test Runner - Web UI version.
Opens in your browser - no tkinter needed.
"""

import subprocess
import threading
import os
import sys
import time
import webbrowser
import json
from pathlib import Path
from flask import Flask, render_template_string, jsonify, Response

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
TEST_FILE = PROJECT_ROOT / "tests" / "e2e" / "test_navigation_route_following.py"
REPORTS_DIR = PROJECT_ROOT / "reports" / "e2e"

app = Flask(__name__)

# Global state
test_output = []
test_running = False
test_finished = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Roadlords Test Runner</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status-panel {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .status-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .status-row:last-child { border-bottom: none; }
        .status-label { font-weight: 500; }
        .status-value { font-weight: bold; }
        .status-ok { color: #00ff88; }
        .status-error { color: #ff4757; }
        .status-warning { color: #ffa502; }
        .buttons {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        button {
            padding: 15px 30px;
            font-size: 16px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        button:hover { transform: translateY(-2px); }
        button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-primary {
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            color: #1a1a2e;
        }
        .btn-secondary {
            background: rgba(255,255,255,0.2);
            color: #fff;
        }
        .btn-success {
            background: #00ff88;
            color: #1a1a2e;
        }
        .log-panel {
            background: #0a0a15;
            border-radius: 15px;
            padding: 20px;
            height: 400px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            line-height: 1.6;
        }
        .log-line { padding: 2px 0; }
        .log-info { color: #aaa; }
        .log-success { color: #00ff88; }
        .log-error { color: #ff4757; }
        .log-warning { color: #ffa502; }
        .progress {
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            width: 0%;
            transition: width 0.3s;
        }
        .progress-bar.running {
            width: 100%;
            animation: progress-animation 2s linear infinite;
            background-size: 200% 100%;
            background-image: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
        }
        @keyframes progress-animation {
            0% { background-position: 200% 0; }
            100% { background-position: 0 0; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚛 Roadlords Test Runner</h1>

        <div class="status-panel">
            <div class="status-row">
                <span class="status-label">📱 Android Device</span>
                <span class="status-value" id="device-status">Checking...</span>
            </div>
            <div class="status-row">
                <span class="status-label">⚙️ Appium Server</span>
                <span class="status-value" id="appium-status">Checking...</span>
            </div>
        </div>

        <div class="progress">
            <div class="progress-bar" id="progress"></div>
        </div>

        <div class="buttons">
            <button class="btn-secondary" onclick="checkStatus()">🔄 Refresh</button>
            <button class="btn-secondary" onclick="startAppium()" id="appium-btn">▶️ Start Appium</button>
            <button class="btn-primary" onclick="runTest()" id="run-btn" disabled>🚀 Run Test</button>
            <button class="btn-success" onclick="openReport()" id="report-btn" disabled>📊 Open Report</button>
        </div>

        <div class="log-panel" id="log"></div>
    </div>

    <script>
        let testRunning = false;

        function log(message, type = 'info') {
            const logDiv = document.getElementById('log');
            const line = document.createElement('div');
            line.className = 'log-line log-' + type;
            const time = new Date().toLocaleTimeString();
            line.textContent = '[' + time + '] ' + message;
            logDiv.appendChild(line);
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function checkStatus() {
            log('Checking status...');
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    const deviceEl = document.getElementById('device-status');
                    const appiumEl = document.getElementById('appium-status');
                    const runBtn = document.getElementById('run-btn');

                    if (data.device) {
                        deviceEl.textContent = '✅ Connected (' + data.device + ')';
                        deviceEl.className = 'status-value status-ok';
                        log('Device found: ' + data.device, 'success');
                    } else {
                        deviceEl.textContent = '❌ Not connected';
                        deviceEl.className = 'status-value status-error';
                        log('No device connected', 'warning');
                    }

                    if (data.appium) {
                        appiumEl.textContent = '✅ Running';
                        appiumEl.className = 'status-value status-ok';
                        log('Appium is running', 'success');
                    } else {
                        appiumEl.textContent = '❌ Not running';
                        appiumEl.className = 'status-value status-error';
                        log('Appium not running', 'warning');
                    }

                    runBtn.disabled = !data.device || !data.appium || testRunning;

                    if (data.has_report) {
                        document.getElementById('report-btn').disabled = false;
                    }
                });
        }

        function startAppium() {
            log('Starting Appium server...');
            fetch('/start-appium', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    log(data.message, data.success ? 'success' : 'error');
                    setTimeout(checkStatus, 3000);
                });
        }

        function runTest() {
            if (testRunning) return;
            testRunning = true;
            document.getElementById('run-btn').disabled = true;
            document.getElementById('progress').className = 'progress-bar running';
            document.getElementById('log').innerHTML = '';

            log('========================================', 'info');
            log('Starting E2E test...', 'info');
            log('========================================', 'info');

            const eventSource = new EventSource('/run-test');

            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                if (data.line) {
                    let type = 'info';
                    if (data.line.includes('ERROR') || data.line.includes('FAILED')) type = 'error';
                    else if (data.line.includes('ARRIVED') || data.line.includes('PASS') || data.line.includes('SUCCESS')) type = 'success';
                    else if (data.line.includes('WARNING')) type = 'warning';
                    log(data.line, type);
                }
                if (data.finished) {
                    testRunning = false;
                    document.getElementById('run-btn').disabled = false;
                    document.getElementById('progress').className = 'progress-bar';
                    document.getElementById('report-btn').disabled = false;
                    log('========================================', data.success ? 'success' : 'error');
                    log(data.success ? 'TEST COMPLETED!' : 'TEST FAILED', data.success ? 'success' : 'error');
                    log('========================================', data.success ? 'success' : 'error');
                    eventSource.close();
                    if (data.success) {
                        setTimeout(openReport, 1000);
                    }
                }
            };

            eventSource.onerror = function() {
                testRunning = false;
                document.getElementById('run-btn').disabled = false;
                document.getElementById('progress').className = 'progress-bar';
                log('Connection lost', 'error');
                eventSource.close();
                checkStatus();
            };
        }

        function openReport() {
            fetch('/open-report', {method: 'POST'})
                .then(r => r.json())
                .then(data => log(data.message, data.success ? 'success' : 'warning'));
        }

        // Initial check
        checkStatus();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    # Check device
    device = None
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        devices = [l for l in lines[1:] if l.strip() and "device" in l and "offline" not in l]
        if devices:
            device = devices[0].split()[0]
    except:
        pass

    # Check Appium
    appium = False
    try:
        result = subprocess.run(["pgrep", "-f", "appium"], capture_output=True, timeout=5)
        appium = result.returncode == 0
    except:
        pass

    # Check for reports
    has_report = False
    if REPORTS_DIR.exists():
        reports = list(REPORTS_DIR.glob("stress_report_*.html"))
        has_report = len(reports) > 0

    return jsonify({"device": device, "appium": appium, "has_report": has_report})

@app.route('/start-appium', methods=['POST'])
def start_appium():
    try:
        subprocess.run(["pkill", "-f", "appium"], capture_output=True)
        time.sleep(1)
        subprocess.Popen(
            ["appium", "--allow-insecure", "chromedriver_autodownload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return jsonify({"success": True, "message": "Appium starting..."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/run-test')
def run_test():
    def generate():
        try:
            os.chdir(PROJECT_ROOT)
            venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
            python_cmd = str(venv_python) if venv_python.exists() else sys.executable

            process = subprocess.Popen(
                [python_cmd, str(TEST_FILE)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(PROJECT_ROOT)
            )

            for line in iter(process.stdout.readline, ''):
                if line:
                    yield f"data: {json.dumps({'line': line.rstrip()})}\n\n"

            process.wait()
            success = process.returncode == 0
            yield f"data: {json.dumps({'finished': True, 'success': success})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'line': f'Error: {e}', 'finished': True, 'success': False})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/open-report', methods=['POST'])
def open_report():
    if REPORTS_DIR.exists():
        reports = list(REPORTS_DIR.glob("stress_report_*.html"))
        if reports:
            latest = max(reports, key=lambda p: p.stat().st_mtime)
            webbrowser.open(f"file://{latest}")
            return jsonify({"success": True, "message": f"Opened: {latest.name}"})
    return jsonify({"success": False, "message": "No report found"})

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Roadlords Test Runner")
    print("="*50)
    print("\nOpening browser at http://localhost:5050")
    print("Press Ctrl+C to stop\n")

    # Open browser after short delay
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5050")).start()

    app.run(host='127.0.0.1', port=5050, debug=False, threaded=True)
