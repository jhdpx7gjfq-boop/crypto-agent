"""Detect data leakage and look-ahead bias in features."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple
import numpy as np


@dataclass
class LeakageReport:
    """Report on potential data leakage in a feature."""

    feature_name: str
    has_leakage: bool
    leakage_score: float
    forward_correlation: float
    lookahead_correlation: float
    issue_count: int
    details: str


class LeakageDetector:
    """Detect if features use information not available at decision time."""

    def __init__(self, correlation_threshold: float = 0.3):
        self.correlation_threshold = correlation_threshold

    def check_feature(
        self,
        feature_name: str,
        feature_values: List[float],
        prices: List[float],
        timestamps: List[datetime],
    ) -> LeakageReport:
        """
        Detect if feature uses future information.

        High correlation between feature change and future price change
        at lag=0 suggests leakage.

        Args:
            feature_name: Name of feature being tested
            feature_values: Feature values over time
            prices: Price series over same period
            timestamps: Timestamps for validation

        Returns:
            LeakageReport with findings
        """
        if len(feature_values) < 3 or len(prices) < 3:
            return LeakageReport(
                feature_name=feature_name,
                has_leakage=False,
                leakage_score=0.0,
                forward_correlation=0.0,
                lookahead_correlation=0.0,
                issue_count=0,
                details="Insufficient data",
            )

        feature_arr = np.array(feature_values)
        prices_arr = np.array(prices)

        valid_idx = ~np.isnan(feature_arr)
        if np.sum(valid_idx) < 3:
            return LeakageReport(
                feature_name=feature_name,
                has_leakage=False,
                leakage_score=0.0,
                forward_correlation=0.0,
                lookahead_correlation=0.0,
                issue_count=0,
                details="Too many NaN values",
            )

        feature_clean = feature_arr[valid_idx]
        prices_clean = prices_arr[valid_idx]

        feature_changes = np.diff(feature_clean)
        price_changes = np.diff(prices_clean)

        forward_corr = self._safe_correlation(feature_clean[:-1], price_changes)
        lookahead_corr = self._safe_correlation(feature_changes, price_changes)

        leakage_score = max(abs(forward_corr), abs(lookahead_corr))
        has_leakage = leakage_score > self.correlation_threshold

        return LeakageReport(
            feature_name=feature_name,
            has_leakage=has_leakage,
            leakage_score=leakage_score,
            forward_correlation=forward_corr,
            lookahead_correlation=lookahead_corr,
            issue_count=1 if has_leakage else 0,
            details=f"Lookahead: {lookahead_corr:.3f}, Forward: {forward_corr:.3f}",
        )

    def check_forward_bias(self, prices: List[float], timestamps: List[datetime]) -> float:
        """
        Check if price labels are properly time-ordered.

        Returns correlation of price_today vs price_tomorrow.
        High correlation at lag=1 suggests potential look-ahead bias.

        Args:
            prices: Price series
            timestamps: Corresponding timestamps

        Returns:
            Correlation coefficient (0.0 = no bias, >0.7 = potential bias)
        """
        if len(prices) < 3:
            return 0.0

        prices_arr = np.array(prices)
        prices_today = prices_arr[:-1]
        prices_tomorrow = prices_arr[1:]

        return self._safe_correlation(prices_today, prices_tomorrow)

    def check_survivorship_bias(
        self, symbols: List[str], prices: dict, start_date: datetime, end_date: datetime
    ) -> Tuple[bool, List[str]]:
        """
        Detect survivorship bias: assets that disappear from universe.

        Args:
            symbols: Asset symbols in universe
            prices: Dict mapping symbol → price series
            start_date: Start of study period
            end_date: End of study period

        Returns:
            (has_bias, symbols_with_gaps) — symbols that have data gaps
        """
        symbols_with_gaps = []

        for symbol in symbols:
            if symbol not in prices or len(prices[symbol]) == 0:
                symbols_with_gaps.append(symbol)
                continue

            price_series = prices[symbol]
            if len(price_series) < 10:
                symbols_with_gaps.append(symbol)

        has_bias = len(symbols_with_gaps) > 0
        return has_bias, symbols_with_gaps

    def _safe_correlation(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Safely calculate correlation, returning 0.0 on error.

        Args:
            x: First series
            y: Second series

        Returns:
            Correlation coefficient or 0.0 if calculation fails
        """
        try:
            if len(x) < 2 or len(y) < 2 or len(x) != len(y):
                return 0.0

            x_arr = np.asarray(x, dtype=float)
            y_arr = np.asarray(y, dtype=float)

            x_valid = ~(np.isnan(x_arr) | np.isinf(x_arr))
            y_valid = ~(np.isnan(y_arr) | np.isinf(y_arr))
            valid = x_valid & y_valid

            if np.sum(valid) < 2:
                return 0.0

            x_clean = x_arr[valid]
            y_clean = y_arr[valid]

            x_std = np.std(x_clean)
            y_std = np.std(y_clean)

            if x_std == 0 or y_std == 0:
                return 0.0

            return float(np.corrcoef(x_clean, y_clean)[0, 1])

        except (ValueError, RuntimeError, TypeError):
            return 0.0
