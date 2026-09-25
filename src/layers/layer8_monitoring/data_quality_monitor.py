"""Data Quality Monitoring. Validates OHLCV data integrity and detects anomalies."""

from typing import Dict, Tuple, List
from dataclasses import dataclass
from enum import Enum
import numpy as np


class DataQualityStatus(Enum):
    """Data quality status."""
    PASS = "pass"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class OHLCVMetrics:
    """OHLCV data quality metrics."""
    symbol: str
    timestamp: str
    record_count: int
    gap_count: int
    missing_fields: int
    outlier_count: int
    price_anomalies: int
    volume_anomalies: int
    status: DataQualityStatus
    quality_score: float


class DataQualityMonitor:
    """Monitors OHLCV data quality and detects anomalies."""

    def validate_ohlcv_records(
        self,
        symbol: str,
        opens: list,
        highs: list,
        lows: list,
        closes: list,
        volumes: list,
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Validate OHLCV record structure and relationships.

        Args:
            symbol: Asset symbol
            opens: Open prices
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Trading volumes

        Returns:
            (is_valid, issues_dict)
        """
        issues = {}

        # Check array lengths match
        lengths = [len(opens), len(highs), len(lows), len(closes), len(volumes)]
        if len(set(lengths)) > 1:
            issues["length_mismatch"] = 1
            return False, issues

        # Check for required fields
        record_count = len(closes)
        if record_count == 0:
            issues["empty_data"] = 1
            return False, issues

        # Check OHLC relationships: L <= O,C <= H
        invalid_ohlc = 0
        for i in range(record_count):
            if not (lows[i] <= opens[i] <= highs[i]):
                invalid_ohlc += 1
            if not (lows[i] <= closes[i] <= highs[i]):
                invalid_ohlc += 1

        if invalid_ohlc > 0:
            issues["invalid_ohlc"] = invalid_ohlc

        # Check for non-positive values
        if any(p <= 0 for p in opens) or any(p <= 0 for p in closes):
            issues["non_positive_prices"] = 1

        if any(v < 0 for v in volumes):
            issues["negative_volumes"] = 1

        return len(issues) == 0, issues

    def detect_price_gaps(
        self,
        symbol: str,
        closes: list,
        gap_threshold_pct: float = 10.0,
    ) -> Tuple[int, List[int]]:
        """
        Detect significant price gaps between bars.

        Args:
            symbol: Asset symbol
            closes: Close prices
            gap_threshold_pct: Gap threshold % (default 10%)

        Returns:
            (gap_count, gap_indices)
        """
        if len(closes) < 2:
            return 0, []

        closes_arr = np.array(closes)
        gaps = np.abs(np.diff(closes_arr) / closes_arr[:-1]) * 100

        gap_indices = np.where(gaps > gap_threshold_pct)[0].tolist()
        gap_count = len(gap_indices)

        return gap_count, gap_indices

    def detect_outliers(
        self,
        symbol: str,
        values: list,
        method: str = "zscore",
        threshold: float = 3.0,
    ) -> Tuple[int, List[int]]:
        """
        Detect statistical outliers in price/volume data.

        Args:
            symbol: Asset symbol
            values: Price or volume values
            method: Detection method ("zscore" or "iqr")
            threshold: Threshold (zscore=3.0, iqr=1.5)

        Returns:
            (outlier_count, outlier_indices)
        """
        if len(values) < 3:
            return 0, []

        values_arr = np.array(values)

        if method == "zscore":
            mean = np.mean(values_arr)
            std = np.std(values_arr)
            if std == 0:
                return 0, []
            z_scores = np.abs((values_arr - mean) / std)
            outlier_indices = np.where(z_scores > threshold)[0].tolist()

        elif method == "iqr":
            q1 = np.percentile(values_arr, 25)
            q3 = np.percentile(values_arr, 75)
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            outlier_indices = np.where((values_arr < lower_bound) | (values_arr > upper_bound))[0].tolist()

        else:
            return 0, []

        outlier_count = len(outlier_indices)
        return outlier_count, outlier_indices

    def calculate_quality_score(
        self,
        record_count: int,
        gap_count: int,
        missing_fields: int,
        outlier_count: int,
    ) -> float:
        """
        Calculate composite data quality score (0-100).

        Args:
            record_count: Number of valid records
            gap_count: Number of price gaps detected
            missing_fields: Number of missing fields
            outlier_count: Number of statistical outliers

        Returns:
            Quality score 0-100
        """
        if record_count < 5:
            return 0.0

        # Penalties
        gap_penalty = min(30.0, gap_count * 5.0)  # Max 30 points
        missing_penalty = min(20.0, missing_fields * 10.0)  # Max 20 points
        outlier_penalty = min(30.0, outlier_count * 2.0)  # Max 30 points

        total_penalty = gap_penalty + missing_penalty + outlier_penalty
        quality_score = max(0.0, 100.0 - total_penalty)

        return float(quality_score)

    def get_quality_status(self, quality_score: float) -> DataQualityStatus:
        """
        Determine quality status from score.

        Args:
            quality_score: Quality score 0-100

        Returns:
            Status: PASS (>=80), WARNING (50-80), CRITICAL (<50)
        """
        if quality_score >= 80.0:
            return DataQualityStatus.PASS
        elif quality_score >= 50.0:
            return DataQualityStatus.WARNING
        else:
            return DataQualityStatus.CRITICAL

    def monitor_ohlcv(
        self,
        symbol: str,
        opens: list,
        highs: list,
        lows: list,
        closes: list,
        volumes: list,
        timestamp: str,
        gap_threshold_pct: float = 10.0,
    ) -> OHLCVMetrics:
        """
        Complete OHLCV data quality monitoring pipeline.

        Args:
            symbol: Asset symbol
            opens: Open prices
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Trading volumes
            timestamp: Monitoring timestamp
            gap_threshold_pct: Gap threshold %

        Returns:
            OHLCVMetrics with quality assessment
        """
        # Validate structure
        is_valid, validation_issues = self.validate_ohlcv_records(symbol, opens, highs, lows, closes, volumes)

        missing_fields = 0
        if not is_valid:
            missing_fields = len(validation_issues)

        record_count = len(closes) if is_valid else 0

        # Detect gaps
        gap_count, gap_indices = self.detect_price_gaps(symbol, closes, gap_threshold_pct)

        # Detect outliers
        price_outliers, price_outlier_idx = self.detect_outliers(symbol, closes, method="zscore", threshold=3.0)
        volume_outliers, vol_outlier_idx = self.detect_outliers(symbol, volumes, method="iqr", threshold=1.5)
        total_outliers = price_outliers + volume_outliers

        # Calculate quality score
        quality_score = self.calculate_quality_score(record_count, gap_count, missing_fields, total_outliers)

        # Determine status
        status = self.get_quality_status(quality_score)

        return OHLCVMetrics(
            symbol=symbol,
            timestamp=timestamp,
            record_count=record_count,
            gap_count=gap_count,
            missing_fields=missing_fields,
            outlier_count=total_outliers,
            price_anomalies=price_outliers,
            volume_anomalies=volume_outliers,
            status=status,
            quality_score=quality_score,
        )

    def is_data_usable(self, metrics: OHLCVMetrics) -> bool:
        """
        Determine if data is usable for analysis.

        Args:
            metrics: OHLCVMetrics from monitoring

        Returns:
            True if data quality is acceptable (PASS or WARNING)
        """
        return metrics.status in [DataQualityStatus.PASS, DataQualityStatus.WARNING]
