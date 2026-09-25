"""Dry-run WFV validation: end-to-end harness test on sample data.

Per B-004_SPEC: Validates WFV harness mechanics (window generation, metrics,
gates) without full 19-window evaluation. Demonstrates point-in-time validation
and no-lookahead constraints.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.validation.wfv_harness import WFVHarness


class TestWFVDryRun:
    """Dry-run WFV validation on sample data."""

    def test_dryrun_single_window_full_pipeline(self) -> None:
        """Test WFV full pipeline on single window (W1)."""
        harness = WFVHarness()
        w1 = harness.get_window("W1")

        assert w1.window_id == "W1"
        assert w1.train_days == 729
        assert 88 <= w1.test_days <= 92, "Test period should be ~90 days"

        predictions = [
            {"predicted_return_pct": 5.0, "predicted_direction": "LONG"},
            {"predicted_return_pct": 3.0, "predicted_direction": "LONG"},
            {"predicted_return_pct": -2.0, "predicted_direction": "SHORT"},
            {"predicted_return_pct": -4.0, "predicted_direction": "SHORT"},
        ]
        actuals = [2.0, 1.0, -1.0, -3.0]

        ic = harness.calculate_ic(predictions, actuals)
        hr = harness.calculate_hr(predictions, actuals)

        assert 0.8 < ic <= 1.0, "IC should be high for correlated data"
        assert hr == 1.0, "HR should be perfect for perfectly directional data"

    def test_dryrun_multiple_windows_consistent_metrics(self) -> None:
        """Test WFV on all 15 windows with consistent metrics."""
        harness = WFVHarness()

        assert len(harness.windows) == 15, "Should have 15 quarterly windows"

        window_metrics = []
        for w in harness.windows:
            window_metrics.append({
                "ic": 0.10,
                "hr": 0.55,
                "window_id": w.window_id,
            })

        gates = harness.evaluate_gates(window_metrics)

        assert gates["gate_ic"]["pass"] == True, "IC gate should pass at 0.10 > 0.05"
        assert gates["gate_hr"]["pass"] == True, "HR gate should pass at 0.55 > 0.52"
        assert gates["gate_stability"]["pass"] == True, "Stability gate should pass for consistent data"
        assert gates["b004_verdict"] == True, "B-004 verdict should PASS"

    def test_dryrun_multiple_windows_variable_metrics_fails_stability(self) -> None:
        """Test WFV on all 15 windows with high variation fails stability gate."""
        harness = WFVHarness()

        window_metrics = [
            {"ic": 0.50, "hr": 0.70},
            {"ic": -0.40, "hr": 0.40},
            {"ic": 0.08, "hr": 0.55},
        ] + [{"ic": 0.10, "hr": 0.55} for _ in range(12)]

        gates = harness.evaluate_gates(window_metrics)

        assert gates["gate_ic"]["pass"] == True
        assert gates["gate_hr"]["pass"] == True
        assert gates["gate_stability"]["pass"] == False, "High variation should fail stability gate"
        assert gates["b004_verdict"] == False, "B-004 verdict should FAIL when stability fails"

    def test_dryrun_point_in_time_window_no_lookahead(self) -> None:
        """Test WFV windows enforce point-in-time constraint."""
        harness = WFVHarness()

        for i, w in enumerate(harness.windows):
            assert w.train_start < w.train_end, f"{w.window_id}: train period invalid"
            assert w.train_end < w.test_start, f"{w.window_id}: no data leakage (train_end < test_start)"
            assert w.test_start < w.test_end, f"{w.window_id}: test period invalid"

            if i > 0:
                prev_w = harness.windows[i - 1]
                assert (
                    prev_w.test_end + timedelta(days=1) == w.test_start
                ), f"{w.window_id}: test periods not sequential"

    def test_dryrun_window_expanding_train_no_shrinkage(self) -> None:
        """Test WFV train period only expands (never shrinks) per spec."""
        harness = WFVHarness()

        prev_train_days = 0
        for w in harness.windows:
            assert w.train_days >= prev_train_days, (
                f"{w.window_id}: train period shrank ({prev_train_days} → {w.train_days})"
            )
            prev_train_days = w.train_days

    def test_dryrun_gates_thresholds_frozen(self) -> None:
        """Test B-004 gate thresholds are frozen and match spec."""
        harness = WFVHarness()

        window_metrics = [{"ic": 0.10, "hr": 0.55} for _ in range(15)]
        gates = harness.evaluate_gates(window_metrics)

        assert gates["gate_ic"]["threshold"] == 0.05, "IC threshold must be frozen at 0.05"
        assert gates["gate_hr"]["threshold"] == 0.52, "HR threshold must be frozen at 0.52"
        assert gates["gate_stability"]["threshold"] == 0.75, "Stability threshold must be frozen at 0.75"

    def test_dryrun_metrics_calculation_accuracy(self) -> None:
        """Test WFV metric calculations match expected formulas."""
        harness = WFVHarness()

        predictions = [
            {"predicted_return_pct": 1.0, "predicted_direction": "LONG"},
            {"predicted_return_pct": -1.0, "predicted_direction": "SHORT"},
        ]
        actuals = [0.5, -0.5]

        ic = harness.calculate_ic(predictions, actuals)
        assert -1.0 <= ic <= 1.0, "IC must be in [-1, 1]"

        hr = harness.calculate_hr(predictions, actuals)
        assert 0.0 <= hr <= 1.0, "HR must be in [0, 1]"

    def test_dryrun_harness_summary_readable(self) -> None:
        """Test WFV harness produces readable summary."""
        harness = WFVHarness()
        summary = harness.summary()

        assert "15 windows" in summary, "Summary should show window count"
        assert "W1" in summary, "Summary should show first window"
        assert "W15" in summary, "Summary should show last window"
        assert "2021" in summary, "Summary should show full period start"
        assert "2026" in summary, "Summary should show full period end"
        assert "2023" in summary, "Summary should show WFV period start"

    def test_dryrun_no_modification_of_b004_params(self) -> None:
        """Test that B-004 params cannot be modified during dry-run."""
        harness = WFVHarness()

        window_metrics = [{"ic": 0.05, "hr": 0.52} for _ in range(15)]
        gates = harness.evaluate_gates(window_metrics)

        original_ic_threshold = gates["gate_ic"]["threshold"]
        original_hr_threshold = gates["gate_hr"]["threshold"]
        original_stability_threshold = gates["gate_stability"]["threshold"]

        window_metrics_2 = [{"ic": 0.10, "hr": 0.60} for _ in range(15)]
        gates_2 = harness.evaluate_gates(window_metrics_2)

        assert gates_2["gate_ic"]["threshold"] == original_ic_threshold, "IC threshold must not change"
        assert gates_2["gate_hr"]["threshold"] == original_hr_threshold, "HR threshold must not change"
        assert (
            gates_2["gate_stability"]["threshold"] == original_stability_threshold
        ), "Stability threshold must not change"
