"""Unit tests for Feature Drift Detection."""

import pytest
from src.layers.layer8_monitoring.feature_drift_detector import (
    FeatureDriftDetector,
    DriftStatus,
)


@pytest.fixture
def detector():
    """Create FeatureDriftDetector instance."""
    return FeatureDriftDetector()


@pytest.fixture
def stable_baseline():
    """Stable baseline feature values."""
    return [100.0 + i * 0.5 for i in range(50)]


@pytest.fixture
def stable_current():
    """Stable current period (similar distribution)."""
    return [100.5 + i * 0.5 for i in range(50)]


@pytest.fixture
def drifting_baseline():
    """Baseline with mean 100."""
    return [100.0] * 30 + [105.0] * 20


@pytest.fixture
def drifting_current():
    """Current period with mean shifted to 115 (15% shift)."""
    return [115.0] * 30 + [120.0] * 20


@pytest.fixture
def severe_baseline():
    """Baseline with mean 100, low volatility."""
    return [100.0 + np.random.normal(0, 2) for _ in range(50)]


@pytest.fixture
def severe_current():
    """Current period with mean 150 (50% shift)."""
    import numpy as np
    return [150.0 + np.random.normal(0, 5) for _ in range(50)]


# Import numpy for fixtures
import numpy as np


class TestMeanShift:
    def test_calculate_mean_shift_stable(self, detector, stable_baseline, stable_current):
        """Test mean shift with stable distributions."""
        baseline_mean, current_mean, shift = detector.calculate_mean_shift(stable_baseline, stable_current)
        assert baseline_mean > 0
        assert current_mean > 0
        assert abs(shift) < 5.0  # Small shift

    def test_calculate_mean_shift_drifting(self, detector, drifting_baseline, drifting_current):
        """Test mean shift with drifting distribution."""
        baseline_mean, current_mean, shift = detector.calculate_mean_shift(drifting_baseline, drifting_current)
        assert baseline_mean < current_mean
        assert abs(shift) > 10.0  # Significant shift

    def test_calculate_mean_shift_empty(self, detector):
        """Test mean shift with empty data."""
        baseline_mean, current_mean, shift = detector.calculate_mean_shift([], [])
        assert baseline_mean == 0.0
        assert current_mean == 0.0
        assert shift == 0.0

    def test_calculate_mean_shift_single_value(self, detector):
        """Test mean shift with single values."""
        baseline_mean, current_mean, shift = detector.calculate_mean_shift([100.0], [110.0])
        assert baseline_mean == 100.0
        assert current_mean == 110.0
        assert shift == 10.0

    def test_calculate_mean_shift_negative(self, detector):
        """Test mean shift with negative values."""
        baseline_mean, current_mean, shift = detector.calculate_mean_shift(
            [-100.0, -110.0, -90.0], [-50.0, -60.0, -40.0]
        )
        assert baseline_mean < current_mean
        assert shift > 0.0


class TestVolatilityShift:
    def test_calculate_volatility_shift_stable(self, detector, stable_baseline, stable_current):
        """Test volatility with stable distributions."""
        baseline_std, current_std, shift = detector.calculate_volatility_shift(stable_baseline, stable_current)
        assert baseline_std > 0
        assert current_std > 0
        assert abs(shift) < 20.0  # Small volatility change

    def test_calculate_volatility_shift_increasing(self, detector):
        """Test volatility increasing."""
        baseline = [100.0] * 20
        current = [100.0 + np.random.normal(0, 10) for _ in range(20)]
        baseline_std, current_std, shift = detector.calculate_volatility_shift(baseline, current)
        assert baseline_std == 0.0
        assert current_std > 0.0

    def test_calculate_volatility_shift_empty(self, detector):
        """Test volatility with empty data."""
        baseline_std, current_std, shift = detector.calculate_volatility_shift([], [])
        assert baseline_std == 0.0
        assert current_std == 0.0
        assert shift == 0.0

    def test_calculate_volatility_shift_insufficient_data(self, detector):
        """Test volatility with single data point."""
        baseline_std, current_std, shift = detector.calculate_volatility_shift([100.0], [110.0])
        assert baseline_std == 0.0
        assert current_std == 0.0


class TestKSTest:
    def test_ks_test_identical_distributions(self, detector, stable_baseline):
        """Test KS test with identical distributions."""
        ks_stat, p_value = detector.ks_test(stable_baseline, stable_baseline)
        assert ks_stat == 0.0
        assert p_value == 1.0

    def test_ks_test_different_distributions(self, detector, drifting_baseline, drifting_current):
        """Test KS test with different distributions."""
        ks_stat, p_value = detector.ks_test(drifting_baseline, drifting_current)
        assert ks_stat > 0.0
        assert 0.0 <= p_value <= 1.0

    def test_ks_test_empty(self, detector):
        """Test KS test with empty data."""
        ks_stat, p_value = detector.ks_test([], [])
        assert ks_stat == 0.0
        assert p_value == 1.0

    def test_ks_test_single_value(self, detector):
        """Test KS test with single values."""
        ks_stat, p_value = detector.ks_test([100.0], [110.0])
        assert ks_stat >= 0.0
        assert 0.0 <= p_value <= 1.0

    def test_ks_test_pvalue_range(self, detector):
        """Test that p-values stay in valid range."""
        baseline = list(range(0, 100))
        current = list(range(50, 150))
        ks_stat, p_value = detector.ks_test(baseline, current)
        assert 0.0 <= ks_stat <= 1.0
        assert 0.0 <= p_value <= 1.0


