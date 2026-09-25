"""Tests for WFV Executor (harness runner)."""

from datetime import UTC, datetime

import pytest

from src.validation.wfv_executor import B004Evaluation, WFVExecutor


class TestWFVExecutor:
    """Tests for WFV executor functionality."""

    def test_executor_init(self) -> None:
        """Test executor initialization."""
        executor = WFVExecutor()

        assert executor.window_results == []
        assert executor.evaluation is None

    def test_validate_predictions_single_window(self) -> None:
        """Test validation of predictions for single window."""
        executor = WFVExecutor()
        harness = executor.harness
        w1 = harness.get_window("W1")

        predictions = [
            {"predicted_return_pct": 1.0, "predicted_direction": "LONG"},
            {"predicted_return_pct": 2.0, "predicted_direction": "LONG"},
            {"predicted_return_pct": -1.0, "predicted_direction": "SHORT"},
        ]
        actuals = [0.5, 1.0, -0.5]

        result = executor.validate_predictions(w1, predictions, actuals)

        assert result.window_id == "W1"
        assert result.sample_count == 3
        assert 0.0 <= result.ic <= 1.0
        assert 0.0 <= result.hr <= 1.0
        assert result.train_start == w1.train_start
        assert result.test_start == w1.test_start

    def test_validate_predictions_mismatch_raises(self) -> None:
        """Test validation raises on prediction/actual mismatch."""
        executor = WFVExecutor()
        w1 = executor.harness.get_window("W1")

        predictions = [{"predicted_direction": "LONG"}]
        actuals = [1.0, 2.0]

        with pytest.raises(ValueError, match="Prediction/actual count mismatch"):
            executor.validate_predictions(w1, predictions, actuals)

    def test_validate_predictions_empty_raises(self) -> None:
        """Test validation raises on empty predictions."""
        executor = WFVExecutor()
        w1 = executor.harness.get_window("W1")

        with pytest.raises(ValueError, match="No predictions"):
            executor.validate_predictions(w1, [], [])

    def test_evaluate_all_windows_pass(self) -> None:
        """Test gate evaluation with passing metrics."""
        executor = WFVExecutor()
        harness = executor.harness

        for i, w in enumerate(harness.windows[:3]):
            predictions = [{"predicted_direction": "LONG"}] * 10
            actuals = [0.5] * 10
            executor.validate_predictions(w, predictions, actuals)

        eval_result = executor.evaluate_all_windows()

        assert isinstance(eval_result, B004Evaluation)
        assert eval_result.ic_value >= 0.0
        assert eval_result.hr_value >= 0.0
        assert eval_result.ic_threshold == 0.05
        assert eval_result.hr_threshold == 0.52
        assert eval_result.stability_threshold == 0.75

    def test_evaluate_all_windows_no_results_raises(self) -> None:
        """Test gate evaluation raises without window results."""
        executor = WFVExecutor()

        with pytest.raises(ValueError, match="No window results"):
            executor.evaluate_all_windows()

    def test_executor_summary_readable(self) -> None:
        """Test executor summary output."""
        executor = WFVExecutor()
        harness = executor.harness

        w1 = harness.get_window("W1")
        predictions = [
            {"predicted_direction": "LONG", "predicted_return_pct": 1.0}
        ] * 5
        actuals = [0.5] * 5
        executor.validate_predictions(w1, predictions, actuals)

        summary = executor.summary()

        assert "WFV Execution Summary" in summary
        assert "W1" in summary
        assert "IC=" in summary
        assert "HR=" in summary
        assert "B-004 Gate Evaluation" in summary

    def test_executor_summary_with_evaluation(self) -> None:
        """Test executor summary after full evaluation."""
        executor = WFVExecutor()
        harness = executor.harness

        for w in harness.windows[:3]:
            predictions = [{"predicted_direction": "LONG"}] * 10
            actuals = [0.5] * 10
            executor.validate_predictions(w, predictions, actuals)

        executor.evaluate_all_windows()
        summary = executor.summary()

        assert "B-004 VERDICT:" in summary
        assert "✓ PASS" in summary or "✗ FAIL" in summary

    def test_executor_to_dict_export(self) -> None:
        """Test executor results export to dictionary."""
        executor = WFVExecutor()
        harness = executor.harness

        w1 = harness.get_window("W1")
        predictions = [{"predicted_direction": "LONG"}] * 5
        actuals = [0.5] * 5
        executor.validate_predictions(w1, predictions, actuals)

        executor.evaluate_all_windows()
        result_dict = executor.to_dict()

        assert result_dict["window_count"] == 1
        assert len(result_dict["windows"]) == 1
        assert result_dict["windows"][0]["window_id"] == "W1"
        assert "evaluation" in result_dict
        assert "verdict" in result_dict["evaluation"]

    def test_executor_multiple_windows_sequential(self) -> None:
        """Test executor processes multiple windows in sequence."""
        executor = WFVExecutor()
        harness = executor.harness

        windows_to_test = harness.windows[:5]
        for w in windows_to_test:
            predictions = [{"predicted_direction": "LONG"}] * 20
            actuals = [0.5] * 20
            executor.validate_predictions(w, predictions, actuals)

        assert len(executor.window_results) == 5
        assert executor.window_results[0].window_id == "W1"
        assert executor.window_results[4].window_id == "W5"

        eval_result = executor.evaluate_all_windows()
        assert eval_result.metadata["window_count"] == 5

    def test_executor_b004_evaluation_has_all_fields(self) -> None:
        """Test B004Evaluation contains all required fields."""
        executor = WFVExecutor()
        harness = executor.harness

        for w in harness.windows[:2]:
            predictions = [
                {"predicted_direction": "LONG", "predicted_return_pct": 1.0}
            ] * 10
            actuals = [0.5] * 10
            executor.validate_predictions(w, predictions, actuals)

        eval_result = executor.evaluate_all_windows()

        assert hasattr(eval_result, "verdict")
        assert hasattr(eval_result, "ic_pass") and hasattr(eval_result, "ic_value")
        assert hasattr(eval_result, "hr_pass") and hasattr(eval_result, "hr_value")
        assert hasattr(eval_result, "stability_pass")
        assert hasattr(eval_result, "stability_value")
        assert hasattr(eval_result, "timestamp")
        assert hasattr(eval_result, "metadata")
