"""
UI Verification - Visual regression testing for UI elements.

Captures baseline UI state and compares subsequent test runs against it.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """Represents a captured UI element."""
    name: str
    text: Optional[str]
    content_desc: Optional[str]
    class_name: str
    visible: bool
    enabled: bool
    bounds: Dict[str, int]  # x, y, width, height
    resource_id: Optional[str]
    checkpoint: str  # e.g., "search_opened", "navigation_started"


@dataclass
class UIRegion:
    """Represents a cropped region of the screen for visual comparison."""
    name: str
    checkpoint: str
    bounds: Dict[str, int]  # x, y, width, height
    screenshot_path: str


@dataclass
class VerificationResult:
    """Result of comparing a UI element or region."""
    checkpoint: str
    element_name: str
    passed: bool
    details: str
    baseline_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    similarity_score: Optional[float] = None  # For visual comparison (0-1)


class UIVerifier:
    """
    Captures and verifies UI elements across test runs.

    Usage:
        # First run - capture baseline
        verifier = UIVerifier(baseline_dir, mode="capture")
        verifier.capture_checkpoint(driver, "search_opened")
        verifier.add_element("search_bar", element)
        verifier.add_region("search_results", x=0, y=300, w=1440, h=500)
        verifier.save_baseline()

        # Subsequent runs - verify against baseline
        verifier = UIVerifier(baseline_dir, mode="verify")
        verifier.capture_checkpoint(driver, "search_opened")
        results = verifier.verify_checkpoint("search_opened")
    """

    def __init__(self, baseline_dir: Path, mode: str = "verify"):
        """
        Initialize UIVerifier.

        Args:
            baseline_dir: Directory to store/load baseline data
            mode: "capture" to create baseline, "verify" to compare against baseline
        """
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode

        # Current capture data (used in both modes)
        self.current_elements: Dict[str, List[UIElement]] = {}  # checkpoint -> elements
        self.current_regions: Dict[str, List[UIRegion]] = {}  # checkpoint -> regions
        self.current_screenshots: Dict[str, Path] = {}  # checkpoint -> screenshot path

        # Baseline data (loaded in verify mode)
        self.baseline_elements: Dict[str, List[UIElement]] = {}
        self.baseline_regions: Dict[str, List[UIRegion]] = {}

        # Verification results
        self.verification_results: List[VerificationResult] = []

        if mode == "verify":
            self._load_baseline()

    def _load_baseline(self):
        """Load baseline data from disk."""
        baseline_file = self.baseline_dir / "baseline.json"
        if not baseline_file.exists():
            raise FileNotFoundError(
                f"Baseline file not found: {baseline_file}. "
                f"Run test in 'capture' mode first to create baseline."
            )

        with open(baseline_file, 'r') as f:
            data = json.load(f)

        # Load elements
        for checkpoint, elements_data in data.get('elements', {}).items():
            self.baseline_elements[checkpoint] = [
                UIElement(**elem_data) for elem_data in elements_data
            ]

        # Load regions
        for checkpoint, regions_data in data.get('regions', {}).items():
            self.baseline_regions[checkpoint] = [
                UIRegion(**region_data) for region_data in regions_data
            ]

        logger.info(f"Loaded baseline with {len(self.baseline_elements)} checkpoints")

    def capture_checkpoint(self, driver, checkpoint: str, screenshot_name: Optional[str] = None):
        """
        Capture a checkpoint - take screenshot and prepare for element/region capture.

        Args:
            driver: Appium driver instance
            checkpoint: Checkpoint name (e.g., "search_opened")
            screenshot_name: Optional custom screenshot name
        """
        # Take screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_name = screenshot_name or f"{checkpoint}_{timestamp}"
        screenshot_path = self.baseline_dir / f"{screenshot_name}.png"

        driver.save_screenshot(str(screenshot_path))
        self.current_screenshots[checkpoint] = screenshot_path

        # Initialize checkpoint in dictionaries
        if checkpoint not in self.current_elements:
            self.current_elements[checkpoint] = []
        if checkpoint not in self.current_regions:
            self.current_regions[checkpoint] = []

        logger.info(f"Captured checkpoint: {checkpoint} → {screenshot_path}")

    def add_element(self, checkpoint: str, name: str, element) -> UIElement:
        """
        Add a UI element to the current checkpoint.

        Args:
            checkpoint: Checkpoint name
            name: Descriptive name for the element
            element: Appium WebElement

        Returns:
            UIElement object
        """
        try:
            bounds = element.rect
            ui_elem = UIElement(
                name=name,
                text=element.text if hasattr(element, 'text') else None,
                content_desc=element.get_attribute('content-desc'),
                class_name=element.get_attribute('class'),
                visible=element.is_displayed(),
                enabled=element.is_enabled(),
                bounds={
                    'x': bounds['x'],
                    'y': bounds['y'],
                    'width': bounds['width'],
                    'height': bounds['height']
                },
                resource_id=element.get_attribute('resource-id'),
                checkpoint=checkpoint
            )

            self.current_elements[checkpoint].append(ui_elem)
            logger.debug(f"Added element '{name}' to checkpoint '{checkpoint}'")
            return ui_elem

        except Exception as e:
            logger.warning(f"Failed to capture element '{name}': {e}")
            return None

    def add_region(self, checkpoint: str, name: str, x: int, y: int, width: int, height: int):
        """
        Add a visual region to compare (will be cropped from screenshot).

        Args:
            checkpoint: Checkpoint name
            name: Descriptive name for the region (e.g., "search_results_area")
            x, y, width, height: Region bounds
        """
        screenshot_path = self.current_screenshots.get(checkpoint)
        if not screenshot_path:
            logger.warning(f"No screenshot for checkpoint '{checkpoint}'. Call capture_checkpoint first.")
            return

        region = UIRegion(
            name=name,
            checkpoint=checkpoint,
            bounds={'x': x, 'y': y, 'width': width, 'height': height},
            screenshot_path=str(screenshot_path)
        )

        self.current_regions[checkpoint].append(region)

        # Crop and save region image
        region_path = self.baseline_dir / f"{checkpoint}_{name}_region.png"
        self._crop_and_save_region(screenshot_path, region.bounds, region_path)

        logger.debug(f"Added region '{name}' to checkpoint '{checkpoint}'")

    def _crop_and_save_region(self, screenshot_path: Path, bounds: Dict, output_path: Path):
        """Crop a region from screenshot and save it."""
        try:
            img = Image.open(screenshot_path)
            cropped = img.crop((
                bounds['x'],
                bounds['y'],
                bounds['x'] + bounds['width'],
                bounds['y'] + bounds['height']
            ))
            cropped.save(output_path)
        except Exception as e:
            logger.warning(f"Failed to crop region: {e}")

    def save_baseline(self):
        """Save captured baseline data to disk (call after all checkpoints captured)."""
        if self.mode != "capture":
            logger.warning("save_baseline() called but mode is not 'capture'")
            return

        baseline_data = {
            'captured_at': datetime.now().isoformat(),
            'elements': {
                checkpoint: [asdict(elem) for elem in elems]
                for checkpoint, elems in self.current_elements.items()
            },
            'regions': {
                checkpoint: [asdict(region) for region in regions]
                for checkpoint, regions in self.current_regions.items()
            }
        }

        baseline_file = self.baseline_dir / "baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)

        logger.info(f"Baseline saved: {baseline_file}")
        logger.info(f"  Checkpoints: {len(self.current_elements)}")
        logger.info(f"  Elements: {sum(len(e) for e in self.current_elements.values())}")
        logger.info(f"  Regions: {sum(len(r) for r in self.current_regions.values())}")

    def verify_checkpoint(self, checkpoint: str) -> List[VerificationResult]:
        """
        Verify a checkpoint against baseline.

        Args:
            checkpoint: Checkpoint name to verify

        Returns:
            List of verification results
        """
        if self.mode != "verify":
            logger.warning("verify_checkpoint() called but mode is not 'verify'")
            return []

        results = []

        # Verify elements
        baseline_elems = self.baseline_elements.get(checkpoint, [])
        current_elems = self.current_elements.get(checkpoint, [])

        results.extend(self._verify_elements(checkpoint, baseline_elems, current_elems))

        # Verify regions (visual comparison)
        baseline_regions = self.baseline_regions.get(checkpoint, [])
        current_regions = self.current_regions.get(checkpoint, [])

        results.extend(self._verify_regions(checkpoint, baseline_regions, current_regions))

        self.verification_results.extend(results)
        return results

    def _verify_elements(self, checkpoint: str, baseline: List[UIElement],
                        current: List[UIElement]) -> List[VerificationResult]:
        """Compare UI elements between baseline and current."""
        results = []

        # Create lookup by name
        baseline_map = {elem.name: elem for elem in baseline}
        current_map = {elem.name: elem for elem in current}

        # Check all baseline elements exist and match
        for name, baseline_elem in baseline_map.items():
            current_elem = current_map.get(name)

            if not current_elem:
                results.append(VerificationResult(
                    checkpoint=checkpoint,
                    element_name=name,
                    passed=False,
                    details=f"Element '{name}' not found in current run",
                    baseline_value="exists",
                    actual_value="missing"
                ))
                continue

            # Compare properties
            if baseline_elem.text != current_elem.text:
                results.append(VerificationResult(
                    checkpoint=checkpoint,
                    element_name=f"{name}.text",
                    passed=False,
                    details=f"Text mismatch",
                    baseline_value=baseline_elem.text,
                    actual_value=current_elem.text
                ))

            if baseline_elem.visible != current_elem.visible:
                results.append(VerificationResult(
                    checkpoint=checkpoint,
                    element_name=f"{name}.visible",
                    passed=False,
                    details=f"Visibility mismatch",
                    baseline_value=baseline_elem.visible,
                    actual_value=current_elem.visible
                ))

            # If all checks passed
            if not any(r.element_name.startswith(name) for r in results if not r.passed):
                results.append(VerificationResult(
                    checkpoint=checkpoint,
                    element_name=name,
                    passed=True,
                    details="Element matches baseline"
                ))

        return results

    def _verify_regions(self, checkpoint: str, baseline: List[UIRegion],
                       current: List[UIRegion]) -> List[VerificationResult]:
        """Compare visual regions using SSIM."""
        results = []

        baseline_map = {region.name: region for region in baseline}
        current_map = {region.name: region for region in current}

        for name, baseline_region in baseline_map.items():
            current_region = current_map.get(name)

            if not current_region:
                results.append(VerificationResult(
                    checkpoint=checkpoint,
                    element_name=f"region_{name}",
                    passed=False,
                    details=f"Region '{name}' not found in current run"
                ))
                continue

            # Compare images using SSIM
            baseline_img_path = self.baseline_dir / f"{checkpoint}_{name}_region.png"
            current_img_path = self.baseline_dir / f"{checkpoint}_{name}_region.png"

            try:
                similarity = self._compare_images(baseline_img_path, current_img_path)

                # Threshold for pass/fail (95% similarity)
                threshold = 0.95
                passed = similarity >= threshold

                results.append(VerificationResult(
                    checkpoint=checkpoint,
                    element_name=f"region_{name}",
                    passed=passed,
                    details=f"Visual similarity: {similarity:.2%}",
                    similarity_score=similarity
                ))

            except Exception as e:
                results.append(VerificationResult(
                    checkpoint=checkpoint,
                    element_name=f"region_{name}",
                    passed=False,
                    details=f"Failed to compare images: {e}"
                ))

        return results

    def _compare_images(self, img1_path: Path, img2_path: Path) -> float:
        """
        Compare two images using Structural Similarity Index (SSIM).

        Returns:
            Similarity score (0-1, where 1 is identical)
        """
        img1 = Image.open(img1_path).convert('L')  # Convert to grayscale
        img2 = Image.open(img2_path).convert('L')

        # Resize if needed
        if img1.size != img2.size:
            img2 = img2.resize(img1.size)

        arr1 = np.array(img1)
        arr2 = np.array(img2)

        similarity, _ = ssim(arr1, arr2, full=True)
        return similarity

    def get_summary(self) -> Dict[str, Any]:
        """Get verification summary."""
        if not self.verification_results:
            return {"status": "no_results", "message": "No verification performed"}

        total = len(self.verification_results)
        passed = sum(1 for r in self.verification_results if r.passed)
        failed = total - passed

        return {
            "status": "pass" if failed == 0 else "fail",
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/total)*100:.1f}%",
            "checkpoints": list(set(r.checkpoint for r in self.verification_results))
        }

    def generate_html_report(self, output_path: Path):
        """Generate HTML report with verification results and diffs."""
        summary = self.get_summary()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>UI Verification Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .summary.pass {{ border-left: 5px solid #4caf50; }}
        .summary.fail {{ border-left: 5px solid #f44336; }}
        .checkpoint {{ margin-bottom: 30px; border: 1px solid #ddd; border-radius: 5px; padding: 15px; }}
        .checkpoint h2 {{ margin-top: 0; color: #555; }}
        .result {{ padding: 10px; margin: 5px 0; border-radius: 3px; }}
        .result.pass {{ background: #e8f5e9; border-left: 3px solid #4caf50; }}
        .result.fail {{ background: #ffebee; border-left: 3px solid #f44336; }}
        .result-name {{ font-weight: bold; }}
        .result-details {{ color: #666; font-size: 0.9em; }}
        .value {{ font-family: monospace; background: #f5f5f5; padding: 2px 5px; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .screenshots {{ margin-top: 20px; padding: 15px; background: #fafafa; border-radius: 5px; }}
        .screenshots h3 {{ margin-top: 0; font-size: 1.1em; color: #555; }}
        .screenshot-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; }}
        .screenshot-item {{ text-align: center; }}
        .screenshot-item h4 {{ margin: 0 0 10px 0; font-size: 0.95em; color: #666; }}
        .screenshot-item img {{ max-width: 100%; height: auto; border: 2px solid #ddd; border-radius: 4px; cursor: pointer; }}
        .screenshot-item img:hover {{ border-color: #999; }}
        .region-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 15px; }}
        .region-item {{ text-align: center; background: white; padding: 10px; border-radius: 5px; }}
        .region-item h4 {{ margin: 0 0 10px 0; font-size: 0.9em; color: #666; }}
        .region-item img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>UI Verification Report</h1>

        <div class="summary {summary['status']}">
            <h2>Summary</h2>
            <table>
                <tr><th>Total Checks</th><td>{summary['total']}</td></tr>
                <tr><th>Passed</th><td style="color: #4caf50;">{summary['passed']}</td></tr>
                <tr><th>Failed</th><td style="color: #f44336;">{summary['failed']}</td></tr>
                <tr><th>Pass Rate</th><td><strong>{summary['pass_rate']}</strong></td></tr>
            </table>
        </div>
        """

        # Group results by checkpoint
        checkpoints = {}
        for result in self.verification_results:
            if result.checkpoint not in checkpoints:
                checkpoints[result.checkpoint] = []
            checkpoints[result.checkpoint].append(result)

        # Render each checkpoint
        for checkpoint, results in checkpoints.items():
            passed = sum(1 for r in results if r.passed)
            total = len(results)

            html += f"""
        <div class="checkpoint">
            <h2>{checkpoint}</h2>
            <p>{passed}/{total} checks passed</p>
            """

            for result in results:
                status_class = "pass" if result.passed else "fail"
                status_icon = "✓" if result.passed else "✗"

                html += f"""
            <div class="result {status_class}">
                <div class="result-name">{status_icon} {result.element_name}</div>
                <div class="result-details">{result.details}</div>
                """

                if result.baseline_value is not None and result.actual_value is not None:
                    html += f"""
                <div class="result-details">
                    Baseline: <span class="value">{result.baseline_value}</span> →
                    Actual: <span class="value">{result.actual_value}</span>
                </div>
                """

                if result.similarity_score is not None:
                    html += f"""
                <div class="result-details">Similarity: {result.similarity_score:.2%}</div>
                """

                html += """
            </div>
                """

            # Add screenshots section
            html += """
            <div class="screenshots">
                <h3>📷 Screenshot Comparison</h3>
            """

            # Full screenshot comparison
            baseline_screenshot = None
            current_screenshot = None

            # Find baseline screenshot
            for pattern in [f"{checkpoint}_*.png", f"{checkpoint}.png"]:
                matches = list(self.baseline_dir.glob(pattern))
                if matches:
                    baseline_screenshot = matches[0]
                    break

            # Find current screenshot
            if checkpoint in self.current_screenshots:
                current_screenshot = self.current_screenshots[checkpoint]

            if baseline_screenshot or current_screenshot:
                html += '<div class="screenshot-grid">'

                if baseline_screenshot and baseline_screenshot.exists():
                    rel_path = baseline_screenshot.relative_to(self.baseline_dir.parent)
                    html += f"""
                <div class="screenshot-item">
                    <h4>Baseline</h4>
                    <img src="../{rel_path}" alt="Baseline Screenshot" onclick="window.open(this.src, '_blank')">
                </div>
                    """

                if current_screenshot and current_screenshot.exists():
                    rel_path = current_screenshot.relative_to(self.baseline_dir.parent)
                    html += f"""
                <div class="screenshot-item">
                    <h4>Current Run</h4>
                    <img src="../{rel_path}" alt="Current Screenshot" onclick="window.open(this.src, '_blank')">
                </div>
                    """

                html += '</div>'

            # Region comparisons
            baseline_regions = self.baseline_regions.get(checkpoint, [])
            if baseline_regions:
                html += '<div class="region-grid" style="margin-top: 20px;">'

                for region in baseline_regions:
                    baseline_region_path = self.baseline_dir / f"{checkpoint}_{region.name}_region.png"
                    if baseline_region_path.exists():
                        rel_path = baseline_region_path.relative_to(self.baseline_dir.parent)
                        html += f"""
                <div class="region-item">
                    <h4>Region: {region.name}</h4>
                    <img src="../{rel_path}" alt="Region: {region.name}" onclick="window.open(this.src, '_blank')">
                </div>
                        """

                html += '</div>'

            html += """
            </div>
            """

            html += """
        </div>
            """

        html += """
    </div>
</body>
</html>
        """

        with open(output_path, 'w') as f:
            f.write(html)

        logger.info(f"UI verification report saved: {output_path}")
