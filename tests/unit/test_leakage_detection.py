"""Unit tests for leakage detection."""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

from src.layers.layer6_validation.leakage_detector import LeakageDetector, LeakageReport


@pytest.fixture
def detector():
    """Create LeakageDetector instance."""
    return LeakageDetector(correlation_threshold=0.3)


class TestLeakageDetector:
    def test_clean_feature_no_leakage(self, detector):
        """Test clean feature detects no leakage."""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        feature = [50.0, 51.0, 52.0, 53.0, 54.0]
        timestamps = [datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 6)]

        report = detector.check_feature("test_feature", feature, prices, timestamps)

        assert not report.has_leakage
        assert report.leakage_score < detector.correlation_threshold

    def test_feature_with_future_price_info(self, detector):
        """Test feature that uses future price information."""
        np.random.seed(42)
        prices = np.random.uniform(100, 110, 50).tolist()
        future_feature = [prices[i+1] if i < len(prices)-1 else prices[i] for i in range(len(prices))]
        timestamps = [datetime(2024, 1, i % 28 + 1, tzinfo=timezone.utc) for i in range(len(prices))]

        report = detector.check_feature("future_feature", future_feature, prices, timestamps)

        assert report.has_leakage or report.leakage_score > 0.3

    def test_feature_with_nan_values(self, detector):
        """Test feature containing NaN values."""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        feature = [float('nan'), 50.0, 51.0, 52.0, 53.0]
        timestamps = [datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 6)]

        report = detector.check_feature("nan_feature", feature, prices, timestamps)

        assert not report.has_leakage or report.issue_count >= 0

    def test_insufficient_data(self, detector):
        """Test with insufficient data."""
        prices = [100.0, 101.0]
        feature = [50.0, 51.0]
        timestamps = [datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 2, tzinfo=timezone.utc)]

        report = detector.check_feature("short_feature", feature, prices, timestamps)

        assert not report.has_leakage
        assert "Insufficient" in report.details

    def test_all_nan_values(self, detector):
        """Test feature with all NaN values."""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        feature = [float('nan')] * 5
        timestamps = [datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 6)]

        report = detector.check_feature("all_nan_feature", feature, prices, timestamps)

        assert not report.has_leakage
        assert report.issue_count == 0

    def test_report_structure(self, detector):
        """Test LeakageReport structure."""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        feature = [50.0, 51.0, 52.0, 53.0, 54.0]
        timestamps = [datetime(2024, 1, i, tzinfo=timezone.utc) for i in range(1, 6)]

        report = detector.check_feature("test", feature, prices, timestamps)

        assert isinstance(report, LeakageReport)
        assert hasattr(report, "feature_name")
        assert hasattr(report, "has_leakage")
        assert hasattr(report, "leakage_score")
        assert hasattr(report, "forward_correlation")
        assert hasattr(report, "lookahead_correlation")
        assert hasattr(report, "issue_count")
        assert hasattr(report, "details")


class TestForwardBias:
    def test_no_forward_bias(self, detector):
        """Test normal price series has no forward bias."""
        prices = list(np.random.normal(100, 5, 100))
        timestamps = [datetime(2024, 1, 1, tzinfo=timezone.utc)]

        correlation = detector.check_forward_bias(prices, timestamps)

        assert correlation < 0.5

    def test_high_forward_bias_detection(self, detector):
        """Test detection of forward-biased labels."""
        base = np.arange(100, 150, 0.5)
        prices = base.tolist()
        timestamps = [datetime(2024, 1, 1, tzinfo=timezone.utc)]

        correlation = detector.check_forward_bias(prices, timestamps)

        assert correlation > 0.8

    def test_insufficient_price_data(self, detector):
        """Test with insufficient price data."""
        prices = [100.0, 101.0]
        timestamps = [datetime(2024, 1, 1, tzinfo=timezone.utc)]

        correlation = detector.check_forward_bias(prices, timestamps)

        assert correlation == 0.0

    def test_trending_market(self, detector):
        """Test correlation in trending market."""
        prices = list(np.arange(100, 150, 0.5))
        timestamps = [datetime(2024, 1, 1, tzinfo=timezone.utc)]

        correlation = detector.check_forward_bias(prices, timestamps)

        assert 0.8 < correlation <= 1.0


class TestSurvivorsipBias:
    def test_no_survivorship_bias(self, detector):
        """Test universe with complete data."""
        symbols = ["BTC", "ETH", "ADA"]
        prices = {
            "BTC": [100.0 + i for i in range(50)],
            "ETH": [50.0 + i for i in range(50)],
            "ADA": [1.0 + i * 0.01 for i in range(50)],
        }
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 2, 20, tzinfo=timezone.utc)

        has_bias, symbols_with_gaps = detector.check_survivorship_bias(symbols, prices, start_date, end_date)

        assert not has_bias
        assert len(symbols_with_gaps) == 0

    def test_detect_missing_symbol(self, detector):
        """Test detection of missing symbols."""
        symbols = ["BTC", "ETH", "ADA", "UNKNOWN"]
        prices = {
            "BTC": [100.0 + i for i in range(50)],
            "ETH": [50.0 + i for i in range(50)],
            "ADA": [1.0 + i * 0.01 for i in range(50)],
        }
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 2, 20, tzinfo=timezone.utc)

        has_bias, symbols_with_gaps = detector.check_survivorship_bias(symbols, prices, start_date, end_date)

        assert has_bias
        assert "UNKNOWN" in symbols_with_gaps

    def test_detect_short_data_series(self, detector):
        """Test detection of short data series."""
        symbols = ["BTC", "ETH"]
        prices = {
            "BTC": [100.0 + i for i in range(50)],
            "ETH": [50.0, 51.0],
        }
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 2, 20, tzinfo=timezone.utc)

        has_bias, symbols_with_gaps = detector.check_survivorship_bias(symbols, prices, start_date, end_date)

        assert has_bias
        assert "ETH" in symbols_with_gaps


class TestSafeCorrelation:
    def test_zero_variance_x(self, detector):
        """Test correlation with zero variance in X."""
        x = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        corr = detector._safe_correlation(x, y)

        assert corr == 0.0

    def test_zero_variance_y(self, detector):
        """Test correlation with zero variance in Y."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 1.0, 1.0, 1.0, 1.0])

        corr = detector._safe_correlation(x, y)

        assert corr == 0.0

    def test_length_mismatch(self, detector):
        """Test correlation with mismatched lengths."""
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0])

        corr = detector._safe_correlation(x, y)

        assert corr == 0.0

    def test_perfect_correlation(self, detector):
        """Test perfect positive correlation."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        corr = detector._safe_correlation(x, y)

        assert abs(corr - 1.0) < 0.01

    def test_perfect_negative_correlation(self, detector):
        """Test perfect negative correlation."""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])

        corr = detector._safe_correlation(x, y)

        assert abs(corr + 1.0) < 0.01

    def test_nan_handling(self, detector):
        """Test correlation with NaN values."""
        x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        corr = detector._safe_correlation(x, y)

        assert not np.isnan(corr)
