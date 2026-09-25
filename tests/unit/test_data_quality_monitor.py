"""Unit tests for Data Quality Monitoring."""

import pytest
from src.layers.layer8_monitoring.data_quality_monitor import (
    DataQualityMonitor,
    DataQualityStatus,
)


@pytest.fixture
def monitor():
    """Create DataQualityMonitor instance."""
    return DataQualityMonitor()


@pytest.fixture
def valid_ohlcv():
    """Valid OHLCV data."""
    return {
        "opens": [100.0 + i for i in range(20)],
        "highs": [105.0 + i for i in range(20)],
        "lows": [95.0 + i for i in range(20)],
        "closes": [102.0 + i for i in range(20)],
        "volumes": [1000000 + i * 10000 for i in range(20)],
    }


@pytest.fixture
def invalid_ohlcv_low_high():
    """Invalid OHLCV with low > high."""
    return {
        "opens": [100.0] * 20,
        "highs": [95.0] * 20,  # High < Low
        "lows": [100.0] * 20,
        "closes": [100.0] * 20,
        "volumes": [1000000] * 20,
    }


class TestOHLCVValidation:
    def test_validate_ohlcv_records_valid(self, monitor, valid_ohlcv):
        """Test validation passes for valid data."""
        is_valid, issues = monitor.validate_ohlcv_records(
            "BTC",
            valid_ohlcv["opens"],
            valid_ohlcv["highs"],
            valid_ohlcv["lows"],
            valid_ohlcv["closes"],
            valid_ohlcv["volumes"],
        )
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_ohlcv_records_invalid_ohlc(self, monitor, invalid_ohlcv_low_high):
        """Test validation fails for invalid OHLC."""
        is_valid, issues = monitor.validate_ohlcv_records(
            "BTC",
            invalid_ohlcv_low_high["opens"],
            invalid_ohlcv_low_high["highs"],
            invalid_ohlcv_low_high["lows"],
            invalid_ohlcv_low_high["closes"],
            invalid_ohlcv_low_high["volumes"],
        )
        assert is_valid is False
        assert "invalid_ohlc" in issues

    def test_validate_ohlcv_records_length_mismatch(self, monitor):
        """Test validation fails for length mismatch."""
        is_valid, issues = monitor.validate_ohlcv_records(
            "BTC",
            [100.0] * 20,
            [105.0] * 20,
            [95.0] * 20,
            [102.0] * 15,  # Mismatch
            [1000000] * 20,
        )
        assert is_valid is False
        assert "length_mismatch" in issues

    def test_validate_ohlcv_records_empty_data(self, monitor):
        """Test validation fails for empty data."""
        is_valid, issues = monitor.validate_ohlcv_records("BTC", [], [], [], [], [])
        assert is_valid is False
        assert "empty_data" in issues

    def test_validate_ohlcv_records_negative_volumes(self, monitor, valid_ohlcv):
        """Test validation fails for negative volumes."""
        is_valid, issues = monitor.validate_ohlcv_records(
            "BTC",
            valid_ohlcv["opens"],
            valid_ohlcv["highs"],
            valid_ohlcv["lows"],
            valid_ohlcv["closes"],
            [-1000000] + valid_ohlcv["volumes"][1:],
        )
        assert is_valid is False
        assert "negative_volumes" in issues


class TestGapDetection:
    def test_detect_price_gaps_no_gaps(self, monitor, valid_ohlcv):
        """Test no gaps in smooth data."""
        gap_count, gap_indices = monitor.detect_price_gaps(
            "BTC", valid_ohlcv["closes"], gap_threshold_pct=10.0
        )
        assert gap_count == 0
        assert gap_indices == []

    def test_detect_price_gaps_with_gaps(self, monitor):
        """Test detection of large gaps."""
        closes = [100.0, 100.5, 100.5, 120.0, 120.5]  # Gap at index 2
        gap_count, gap_indices = monitor.detect_price_gaps("BTC", closes, gap_threshold_pct=10.0)
        assert gap_count > 0
        assert len(gap_indices) > 0

    def test_detect_price_gaps_insufficient_data(self, monitor):
        """Test with insufficient data."""
        gap_count, gap_indices = monitor.detect_price_gaps("BTC", [100.0], gap_threshold_pct=10.0)
        assert gap_count == 0
        assert gap_indices == []

    def test_detect_price_gaps_custom_threshold(self, monitor):
        """Test custom gap threshold."""
        closes = [100.0, 110.0, 120.0]  # 10% gaps
        # With 15% threshold, no gaps
        gap_count_15, _ = monitor.detect_price_gaps("BTC", closes, gap_threshold_pct=15.0)
        assert gap_count_15 == 0
        # With 5% threshold, gaps detected
        gap_count_5, _ = monitor.detect_price_gaps("BTC", closes, gap_threshold_pct=5.0)
        assert gap_count_5 > 0


