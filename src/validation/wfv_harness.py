"""Walk-Forward Validation (WFV) harness per B-004_SPEC.

Implements 19-window expanding train/test protocol with strict point-in-time validation.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from scipy.stats import spearmanr

from src.utils.logging import get_logger

logger = get_logger(__name__)


class WFVWindow:
    """Single walk-forward window configuration."""

    def __init__(
        self,
        window_id: str,
        train_start: datetime,
        train_end: datetime,
        test_start: datetime,
        test_end: datetime,
    ) -> None:
        """Initialize WFV window.

        Args:
            window_id: Window identifier (W1, W2, ..., W19).
            train_start: Train period start (UTC).
            train_end: Train period end (UTC).
            test_start: Test period start (UTC).
            test_end: Test period end (UTC).

        Raises:
            ValueError: If dates invalid or overlapping.
        """
        if train_end >= test_start:
            raise ValueError(f"Train end ({train_end}) must be < test start ({test_start})")
        if test_start >= test_end:
            raise ValueError(f"Test start ({test_start}) must be < test end ({test_end})")

        self.window_id = window_id
        self.train_start = train_start
        self.train_end = train_end
        self.test_start = test_start
        self.test_end = test_end

        self.train_days = (train_end - train_start).days
        self.test_days = (test_end - test_start).days

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"WFVWindow({self.window_id}, "
            f"train={self.train_start.date()}-{self.train_end.date()}, "
            f"test={self.test_start.date()}-{self.test_end.date()})"
        )


class WFVHarness:
    """Walk-Forward Validation harness (frozen per B-004_SPEC)."""

    FULL_PERIOD_START = datetime(2021, 1, 1, tzinfo=UTC)
    FULL_PERIOD_END = datetime(2026, 9, 25, tzinfo=UTC)
    WFV_PERIOD_START = datetime(2023, 1, 1, tzinfo=UTC)
    WFV_PERIOD_END = datetime(2026, 9, 25, tzinfo=UTC)

    def __init__(self) -> None:
        """Initialize WFV harness."""
        self.windows: list[WFVWindow] = []
        self._generate_windows()
        logger.info(
            "WFV harness initialized",
            extra={
                "extra_fields": {
                    "num_windows": len(self.windows),
                    "full_period": f"{self.FULL_PERIOD_START} to {self.FULL_PERIOD_END}",
                    "wfv_period": f"{self.WFV_PERIOD_START} to {self.WFV_PERIOD_END}",
                }
            },
        )

    def _generate_windows(self) -> None:
        """Generate 19 windows spanning WFV period (expanding train/fixed test ~90d)."""
        current_test_start = self.WFV_PERIOD_START
        window_num = 1

        while current_test_start < self.WFV_PERIOD_END:
            test_end = min(current_test_start + timedelta(days=92), self.WFV_PERIOD_END)

            if test_end == current_test_start:
                break

            train_start = self.FULL_PERIOD_START
            train_end = current_test_start - timedelta(days=1)

            window_id = f"W{window_num}"
            window = WFVWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=current_test_start,
                test_end=test_end,
            )
            self.windows.append(window)

            current_test_start = test_end + timedelta(days=1)
            window_num += 1

    def get_window(self, window_id: str) -> WFVWindow:
        """Retrieve window by ID.

        Args:
            window_id: Window identifier (W1, W2, ..., W19).

        Returns:
            WFVWindow.

        Raises:
            ValueError: If window not found.
        """
        for w in self.windows:
            if w.window_id == window_id:
                return w
        raise ValueError(f"Window {window_id} not found in harness")

    def validate_window_integrity(self) -> None:
        """Validate all windows satisfy constraints.

        Raises:
            ValueError: If any constraint violated.
        """
        for i, w in enumerate(self.windows):
            if w.train_start >= w.train_end:
                raise ValueError(f"{w.window_id}: train_start >= train_end")
            if w.train_end >= w.test_start:
                raise ValueError(f"{w.window_id}: train_end >= test_start")
            if w.test_start >= w.test_end:
                raise ValueError(f"{w.window_id}: test_start >= test_end")

            if i > 0:
                prev_w = self.windows[i - 1]
                if w.train_start != prev_w.train_start:
                    raise ValueError(f"{w.window_id}: train_start not expanding")

        logger.info("WFV window integrity validated", extra={"extra_fields": {}})

    @staticmethod
    def calculate_ic(predictions: list[dict[str, Any]], actuals: list[float]) -> float:
        """Calculate Information Coefficient (Spearman correlation).

        Args:
            predictions: List of dicts with 'predicted_direction' and 'predicted_return_pct'.
            actuals: List of actual period returns (%).

        Returns:
            IC score [-1, 1].
        """
        if len(predictions) != len(actuals) or not predictions:
            return 0.0

        predicted_signs = [
            1.0 if p.get("predicted_return_pct", 0) > 0 else -1.0 for p in predictions
        ]
        actual_signs = [1.0 if a > 0 else -1.0 for a in actuals]

        ic, _ = spearmanr(predicted_signs, actual_signs)
        return float(ic) if not np.isnan(ic) else 0.0

    @staticmethod
    def calculate_hr(predictions: list[dict[str, Any]], actuals: list[float]) -> float:
        """Calculate Hit Rate (directional accuracy).

        Args:
            predictions: List of dicts with 'predicted_direction'.
            actuals: List of actual period returns (%).

        Returns:
            HR [0, 1].
        """
        if len(predictions) != len(actuals) or not predictions:
            return 0.0

        correct = 0
        for p, a in zip(predictions, actuals, strict=True):
            direction = p.get("predicted_direction", "NEUTRAL")
            if (direction == "LONG" and a > 0) or (direction == "SHORT" and a < 0) or (
                direction == "NEUTRAL" and abs(a) <= 0.5
            ):
                correct += 1

        return correct / len(predictions)

    @staticmethod
    def calculate_stability(window_metrics: list[dict[str, Any]]) -> float:
        """Calculate Stability (coefficient of variation across windows).

        Args:
            window_metrics: List of dicts with 'ic' and 'hr' per window.

        Returns:
            Stability score (lower = more consistent).
        """
        if not window_metrics:
            return 0.0

        ics = [w.get("ic", 0.0) for w in window_metrics]
        hrs = [w.get("hr", 0.5) for w in window_metrics]

        ic_mean = np.mean(ics)
        ic_std = np.std(ics)
        ic_cv = ic_std / (abs(ic_mean) + 1e-6)

        hr_mean = np.mean(hrs)
        hr_std = np.std(hrs)
        hr_cv = hr_std / (hr_mean + 1e-6) if hr_mean > 0 else 1.0

        stability = (ic_cv + hr_cv) / 2.0
        return float(stability)

    def evaluate_gates(
        self, window_metrics: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any] | bool]:
        """Evaluate B-004 gates (ΔIC, HR, Stability).

        Args:
            window_metrics: List of dicts with 'ic' and 'hr' per window.

        Returns:
            Dict with gate results and B-004 verdict.
        """
        ic_values = [w.get("ic", 0.0) for w in window_metrics]
        hr_values = [w.get("hr", 0.5) for w in window_metrics]

        ic_mean = np.mean(ic_values)
        hr_mean = np.mean(hr_values)
        stability = self.calculate_stability(window_metrics)

        gate_ic = ic_mean >= 0.05
        gate_hr = hr_mean >= 0.52
        gate_stability = stability <= 0.75

        verdict = gate_ic and gate_hr and gate_stability

        return {
            "gate_ic": {
                "threshold": 0.05,
                "value": ic_mean,
                "pass": gate_ic,
            },
            "gate_hr": {
                "threshold": 0.52,
                "value": hr_mean,
                "pass": gate_hr,
            },
            "gate_stability": {
                "threshold": 0.75,
                "value": stability,
                "pass": gate_stability,
            },
            "b004_verdict": verdict,
        }

    def summary(self) -> str:
        """Return summary of harness configuration."""
        return (
            f"WFVHarness: {len(self.windows)} windows\n"
            f"  Full period: {self.FULL_PERIOD_START.date()} to {self.FULL_PERIOD_END.date()}\n"
            f"  WFV test period: {self.WFV_PERIOD_START.date()} to {self.WFV_PERIOD_END.date()}\n"
            f"  First window: {self.windows[0]}\n"
            f"  Last window: {self.windows[-1]}"
        )
