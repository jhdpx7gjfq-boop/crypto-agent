"""
Universe filtering — P0.2 independent filters.
Reduces Top 500 to scannable subset based on data availability and minimal thresholds.
"""
import logging
from dataclasses import dataclass
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Individual filter result."""
    token: str
    status: str  # PASS, FAIL, UNKNOWN
    reason: str
    value: Optional[float] = None
    threshold: Optional[float] = None


class MarketCapFilter:
    """Filter by market cap — RESEARCH_CANDIDATE."""

    def __init__(self, min_market_cap: Optional[float] = None, max_market_cap: Optional[float] = None):
        self.min = min_market_cap
        self.max = max_market_cap

    def apply(self, market_cap: Optional[float], symbol: str) -> FilterResult:
        if market_cap is None:
            return FilterResult(symbol, "UNKNOWN", "market_cap is None", None, None)

        if self.min is not None and market_cap < self.min:
            return FilterResult(symbol, "FAIL", f"market_cap < min", market_cap, self.min)

        if self.max is not None and market_cap > self.max:
            return FilterResult(symbol, "FAIL", f"market_cap > max", market_cap, self.max)

        return FilterResult(symbol, "PASS", "market_cap within range", market_cap, self.min)


class VolumeFilter:
    """Filter by 24h volume — RESEARCH_CANDIDATE."""

    def __init__(self, min_volume_24h: Optional[float] = None):
        self.min = min_volume_24h

    def apply(self, volume_24h: Optional[float], symbol: str) -> FilterResult:
        if volume_24h is None or volume_24h == 0:
            return FilterResult(symbol, "UNKNOWN", "volume_24h is None or 0", None, self.min)

        if self.min is not None and volume_24h < self.min:
            return FilterResult(symbol, "FAIL", f"volume_24h < min", volume_24h, self.min)

        return FilterResult(symbol, "PASS", "volume_24h sufficient", volume_24h, self.min)


class DataAvailabilityFilter:
    """Filter by OHLCV availability (must have Daily and 4H)."""

    def __init__(self, require_daily: bool = True, require_4h: bool = True, min_candles: int = 50):
        self.require_daily = require_daily
        self.require_4h = require_4h
        self.min_candles = min_candles

    def apply(self, symbol: str, daily_count: int, fourbh_count: int) -> FilterResult:
        """Check if symbol has sufficient OHLCV data."""
        missing = []

        if self.require_daily and daily_count < self.min_candles:
            missing.append(f"daily ({daily_count} < {self.min_candles})")

        if self.require_4h and fourbh_count < self.min_candles:
            missing.append(f"4h ({fourbh_count} < {self.min_candles})")

        if missing:
            return FilterResult(symbol, "FAIL", f"insufficient data: {', '.join(missing)}",
                               None, self.min_candles)

        return FilterResult(symbol, "PASS", "daily + 4h data available",
                           min(daily_count, fourbh_count), self.min_candles)


class DataQualityFilter:
    """Filter by OHLCV quality — check for duplicates, gaps, NaN."""

    def __init__(self, allow_missing_candles: bool = False):
        self.allow_missing_candles = allow_missing_candles

    def apply(self, symbol: str, daily_df: Optional[pd.DataFrame], fourbh_df: Optional[pd.DataFrame]) -> FilterResult:
        """Check OHLCV data quality."""
        issues = []

        for name, df in [("daily", daily_df), ("4h", fourbh_df)]:
            if df is None or len(df) == 0:
                issues.append(f"{name} is empty")
                continue

            # Check for NaN
            if df[["open", "high", "low", "close", "volume"]].isna().any().any():
                issues.append(f"{name} contains NaN")

            # Check for duplicates
            if df.duplicated(subset=["timestamp"]).any():
                issues.append(f"{name} has duplicate timestamps")

            # Check monotonic timestamps
            if not df["timestamp"].is_monotonic_increasing:
                issues.append(f"{name} timestamps not monotonic")

        if issues:
            return FilterResult(symbol, "FAIL", f"quality issues: {', '.join(issues)}", None, None)

        return FilterResult(symbol, "PASS", "data quality OK", None, None)


class UniverseFilter:
    """Composition of all filters — produces scannable universe."""

    def __init__(self, market_cap_filter: MarketCapFilter, volume_filter: VolumeFilter,
                 data_avail_filter: DataAvailabilityFilter, data_quality_filter: DataQualityFilter):
        self.market_cap_filter = market_cap_filter
        self.volume_filter = volume_filter
        self.data_avail_filter = data_avail_filter
        self.data_quality_filter = data_quality_filter

    def apply_all(self, token_metadata: pd.DataFrame,
                  ohlcv_counts: dict, ohlcv_data: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply all filters to metadata.

        Returns:
        - filtered_universe: DataFrame of tokens that PASS all filters
        - rejection_report: DataFrame of rejected tokens with reasons
        """
        results = []

        for _, row in token_metadata.iterrows():
            symbol = row["symbol"]

            # Apply filters in sequence
            mc_result = self.market_cap_filter.apply(row.get("market_cap"), symbol)
            if mc_result.status == "FAIL":
                results.append((symbol, mc_result))
                continue

            vol_result = self.volume_filter.apply(row.get("volume_24h"), symbol)
            if vol_result.status == "FAIL":
                results.append((symbol, vol_result))
                continue

            daily_count = ohlcv_counts.get((symbol, "daily"), 0)
            fourbh_count = ohlcv_counts.get((symbol, "4h"), 0)
            avail_result = self.data_avail_filter.apply(symbol, daily_count, fourbh_count)
            if avail_result.status == "FAIL":
                results.append((symbol, avail_result))
                continue

            daily_df = ohlcv_data.get((symbol, "daily"))
            fourbh_df = ohlcv_data.get((symbol, "4h"))
            quality_result = self.data_quality_filter.apply(symbol, daily_df, fourbh_df)
            if quality_result.status == "FAIL":
                results.append((symbol, quality_result))
                continue

            # All filters passed
            results.append((symbol, FilterResult(symbol, "PASS", "all filters passed")))

        # Build output tables
        passed = []
        rejected = []

        for symbol, result in results:
            if result.status == "PASS":
                passed.append(symbol)
            else:
                rejected.append({
                    "symbol": symbol,
                    "status": result.status,
                    "filter": self._infer_filter_name(result),
                    "reason": result.reason,
                    "value": result.value,
                    "threshold": result.threshold,
                })

        # Filter universe to passing tokens
        filtered = token_metadata[token_metadata["symbol"].isin(passed)].reset_index(drop=True)

        # Rejection report
        rejection_df = pd.DataFrame(rejected)

        logger.info(f"Universe filter: {len(passed)} PASS, {len(rejected)} FAIL")

        return filtered, rejection_df

    @staticmethod
    def _infer_filter_name(result: FilterResult) -> str:
        """Infer which filter produced the result."""
        reason = result.reason.lower()
        if "market_cap" in reason:
            return "market_cap"
        elif "volume" in reason:
            return "volume"
        elif "data" in reason and "insufficient" in reason:
            return "data_availability"
        elif "quality" in reason:
            return "data_quality"
        return "unknown"