class TestOutlierDetection:
    def test_detect_outliers_zscore(self, monitor):
        """Test Z-score outlier detection."""
        values = [100.0] * 18 + [500.0, 510.0]  # Outliers at end
        outlier_count, indices = monitor.detect_outliers(
            "BTC", values, method="zscore", threshold=3.0
        )
        assert outlier_count > 0
        assert len(indices) > 0

    def test_detect_outliers_iqr(self, monitor):
        """Test IQR outlier detection."""
        values = [100.0] * 20 + [500.0]
        outlier_count, indices = monitor.detect_outliers(
            "BTC", values, method="iqr", threshold=1.5
        )
        assert outlier_count > 0

    def test_detect_outliers_no_outliers(self, monitor):
        """Test no outliers in uniform data."""
        values = [100.0] * 20
        outlier_count, indices = monitor.detect_outliers(
            "BTC", values, method="zscore", threshold=3.0
        )
        assert outlier_count == 0
        assert indices == []

    def test_detect_outliers_insufficient_data(self, monitor):
        """Test with insufficient data."""
        outlier_count, indices = monitor.detect_outliers("BTC", [100.0], method="zscore")
        assert outlier_count == 0


class TestQualityScore:
    def test_calculate_quality_score_perfect(self, monitor):
        """Test perfect data produces high score."""
        score = monitor.calculate_quality_score(
            record_count=100, gap_count=0, missing_fields=0, outlier_count=0
        )
        assert score == 100.0

    def test_calculate_quality_score_with_gaps(self, monitor):
        """Test gaps reduce score."""
        score = monitor.calculate_quality_score(
            record_count=100, gap_count=5, missing_fields=0, outlier_count=0
        )
        assert 0.0 < score < 100.0

    def test_calculate_quality_score_with_outliers(self, monitor):
        """Test outliers reduce score."""
        score = monitor.calculate_quality_score(
            record_count=100, gap_count=0, missing_fields=0, outlier_count=10
        )
        assert 0.0 < score < 100.0

    def test_calculate_quality_score_insufficient_records(self, monitor):
        """Test insufficient records produces zero score."""
        score = monitor.calculate_quality_score(
            record_count=3, gap_count=0, missing_fields=0, outlier_count=0
        )
        assert score == 0.0

    def test_calculate_quality_score_penalties_accumulate(self, monitor):
        """Test multiple penalties reduce score."""
        score_gaps = monitor.calculate_quality_score(
            record_count=100, gap_count=5, missing_fields=0, outlier_count=0
        )
        score_outliers = monitor.calculate_quality_score(
            record_count=100, gap_count=5, missing_fields=0, outlier_count=10
        )
        assert score_outliers < score_gaps


class TestQualityStatus:
    def test_get_quality_status_pass(self, monitor):
        """Test PASS status for high score."""
        status = monitor.get_quality_status(85.0)
        assert status == DataQualityStatus.PASS

    def test_get_quality_status_warning(self, monitor):
        """Test WARNING status for medium score."""
        status = monitor.get_quality_status(65.0)
        assert status == DataQualityStatus.WARNING

    def test_get_quality_status_critical(self, monitor):
        """Test CRITICAL status for low score."""
        status = monitor.get_quality_status(30.0)
        assert status == DataQualityStatus.CRITICAL

    def test_get_quality_status_boundaries(self, monitor):
        """Test status boundaries."""
        assert monitor.get_quality_status(80.0) == DataQualityStatus.PASS
        assert monitor.get_quality_status(79.9) == DataQualityStatus.WARNING
        assert monitor.get_quality_status(50.0) == DataQualityStatus.WARNING
        assert monitor.get_quality_status(49.9) == DataQualityStatus.CRITICAL


