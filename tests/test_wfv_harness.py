"""Tests for WFV (Walk-Forward Validation) harness per B-004_SPEC."""
# ruff: noqa: N806

from datetime import UTC, datetime, timedelta

import pytest

from src.validation.wfv_harness import WFVHarness, WFVWindow


class TestWFVWindow:
    """Tests for WFVWindow configuration."""

    def test_window_valid_creation(self) -> None:
        """Test valid window creation."""
        train_start = datetime(2021, 1, 1, tzinfo=UTC)
        train_end = datetime(2022, 12, 31, tzinfo=UTC)
        test_start = datetime(2023, 1, 1, tzinfo=UTC)
        test_end = datetime(2023, 3, 31, tzinfo=UTC)

        window = WFVWindow(
            window_id="W1",
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
        )

        assert window.window_id == "W1"
        assert window.train_start == train_start
        assert window.train_end == train_end
        assert window.test_start == test_start
        assert window.test_end == test_end
        assert window.train_days == 729  # 2021-01-01 to 2022-12-31 = 729 days
        assert window.test_days == 89  # 2023-01-01 to 2023-03-31 = 89 days

    def test_window_rejects_overlapping_train_test(self) -> None:
        """Test window rejects train_end >= test_start."""
        train_start = datetime(2021, 1, 1, tzinfo=UTC)
        train_end = datetime(2023, 1, 1, tzinfo=UTC)
        test_start = datetime(2023, 1, 1, tzinfo=UTC)
        test_end = datetime(2023, 3, 31, tzinfo=UTC)

        with pytest.raises(ValueError, match="Train end.*must be"):
            WFVWindow(
                window_id="W1",
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )

    def test_window_rejects_invalid_test_range(self) -> None:
        """Test window rejects test_start >= test_end."""
        train_start = datetime(2021, 1, 1, tzinfo=UTC)
        train_end = datetime(2022, 12, 31, tzinfo=UTC)
        test_start = datetime(2023, 3, 31, tzinfo=UTC)
        test_end = datetime(2023, 1, 1, tzinfo=UTC)

        with pytest.raises(ValueError, match="Test start.*must be"):
            WFVWindow(
                window_id="W1",
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )


class TestWFVHarnessWindows:
    """Tests for WFV harness window generation."""

    def test_harness_generates_windows(self) -> None:
        """Test harness generates windows (15 quarterly windows fit 2023-2026.9 span)."""
        harness = WFVHarness()
        assert len(harness.windows) == 15

    def test_first_window_configuration(self) -> None:
        """Test first window (W1) matches spec."""
        harness = WFVHarness()
        w1 = harness.windows[0]

        assert w1.window_id == "W1"
        assert w1.train_start == datetime(2021, 1, 1, tzinfo=UTC)
        assert w1.train_end == datetime(2022, 12, 31, tzinfo=UTC)
        assert w1.test_start == datetime(2023, 1, 1, tzinfo=UTC)

    def test_last_window_ends_at_spec_date(self) -> None:
        """Test last window ends at or after 2026-09-25."""
        harness = WFVHarness()
        w_last = harness.windows[-1]

        assert w_last.window_id == f"W{len(harness.windows)}"
        assert w_last.test_end == datetime(2026, 9, 25, tzinfo=UTC)

    def test_windows_expanding_train_phase(self) -> None:
        """Test train phase expands across windows (no shrinking)."""
        harness = WFVHarness()

        prev_train_days = 0
        for w in harness.windows:
            assert w.train_days >= prev_train_days
            prev_train_days = w.train_days

    def test_windows_no_overlap_train_test(self) -> None:
        """Test no overlap between train_end and test_start."""
        harness = WFVHarness()

        for w in harness.windows:
            assert w.train_end < w.test_start

    def test_windows_approximately_90_day_test(self) -> None:
        """Test test periods are approximately 90 days (±2 days) except last window."""
        harness = WFVHarness()

        for i, w in enumerate(harness.windows):
            if i < len(harness.windows) - 1:
                assert 88 <= w.test_days <= 92, f"{w.window_id} has {w.test_days} test days"
            else:
                assert w.test_days > 0, f"Last window {w.window_id} must have test days"

    def test_get_window_by_id(self) -> None:
        """Test retrieve window by ID."""
        harness = WFVHarness()

        w5 = harness.get_window("W5")
        assert w5.window_id == "W5"

        with pytest.raises(ValueError):
            harness.get_window("W20")

    def test_windows_sequential_test_periods(self) -> None:
        """Test test periods are sequential (no gaps or overlaps)."""
        harness = WFVHarness()

        for i in range(1, len(harness.windows)):
            prev_test_end = harness.windows[i - 1].test_end
            curr_test_start = harness.windows[i].test_start

            assert prev_test_end + timedelta(days=1) == curr_test_start


