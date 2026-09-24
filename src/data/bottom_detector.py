"""Bottom Detector — P0.3 RESEARCH_CANDIDATE

Classifies tokens into 4 mutually exclusive bottom states based on daily OHLCV:
- NO_BOTTOM_STRUCTURE: Insufficient data or uptrend
- DRAWDOWN: Price down, no stabilization
- BASE_CANDIDATE: Drawdown + stabilization detected

Status: RESEARCH_CANDIDATE (not backtested, not validated PIT/OOS/WFV)
"""

import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from pydantic import BaseModel, field_validator

from src.data.schema import OHLCVCandle


class BottomDetectorError(Exception):
    """Base exception for Bottom Detector."""
    pass


class InsufficientDataError(BottomDetectorError):
    """Raised when DataFrame has fewer than 50 candles."""
    pass


class DataQualityError(BottomDetectorError):
    """Raised when DataFrame contains NaN, duplicates, or non-monotonic timestamps."""
    pass


class BottomDetectorOutput(BaseModel):
    """Machine-readable output from Bottom Detector."""
    symbol: str
    timestamp: datetime
    timeframe: str = "daily"
    state: str
    evidence: Dict[str, Any]
    status: str = "RESEARCH_CANDIDATE"
    reason: Optional[str] = None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        valid_states = {"NO_BOTTOM_STRUCTURE", "DRAWDOWN", "BASE_CANDIDATE"}
        if v not in valid_states:
            raise ValueError(f"Invalid state: {v}. Must be one of {valid_states}")
        return v


class DrawdownCalculator:
    """Calculates drawdown from rolling historical high."""

    def __init__(self, lookback: int = 100):
        """
        Args:
            lookback: Number of candles to look back for rolling high (default 100 days)
        """
        self.lookback = lookback

    def calculate(self, df: pd.DataFrame) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate drawdown from rolling high.

        Args:
            df: DataFrame with 'high' and 'close' columns

        Returns:
            (drawdown_pct, rolling_high, current_close) or (None, None, None) if insufficient data
        """
        if len(df) < 50:
            return None, None, None

        if df["high"].isna().any() or df["close"].isna().any():
            raise DataQualityError("DataFrame contains NaN in high or close")

        rolling_high = df["high"].rolling(self.lookback, min_periods=1).max()
        current_high = rolling_high.iloc[-1]
        current_close = df["close"].iloc[-1]

        if current_high == 0:
            return None, None, None

        drawdown_pct = (current_close - current_high) / current_high * 100
        return drawdown_pct, current_high, current_close


class BaseConsolidationDetector:
    """Detects price consolidation (base range) in recent candles."""

    def __init__(self, lookback: int = 30, range_threshold: float = 12.0, stability_threshold: float = 30.0):
        """
        Args:
            lookback: Number of recent candles to analyze (default 30 days)
            range_threshold: Max range width % (default 12%)
            stability_threshold: Min % closes above mid-range (default 30%)
        """
        self.lookback = lookback
        self.range_threshold = range_threshold
        self.stability_threshold = stability_threshold

    def detect(self, df: pd.DataFrame) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], bool]:
        """
        Detect consolidation in recent candles.

        Args:
            df: DataFrame with 'high', 'low', 'close' columns

        Returns:
            (base_high, base_low, base_range_pct, stability_pct, is_consolidated)
            or (None, None, None, None, False) if insufficient data
        """
        if len(df) < self.lookback:
            return None, None, None, None, False

        if df["high"].isna().any() or df["low"].isna().any() or df["close"].isna().any():
            raise DataQualityError("DataFrame contains NaN in high, low, or close")

        recent = df.tail(self.lookback)
        base_high = recent["high"].max()
        base_low = recent["low"].min()
        base_close = recent["close"].iloc[-1]

        if base_close == 0:
            return None, None, None, None, False

        base_range_pct = (base_high - base_low) / base_close * 100
        mid_range = (base_high + base_low) / 2
        closes_above_mid = (recent["close"] >= mid_range).sum()
        stability_pct = (closes_above_mid / len(recent)) * 100

        is_consolidated = (base_range_pct <= self.range_threshold) and (stability_pct >= self.stability_threshold)

        return base_high, base_low, base_range_pct, stability_pct, is_consolidated


class BottomStateMachine:
    """State machine for bottom detection (4 mutually exclusive states)."""

    def __init__(
        self,
        drawdown_threshold: float = -20.0,
        base_range_threshold: float = 12.0,
        stability_threshold: float = 30.0,
        escape_threshold: float = -2.0,
    ):
        """
        Args:
            drawdown_threshold: Min drawdown % to enter DRAWDOWN state (default -20%)
            base_range_threshold: Max range width % for BASE_CANDIDATE (default 12%)
            stability_threshold: Min % closes above mid-range for BASE_CANDIDATE (default 30%)
            escape_threshold: Max % below base_low to invalidate BASE_CANDIDATE (default -2%)
        """
        self.drawdown_threshold = drawdown_threshold
        self.base_range_threshold = base_range_threshold
        self.stability_threshold = stability_threshold
        self.escape_threshold = escape_threshold

    def classify(
        self,
        df: pd.DataFrame,
        drawdown_pct: Optional[float],
        base_high: Optional[float],
        base_low: Optional[float],
        base_range_pct: Optional[float],
        stability_pct: Optional[float],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Classify token into one of 4 states.

        Args:
            df: Full daily DataFrame
            drawdown_pct: Drawdown from rolling high (%)
            base_high, base_low: Base range boundaries
            base_range_pct: Base range width (%)
            stability_pct: % closes above mid-range

        Returns:
            (state: str, evidence: dict)
        """
        # Check data sufficiency
        if len(df) < 50:
            return "NO_BOTTOM_STRUCTURE", {"reason": "insufficient_data", "candles": len(df)}

        # No drawdown detected
        if drawdown_pct is None or drawdown_pct > -5:
            return "NO_BOTTOM_STRUCTURE", {
                "drawdown": drawdown_pct,
                "reason": "uptrend_or_minimal_drawdown",
            }

        # Significant drawdown; check for stabilization
        if drawdown_pct < self.drawdown_threshold:
            # Check for wide range (still volatile)
            if base_range_pct is None or base_range_pct > self.base_range_threshold + 3:
                return "DRAWDOWN", {
                    "drawdown": drawdown_pct,
                    "base_range": base_range_pct,
                    "reason": "wide_base_range",
                }

            # Check for continued selling (new lows in last 5 candles)
            recent_5 = df.tail(5)
            lowest_5 = recent_5["low"].min()
            if base_low is not None and lowest_5 < base_low * (1 + self.escape_threshold / 100):
                return "DRAWDOWN", {
                    "drawdown": drawdown_pct,
                    "recent_new_low": True,
                    "reason": "continuing_selloff",
                }

            # Check stability (closes near lows)
            if stability_pct is None or stability_pct < self.stability_threshold:
                return "DRAWDOWN", {
                    "drawdown": drawdown_pct,
                    "stability": stability_pct,
                    "reason": "low_stability",
                }

            # All checks passed → BASE_CANDIDATE
            return "BASE_CANDIDATE", {
                "drawdown": drawdown_pct,
                "rolling_high": df["high"].rolling(100, min_periods=1).max().iloc[-1],
                "base_high": base_high,
                "base_low": base_low,
                "base_range": base_range_pct,
                "stability": stability_pct,
                "consolidation_candles": len(df.tail(30)),
            }

        # -5% to -20% drawdown
        return "DRAWDOWN", {
            "drawdown": drawdown_pct,
            "reason": "moderate_drawdown",
        }


