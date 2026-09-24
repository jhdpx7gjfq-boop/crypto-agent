"""Spring Detector — P0.4 RESEARCH_CANDIDATE

Classifies tokens into 5 mutually exclusive Spring states based on daily OHLCV:
- NO_SPRING: No identifiable range
- RANGE: Consolidation detected, no sweep
- SWEEP: Below support, awaiting reclaim
- SPRING_CANDIDATE: Sweep + reclaim confirmed
- BREAKDOWN: Sweep without reclaim, sustained weakness

Status: RESEARCH_CANDIDATE (not backtested, not validated PIT/OOS/WFV)
"""

import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from pydantic import BaseModel, field_validator

from src.data.schema import OHLCVCandle


class SpringDetectorError(Exception):
    """Base exception for Spring Detector."""
    pass


class DataQualityError(SpringDetectorError):
    """Raised when DataFrame contains NaN, duplicates, or non-monotonic timestamps."""
    pass


class SpringDetectorOutput(BaseModel):
    """Machine-readable output from Spring Detector."""
    symbol: str
    timestamp: datetime
    timeframe: str = "daily"
    state: str
    signal_timestamp: Optional[datetime] = None
    evidence: Dict[str, Any]
    status: str = "RESEARCH_CANDIDATE"
    reason: Optional[str] = None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        valid_states = {"NO_SPRING", "RANGE", "SWEEP", "SPRING_CANDIDATE", "BREAKDOWN"}
        if v not in valid_states:
            raise ValueError(f"Invalid state: {v}. Must be one of {valid_states}")
        return v


class RangeDetector:
    """Detects identifiable consolidation range."""

    def __init__(self, lookback: int = 30, min_width: float = 2.0, max_width: float = 25.0):
        """
        Args:
            lookback: Number of recent candles to analyze (default 30 days)
            min_width: Minimum range width % (default 2%)
            max_width: Maximum range width % (default 25%)
        """
        self.lookback = lookback
        self.min_width = min_width
        self.max_width = max_width

    def detect(self, df: pd.DataFrame) -> Tuple[Optional[float], Optional[float], Optional[float], bool]:
        """
        Detect range structure in recent candles.
        Uses robust range_low to avoid contamination from extreme lows.

        Args:
            df: DataFrame with 'high', 'low' columns

        Returns:
            (range_high, range_low, range_width_pct, is_valid)
        """
        if len(df) < self.lookback:
            return None, None, None, False

        if df["high"].isna().any() or df["low"].isna().any():
            raise DataQualityError("DataFrame contains NaN in high or low")

        recent = df.tail(self.lookback)
        range_high = recent["high"].max()
        range_low = recent["low"].min()

        if range_low == 0:
            return None, None, None, False

        range_width_pct = (range_high - range_low) / range_low * 100
        is_valid = self.min_width <= range_width_pct <= self.max_width

        return range_high, range_low, range_width_pct, is_valid


class SweepDetector:
    """Detects liquidity sweep below support level."""

    def detect(
        self, df: pd.DataFrame, range_low: float, lookback: int = 30
    ) -> Tuple[Optional[int], Optional[float], Optional[float], Optional[int]]:
        """
        Detect sweep below support level within recent candles.

        Args:
            df: DataFrame with 'low' column
            range_low: Support level (range low)
            lookback: Number of recent candles to search (default 30, must match range detection)

        Returns:
            (sweep_idx, sweep_low, sweep_depth_pct, sweep_candles) or (None, None, None, None)
        """
        if len(df) == 0 or range_low is None:
            return None, None, None, None

        if df["low"].isna().any():
            raise DataQualityError("DataFrame contains NaN in low")

        # Find most recent penetration below support (backward scan recent history)
        # Search in a wider window (2x lookback) to capture sweeps that occur before range contamination
        max_lookback = max(lookback * 2, 50)
        start_idx = max(0, len(df) - max_lookback)

        sweep_idx = None
        for i in range(len(df) - 1, start_idx - 1, -1):
            if df["low"].iloc[i] < range_low:
                sweep_idx = i
                break

        if sweep_idx is None:
            return None, None, None, None

        # Measure sweep depth
        sweep_low = df.iloc[sweep_idx:]["low"].min()
        sweep_depth_pct = (range_low - sweep_low) / range_low * 100
        sweep_candles = len(df) - sweep_idx

        return sweep_idx, sweep_low, sweep_depth_pct, sweep_candles