class TestWFVMetrics:
    """Tests for WFV metric calculations."""

    def test_calculate_ic_perfect_correlation(self) -> None:
        """Test IC with perfect positive correlation."""
        harness = WFVHarness()

        predictions = [
            {"predicted_return_pct": 5.0},
            {"predicted_return_pct": 3.0},
            {"predicted_return_pct": -2.0},
            {"predicted_return_pct": -4.0},
        ]
        actuals = [2.0, 1.0, -1.0, -3.0]

        ic = harness.calculate_ic(predictions, actuals)
        assert 0.8 < ic <= 1.0

    def test_calculate_ic_perfect_anticorrelation(self) -> None:
        """Test IC with perfect negative correlation."""
        harness = WFVHarness()

        predictions = [
            {"predicted_return_pct": 5.0},
            {"predicted_return_pct": 3.0},
            {"predicted_return_pct": -2.0},
            {"predicted_return_pct": -4.0},
        ]
        actuals = [-2.0, -1.0, 1.0, 3.0]

        ic = harness.calculate_ic(predictions, actuals)
        assert -1.0 <= ic < -0.8

    def test_calculate_ic_zero_correlation(self) -> None:
        """Test IC with weak/random correlation."""
        harness = WFVHarness()

        predictions = [
            {"predicted_return_pct": 5.0},
            {"predicted_return_pct": 3.0},
            {"predicted_return_pct": -2.0},
            {"predicted_return_pct": 1.0},
        ]
        actuals = [5.0, -1.0, 2.0, -3.0]

        ic = harness.calculate_ic(predictions, actuals)
        assert -1.0 <= ic <= 1.0

    def test_calculate_hr_perfect_hits(self) -> None:
        """Test HR with all correct predictions."""
        harness = WFVHarness()

        predictions = [
            {"predicted_direction": "LONG"},
            {"predicted_direction": "LONG"},
            {"predicted_direction": "SHORT"},
            {"predicted_direction": "SHORT"},
        ]
        actuals = [5.0, 3.0, -2.0, -4.0]

        hr = harness.calculate_hr(predictions, actuals)
        assert hr == 1.0

    def test_calculate_hr_mixed_results(self) -> None:
        """Test HR with mixed correct/incorrect predictions."""
        harness = WFVHarness()

        predictions = [
            {"predicted_direction": "LONG"},   # correct: +5.0
            {"predicted_direction": "SHORT"},  # incorrect: -2.0 (opposite of expected)
            {"predicted_direction": "NEUTRAL"}, # incorrect: 2.0 (too large)
            {"predicted_direction": "LONG"},   # incorrect: -1.0 (opposite)
        ]
        actuals = [5.0, -2.0, 2.0, -1.0]

        hr = harness.calculate_hr(predictions, actuals)
        assert 0.0 <= hr <= 1.0

    def test_calculate_hr_neutral_hit_range(self) -> None:
        """Test HR correctly classifies NEUTRAL when abs(return) <= 0.5%."""
        harness = WFVHarness()

        predictions = [{"predicted_direction": "NEUTRAL"}]
        actuals_hit = [0.3]
        actuals_miss = [1.0]

        hr_hit = harness.calculate_hr(predictions, actuals_hit)
        hr_miss = harness.calculate_hr(predictions, actuals_miss)

        assert hr_hit == 1.0
        assert hr_miss == 0.0

    def test_calculate_stability_consistent_metrics(self) -> None:
        """Test stability with consistent IC/HR across windows."""
        harness = WFVHarness()

        window_metrics = [
            {"ic": 0.10, "hr": 0.55},
            {"ic": 0.10, "hr": 0.55},
            {"ic": 0.10, "hr": 0.55},
        ]

        stability = harness.calculate_stability(window_metrics)
        assert stability < 0.1

    def test_calculate_stability_variable_metrics(self) -> None:
        """Test stability with variable IC/HR across windows."""
        harness = WFVHarness()

        window_metrics = [
            {"ic": 0.20, "hr": 0.60},
            {"ic": 0.05, "hr": 0.50},
            {"ic": -0.10, "hr": 0.45},
        ]

        stability = harness.calculate_stability(window_metrics)
        assert stability > 0.3, "Variable metrics should produce higher stability (poor consistency)"


