"""Tests for DATA-SRC-COINDESK-001 Checkpoint 6: Signal Quality Assessment."""

import pytest
from src.layers.layer1_data.coindesk_checkpoint6_signal_quality import (
    Checkpoint6SignalQuality,
)


class TestCheckpoint6SignalQuality:
    """Test signal quality assessment framework."""

    def test_validator_init(self):
        """Test validator initialization."""
        validator = Checkpoint6SignalQuality()
        assert validator.ASSETS == ["BTC", "ETH", "SOL"]

    def test_compute_ttcr_zscore_no_data(self):
        """Test zscore computation with missing data returns SKIPPED."""
        validator = Checkpoint6SignalQuality()
        result = validator.compute_ttcr_zscore()

        assert result["status"] == "SKIPPED"
        assert result["verdict"] == "UNVERIFIED"
        assert "No TTCR data" in result["error"]

    def test_compute_ttcr_zscore_insufficient_length(self):
        """Test zscore computation with insufficient data."""
        validator = Checkpoint6SignalQuality()
        short_series = [0.5, 0.51, 0.52]  # Only 3 points, window=7

        result = validator.compute_ttcr_zscore(ttcr_series=short_series, window=7)

        assert result["status"] == "SKIPPED"
        assert "insufficient length" in result["error"].lower()

    def test_compute_ttcr_zscore_with_data(self):
        """Test zscore computation with sufficient data."""
        validator = Checkpoint6SignalQuality()
        ttcr_series = [0.5, 0.51, 0.52, 0.51, 0.50, 0.51, 0.52, 0.53, 0.54, 0.55]

        result = validator.compute_ttcr_zscore(
            ttcr_series=ttcr_series,
            window=7
        )

        assert result["checkpoint"] == "C6_SIGNAL_QUALITY"
        assert result["status"] == "RESEARCH_READY"
        assert result["data_points"] == len(ttcr_series)
        assert result["metric"] == "TTCR zscore"

    def test_correlate_zscore_to_expansion_no_data(self):
        """Test correlation with missing data returns SKIPPED."""
        validator = Checkpoint6SignalQuality()
        result = validator.correlate_zscore_to_expansion()

        assert result["status"] == "SKIPPED"
        assert result["verdict"] == "UNVERIFIED"
        assert "Missing" in result["error"]

    def test_correlate_zscore_to_expansion_length_mismatch(self):
        """Test correlation with mismatched series lengths."""
        validator = Checkpoint6SignalQuality()
        zscore = [0.5, 0.6, 0.7]
        expansion = [1.02, 1.03]  # Different length

        result = validator.correlate_zscore_to_expansion(
            ttcr_zscore=zscore,
            volume_expansion_7d=expansion
        )

        assert result["status"] == "SKIPPED"
        assert "length mismatch" in result["error"].lower()

    def test_correlate_zscore_to_expansion_with_data(self):
        """Test correlation analysis with data."""
        validator = Checkpoint6SignalQuality()
        zscore = [0.5, 0.6, 0.7, 0.8, 0.9]
        expansion = [1.02, 1.03, 1.04, 1.05, 1.06]

        result = validator.correlate_zscore_to_expansion(
            ttcr_zscore=zscore,
            volume_expansion_7d=expansion
        )

        assert result["checkpoint"] == "C6_SIGNAL_QUALITY"
        assert result["status"] == "RESEARCH_READY"
        assert result["data_points"] == 5
        assert "High TTCR zscore predicts" in result["hypothesis"]

    def test_validate_predictive_threshold_above_threshold(self):
        """Test predictive power validation when above threshold."""
        validator = Checkpoint6SignalQuality()
        result = validator.validate_predictive_threshold(
            mean_high=1.08,
            mean_low=1.02,
            min_difference=0.05
        )

        assert result["is_predictive"] is True
        assert "predictive power" in result["interpretation"].lower()

    def test_validate_predictive_threshold_below_threshold(self):
        """Test predictive power validation when below threshold."""
        validator = Checkpoint6SignalQuality()
        result = validator.validate_predictive_threshold(
            mean_high=1.03,
            mean_low=1.02,
            min_difference=0.05
        )

        assert result["is_predictive"] is False
        assert "lacks predictive" in result["interpretation"].lower()

    def test_validate_predictive_threshold_edge_case(self):
        """Test predictive power at boundary."""
        validator = Checkpoint6SignalQuality()
        result = validator.validate_predictive_threshold(
            mean_high=1.05,
            mean_low=1.00,
            min_difference=0.05
        )

        assert result["is_predictive"] is True

    def test_validate_predictive_threshold_negative_difference(self):
        """Test predictive power with inverted signal (negative correlation)."""
        validator = Checkpoint6SignalQuality()
        result = validator.validate_predictive_threshold(
            mean_high=1.00,
            mean_low=1.07,  # Expansion is higher when zscore is low (inverse)
            min_difference=0.05
        )

        assert result["is_predictive"] is True  # Uses abs(difference)
        assert "predictive" in result["interpretation"].lower()

    def test_assess_signal_regime_consistency_no_data(self):
        """Test regime consistency assessment with no regime data."""
        validator = Checkpoint6SignalQuality()
        result = validator.assess_signal_regime_consistency()

        assert result["verdict"] == "RESEARCH_READY"
        assert "regimes_tested" in result

    def test_assess_signal_regime_consistency_with_regimes(self):
        """Test regime consistency assessment with regime data."""
        validator = Checkpoint6SignalQuality()
        regimes = [
            ("2026-01-01", "bullish"),
            ("2026-02-01", "sideways"),
            ("2026-03-01", "bearish"),
        ]

        result = validator.assess_signal_regime_consistency(regime_changes=regimes)

        assert result["verdict"] == "RESEARCH"
        assert len(result["consistency"]) == 3
        assert "bullish" in result["consistency"]

    def test_generate_report_structure(self):
        """Test report generation."""
        validator = Checkpoint6SignalQuality()
        report = validator.generate_report()

        assert report["checkpoint"] == "C6_SIGNAL_QUALITY"
        assert report["status"] == "RESEARCH_MODE"
        assert "validation_plan" in report
        assert "expected_findings" in report
        assert "success_criteria" in report

    def test_generate_report_validation_plan(self):
        """Test report validation plan is complete."""
        validator = Checkpoint6SignalQuality()
        report = validator.generate_report()

        plan = report["validation_plan"]
        assert len(plan) >= 6
        assert any("Load C5" in step for step in plan.values())
        assert any("TTCR zscore" in step for step in plan.values())
        assert any("expansion" in step.lower() for step in plan.values())
        assert any("Pearson" in step for step in plan.values())

    def test_generate_report_success_criteria(self):
        """Test success criteria are defined."""
        validator = Checkpoint6SignalQuality()
        report = validator.generate_report()

        criteria = report["success_criteria"]
        assert len(criteria) >= 6
        assert any("C5" in criterion for criterion in criteria)
        assert any("zscore" in criterion.lower() for criterion in criteria)
        assert any("predictive" in criterion.lower() for criterion in criteria)

    def test_generate_report_dependencies(self):
        """Test dependencies are documented."""
        validator = Checkpoint6SignalQuality()
        report = validator.generate_report()

        deps = report["dependencies"]
        assert len(deps) >= 3
        assert any("C5" in dep for dep in deps)
        assert any("TTCR" in dep for dep in deps)
        assert any("Layer 2" in dep for dep in deps)

    def test_generate_report_non_wfv_note(self):
        """Test that non-WFV disclaimer is included."""
        validator = Checkpoint6SignalQuality()
        report = validator.generate_report()

        assert "non_wfv_note" in report
        assert "research-level" in report["non_wfv_note"].lower()
        assert "NOT walk-forward" in report["non_wfv_note"]

    def test_metric_field_structure(self):
        """Test metric fields are correctly structured."""
        validator = Checkpoint6SignalQuality()

        # Test zscore result structure
        zscore_result = validator.compute_ttcr_zscore(
            ttcr_series=[0.5] * 10
        )
        assert "zscore_stats" in zscore_result
        assert "mean" in zscore_result["zscore_stats"]

        # Test correlation result structure
        corr_result = validator.correlate_zscore_to_expansion(
            ttcr_zscore=[0.5] * 5,
            volume_expansion_7d=[1.02] * 5
        )
        assert "correlation" in corr_result
        assert "predictive_power" in corr_result


def test_checkpoint_6_can_run():
    """Test that C6 validation can be executed."""
    from src.layers.layer1_data.coindesk_checkpoint6_signal_quality import (
        checkpoint_6_status,
    )

    report = checkpoint_6_status()

    assert report is not None
    assert report["checkpoint"] == "C6_SIGNAL_QUALITY"
    assert "validation_plan" in report