class ReclaimDetector:
    """Detects reclaim above support level after sweep."""

    def detect(
        self, df: pd.DataFrame, sweep_idx: int, range_low: float, window_candles: int = 10
    ) -> Tuple[Optional[int], Optional[datetime], Optional[float], Optional[int]]:
        """
        Detect reclaim (close > range_low) after sweep.

        Args:
            df: DataFrame with 'close' and 'timestamp' columns
            sweep_idx: Index where sweep occurred
            range_low: Support level to reclaim
            window_candles: Max candles to wait for reclaim (default 10)

        Returns:
            (reclaim_idx, reclaim_timestamp, reclaim_close, candles_to_reclaim)
            or (None, None, None, None) if no reclaim within window
        """
        if sweep_idx is None or range_low is None:
            return None, None, None, None

        if df["close"].isna().any():
            raise DataQualityError("DataFrame contains NaN in close")

        # Search for reclaim within window
        reclaim_window_end = min(sweep_idx + window_candles + 1, len(df))

        for i in range(sweep_idx + 1, reclaim_window_end):
            if df["close"].iloc[i] > range_low:
                reclaim_idx = i
                reclaim_timestamp = df["timestamp"].iloc[i]
                reclaim_close = df["close"].iloc[i]
                candles_to_reclaim = i - sweep_idx
                return reclaim_idx, reclaim_timestamp, reclaim_close, candles_to_reclaim

        return None, None, None, None


class SpringStateMachine:
    """State machine for Spring detection (5 mutually exclusive states)."""

    def __init__(
        self,
        range_lookback: int = 30,
        range_min_width: float = 2.0,
        range_max_width: float = 25.0,
        reclaim_window_candles: int = 10,
    ):
        """
        Args:
            range_lookback: Candles to analyze for range (default 30)
            range_min_width: Min range width % (default 2%)
            range_max_width: Max range width % (default 25%)
            reclaim_window_candles: Max candles to wait for reclaim (default 10)
        """
        self._range_detector = RangeDetector(range_lookback, range_min_width, range_max_width)
        self._sweep_detector = SweepDetector()
        self._reclaim_detector = ReclaimDetector()
        self.reclaim_window_candles = reclaim_window_candles

    def classify(self, df: pd.DataFrame) -> Tuple[str, Dict[str, Any], Optional[datetime]]:
        """
        Classify token into one of 5 states.

        Args:
            df: Daily OHLCV DataFrame

        Returns:
            (state: str, evidence: dict, signal_timestamp: Optional[datetime])
        """
        # Data checks
        if len(df) < 50:
            return "NO_SPRING", {"reason": "insufficient_data", "candles": len(df)}, None

        # Step 1: Detect range
        range_high, range_low, range_width_pct, is_valid_range = self._range_detector.detect(df)

        if not is_valid_range:
            return "NO_SPRING", {
                "reason": "range_not_identifiable",
                "range_width": range_width_pct,
            }, None

        # Step 2: Check if price is above range (breakout, not Spring setup)
        current_close = df["close"].iloc[-1]
        if current_close > range_high:
            return "NO_SPRING", {
                "reason": "price_above_range",
                "current_close": current_close,
                "range_high": range_high,
            }, None

        # Step 3: Detect sweep (search only within recent lookback window)
        sweep_idx, sweep_low, sweep_depth_pct, sweep_candles = self._sweep_detector.detect(
            df, range_low, lookback=self._range_detector.lookback
        )

        if sweep_idx is None:
            # No sweep; price within range → RANGE state
            return "RANGE", {
                "range_high": range_high,
                "range_low": range_low,
                "range_width": range_width_pct,
                "range_lookback": self._range_detector.lookback,
            }, None

        # Step 4: Look for reclaim after sweep
        reclaim_idx, reclaim_timestamp, reclaim_close, candles_to_reclaim = (
            self._reclaim_detector.detect(df, sweep_idx, range_low, self.reclaim_window_candles)
        )

        if reclaim_idx is not None:
            # Reclaim found → SPRING_CANDIDATE
            recovery_pct = (reclaim_close - sweep_low) / sweep_low * 100 if sweep_low > 0 else 0
            volume = df["volume"].iloc[reclaim_idx] if "volume" in df.columns else None

            return "SPRING_CANDIDATE", {
                "range_high": range_high,
                "range_low": range_low,
                "range_width": range_width_pct,
                "sweep_low": sweep_low,
                "sweep_depth": sweep_depth_pct,
                "recovery_pct": recovery_pct,
                "reclaim_close": reclaim_close,
                "candles_to_reclaim": candles_to_reclaim,
                "volume": volume,
            }, reclaim_timestamp

        # Step 5: Check if reclaim window closed without reclaim
        if sweep_idx + self.reclaim_window_candles < len(df):
            # Calculate sweep_low from sweep window only (not including post-window)
            sweep_window_end = min(sweep_idx + self.reclaim_window_candles, len(df))
            sweep_low_in_window = df.iloc[sweep_idx:sweep_window_end]["low"].min()

            post_window = df.iloc[sweep_idx + self.reclaim_window_candles :]
            new_low = post_window["low"].min()

            if new_low < sweep_low_in_window:
                # Continued weakness → BREAKDOWN
                return "BREAKDOWN", {
                    "reason": "continued_weakness_no_reclaim",
                    "sweep_low": sweep_low,
                    "breakdown_low": new_low,
                    "reclaim_window_candles": self.reclaim_window_candles,
                }, None

        # Still in sweep, awaiting reclaim or breakdown
        current_recovery_pct = (current_close - sweep_low) / sweep_low * 100 if sweep_low > 0 else 0

        return "SWEEP", {
            "range_low": range_low,
            "sweep_low": sweep_low,
            "sweep_depth": sweep_depth_pct,
            "candles_since_sweep": sweep_candles,
            "recovery_pct": current_recovery_pct,
            "reclaim_window_remaining": max(0, self.reclaim_window_candles - sweep_candles),
        }, None