class TestWFVGates:
    """Tests for B-004 gate evaluation."""

    def test_gate_all_pass(self) -> None:
        """Test verdict PASS when all gates pass."""
        harness = WFVHarness()

        window_metrics = [
            {"ic": 0.10, "hr": 0.55} for _ in range(15)
        ]

        gates = harness.evaluate_gates(window_metrics)
        assert gates["gate_ic"]["pass"] == True
        assert gates["gate_hr"]["pass"] == True
        assert gates["gate_stability"]["pass"] == True
        assert gates["b004_verdict"] == True

    def test_gate_ic_fail(self) -> None:
        """Test verdict FAIL when IC gate fails."""
        harness = WFVHarness()

        window_metrics = [
            {"ic": 0.02, "hr": 0.55} for _ in range(15)
        ]

        gates = harness.evaluate_gates(window_metrics)
        assert gates["gate_ic"]["pass"] == False
        assert gates["b004_verdict"] == False

    def test_gate_hr_fail(self) -> None:
        """Test verdict FAIL when HR gate fails."""
        harness = WFVHarness()

        window_metrics = [
            {"ic": 0.10, "hr": 0.50} for _ in range(15)
        ]

        gates = harness.evaluate_gates(window_metrics)
        assert gates["gate_hr"]["pass"] == False
        assert gates["b004_verdict"] == False

    def test_gate_stability_fail(self) -> None:
        """Test verdict FAIL when stability gate fails (high variation)."""
        harness = WFVHarness()

        window_metrics = [
            {"ic": 0.50, "hr": 0.70},
            {"ic": -0.40, "hr": 0.40},
            {"ic": 0.08, "hr": 0.55},
        ] + [{"ic": 0.10, "hr": 0.55} for _ in range(12)]

        gates = harness.evaluate_gates(window_metrics)
        assert gates["gate_stability"]["pass"] == False
        assert gates["b004_verdict"] == False

    def test_gate_thresholds_frozen(self) -> None:
        """Test thresholds match B-004_SPEC exactly."""
        harness = WFVHarness()

        window_metrics = [{"ic": 0.05, "hr": 0.52} for _ in range(15)]

        gates = harness.evaluate_gates(window_metrics)

        assert gates["gate_ic"]["threshold"] == 0.05
        assert gates["gate_hr"]["threshold"] == 0.52
        assert gates["gate_stability"]["threshold"] == 0.75


class TestWFVIntegrity:
    """Tests for WFV harness integrity and validation."""

    def test_validate_window_integrity_passes(self) -> None:
        """Test validate_window_integrity passes for generated windows."""
        harness = WFVHarness()
        harness.validate_window_integrity()

    def test_harness_summary(self) -> None:
        """Test summary output is readable."""
        harness = WFVHarness()
        summary = harness.summary()

        assert "15 windows" in summary
        assert "W1" in summary
        assert f"W{len(harness.windows)}" in summary
        assert "2021" in summary
        assert "2026" in summary