class BottomDetector:
    """Public interface for Bottom Detector (composition of calculators)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Configuration dict with keys:
                - drawdown_lookback: int (default 100)
                - drawdown_threshold: float (default -20)
                - base_lookback: int (default 30)
                - base_range_threshold: float (default 12)
                - stability_threshold: float (default 30)
                - escape_threshold: float (default -2)
        """
        config = config or {}
        drawdown_lookback = config.get("drawdown_lookback", 100)
        drawdown_threshold = config.get("drawdown_threshold", -20.0)
        base_lookback = config.get("base_lookback", 30)
        base_range_threshold = config.get("base_range_threshold", 12.0)
        stability_threshold = config.get("stability_threshold", 30.0)
        escape_threshold = config.get("escape_threshold", -2.0)

        self._drawdown_calc = DrawdownCalculator(lookback=drawdown_lookback)
        self._base_detector = BaseConsolidationDetector(
            lookback=base_lookback,
            range_threshold=base_range_threshold,
            stability_threshold=stability_threshold,
        )
        self._state_machine = BottomStateMachine(
            drawdown_threshold=drawdown_threshold,
            base_range_threshold=base_range_threshold,
            stability_threshold=stability_threshold,
            escape_threshold=escape_threshold,
        )

    def classify(self, symbol: str, df: pd.DataFrame) -> BottomDetectorOutput:
        """
        Classify token into bottom state.

        Args:
            symbol: Token symbol (e.g., "BTC")
            df: Daily OHLCV DataFrame with columns [timestamp, open, high, low, close, volume]

        Returns:
            BottomDetectorOutput with state, evidence, and status

        Raises:
            DataQualityError: If DataFrame contains NaN, duplicates, or non-monotonic timestamps
        """
        try:
            # Validate data quality
            if df.empty:
                raise DataQualityError("DataFrame is empty")

            if df[["open", "high", "low", "close", "volume"]].isna().any().any():
                raise DataQualityError("DataFrame contains NaN values")

            if df["timestamp"].duplicated().any():
                raise DataQualityError("DataFrame contains duplicate timestamps")

            if not df["timestamp"].is_monotonic_increasing:
                raise DataQualityError("DataFrame timestamps are not monotonically increasing")

            # Calculate drawdown
            drawdown_pct, rolling_high, current_close = self._drawdown_calc.calculate(df)

            # Detect base consolidation
            base_high, base_low, base_range_pct, stability_pct, _ = self._base_detector.detect(df)

            # Classify state
            state, evidence = self._state_machine.classify(
                df, drawdown_pct, base_high, base_low, base_range_pct, stability_pct
            )

            return BottomDetectorOutput(
                symbol=symbol,
                timestamp=df["timestamp"].iloc[-1],
                timeframe="daily",
                state=state,
                evidence=evidence,
                status="RESEARCH_CANDIDATE",
                reason=None,
            )

        except (DataQualityError, InsufficientDataError) as e:
            return BottomDetectorOutput(
                symbol=symbol,
                timestamp=df["timestamp"].iloc[-1] if not df.empty else datetime.utcnow(),
                timeframe="daily",
                state="NO_BOTTOM_STRUCTURE",
                evidence={},
                status="RESEARCH_CANDIDATE",
                reason=str(e),
            )