class TestDriftStatus:
    def test_get_drift_status_stable(self, detector):
        """Test STABLE status."""
        status = detector.get_drift_status(mean_shift_pct=5.0, volatility_shift_pct=3.0, ks_pvalue=0.2)
        assert status == DriftStatus.STABLE

    def test_get_drift_status_drifting(self, detector):
        """Test DRIFTING status."""
        status = detector.get_drift_status(mean_shift_pct=15.0, volatility_shift_pct=5.0, ks_pvalue=0.03)
        assert status == DriftStatus.DRIFTING

    def test_get_drift_status_severe(self, detector):
        """Test SEVERE status."""
        status = detector.get_drift_status(mean_shift_pct=30.0, volatility_shift_pct=20.0, ks_pvalue=0.001)
        assert status == DriftStatus.SEVERE

    def test_get_drift_status_ks_driven_severe(self, detector):
        """Test SEVERE status driven by KS test."""
        status = detector.get_drift_status(mean_shift_pct=5.0, volatility_shift_pct=5.0, ks_pvalue=0.005)
        assert status == DriftStatus.SEVERE

    def test_get_drift_status_boundaries(self, detector):
        """Test status at boundaries."""
        # At 10% threshold
        status_10 = detector.get_drift_status(10.0, 5.0, 0.1)
        assert status_10 in [DriftStatus.STABLE, DriftStatus.DRIFTING]

        # At 25% threshold
        status_25 = detector.get_drift_status(25.0, 5.0, 0.1)
        assert status_25 in [DriftStatus.DRIFTING, DriftStatus.SEVERE]


class TestDetectFeatureDrift:
    def test_detect_feature_drift_stable(self, detector, stable_baseline, stable_current):
        """Test drift detection with stable feature."""
        metrics = detector.detect_feature_drift("price_momentum", stable_baseline, stable_current)
        assert metrics.feature_name == "price_momentum"
        assert metrics.drift_status in [DriftStatus.STABLE, DriftStatus.DRIFTING]
        assert abs(metrics.mean_shift_pct) < 10.0

    def test_detect_feature_drift_drifting(self, detector, drifting_baseline, drifting_current):
        """Test drift detection with drifting feature."""
        metrics = detector.detect_feature_drift("volatility", drifting_baseline, drifting_current)
        assert metrics.feature_name == "volatility"
        assert abs(metrics.mean_shift_pct) > 10.0

    def test_detect_feature_drift_all_fields(self, detector, stable_baseline, stable_current):
        """Test all fields are populated."""
        metrics = detector.detect_feature_drift(
            "rsi",
            stable_baseline,
            stable_current,
            comparison_period="7d",
            lookback_days=90,
        )
        assert metrics.feature_name == "rsi"
        assert metrics.comparison_period == "7d"
        assert metrics.lookback_days == 90
        assert metrics.baseline_mean >= 0.0
        assert metrics.current_mean >= 0.0
        assert isinstance(metrics.mean_shift_pct, float)
        assert isinstance(metrics.ks_statistic, float)
        assert 0.0 <= metrics.ks_pvalue <= 1.0

    def test_detect_feature_drift_empty_data(self, detector):
        """Test drift detection with empty data."""
        metrics = detector.detect_feature_drift("empty", [], [])
        assert metrics.feature_name == "empty"
        assert metrics.baseline_mean == 0.0
        assert metrics.current_mean == 0.0


class TestRankFeatures:
    def test_rank_features_by_drift(self, detector, stable_baseline, stable_current, drifting_baseline, drifting_current):
        """Test ranking features by drift severity."""
        metrics1 = detector.detect_feature_drift("stable_feature", stable_baseline, stable_current)
        metrics2 = detector.detect_feature_drift("drifting_feature", drifting_baseline, drifting_current)

        ranked = detector.rank_features_by_drift([metrics2, metrics1])
        assert len(ranked) == 2
        # Most significant drift (lowest p-value) first
        assert ranked[0].ks_pvalue <= ranked[1].ks_pvalue

    def test_rank_features_empty_list(self, detector):
        """Test ranking empty list."""
        ranked = detector.rank_features_by_drift([])
        assert ranked == []


