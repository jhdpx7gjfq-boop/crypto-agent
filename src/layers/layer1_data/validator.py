"""Data validation and quality checks (Layer 1)."""

import logging
from typing import List, Tuple, Dict, Any
from datetime import datetime, timedelta

from src.core.models import OHLCV


logger = logging.getLogger(__name__)


class DataValidator:
    """Validates OHLCV data integrity and quality."""

    # Default thresholds
    MIN_CANDLES = 100
    MAX_PRICE_JUMP_PCT = 50  # Detect obvious bad data
    MAX_VOLUME_JUMP_PCT = 500
    MIN_TIME_DISTANCE_SECONDS = 3600  # 1 hour for daily candles

    def __init__(self):
        pass

    def validate_ohlcv_list(
        self,
        data: List[OHLCV],
        asset: str = "unknown",
        strict: bool = False
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate complete OHLCV dataset.

        Returns:
            (is_valid, summary, list_of_warnings)
        """

        warnings = []

        # Check: not empty
        if not data:
            return False, "Empty dataset", warnings

        # Check: minimum candles
        if len(data) < self.MIN_CANDLES:
            msg = f"Only {len(data)} candles, need >= {self.MIN_CANDLES}"
            if strict:
                return False, msg, warnings
            warnings.append(f"⚠ {msg}")

        # Check: chronological order
        is_ordered, bad_indices = self._check_chronological_order(data)
        if not is_ordered:
            msg = f"Data not in chronological order at indices {bad_indices[:5]}"
            if strict:
                return False, msg, warnings
            warnings.append(f"⚠ {msg}")

        # Check: no duplicates
        unique_timestamps = len(set(c.timestamp for c in data))
        if unique_timestamps < len(data):
            dupes = len(data) - unique_timestamps
            msg = f"{dupes} duplicate timestamps"
            if strict:
                return False, msg, warnings
            warnings.append(f"⚠ {msg}")

        # Check: OHLC integrity (L <= O,C <= H)
        invalid_indices = self._check_ohlc_integrity(data)
        if invalid_indices:
            msg = f"Invalid OHLC at {len(invalid_indices)} candles"
            if strict:
                return False, msg, warnings
            warnings.append(f"⚠ {msg}")

        # Check: price jumps
        jump_indices = self._check_price_jumps(data)
        if jump_indices:
            msg = f"Suspicious price jumps at {len(jump_indices)} candles"
            warnings.append(f"⚠ {msg}")

        # Check: volume anomalies
        vol_indices = self._check_volume_anomalies(data)
        if vol_indices:
            msg = f"Volume spikes at {len(vol_indices)} candles"
            warnings.append(f"⚠ {msg}")

        # Check: missing data (gaps)
        gap_info = self._check_gaps(data)
        if gap_info:
            for gap_date, gap_size in gap_info:
                warnings.append(f"⚠ Gap of {gap_size} days around {gap_date}")

        is_valid = len(warnings) == 0 or (not strict and len(invalid_indices) == 0)
        summary = f"{asset}: {len(data)} candles" + (
            f" ({len(warnings)} warnings)" if warnings else " — VALID"
        )

        return is_valid, summary, warnings

    def validate_candle(self, candle: OHLCV) -> Tuple[bool, str]:
        """Validate single candle."""
        try:
            # __post_init__ raises on invalid data
            _ = OHLCV(
                timestamp=candle.timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )
            return True, "Valid"
        except ValueError as e:
            return False, str(e)

    @staticmethod
    def _check_chronological_order(data: List[OHLCV]) -> Tuple[bool, List[int]]:
        """Check data is sorted by timestamp."""
        bad_indices = []
        for i in range(1, len(data)):
            if data[i].timestamp < data[i-1].timestamp:
                bad_indices.append(i)
        return len(bad_indices) == 0, bad_indices

    @staticmethod
    def _check_ohlc_integrity(data: List[OHLCV]) -> List[int]:
        """Check L <= O,C <= H for each candle."""
        invalid = []
        for i, c in enumerate(data):
            if not (c.low <= c.high):
                invalid.append(i)
            if not (c.low <= c.open <= c.high):
                invalid.append(i)
            if not (c.low <= c.close <= c.high):
                invalid.append(i)
        return list(set(invalid))

    def _check_price_jumps(
        self,
        data: List[OHLCV],
        threshold_pct: float = None
    ) -> List[int]:
        """Detect suspiciously large price jumps."""
        if threshold_pct is None:
            threshold_pct = self.MAX_PRICE_JUMP_PCT

        jumps = []
        for i in range(1, len(data)):
            prev_close = data[i-1].close
            curr_close = data[i].close

            if prev_close == 0:
                continue

            change_pct = abs((curr_close - prev_close) / prev_close) * 100

            if change_pct > threshold_pct:
                jumps.append(i)

        return jumps

    def _check_volume_anomalies(
        self,
        data: List[OHLCV],
        threshold_pct: float = None
    ) -> List[int]:
        """Detect volume spikes."""
        if threshold_pct is None:
            threshold_pct = self.MAX_VOLUME_JUMP_PCT

        if len(data) < 10:
            return []

        anomalies = []
        avg_volume = sum(c.volume for c in data[-50:]) / min(50, len(data))

        for i, c in enumerate(data):
            if avg_volume == 0:
                continue
            spike_pct = (c.volume / avg_volume) * 100
            if spike_pct > threshold_pct:
                anomalies.append(i)

        return anomalies

    @staticmethod
    def _check_gaps(data: List[OHLCV], max_days: int = 3) -> List[Tuple[str, int]]:
        """Detect temporal gaps in data."""
        gaps = []
        for i in range(1, len(data)):
            time_diff = (data[i].timestamp - data[i-1].timestamp).days
            if time_diff > max_days:
                gaps.append((data[i-1].timestamp.isoformat(), time_diff))
        return gaps


class FeatureEngineer:
    """Derives features from OHLCV data."""

    @staticmethod
    def compute_returns(data: List[OHLCV]) -> List[float]:
        """Simple log returns."""
        import math
        if len(data) < 2:
            return []
        returns = []
        for i in range(1, len(data)):
            ret = math.log(data[i].close / data[i-1].close)
            returns.append(ret)
        return returns

    @staticmethod
    def compute_volatility(data: List[OHLCV], window: int = 20) -> List[float]:
        """Compute rolling volatility (std dev of returns)."""
        returns = FeatureEngineer.compute_returns(data)
        if len(returns) < window:
            return []

        volatilities = []
        for i in range(window, len(returns) + 1):
            window_returns = returns[i-window:i]
            mean = sum(window_returns) / len(window_returns)
            variance = sum((r - mean) ** 2 for r in window_returns) / len(window_returns)
            std = variance ** 0.5
            volatilities.append(std)

        return volatilities

    @staticmethod
    def compute_sma(data: List[OHLCV], window: int = 20) -> List[float]:
        """Simple moving average of close prices."""
        if len(data) < window:
            return []

        smas = []
        for i in range(window - 1, len(data)):
            avg = sum(c.close for c in data[i-window+1:i+1]) / window
            smas.append(avg)

        return smas

    @staticmethod
    def compute_rsi(data: List[OHLCV], period: int = 14) -> List[float]:
        """Relative Strength Index."""
        returns = FeatureEngineer.compute_returns(data)
        if len(returns) < period:
            return []

        rsis = []
        for i in range(period - 1, len(returns)):
            gains = sum(max(r, 0) for r in returns[i-period+1:i+1]) / period
            losses = sum(abs(min(r, 0)) for r in returns[i-period+1:i+1]) / period

            if losses == 0:
                rsi = 100 if gains > 0 else 50
            else:
                rs = gains / losses
                rsi = 100 - (100 / (1 + rs))

            rsis.append(rsi)

        return rsis

    @staticmethod
    def compute_macd(data: List[OHLCV]) -> Tuple[List[float], List[float], List[float]]:
        """MACD (Moving Average Convergence Divergence)."""
        sma_12 = FeatureEngineer.compute_sma(data, 12)
        sma_26 = FeatureEngineer.compute_sma(data, 26)

        if len(sma_12) < 9 or len(sma_26) < 9:
            return [], [], []

        # Trim to same length
        min_len = min(len(sma_12), len(sma_26))
        sma_12 = sma_12[-min_len:]
        sma_26 = sma_26[-min_len:]

        macd_line = [s12 - s26 for s12, s26 in zip(sma_12, sma_26)]

        # Signal line (EMA of MACD, approximated as SMA)
        signal = []
        if len(macd_line) >= 9:
            for i in range(9 - 1, len(macd_line)):
                sig = sum(macd_line[i-9+1:i+1]) / 9
                signal.append(sig)

        histogram = [m - s for m, s in zip(macd_line[-(len(signal)):], signal)]

        return macd_line, signal, histogram
