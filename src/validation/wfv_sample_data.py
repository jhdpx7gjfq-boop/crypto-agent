"""Sample data generator for WFV dry-run execution.

Generates synthetic RPM predictions and actual returns for testing
the full WFV pipeline without requiring real model output.
"""

from datetime import datetime, timedelta
from typing import Any

import numpy as np


class WFVSampleDataGenerator:
    """Generate synthetic RPM predictions + actuals for WFV testing."""

    def __init__(self, seed: int = 42) -> None:
        """Initialize generator with optional seed."""
        np.random.seed(seed)
        self.seed = seed

    def generate_predictions_for_window(
        self,
        window_start: datetime,
        window_end: datetime,
        quality: str = "good",
    ) -> tuple[list[dict[str, Any]], list[float]]:
        """Generate synthetic RPM predictions + actuals for a window.

        Args:
            window_start: Test period start
            window_end: Test period end
            quality: "good" (predictive), "poor" (random), "mixed"

        Returns:
            (predictions, actuals) tuples
        """
        days = (window_end - window_start).days
        n_samples = max(10, days // 7)

        predictions = []
        actuals = []

        for i in range(n_samples):
            if quality == "good":
                base_direction = 1.0 if np.random.rand() > 0.5 else -1.0
                component_error = np.random.normal(0, 0.1)
                predicted_return = base_direction * (0.5 + component_error)
                actual_return = base_direction * (0.4 + np.random.normal(0, 0.2))
            elif quality == "poor":
                predicted_return = np.random.normal(0, 0.5)
                actual_return = np.random.normal(0, 0.5)
            elif quality == "mixed":
                if i < n_samples // 2:
                    base_direction = 1.0 if np.random.rand() > 0.5 else -1.0
                    predicted_return = base_direction * (0.5 + np.random.normal(0, 0.1))
                    actual_return = base_direction * (0.4 + np.random.normal(0, 0.2))
                else:
                    predicted_return = np.random.normal(0, 0.5)
                    actual_return = np.random.normal(0, 0.5)
            else:
                raise ValueError(f"Unknown quality: {quality}")

            direction = "LONG" if predicted_return > 0 else ("SHORT" if predicted_return < 0 else "NEUTRAL")

            predictions.append({
                "predicted_return_pct": float(predicted_return),
                "predicted_direction": direction,
                "timestamp": window_start + timedelta(days=i * 7),
            })
            actuals.append(float(actual_return))

        return predictions, actuals

    def generate_for_all_windows(
        self,
        windows: list[Any],
        quality_schedule: dict[int, str] | None = None,
    ) -> dict[str, tuple[list[dict[str, Any]], list[float]]]:
        """Generate predictions + actuals for all windows.

        Args:
            windows: List of WFVWindow objects
            quality_schedule: Optional {window_idx: quality} mapping

        Returns:
            Dict mapping window_id → (predictions, actuals)
        """
        if quality_schedule is None:
            quality_schedule = {}

        results = {}
        for idx, w in enumerate(windows):
            quality = quality_schedule.get(idx, "good")
            predictions, actuals = self.generate_predictions_for_window(
                w.test_start,
                w.test_end,
                quality=quality,
            )
            results[w.window_id] = (predictions, actuals)

        return results

    def generate_scenario(
        self,
        scenario: str,
        windows: list[Any],
    ) -> dict[str, tuple[list[dict[str, Any]], list[float]]]:
        """Generate a predefined scenario for testing.

        Scenarios:
        - "pass": all windows good quality (should pass all gates)
        - "fail_ic": poor quality IC (fails IC gate)
        - "fail_hr": mixed quality (passes IC, fails HR)
        - "fail_stability": high variation (fails stability gate)
        - "realistic": mixed results across windows

        Args:
            scenario: Scenario name
            windows: List of WFVWindow objects

        Returns:
            Dict mapping window_id → (predictions, actuals)
        """
        if scenario == "pass":
            return self.generate_for_all_windows(
                windows, dict.fromkeys(range(len(windows)), "good")
            )

        elif scenario == "fail_ic":
            return self.generate_for_all_windows(
                windows, dict.fromkeys(range(len(windows)), "poor")
            )

        elif scenario == "fail_hr":
            schedule = {i: "poor" if i < len(windows) // 2 else "good" for i in range(len(windows))}
            return self.generate_for_all_windows(windows, schedule)

        elif scenario == "fail_stability":
            schedule = {
                0: "good",
                1: "poor",
                2: "good",
            }
            for i in range(3, len(windows)):
                schedule[i] = "good"
            return self.generate_for_all_windows(windows, schedule)

        elif scenario == "realistic":
            schedule = {}
            for i in range(len(windows)):
                if i < 3:
                    schedule[i] = np.random.choice(["good", "mixed"])
                elif i < 10:
                    schedule[i] = "good"
                else:
                    schedule[i] = np.random.choice(["good", "mixed", "poor"])
            return self.generate_for_all_windows(windows, schedule)

        else:
            raise ValueError(f"Unknown scenario: {scenario}")
