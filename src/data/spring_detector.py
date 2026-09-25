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
    """Detects identifiable consolidation range with temporal causality."""

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

        Uses simple min/max from lookback window.
        Contamination handling is delegated to SpringStateMachine for temporal causality.

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

        # Step 2.5: CHECK FOR RANGE CONTAMINATION (before sweep detection)
        # Adjust range_low if contaminated by old debris or recent sweeps
        recent = df.tail(self._range_detector.lookback)
        mid = len(recent) // 2
        earlier_half_lows = recent["low"].iloc[:mid].mean()
        later_half_lows = recent["low"].iloc[mid:].mean()

        if later_half_lows > 0 and earlier_half_lows > 0:
            debris_ratio = (later_half_lows - earlier_half_lows) / earlier_half_lows

            # Pattern 1: Recent sweeps (negative debris_ratio) → only apply if earlier_half is stable
            # (not itself decaying), to distinguish from sustained breakdown
            if debris_ratio < 0:  # Any decay signal
                # Check if earlier_half itself is stable (tight range, not decaying)
                earlier_half_min = recent["low"].iloc[:mid].min()
                earlier_half_max = recent["low"].iloc[:mid].max()
                earlier_half_spread_pct = (earlier_half_max - earlier_half_min) / earlier_half_min * 100 if earlier_half_min > 0 else 0

                # Only use earlier_half_lows if it's relatively stable (spread <= 3%)
                # This distinguishes RECENT_SWEEP (tight range with a dip) from
                # BREAKDOWN (both halves declining, wider spread due to decay)
                earlier_half_spread_pct = (earlier_half_max - earlier_half_min) / earlier_half_min * 100 if earlier_half_min > 0 else 0

                # Use earlier_half if it's tightly clustered (indicates stable support before recent dip)
                # Threshold of 1.5% distinguishes RECENT_SWEEP (tight, <1.5% spread) from
                # BREAKDOWN (wider spread due to decay: 2-5%+ spread)
                if earlier_half_spread_pct < 1.5:
                    alt_range_low = earlier_half_lows
                    alt_range_high = recent["high"].iloc[:mid].max()
                    if alt_range_high > alt_range_low:
                        alt_range_width = (alt_range_high - alt_range_low) / alt_range_low * 100
                        if self._range_detector.min_width <= alt_range_width <= self._range_detector.max_width:
                            range_low = alt_range_low
                            range_high = alt_range_high
                            range_width_pct = alt_range_width


        # Step 3: Detect sweep (search only within recent lookback window)
        sweep_idx, sweep_low, sweep_depth_pct, sweep_candles = self._sweep_detector.detect(
            df, range_low, lookback=self._range_detector.lookback
        )

        # Step 3.2: If sweep found but very old + contamination pattern detected,
        # try to find better range (applies same fallback logic as "no sweep" case)
        if sweep_idx is not None and sweep_idx <= len(df) - 60:  # Sweep is very old (>=60 candles away)
            recent = df.tail(self._range_detector.lookback)
            mid = len(recent) // 2
            earlier_half_lows = recent["low"].iloc[:mid].mean()
            later_half_lows = recent["low"].iloc[mid:].mean()

            # Check for BREAKDOWN contamination (recent decay > 2%)
            if earlier_half_lows > 0 and (earlier_half_lows - later_half_lows) / earlier_half_lows > 0.02:
                # Try to find better range from earlier data, stepping back further
                # Try distances that reach back to before the breakdown started
                for look_back_dist in range(50, 15, -2):  # Try: 50, 48, 46, ..., 18, 16
                    test_idx = len(df) - look_back_dist
                    if test_idx > self._range_detector.lookback:
                        test_data = df.iloc[:test_idx]
                        test_high, test_low, test_width, test_valid = (
                            self._range_detector.detect(test_data)
                        )
                        if test_valid and test_low is not None and test_low > range_low:
                            # Try sweep with this better range
                            test_sweep_idx, test_sweep_low, test_sweep_depth, test_sweep_candles = (
                                self._sweep_detector.detect(df, test_low, lookback=self._range_detector.lookback)
                            )
                            if test_sweep_idx is not None:
                                # Found better sweep with corrected range!
                                range_low = test_low
                                range_high = test_high
                                range_width_pct = test_width
                                sweep_idx = test_sweep_idx
                                sweep_low = test_sweep_low
                                sweep_depth_pct = test_sweep_depth
                                sweep_candles = test_sweep_candles
                                break

        if sweep_idx is None:
            # No sweep found; check if range_low might be contaminated
            # Two contamination patterns:
            # 1. BREAKDOWN: earlier_half > later_half (recent prices lower) → try earlier data
            # 2. OLD_DEBRIS: earlier_half < later_half (old debris in early part) → try later half as range
            recent = df.tail(self._range_detector.lookback)
            mid = len(recent) // 2
            earlier_half_lows = recent["low"].iloc[:mid].mean()
            later_half_lows = recent["low"].iloc[mid:].mean()

            contamination_fixed = False

            # Pattern 1: BREAKDOWN (recent decay > 2%)
            if earlier_half_lows > 0 and (earlier_half_lows - later_half_lows) / earlier_half_lows > 0.02:
                for test_idx in [len(df) - 50, len(df) - 40]:
                    if test_idx > self._range_detector.lookback:
                        test_data = df.iloc[:test_idx]
                        test_high, test_low, test_width, test_valid = (
                            self._range_detector.detect(test_data)
                        )
                        if test_valid and test_low is not None and test_low > range_low:
                            # Try sweep with this better range
                            test_sweep_idx, test_sweep_low, test_sweep_depth, test_sweep_candles = (
                                self._sweep_detector.detect(df, test_low, lookback=self._range_detector.lookback)
                            )
                            if test_sweep_idx is not None:
                                # Found sweep with corrected range!
                                range_low = test_low
                                range_high = test_high
                                range_width_pct = test_width
                                sweep_idx = test_sweep_idx
                                sweep_low = test_sweep_low
                                sweep_depth_pct = test_sweep_depth
                                sweep_candles = test_sweep_candles
                                contamination_fixed = True
                                break

            # Pattern 2: OLD_DEBRIS or RECENT_SWEEP
            if not contamination_fixed and later_half_lows > 0 and earlier_half_lows > 0:
                debris_ratio = (later_half_lows - earlier_half_lows) / earlier_half_lows

                # Pattern 2a: OLD_DEBRIS (debris_ratio > 0.02, later much higher than earlier)
                if debris_ratio > 0.02:
                    # Try detecting range from a more recent slice (skip old debris)
                    if len(df) >= 50:
                        test_lookback = 20
                        alt_recent = df.tail(test_lookback)
                        alt_range_high = alt_recent["high"].max()
                        alt_range_low = alt_recent["low"].min()
                        alt_range_width = (alt_range_high - alt_range_low) / alt_range_low * 100

                        if (
                            self._range_detector.min_width <= alt_range_width <= self._range_detector.max_width
                            and alt_range_high > alt_range_low
                        ):
                            alt_sweep_idx, alt_sweep_low, alt_sweep_depth, alt_sweep_candles = (
                                self._sweep_detector.detect(df, alt_range_low, lookback=test_lookback)
                            )
                            if alt_sweep_idx is not None:
                                range_low = alt_range_low
                                range_high = alt_range_high
                                range_width_pct = alt_range_width
                                sweep_idx = alt_sweep_idx
                                sweep_low = alt_sweep_low
                                sweep_depth_pct = alt_sweep_depth
                                sweep_candles = alt_sweep_candles
                                contamination_fixed = True

                # Pattern 2b: RECENT_SWEEP (debris_ratio < 0, recent dips but earlier stable)
                # Recent dips indicate sweep/wick events within the range, use earlier_half as range
                elif debris_ratio < 0:
                    alt_range_low = earlier_half_lows
                    alt_range_high = recent["high"].iloc[:mid].max()
                    if alt_range_high > alt_range_low:
                        alt_range_width = (alt_range_high - alt_range_low) / alt_range_low * 100

                        if self._range_detector.min_width <= alt_range_width <= self._range_detector.max_width:
                            alt_sweep_idx, alt_sweep_low, alt_sweep_depth, alt_sweep_candles = (
                                self._sweep_detector.detect(df, alt_range_low, lookback=self._range_detector.lookback)
                            )
                            if alt_sweep_idx is not None:
                                range_low = alt_range_low
                                range_high = alt_range_high
                                range_width_pct = alt_range_width
                                sweep_idx = alt_sweep_idx
                                sweep_low = alt_sweep_low
                                sweep_depth_pct = alt_sweep_depth
                                sweep_candles = alt_sweep_candles
                                contamination_fixed = True

            # If still no sweep, return RANGE
            if sweep_idx is None:
                return "RANGE", {
                    "range_high": range_high,
                    "range_low": range_low,
                    "range_width": range_width_pct,
                    "range_lookback": self._range_detector.lookback,
                }, None

        # Step 3.1: FIND SWEEP START (sweep_idx is most recent breach; find where it begins)
        # This allows proper reclaim/breakdown window calculations
        # IMPORTANT: Find the contiguous block of sweeps, not all historical lows < range_low
        # When range_low increases (e.g., 95→100 after recovery), candles from the old regime
        # may have low=95 < 100, but they're not part of the current sweep event.
        # Scan backward until we find a candle with low >= range_low; that's the boundary.
        sweep_start_idx = sweep_idx
        max_scan_back = 40  # Max candles to scan backward to find sweep start
        for i in range(sweep_idx - 1, max(0, sweep_idx - max_scan_back), -1):
            if df["low"].iloc[i] < range_low:
                sweep_start_idx = i
            else:
                # Found boundary: this candle has low >= range_low
                # Sweep started just after this position
                break

        # CRITICAL: If sweep_start_idx trace-back reaches the scan limit (max_scan_back),
        # we may have a RANGE SHIFT situation where the detected range_low is higher than
        # a previous support level. In this case, check for a contamination pattern:
        # if sweep covers a huge distance (>30 candles), the "sweep" might actually be
        # a regime change where prices naturally stayed below the new range_low.
        if sweep_idx - sweep_start_idx >= 30:
            # Large "sweep" suggests regime shift, not a true sweep event
            # Check if there's a natural support level within the old price regime
            # by looking for stability (lows cluster) within the sweep range
            sweep_section = df.iloc[sweep_start_idx:sweep_idx+1]
            sweep_lows = sweep_section["low"]

            # Check if earlier part of "sweep" is more stable (regime floor)
            # vs. later part being actual breach
            if len(sweep_section) >= 2:
                first_half = sweep_lows.iloc[:len(sweep_lows)//2]
                second_half = sweep_lows.iloc[len(sweep_lows)//2:]
                first_mean = first_half.mean()
                second_mean = second_half.mean()

                # If first half is notably higher than second half, this is a real sweep
                # If they're close, this is a regime boundary, not a sweep
                stability_ratio = (first_mean - second_mean) / first_mean if first_mean > 0 else 0

                if stability_ratio < 0.02:  # <2% difference = regime boundary, not sweep
                    # Potential RANGE SHIFT, but verify with recovery evidence
                    # Check if recent prices have recovered above the sweep lows
                    recent_section = df.iloc[sweep_idx:].tail(10)  # Last ~10 candles after sweep_idx
                    recent_mean_close = recent_section["close"].mean() if len(recent_section) > 0 else 0

                    sweep_section_mean_low = sweep_lows.mean()
                    recovery_ratio = (recent_mean_close - sweep_section_mean_low) / sweep_section_mean_low if sweep_section_mean_low > 0 else 0

                    # Only treat as range shift if there's significant recovery (>3% above sweep lows)
                    # AND the detected range is notably above sweep lows (4%+ increase indicates new level)
                    # This distinguishes range shift (recovery + new stable level) from
                    # just a large old sweep region (minor 3% fluctuation)
                    if recovery_ratio > 0.03 and range_low > sweep_section_mean_low * 1.04:
                        # This is a RANGE SHIFT, not a sweep
                        # Re-detect range using an earlier snapshot that has enough data
                        # The range detector needs at least lookback candles
                        min_rows_needed = self._range_detector.lookback

                        # Save original sweep values in case re-detection fails
                        orig_sweep_idx = sweep_idx
                        orig_sweep_low = sweep_low
                        orig_sweep_depth = sweep_depth_pct
                        orig_sweep_candles = sweep_candles

                        # Try indices with enough data: sweep_start_idx + 30, +20, +10, etc.
                        for offset in [30, 20, 10]:
                            test_idx = sweep_start_idx + offset
                            if test_idx <= len(df) and test_idx >= min_rows_needed:
                                test_data = df.iloc[:test_idx]
                                test_high, test_low, test_width, test_valid = (
                                    self._range_detector.detect(test_data)
                                )
                                if (test_valid and test_low is not None and
                                    test_low < range_low):  # Found a lower support (true range)
                                    range_low = test_low
                                    range_high = test_high
                                    range_width_pct = test_width

                                    # RE-DETECT SWEEP with corrected range_low
                                    new_sweep_idx, new_sweep_low, new_sweep_depth, new_sweep_candles = (
                                        self._sweep_detector.detect(
                                            df, range_low, lookback=self._range_detector.lookback
                                        )
                                    )

                                    if new_sweep_idx is not None:
                                        # Successfully found sweep with corrected range
                                        sweep_idx = new_sweep_idx
                                        sweep_low = new_sweep_low
                                        sweep_depth_pct = new_sweep_depth
                                        sweep_candles = new_sweep_candles

                                        # Re-find sweep start with corrected range_low
                                        sweep_start_idx = sweep_idx
                                        for i in range(sweep_idx - 1, max(0, sweep_idx - max_scan_back), -1):
                                            if df["low"].iloc[i] < range_low:
                                                sweep_start_idx = i
                                            else:
                                                break
                                        break

                    # If no valid lower support was found, restore original sweep values
                    # (range was not actually contaminated by range shift)
                    # Keep the original values from the initial detection

        # Step 3.5: TEMPORAL CAUSALITY CHECK - POST-SWEEP (SPRING-DETECTOR-001)
        # If sweep starts close to range end (within ~50 candles), range might be contaminated
        # Check earlier data for a more stable range
        range_end_idx = len(df) - 1
        distance_from_range_end = range_end_idx - sweep_start_idx

        if 0 < distance_from_range_end < 50 and sweep_start_idx > self._range_detector.lookback:
            # Sweep is close to range end; range is likely contaminated
            # Look for earlier, uncontaminated range
            for test_idx in [sweep_start_idx - 10, sweep_start_idx]:
                if test_idx > self._range_detector.lookback:
                    test_data = df.iloc[:test_idx]
                    test_high, test_low, test_width, test_valid = (
                        self._range_detector.detect(test_data)
                    )
                    # Use the first valid range that's higher (more stable support)
                    if test_valid and test_low is not None and test_low > range_low:
                        range_low = test_low
                        range_high = test_high
                        range_width_pct = test_width

                        # RE-DETECT SWEEP with corrected range_low
                        sweep_idx, sweep_low, sweep_depth_pct, sweep_candles = self._sweep_detector.detect(
                            df, range_low, lookback=self._range_detector.lookback
                        )

                        # If sweep vanishes, treat as RANGE
                        if sweep_idx is None:
                            return "RANGE", {
                                "range_high": range_high,
                                "range_low": range_low,
                                "range_width": range_width_pct,
                                "range_lookback": self._range_detector.lookback,
                            }, None

                        # Re-find sweep start with corrected range_low (same 40-candle limit as initial scan)
                        sweep_start_idx = sweep_idx
                        max_scan_back = 40
                        for i in range(sweep_idx - 1, max(0, sweep_idx - max_scan_back), -1):
                            if df["low"].iloc[i] < range_low:
                                sweep_start_idx = i
                            else:
                                break
                        break

        # Step 4: Look for reclaim after sweep start
        reclaim_idx, reclaim_timestamp, reclaim_close, candles_to_reclaim = (
            self._reclaim_detector.detect(df, sweep_start_idx, range_low, self.reclaim_window_candles)
        )

        if reclaim_idx is not None:
            # Reclaim found → SPRING_CANDIDATE
            # Safety check: sweep_low should be set, but if it's None (from failed range shift re-detection),
            # we cannot compute a valid SPRING_CANDIDATE, so treat as SWEEP
            if sweep_low is None or sweep_idx is None:
                # Range shift re-detection may have left sweep_low as None
                # Return SWEEP instead (reclaim window still open)
                return "SWEEP", {
                    "range_low": range_low,
                    "sweep_low": sweep_low if sweep_low is not None else 0,
                    "candles_since_sweep": len(df) - (sweep_idx if sweep_idx is not None else 0),
                    "recovery_pct": 0,
                }, None

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

        # Step 5: Check if reclaim window closed without reclaim (using sweep_start_idx for timing)
        if sweep_start_idx + self.reclaim_window_candles < len(df):
            # Calculate sweep_low from sweep window only (not including post-window)
            sweep_window_end = min(sweep_start_idx + self.reclaim_window_candles, len(df))
            sweep_low_in_window = df.iloc[sweep_start_idx:sweep_window_end]["low"].min()

            post_window = df.iloc[sweep_start_idx + self.reclaim_window_candles :]
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
