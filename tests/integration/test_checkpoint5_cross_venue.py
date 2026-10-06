"""Tests for DATA-SRC-COINDESK-001 Checkpoint 5: Cross-Venue Validation."""

import pytest
from src.layers.layer1_data.coindesk_checkpoint5_cross_venue import (
    Checkpoint5CrossVenueValidator,
)


class TestCheckpoint5CrossVenueValidator:
    """Test cross-venue comparison framework."""

    def test_validator_init(self):
        """Test validator initialization."""
        validator = Checkpoint5CrossVenueValidator()
        assert validator.ASSETS == ["BTC", "ETH", "SOL"]

    def test_compare_volumes_no_data(self):
        """Test comparison with missing data returns SKIPPED."""
        validator = Checkpoint5CrossVenueValidator()
        result = validator.compare_volumes(asset="BTC")

        assert result["status"] == "SKIPPED"
        assert result["verdict"] == "UNVERIFIED"
        assert "No volume data" in result["error"]

    def test_compare_volumes_with_data(self):
        """Test comparison with data available."""
        validator = Checkpoint5CrossVenueValidator()
        coindesk_vols = [100.0, 101.0, 102.0]
        binance_vols = [30.0, 31.0, 32.0]

        result = validator.compare_volumes(
            asset="BTC",
            coindesk_volumes=coindesk_vols,
            binance_volumes=binance_vols
        )

        assert result["checkpoint"] == "C5_CROSS_VENUE"
        assert result["status"] == "RESEARCH_READY"
        assert result["data_points"] == 0  # Research mode

    def test_validate_ratio_range_in_range(self):
        """Test BCR validation when ratio is in expected range."""
        validator = Checkpoint5CrossVenueValidator()
        result = validator.validate_ratio_range(
            ratio_mean=0.5,
            ratio_min=0.4,
            ratio_max=0.6,
            expected_range=(0.3, 0.8)
        )

        assert result["in_range"] is True
        assert result["checkpoint"] == "C5_CROSS_VENUE"
        assert "dominates" in result["interpretation"].lower()

    def test_validate_ratio_range_out_of_range(self):
        """Test BCR validation when ratio is outside expected range."""
        validator = Checkpoint5CrossVenueValidator()
        result = validator.validate_ratio_range(
            ratio_mean=0.1,
            ratio_min=0.08,
            ratio_max=0.12,
            expected_range=(0.3, 0.8)
        )

        assert result["in_range"] is False
        assert "investigate" in result["interpretation"].lower()

    def test_validate_ratio_range_edge_cases(self):
        """Test BCR validation at boundaries."""
        validator = Checkpoint5CrossVenueValidator()

        # Test at lower boundary
        result_low = validator.validate_ratio_range(
            ratio_mean=0.3,
            ratio_min=0.29,
            ratio_max=0.31,
            expected_range=(0.3, 0.8)
        )
        assert result_low["in_range"] is True

        # Test at upper boundary
        result_high = validator.validate_ratio_range(
            ratio_mean=0.8,
            ratio_min=0.79,
            ratio_max=0.81,
            expected_range=(0.3, 0.8)
        )
        assert result_high["in_range"] is True

    def test_validate_correlation_strong_significant(self):
        """Test correlation validation when strong and significant."""
        validator = Checkpoint5CrossVenueValidator()
        result = validator.validate_correlation(
            pearson_r=0.75,
            p_value=0.001,
            min_r=0.6
        )

        assert result["strong"] is True
        assert result["significant"] is True
        assert "strong daily correlation" in result["interpretation"].lower()

    def test_validate_correlation_weak(self):
        """Test correlation validation when weak."""
        validator = Checkpoint5CrossVenueValidator()
        result = validator.validate_correlation(
            pearson_r=0.4,
            p_value=0.05,
            min_r=0.6
        )

        assert result["strong"] is False
        assert "weak" in result["interpretation"].lower()

    def test_validate_correlation_not_significant(self):
        """Test correlation validation when not statistically significant."""
        validator = Checkpoint5CrossVenueValidator()
        result = validator.validate_correlation(
            pearson_r=0.65,
            p_value=0.1,
            min_r=0.6
        )

        assert result["significant"] is False
        assert "weak" in result["interpretation"].lower()

    def test_validate_correlation_negative(self):
        """Test correlation validation with negative correlation."""
        validator = Checkpoint5CrossVenueValidator()
        result = validator.validate_correlation(
            pearson_r=-0.75,
            p_value=0.001,
            min_r=0.6
        )

        assert result["strong"] is True  # abs(r) >= 0.6
        assert result["significant"] is True

    def test_generate_report_structure(self):
        """Test report generation."""
        validator = Checkpoint5CrossVenueValidator()
        report = validator.generate_report()

        assert report["checkpoint"] == "C5_CROSS_VENUE"
        assert report["status"] == "RESEARCH_MODE"
        assert "validation_plan" in report
        assert "expected_findings" in report
        assert "success_criteria" in report

    def test_generate_report_validation_plan(self):
        """Test report validation plan is complete."""
        validator = Checkpoint5CrossVenueValidator()
        report = validator.generate_report()

        plan = report["validation_plan"]
        assert len(plan) >= 6
        assert any("Load C4" in step for step in plan.values())
        assert any("Binance" in step for step in plan.values())
        assert any("BCR" in step for step in plan.values())
        assert any("correlation" in step.lower() for step in plan.values())

    def test_generate_report_success_criteria(self):
        """Test success criteria are defined."""
        validator = Checkpoint5CrossVenueValidator()
        report = validator.generate_report()

        criteria = report["success_criteria"]
        assert len(criteria) >= 4
        assert any("C4" in criterion for criterion in criteria)
        assert any("BCR" in criterion or "0.3-0.8" in criterion for criterion in criteria)
        assert any("correlation" in criterion.lower() for criterion in criteria)

    def test_generate_report_dependencies(self):
        """Test dependencies are documented."""
        validator = Checkpoint5CrossVenueValidator()
        report = validator.generate_report()

        deps = report["dependencies"]
        assert len(deps) >= 2
        assert any("C4" in dep for dep in deps)
        assert any("Binance" in dep for dep in deps)


def test_checkpoint_5_can_run():
    """Test that C5 validation can be executed."""
    from src.layers.layer1_data.coindesk_checkpoint5_cross_venue import (
        checkpoint_5_status,
    )

    report = checkpoint_5_status()

    assert report is not None
    assert report["checkpoint"] == "C5_CROSS_VENUE"
    assert "validation_plan" in report
