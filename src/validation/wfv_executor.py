"""WFV Executor: Run Walk-Forward Validation on RPM predictions.

This module provides infrastructure to execute the WFV harness against
RPM model predictions, computing metrics and evaluating B-004 gates.

No execution occurs without explicit approval. Designed for:
1. Dry-run validation (sample data)
2. Full 19-window evaluation (upon user approval)
3. Post-evaluation regime analysis
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.validation.wfv_harness import WFVHarness, WFVWindow


@dataclass
class WFVResult:
    """Result of WFV evaluation on a single window."""

    window_id: str
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    sample_count: int
    ic: float
    hr: float
    stability_value: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class B004Evaluation:
    """B-004 gate evaluation result."""

    verdict: bool
    ic_pass: bool
    ic_value: float
    ic_threshold: float
    hr_pass: bool
    hr_value: float
    hr_threshold: float
    stability_pass: bool
    stability_value: float
    stability_threshold: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class WFVExecutor:
    """Execute WFV protocol on RPM predictions (non-autonomous)."""

    def __init__(self) -> None:
        """Initialize WFV executor."""
        self.harness = WFVHarness()
        self.window_results: list[WFVResult] = []
        self.evaluation: B004Evaluation | None = None

    def validate_predictions(
        self,
        window: WFVWindow,
        predictions: list[dict[str, Any]],
        actuals: list[float],
    ) -> WFVResult:
        """Validate predictions for a single window (point-in-time).

        Args:
            window: WFVWindow configuration
            predictions: RPM predictions (with direction + return_pct)
            actuals: Actual returns for test period

        Returns:
            WFVResult with IC, HR metrics

        Raises:
            ValueError: If prediction/actual counts mismatch
        """
        if len(predictions) != len(actuals):
            raise ValueError(
                f"Prediction/actual count mismatch: {len(predictions)} vs {len(actuals)}"
            )

        if not predictions:
            raise ValueError(f"No predictions for window {window.window_id}")

        ic = self.harness.calculate_ic(predictions, actuals)
        hr = self.harness.calculate_hr(predictions, actuals)

        result = WFVResult(
            window_id=window.window_id,
            train_start=window.train_start,
            train_end=window.train_end,
            test_start=window.test_start,
            test_end=window.test_end,
            sample_count=len(predictions),
            ic=ic,
            hr=hr,
            metadata={
                "ic_formula": "Spearman(sign(pred), sign(actual))",
                "hr_formula": "Pct correct direction (LONG/SHORT/NEUTRAL±0.5%)",
            },
        )

        self.window_results.append(result)
        return result

    def evaluate_all_windows(self) -> B004Evaluation:
        """Evaluate B-004 gates across all window results.

        Returns:
            B004Evaluation with gate verdicts

        Raises:
            ValueError: If no window results available
        """
        if not self.window_results:
            raise ValueError("No window results to evaluate")

        window_metrics = [
            {"ic": r.ic, "hr": r.hr} for r in self.window_results
        ]

        gates = self.harness.evaluate_gates(window_metrics)

        # Extract gate results with proper typing
        gate_ic = gates["gate_ic"]
        gate_hr = gates["gate_hr"]
        gate_stability = gates["gate_stability"]
        verdict = bool(gates["b004_verdict"])

        assert isinstance(gate_ic, dict), "gate_ic must be dict"
        assert isinstance(gate_hr, dict), "gate_hr must be dict"
        assert isinstance(gate_stability, dict), "gate_stability must be dict"

        self.evaluation = B004Evaluation(
            verdict=verdict,
            ic_pass=gate_ic["pass"],
            ic_value=gate_ic["value"],
            ic_threshold=gate_ic["threshold"],
            hr_pass=gate_hr["pass"],
            hr_value=gate_hr["value"],
            hr_threshold=gate_hr["threshold"],
            stability_pass=gate_stability["pass"],
            stability_value=gate_stability["value"],
            stability_threshold=gate_stability["threshold"],
            metadata={
                "window_count": len(self.window_results),
                "gates_evaluated": "IC, HR, Stability (B-004 frozen)",
                "verdict_meaning": "PASS = all 3 gates pass, FAIL = any gate fails",
            },
        )

        return self.evaluation

    def summary(self) -> str:
        """Generate human-readable summary of evaluation."""
        if not self.window_results:
            return "No window results to summarize"

        summary_lines = [
            f"WFV Execution Summary ({len(self.window_results)} windows)",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "Window Results:",
        ]

        for r in self.window_results:
            summary_lines.append(
                f"  {r.window_id}: IC={r.ic:.3f}, HR={r.hr:.3f}, samples={r.sample_count}"
            )

        if self.evaluation:
            summary_lines.extend([
                "",
                "B-004 Gate Evaluation:",
                f"  IC Gate (≥0.05):  {self.evaluation.ic_value:.3f} → {'PASS' if self.evaluation.ic_pass else 'FAIL'}",
                f"  HR Gate (≥0.52):  {self.evaluation.hr_value:.3f} → {'PASS' if self.evaluation.hr_pass else 'FAIL'}",
                f"  Stability (≤0.75): {self.evaluation.stability_value:.3f} → {'PASS' if self.evaluation.stability_pass else 'FAIL'}",
                "",
                f"B-004 VERDICT: {'✓ PASS' if self.evaluation.verdict else '✗ FAIL'}",
            ])
        else:
            summary_lines.extend([
                "",
                "B-004 Gate Evaluation: (awaiting evaluate_all_windows())",
            ])

        return "\n".join(summary_lines)

    def to_dict(self) -> dict[str, Any]:
        """Export evaluation as dictionary (for reporting/logging)."""
        return {
            "window_count": len(self.window_results),
            "windows": [
                {
                    "window_id": r.window_id,
                    "ic": float(r.ic),
                    "hr": float(r.hr),
                    "sample_count": r.sample_count,
                }
                for r in self.window_results
            ],
            "evaluation": {
                "verdict": bool(self.evaluation.verdict) if self.evaluation else None,
                "ic": {
                    "value": float(self.evaluation.ic_value),
                    "threshold": float(self.evaluation.ic_threshold),
                    "pass": bool(self.evaluation.ic_pass),
                }
                if self.evaluation
                else None,
                "hr": {
                    "value": float(self.evaluation.hr_value),
                    "threshold": float(self.evaluation.hr_threshold),
                    "pass": bool(self.evaluation.hr_pass),
                }
                if self.evaluation
                else None,
                "stability": {
                    "value": float(self.evaluation.stability_value),
                    "threshold": float(self.evaluation.stability_threshold),
                    "pass": bool(self.evaluation.stability_pass),
                }
                if self.evaluation
                else None,
                "timestamp": (
                    self.evaluation.timestamp.isoformat()
                    if self.evaluation
                    else None
                ),
            } if self.evaluation else {},
        }