class TestMonitorOHLCV:
    def test_monitor_ohlcv_returns_metrics(self, monitor, valid_ohlcv):
        """Test monitoring returns OHLCVMetrics."""
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=valid_ohlcv["opens"],
            highs=valid_ohlcv["highs"],
            lows=valid_ohlcv["lows"],
            closes=valid_ohlcv["closes"],
            volumes=valid_ohlcv["volumes"],
            timestamp="2026-09-25T12:00:00Z",
        )
        assert metrics.symbol == "BTC"
        assert metrics.record_count > 0
        assert metrics.status in [
            DataQualityStatus.PASS,
            DataQualityStatus.WARNING,
            DataQualityStatus.CRITICAL,
        ]

    def test_monitor_ohlcv_valid_data(self, monitor, valid_ohlcv):
        """Test monitoring passes for valid data."""
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=valid_ohlcv["opens"],
            highs=valid_ohlcv["highs"],
            lows=valid_ohlcv["lows"],
            closes=valid_ohlcv["closes"],
            volumes=valid_ohlcv["volumes"],
            timestamp="2026-09-25T12:00:00Z",
        )
        assert metrics.status in [DataQualityStatus.PASS, DataQualityStatus.WARNING]
        assert metrics.quality_score >= 50.0

    def test_monitor_ohlcv_invalid_data(self, monitor, invalid_ohlcv_low_high):
        """Test monitoring detects invalid data."""
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=invalid_ohlcv_low_high["opens"],
            highs=invalid_ohlcv_low_high["highs"],
            lows=invalid_ohlcv_low_high["lows"],
            closes=invalid_ohlcv_low_high["closes"],
            volumes=invalid_ohlcv_low_high["volumes"],
            timestamp="2026-09-25T12:00:00Z",
        )
        assert metrics.status == DataQualityStatus.CRITICAL
        assert metrics.missing_fields > 0

    def test_monitor_ohlcv_empty_data(self, monitor):
        """Test monitoring handles empty data."""
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=[],
            highs=[],
            lows=[],
            closes=[],
            volumes=[],
            timestamp="2026-09-25T12:00:00Z",
        )
        assert metrics.record_count == 0
        assert metrics.status == DataQualityStatus.CRITICAL


class TestDataUsability:
    def test_is_data_usable_pass(self, monitor, valid_ohlcv):
        """Test data is usable when status is PASS."""
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=valid_ohlcv["opens"],
            highs=valid_ohlcv["highs"],
            lows=valid_ohlcv["lows"],
            closes=valid_ohlcv["closes"],
            volumes=valid_ohlcv["volumes"],
            timestamp="2026-09-25T12:00:00Z",
        )
        usable = monitor.is_data_usable(metrics)
        assert usable is True

    def test_is_data_usable_critical(self, monitor, invalid_ohlcv_low_high):
        """Test data is not usable when status is CRITICAL."""
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=invalid_ohlcv_low_high["opens"],
            highs=invalid_ohlcv_low_high["highs"],
            lows=invalid_ohlcv_low_high["lows"],
            closes=invalid_ohlcv_low_high["closes"],
            volumes=invalid_ohlcv_low_high["volumes"],
            timestamp="2026-09-25T12:00:00Z",
        )
        usable = monitor.is_data_usable(metrics)
        assert usable is False


class TestEdgeCases:
    def test_monitor_single_record(self, monitor):
        """Test with single record."""
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=[100.0],
            highs=[105.0],
            lows=[95.0],
            closes=[102.0],
            volumes=[1000000],
            timestamp="2026-09-25T12:00:00Z",
        )
        assert metrics.record_count == 1
        assert metrics.gap_count == 0

    def test_monitor_large_dataset(self, monitor):
        """Test with large dataset."""
        size = 1000
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=[100.0 + i * 0.01 for i in range(size)],
            highs=[105.0 + i * 0.01 for i in range(size)],
            lows=[95.0 + i * 0.01 for i in range(size)],
            closes=[102.0 + i * 0.01 for i in range(size)],
            volumes=[1000000 + i * 100 for i in range(size)],
            timestamp="2026-09-25T12:00:00Z",
        )
        assert metrics.record_count == size

    def test_monitor_zero_volumes(self, monitor):
        """Test with zero trading volumes."""
        metrics = monitor.monitor_ohlcv(
            symbol="BTC",
            opens=[100.0] * 20,
            highs=[105.0] * 20,
            lows=[95.0] * 20,
            closes=[102.0] * 20,
            volumes=[0] * 20,  # Zero volumes
            timestamp="2026-09-25T12:00:00Z",
        )
        assert metrics.record_count == 20
        # Zero volumes should not cause validation to fail
        assert metrics.status in [
            DataQualityStatus.PASS,
            DataQualityStatus.WARNING,
        ]