class SpringDetector:
    """Public interface for Spring Detector (composition-based)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Configuration dict with keys:
                - range_lookback: int (default 30)
                - range_width_min: float (default 2.0)
                - range_width_max: float (default 25.0)
                - reclaim_window_candles: int (default 10)
        """
        config = config or {}
        range_lookback = config.get("range_lookback", 30)
        range_min_width = config.get("range_width_min", 2.0)
        range_max_width = config.get("range_width_max", 25.0)
        reclaim_window = config.get("reclaim_window_candles", 10)

        self._state_machine = SpringStateMachine(
            range_lookback=range_lookback,
            range_min_width=range_min_width,
            range_max_width=range_max_width,
            reclaim_window_candles=reclaim_window,
        )

    def classify(self, symbol: str, df: pd.DataFrame) -> SpringDetectorOutput:
        """
        Classify token into Spring state.

        Args:
            symbol: Token symbol (e.g., "BTC")
            df: Daily OHLCV DataFrame with columns [timestamp, open, high, low, close, volume]

        Returns:
            SpringDetectorOutput with state, evidence, and signal_timestamp

        Raises:
            DataQualityError: If DataFrame contains NaN, duplicates, or non-monotonic timestamps
        """
        try:
            # Validate data quality
            if df.empty:
                raise DataQualityError("DataFrame is empty")

            required_cols = ["open", "high", "low", "close"]
            if df[required_cols].isna().any().any():
                raise DataQualityError("DataFrame contains NaN values")

            if df["timestamp"].duplicated().any():
                raise DataQualityError("DataFrame contains duplicate timestamps")

            if not df["timestamp"].is_monotonic_increasing:
                raise DataQualityError("DataFrame timestamps are not monotonically increasing")

            # Classify state
            state, evidence, signal_timestamp = self._state_machine.classify(df)

            return SpringDetectorOutput(
                symbol=symbol,
                timestamp=df["timestamp"].iloc[-1],
                timeframe="daily",
                state=state,
                signal_timestamp=signal_timestamp,
                evidence=evidence,
                status="RESEARCH_CANDIDATE",
                reason=None,
            )

        except (DataQualityError,) as e:
            return SpringDetectorOutput(
                symbol=symbol,
                timestamp=df["timestamp"].iloc[-1] if not df.empty else datetime.utcnow(),
                timeframe="daily",
                state="NO_SPRING",
                evidence={},
                status="RESEARCH_CANDIDATE",
                reason=str(e),
            )
