"""
Report Generator for Stress Tests

Generates visual HTML reports with:
- Memory usage charts
- Key statistics
- Screenshots gallery
- Pass/Fail verdict
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
import base64


@dataclass
class StressTestResult:
    """Results from a stress test run."""
    test_name: str
    start_time: datetime
    duration_seconds: float

    # Memory metrics
    initial_memory_mb: float
    final_memory_mb: float
    peak_memory_mb: float
    memory_growth_mb: float
    memory_growth_percent: float
    memory_samples: List[Dict]  # [{timestamp, pss_mb, elapsed_s}, ...]

    # Recompute metrics
    baseline_recomputes: int
    deviation_recomputes: int
    total_recomputes: int
    recompute_events: List[Dict]  # [{time, pattern, line}, ...]

    # Test phases
    baseline_duration_s: int
    deviation_duration_s: int

    # Screenshots
    screenshots: List[Path]

    # Video
    video_path: Optional[Path] = None

    # Verdict
    passed: bool = True
    verdict_reason: str = ""


def generate_ui_verification_html(ui_verifier) -> str:
    """Generate HTML for UI verification screenshots comparison."""
    if not ui_verifier:
        return ""

    # Checkpoint descriptions
    checkpoint_info = {
        "search_opened": {
            "title": "Search Bar Opened",
            "icon": "🔍",
            "description": "Verifies that search input field is visible and accessible",
            "what_tested": ["Search bar presence", "Text input field", "UI layout consistency"]
        },
        "search_results": {
            "title": "Search Results Display",
            "icon": "📋",
            "description": "Validates search results layout and result items",
            "what_tested": ["Results list visibility", "Distance labels", "Result items layout"]
        },
        "destination_selected": {
            "title": "Destination Selected",
            "icon": "📍",
            "description": "Checks destination detail panel and action buttons",
            "what_tested": ["'Get directions' button", "Destination info panel", "Address display"]
        },
        "navigation_started": {
            "title": "Navigation Active",
            "icon": "🧭",
            "description": "Verifies navigation UI elements during active navigation",
            "what_tested": ["Navigation instructions", "Distance to turn", "Speed indicator", "Navigation header"]
        },
        "arrived": {
            "title": "Arrival Dialog",
            "icon": "🎯",
            "description": "Validates arrival confirmation dialog and buttons",
            "what_tested": ["'You've reached destination' message", "'Close' button", "Feedback dialog"]
        }
    }

    html = ""
    checkpoints = ["search_opened", "search_results", "destination_selected", "navigation_started", "arrived"]

    for checkpoint in checkpoints:
        if checkpoint not in ui_verifier.current_screenshots:
            continue

        current_screenshot = ui_verifier.current_screenshots[checkpoint]
        if not current_screenshot or not current_screenshot.exists():
            continue

        # Find baseline screenshot
        baseline_screenshot = None
        for pattern in [f"{checkpoint}_*.png", f"{checkpoint}.png"]:
            matches = list(ui_verifier.baseline_dir.glob(pattern))
            if matches:
                baseline_screenshot = matches[0]
                break

        if not baseline_screenshot or not baseline_screenshot.exists():
            continue

        # Read and encode screenshots as base64
        with open(baseline_screenshot, 'rb') as f:
            baseline_img_data = base64.b64encode(f.read()).decode('utf-8')

        with open(current_screenshot, 'rb') as f:
            current_img_data = base64.b64encode(f.read()).decode('utf-8')

        # Get checkpoint info
        info = checkpoint_info.get(checkpoint, {
            "title": checkpoint.replace('_', ' ').title(),
            "icon": "📱",
            "description": "UI verification checkpoint",
            "what_tested": []
        })

        # Get verification results for this checkpoint
        verification_status = "✅ PASS"
        verification_details = []
        if ui_verifier.verification_results:
            checkpoint_results = [r for r in ui_verifier.verification_results if r.checkpoint == checkpoint]
            failed_checks = [r for r in checkpoint_results if not r.passed]

            if failed_checks:
                verification_status = f"❌ FAIL ({len(failed_checks)} issues)"
                for check in failed_checks:
                    verification_details.append(f"• {check.element_name}: {check.details}")
            else:
                passed_count = len(checkpoint_results)
                if passed_count > 0:
                    verification_status = f"✅ PASS ({passed_count}/{passed_count} checks)"

        verification_html = ""
        if verification_details:
            verification_html = f'''
            <div style="background: rgba(255,0,0,0.1); padding: 10px; border-radius: 4px; margin-top: 10px;">
                <strong style="color: #ff6b6b;">Issues Found:</strong><br>
                {'<br>'.join(verification_details)}
            </div>
            '''

        # Build what's tested list
        tested_items_html = "".join([f"<li>{item}</li>" for item in info['what_tested']])

        html += f'''
        <div class="ui-checkpoint" style="margin-bottom: 40px; padding: 25px; background: rgba(255,255,255,0.05); border-radius: 8px; border-left: 4px solid #4CAF50;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h4 style="color: #fff; margin: 0; font-size: 1.3em;">
                    {info['icon']} {info['title']}
                </h4>
                <span style="background: rgba(76,175,80,0.2); color: #4CAF50; padding: 5px 15px; border-radius: 20px; font-size: 0.9em; font-weight: bold;">
                    {verification_status}
                </span>
            </div>

            <p style="color: #bbb; margin-bottom: 15px; font-size: 0.95em;">
                {info['description']}
            </p>

            <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 5px; margin-bottom: 15px;">
                <strong style="color: #888; font-size: 0.9em;">What's Tested:</strong>
                <ul style="margin: 8px 0 0 20px; color: #aaa; font-size: 0.9em;">
                    {tested_items_html}
                </ul>
            </div>

            {verification_html}

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div style="text-align: center;">
                    <div style="background: rgba(0,100,200,0.2); padding: 8px; border-radius: 5px 5px 0 0;">
                        <strong style="color: #64B5F6; font-size: 0.9em;">📸 Baseline (Expected)</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 0 0 5px 5px;">
                        <img src="data:image/png;base64,{baseline_img_data}"
                             id="baseline_{checkpoint}"
                             style="max-width: 100%; height: auto; border: 2px solid #555; border-radius: 4px; cursor: pointer; transition: transform 0.2s;"
                             onclick="openImageInNewTab('baseline_{checkpoint}')"
                             onmouseover="this.style.transform='scale(1.02)'"
                             onmouseout="this.style.transform='scale(1)'"
                             alt="Baseline"
                             title="Click to open in new tab">
                        <p style="color: #888; font-size: 0.85em; margin-top: 8px;">Click to enlarge</p>
                    </div>
                </div>
                <div style="text-align: center;">
                    <div style="background: rgba(100,200,0,0.2); padding: 8px; border-radius: 5px 5px 0 0;">
                        <strong style="color: #AED581; font-size: 0.9em;">📸 Current Run (Actual)</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 0 0 5px 5px;">
                        <img src="data:image/png;base64,{current_img_data}"
                             id="current_{checkpoint}"
                             style="max-width: 100%; height: auto; border: 2px solid #555; border-radius: 4px; cursor: pointer; transition: transform 0.2s;"
                             onclick="openImageInNewTab('current_{checkpoint}')"
                             onmouseover="this.style.transform='scale(1.02)'"
                             onmouseout="this.style.transform='scale(1)'"
                             alt="Current"
                             title="Click to open in new tab">
                        <p style="color: #888; font-size: 0.85em; margin-top: 8px;">Click to enlarge</p>
                    </div>
                </div>
            </div>
        </div>
        '''

    return html


def generate_html_report(result: StressTestResult, output_path: Path, ui_verifier=None) -> Path:
    """Generate a comprehensive HTML report."""

    # Prepare memory chart data with time in seconds
    memory_labels = []
    memory_values = []
    for i, sample in enumerate(result.memory_samples):
        # Use elapsed_s if available, otherwise calculate from sample index
        elapsed = sample.get('elapsed_s', i)
        memory_labels.append(elapsed)
        memory_values.append(sample.get('pss_mb', 0))

    # Prepare video HTML
    video_html = ""
    if result.video_path and result.video_path.exists():
        # Embed video with base64 for portability (if small enough) or link
        video_size_mb = result.video_path.stat().st_size / (1024 * 1024)
        if video_size_mb < 100:  # Embed if < 100MB
            with open(result.video_path, 'rb') as f:
                video_data = base64.b64encode(f.read()).decode('utf-8')
            video_html = f'''
            <div class="video-container">
                <h3 class="section-title">🎬 Test Recording</h3>
                <p class="video-info">Scroll the video to correlate with memory chart timestamps. Baseline ends at {result.baseline_duration_s}s.</p>
                <video controls width="100%">
                    <source src="data:video/mp4;base64,{video_data}" type="video/mp4">
                    Your browser does not support video playback.
                </video>
            </div>
            '''
        else:
            video_html = f'''
            <div class="video-container">
                <h3 class="section-title">🎬 Test Recording</h3>
                <p class="video-info">Video file: <a href="file://{result.video_path}">{result.video_path.name}</a> ({video_size_mb:.1f} MB)</p>
            </div>
            '''

    # Prepare screenshots HTML
    screenshots_html = ""

    # Use UI verification if available
    if ui_verifier:
        screenshots_html = generate_ui_verification_html(ui_verifier)
    else:
        # Fallback to regular screenshots
        for screenshot in result.screenshots[-12:]:  # Last 12 screenshots
            if screenshot.exists():
                # Embed as base64 for portability
                with open(screenshot, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode('utf-8')
                screenshots_html += f'''
                <div class="screenshot">
                    <img src="data:image/png;base64,{img_data}" alt="{screenshot.name}">
                    <p>{screenshot.name}</p>
                </div>
                '''

    # Determine status colors
    if result.passed:
        status_class = "pass"
        status_icon = "✅"
        status_text = "PASSED"
    elif result.memory_growth_percent > 30:
        status_class = "fail"
        status_icon = "❌"
        status_text = "FAILED"
    else:
        status_class = "warning"
        status_icon = "⚠️"
        status_text = "WARNING"

    # Calculate baseline marker position (percentage of total samples)
    total_samples = len(result.memory_samples)
    baseline_samples = int(result.baseline_duration_s / (result.baseline_duration_s + result.deviation_duration_s) * total_samples) if total_samples > 0 else 0

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stress Test Report - {result.test_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 10px;
            color: #fff;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }}
        .status-banner {{
            text-align: center;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            font-size: 24px;
            font-weight: bold;
        }}
        .status-banner.pass {{
            background: linear-gradient(135deg, #1b4332, #2d6a4f);
            border: 2px solid #40916c;
        }}
        .status-banner.fail {{
            background: linear-gradient(135deg, #641220, #85182a);
            border: 2px solid #a4161a;
        }}
        .status-banner.warning {{
            background: linear-gradient(135deg, #7f4f24, #936639);
            border: 2px solid #b08968;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #0f3460;
        }}
        .card h3 {{
            color: #e94560;
            margin-bottom: 15px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #0f3460;
        }}
        .metric:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}
        .metric-label {{
            color: #888;
        }}
        .metric-value {{
            font-weight: bold;
            color: #fff;
        }}
        .metric-value.positive {{
            color: #40916c;
        }}
        .metric-value.negative {{
            color: #e94560;
        }}
        .chart-container {{
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid #0f3460;
        }}
        .chart-title {{
            color: #e94560;
            margin-bottom: 15px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .screenshots-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .screenshot {{
            background: #16213e;
            border-radius: 10px;
            padding: 10px;
            border: 1px solid #0f3460;
        }}
        .screenshot img {{
            width: 100%;
            border-radius: 5px;
        }}
        .screenshot p {{
            text-align: center;
            margin-top: 8px;
            font-size: 12px;
            color: #888;
        }}
        .section-title {{
            color: #e94560;
            margin: 30px 0 15px 0;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .events-list {{
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #0f3460;
            max-height: 300px;
            overflow-y: auto;
        }}
        .event-item {{
            padding: 10px;
            margin-bottom: 10px;
            background: #0f3460;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
        }}
        .no-events {{
            color: #888;
            text-align: center;
            padding: 20px;
        }}
        .video-container {{
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid #0f3460;
        }}
        .video-container video {{
            border-radius: 8px;
            margin-top: 10px;
        }}
        .video-info {{
            color: #888;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #0f3460;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚛 Roadlords Stress Test Report</h1>
        <p class="subtitle">{result.test_name} | {result.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="status-banner {status_class}">
            {status_icon} {status_text}: {result.verdict_reason}
        </div>

        <div class="cards">
            <div class="card">
                <h3>📊 Memory Summary</h3>
                <div class="metric">
                    <span class="metric-label">Initial</span>
                    <span class="metric-value">{result.initial_memory_mb:.1f} MB</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Final</span>
                    <span class="metric-value">{result.final_memory_mb:.1f} MB</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Peak</span>
                    <span class="metric-value">{result.peak_memory_mb:.1f} MB</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Growth</span>
                    <span class="metric-value {'negative' if result.memory_growth_percent > 15 else 'positive'}">{result.memory_growth_mb:+.1f} MB ({result.memory_growth_percent:+.1f}%)</span>
                </div>
            </div>

            <div class="card">
                <h3>⏱️ Test Duration</h3>
                <div class="metric">
                    <span class="metric-label">Total Navigation</span>
                    <span class="metric-value">{result.duration_seconds:.0f}s</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Memory Samples</span>
                    <span class="metric-value">{len(result.memory_samples)}</span>
                </div>
            </div>
        </div>

        <div class="chart-container">
            <h3 class="chart-title">Memory Usage Over Time</h3>
            <p style="color: #888; font-size: 12px; margin-bottom: 10px;">📊 Memory usage during navigation - correlate with video timestamp</p>
            <canvas id="memoryChart"></canvas>
        </div>

        {video_html}

        <h3 class="section-title">📸 UI Verification - Screenshots Comparison</h3>
        <div class="screenshots-grid">
            {screenshots_html if screenshots_html else '<p class="no-events">No screenshots available</p>'}
        </div>

        <footer>
            Generated by Roadlords Automation Framework | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@2.2.1/dist/chartjs-plugin-annotation.min.js"></script>
    <script>
        const ctx = document.getElementById('memoryChart').getContext('2d');
        const baselineEndSeconds = {result.baseline_duration_s};

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(memory_labels)},
                datasets: [{{
                    label: 'Memory (MB)',
                    data: {json.dumps(memory_values)},
                    borderColor: '#e94560',
                    backgroundColor: 'rgba(233, 69, 96, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                interaction: {{
                    intersect: false,
                    mode: 'index'
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        callbacks: {{
                            title: function(context) {{
                                return 'Time: ' + context[0].label + 's';
                            }},
                            label: function(context) {{
                                return 'Memory: ' + context.parsed.y.toFixed(1) + ' MB';
                            }}
                        }}
                    }},
                    annotation: {{
                        annotations: {{}}
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Time (seconds) - correlate with video',
                            color: '#888'
                        }},
                        grid: {{
                            color: '#0f3460'
                        }},
                        ticks: {{
                            color: '#888',
                            callback: function(value) {{
                                return value + 's';
                            }}
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'Memory (MB)',
                            color: '#888'
                        }},
                        grid: {{
                            color: '#0f3460'
                        }},
                        ticks: {{
                            color: '#888'
                        }}
                    }}
                }}
            }}
        }});

        // Function to open image in new tab
        function openImageInNewTab(imgId) {{
            const img = document.getElementById(imgId);
            const newWindow = window.open('', '_blank');
            newWindow.document.write('<html><head><title>Screenshot</title><style>body{{margin:0;background:#000;display:flex;justify-content:center;align-items:center;min-height:100vh;}}img{{max-width:100%;height:auto;}}</style></head><body><img src="' + img.src + '"></body></html>');
            newWindow.document.close();
        }}
    </script>
</body>
</html>
'''

    output_path.write_text(html)
    return output_path


def generate_report_from_test_data(
    test_name: str,
    memory_csv_path: Path,
    screenshots_dir: Path,
    initial_memory: float,
    baseline_memory: float,
    peak_memory: float,
    baseline_recomputes: int,
    total_recomputes: int,
    recompute_events: List[Dict],
    baseline_duration: int,
    deviation_duration: int,
    output_dir: Path,
    video_path: Optional[Path] = None,
    ui_verifier=None
) -> Path:
    """Generate report from test data files."""

    # Load memory samples from CSV
    memory_samples = []
    first_timestamp = None
    if memory_csv_path.exists():
        import csv
        from datetime import datetime as dt
        with open(memory_csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # CSV has total_pss_kb, convert to MB
                pss_kb = float(row.get('total_pss_kb', 0))
                timestamp_str = row.get('timestamp', '')

                # Calculate elapsed seconds from first sample
                elapsed_s = len(memory_samples)  # Default to sample index
                if timestamp_str:
                    try:
                        ts = dt.fromisoformat(timestamp_str)
                        if first_timestamp is None:
                            first_timestamp = ts
                        elapsed_s = (ts - first_timestamp).total_seconds()
                    except:
                        pass

                memory_samples.append({
                    'timestamp': timestamp_str,
                    'pss_mb': pss_kb / 1024,  # Convert KB to MB
                    'elapsed_s': int(elapsed_s)
                })

    # Get screenshots
    screenshots = sorted(screenshots_dir.glob('*.png')) if screenshots_dir.exists() else []

    # Calculate metrics
    final_memory = memory_samples[-1]['pss_mb'] if memory_samples else initial_memory
    memory_growth = final_memory - initial_memory
    memory_growth_pct = (memory_growth / initial_memory * 100) if initial_memory > 0 else 0

    # Determine verdict
    if memory_growth_pct > 30:
        passed = False
        verdict = "Memory growth exceeds 30% threshold"
    elif memory_growth_pct > 15:
        passed = True
        verdict = "Memory growth elevated but acceptable"
    else:
        passed = True
        verdict = "Memory usage stable during stress test"

    result = StressTestResult(
        test_name=test_name,
        start_time=datetime.now(),
        duration_seconds=baseline_duration + deviation_duration,
        initial_memory_mb=initial_memory,
        final_memory_mb=final_memory,
        peak_memory_mb=peak_memory,
        memory_growth_mb=memory_growth,
        memory_growth_percent=memory_growth_pct,
        memory_samples=memory_samples,
        baseline_recomputes=baseline_recomputes,
        deviation_recomputes=total_recomputes - baseline_recomputes,
        total_recomputes=total_recomputes,
        recompute_events=recompute_events,
        baseline_duration_s=baseline_duration,
        deviation_duration_s=deviation_duration,
        screenshots=screenshots,
        video_path=video_path,
        passed=passed,
        verdict_reason=verdict
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"stress_report_{timestamp}.html"

    return generate_html_report(result, output_path, ui_verifier)
