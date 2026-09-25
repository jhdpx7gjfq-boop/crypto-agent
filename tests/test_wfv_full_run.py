"""Full WFV execution tests: end-to-end pipeline on sample data."""

from datetime import UTC, datetime

import pytest

from src.validation.wfv_executor import WFVExecutor
from src.validation.wfv_harness import WFVHarness
from src.validation.wfv_sample_data import WFVSampleDataGenerator


class TestWFVFullRun:
    """Full WFV pipeline execution tests."""

    def test_full_wfv_run_15_windows_pass_scenario(self) -> None:
        """Execute full 15-window WFV with 'pass' scenario."""
        harness = WFVHarness()
        executor = WFVExecutor()
        generator = WFVSampleDataGenerator(seed=42)

        data = generator.generate_scenario("pass", harness.windows)

        assert len(data) == 15, "Should have 15 windows of data"

        for window in harness.windows:
            predictions, actuals = data[window.window_id]
            assert len(predictions) > 0, f"{window.window_id}: no predictions"
            assert len(predictions) == len(actuals), f"{window.window_id}: mismatch"

            executor.validate_predictions(window, predictions, actuals)

        assert len(executor.window_results) == 15

        eval_result = executor.evaluate_all_windows()

        assert eval_result.verdict == True, "Pass scenario should result in PASS verdict"
        assert eval_result.ic_pass == True
        assert eval_result.hr_pass == True
        assert eval_result.stability_pass == True

    def test_full_wfv_run_15_windows_fail_ic(self) -> None:
        """Execute full 15-window WFV with 'fail_ic' scenario."""
        harness = WFVHarness()
        executor = WFVExecutor()
        generator = WFVSampleDataGenerator(seed=123)

        data = generator.generate_scenario("fail_ic", harness.windows)

        for window in harness.windows:
            predictions, actuals = data[window.window_id]
            executor.validate_predictions(window, predictions, actuals)

        eval_result = executor.evaluate_all_windows()

        assert eval_result.verdict == False, "Fail IC scenario should result in FAIL verdict"
        assert eval_result.ic_pass == False, "IC gate should fail"

    def test_full_wfv_run_summary_readable(self) -> None:
        """Execute full run and verify summary output."""
        harness = WFVHarness()
        executor = WFVExecutor()
        generator = WFVSampleDataGenerator(seed=999)

        data = generator.generate_scenario("realistic", harness.windows)

        for window in harness.windows[:5]:
            predictions, actuals = data[window.window_id]
            executor.validate_predictions(window, predictions, actuals)

        executor.evaluate_all_windows()
        summary = executor.summary()

        assert "WFV Execution Summary" in summary
        assert "5 windows" in summary
        assert "B-004 VERDICT:" in summary
        print("\n" + summary)

    def test_full_wfv_export_to_dict(self) -> None:
        """Execute full run and export to dictionary."""
        harness = WFVHarness()
        executor = WFVExecutor()
        generator = WFVSampleDataGenerator(seed=777)

        data = generator.generate_scenario("realistic", harness.windows)

        for window in harness.windows[:8]:
            predictions, actuals = data[window.window_id]
            executor.validate_predictions(window, predictions, actuals)

        executor.evaluate_all_windows()
        result_dict = executor.to_dict()

        assert result_dict["window_count"] == 8
        assert len(result_dict["windows"]) == 8
        assert "evaluation" in result_dict
        assert result_dict["evaluation"]["verdict"] is not None

    def test_wfv_generator_scenarios(self) -> None:
        """Test all generator scenarios produce valid data."""
        harness = WFVHarness()
        generator = WFVSampleDataGenerator()

        scenarios = ["pass", "fail_ic", "fail_hr", "fail_stability", "realistic"]

        for scenario in scenarios:
            data = generator.generate_scenario(scenario, harness.windows)

            assert len(data) == 15, f"Scenario '{scenario}': should have 15 windows"

            for window_id, (predictions, actuals) in data.items():
                assert len(predictions) > 0, f"{scenario}/{window_id}: no predictions"
                assert len(predictions) == len(actuals), f"{scenario}/{window_id}: mismatch"

                for pred in predictions:
                    assert "predicted_return_pct" in pred
                    assert "predicted_direction" in pred
                    assert pred["predicted_direction"] in ["LONG", "SHORT", "NEUTRAL"]

    def test_full_wfv_stability_variation_scenario(self) -> None:
        """Test full run with varying metrics (fail_stability scenario)."""
        harness = WFVHarness()
        executor = WFVExecutor()
        generator = WFVSampleDataGenerator(seed=555)

        data = generator.generate_scenario("fail_stability", harness.windows)

        for window in harness.windows:
            predictions, actuals = data[window.window_id]
            executor.validate_predictions(window, predictions, actuals)

        eval_result = executor.evaluate_all_windows()

        assert eval_result.stability_value is not None, "Stability should be computed"
        assert eval_result.stability_threshold == 0.75, "Stability threshold frozen at 0.75"

    def test_full_wfv_metric_values_reasonable(self) -> None:
        """Verify that computed metrics are in valid ranges."""
        harness = WFVHarness()
        executor = WFVExecutor()
        generator = WFVSampleDataGenerator(seed=333)

        data = generator.generate_scenario("realistic", harness.windows[:10])

        for window in harness.windows[:10]:
            predictions, actuals = data[window.window_id]
            executor.validate_predictions(window, predictions, actuals)

        eval_result = executor.evaluate_all_windows()

        assert -1.0 <= eval_result.ic_value <= 1.0, "IC must be in [-1, 1]"
        assert 0.0 <= eval_result.hr_value <= 1.0, "HR must be in [0, 1]"
        assert eval_result.stability_value >= 0.0, "Stability must be non-negative"