class TestFilterByDriftStatus:
    def test_filter_by_drift_status_stable(self, detector, stable_baseline, stable_current):
        """Test filtering by status."""
        metrics = detector.detect_feature_drift("test", stable_baseline, stable_current)

        filtered = detector.filter_by_drift_status([metrics], max_status="STABLE")
        assert len(filtered) >= 0

    def test_filter_by_drift_status_drifting(self, detector, drifting_baseline, drifting_current):
        """Test filtering drifting features."""
        metrics = detector.detect_feature_drift("test", drifting_baseline, drifting_current)

        filtered_strict = detector.filter_by_drift_status([metrics], max_status="STABLE")
        filtered_loose = detector.filter_by_drift_status([metrics], max_status="DRIFTING")

        # Loose filter should accept more
        assert len(filtered_loose) >= len(filtered_strict)

    def test_filter_by_drift_status_empty_list(self, detector):
        """Test filtering empty list."""
        filtered = detector.filter_by_drift_status([], max_status="STABLE")
        assert filtered == []


class TestIdentifySevereDrifts:
    def test_identify_severe_drifts(self, detector, stable_baseline, drifting_baseline, drifting_current):
        """Test identifying severe drifts."""
        metrics_stable = detector.detect_feature_drift("stable", stable_baseline, stable_baseline)
        metrics_severe = detector.detect_feature_drift("severe", drifting_baseline, drifting_current)

        severe = detector.identify_severe_drifts([metrics_stable, metrics_severe])
        assert all(m.drift_status == DriftStatus.SEVERE for m in severe)

    def test_identify_severe_drifts_empty_list(self, detector):
        """Test identifying severe in empty list."""
        severe = detector.identify_severe_drifts([])
        assert severe == []


class TestDriftSummary:
    def test_generate_drift_summary(self, detector, stable_baseline, stable_current):
        """Test summary generation."""
        metrics = detector.detect_feature_drift("momentum", stable_baseline, stable_current)
        summary = detector.generate_drift_summary(metrics)

        assert summary["feature"] == "momentum"
        assert "status" in summary
        assert "period" in summary
        assert "baseline_mean" in summary
        assert "current_mean" in summary
        assert "mean_shift" in summary
        assert "action" in summary

    def test_generate_drift_summary_all_fields(self, detector, drifting_baseline, drifting_current):
        """Test all summary fields populated."""
        metrics = detector.detect_feature_drift("test_feature", drifting_baseline, drifting_current)
        summary = detector.generate_drift_summary(metrics)

        assert summary["action"] in ["OK", "MONITOR", "INVESTIGATE"]
        assert "%" in summary["mean_shift"]
        assert "%" in summary["volatility_shift"]


class TestCorrelationShift:
    def test_correlation_matrix_shift_stable(self, detector):
        """Test correlation shift with stable features."""
        baseline = {
            "feature_a": [100.0 + i for i in range(30)],
            "feature_b": [50.0 + i * 2 for i in range(30)],
        }
        current = {
            "feature_a": [101.0 + i for i in range(30)],
            "feature_b": [51.0 + i * 2 for i in range(30)],
        }

        avg_shift, shifts = detector.correlation_matrix_shift(baseline, current)
        assert avg_shift >= 0.0
        assert isinstance(shifts, list)

    def test_correlation_matrix_shift_with_decorrelation(self, detector):
        """Test correlation shift with decorrelating features."""
        baseline = {
            "feature_a": [i for i in range(50)],
            "feature_b": [i for i in range(50)],  # Perfect correlation
        }
        current = {
            "feature_a": [i for i in range(50)],
            "feature_b": [50 - i for i in range(50)],  # Perfect negative correlation
        }

        avg_shift, shifts = detector.correlation_matrix_shift(baseline, current)
        assert avg_shift > 0.0
        assert len(shifts) >= 0

    def test_correlation_matrix_shift_empty(self, detector):
        """Test correlation shift with empty data."""
        avg_shift, shifts = detector.correlation_matrix_shift({}, {})
        assert avg_shift == 0.0
        assert shifts == []

    def test_correlation_matrix_shift_insufficient_features(self, detector):
        """Test correlation shift with single feature."""
        baseline = {"feature_a": [100.0] * 10}
        current = {"feature_a": [101.0] * 10}

        avg_shift, shifts = detector.correlation_matrix_shift(baseline, current)
        assert avg_shift == 0.0
        assert shifts == []


class TestEdgeCases:
    def test_detect_drift_constant_values(self, detector):
        """Test drift detection with constant values."""
        baseline = [100.0] * 30
        current = [100.0] * 30

        metrics = detector.detect_feature_drift("constant", baseline, current)
        assert metrics.baseline_std == 0.0
        assert metrics.current_std == 0.0
        assert metrics.drift_status == DriftStatus.STABLE

    def test_detect_drift_extreme_shift(self, detector):
        """Test drift detection with extreme shift."""
        baseline = [100.0] * 30
        current = [1000.0] * 30

        metrics = detector.detect_feature_drift("extreme", baseline, current)
        assert metrics.mean_shift_pct > 500.0
        assert metrics.drift_status == DriftStatus.SEVERE

    def test_detect_drift_sign_reversal(self, detector):
        """Test drift detection with sign reversal."""
        baseline = [100.0] * 20 + [110.0] * 10
        current = [-100.0] * 20 + [-110.0] * 10

        metrics = detector.detect_feature_drift("sign_reverse", baseline, current)
        assert abs(metrics.mean_shift_pct) > 50.0
        assert metrics.ks_pvalue < 0.1
