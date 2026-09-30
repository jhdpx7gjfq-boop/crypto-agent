"""
Wyckoff Bottom Confirmation Engine v2 (Phase 3)
Version: 2.0.0

Enhanced BCE with:
- Refined component scoring
- Multi-timeframe confirmation (1d, 4h, 1h)
- Confidence scoring (0-100)
- Pattern strength metrics
- Historical validation
"""

import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

from src.core.models import OHLCV, WyckoffSignal

logger = logging.getLogger(__name__)

VERSION = "2.0.0"

# Thresholds for component scoring
THRESHOLDS = {
    "wyckoff_structure_min": 0.60,
    "volume_climax_min": 0.60,
    "selling_exhaustion_min": 0.60,
    "smart_money_min": 0.50,
    "market_structure_min": 0.60,
    "momentum_min": 0.40,
    "bce_valid_threshold": 5.0,  # >= 5/6
    "confidence_threshold": 60,  # % for high confidence signal
}


@dataclass
class MultiTimeframeResult:
    """Multi-timeframe BCE result."""

    timeframe: str  # "1d", "4h", "1h"
    bce_score: float
    components: Dict[str, float]
    valid: bool
    confidence: int  # 0-100


class WyckoffBCEv2:
    """
    Enhanced Wyckoff Bottom Confirmation Engine v2.

    Improvements over v1:
    - Better support/resistance detection
    - Enhanced volume analysis (climax detection)
    - Improved exhaustion pattern recognition
    - Order flow inference for smart money
    - Timeframe confirmation logic
    - Confidence scoring based on pattern strength
    """

    def __init__(self):
        self.lookback_short = 20   # 20 candles for local analysis
        self.lookback_medium = 60  # 60 candles for medium-term structure
        self.lookback_long = 200   # 200 candles for trend context

    def analyze_single_timeframe(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        timeframe: str = "1d",
    ) -> WyckoffSignal:
        """
        Analyze a single timeframe for BCE.

        Args:
            asset: Symbol (e.g., "BTC")
            ohlcv_data: OHLCV candles
            timeframe: "1d", "4h", "1h"

        Returns:
            WyckoffSignal with enhanced v2 scoring
        """
        if not ohlcv_data or len(ohlcv_data) < self.lookback_medium:
            logger.warning(f"{asset} {timeframe}: Insufficient data ({len(ohlcv_data)} candles)")
            return self._empty_signal(asset, ohlcv_data, timeframe)

        timestamp = ohlcv_data[-1].timestamp

        # v2 Component scoring (each 0-1 scale)
        wyckoff_struct = self._score_wyckoff_structure_v2(ohlcv_data)
        volume_score = self._score_volume_analysis_v2(ohlcv_data)
        exhaustion = self._score_selling_exhaustion_v2(ohlcv_data)
        smart_money = self._score_smart_money_v2(ohlcv_data)
        market_struct = self._score_market_structure_v2(ohlcv_data)
        momentum = self._score_momentum_v2(ohlcv_data)

        # Average score (0-6 scale)
        components = {
            "wyckoff_structure": wyckoff_struct,
            "volume_analysis": volume_score,
            "selling_exhaustion": exhaustion,
            "smart_money_accumulation": smart_money,
            "market_structure": market_struct,
            "momentum_confirmation": momentum,
        }

        avg_score = sum(components.values()) / len(components)
        bce_score = avg_score  # 0-1 scale in WyckoffSignal

        # Confidence scoring
        confidence = self._calculate_confidence(components)

        # Validity
        valid = avg_score >= (THRESHOLDS["bce_valid_threshold"] / 6)

        signal = WyckoffSignal(
            timestamp=timestamp,
            asset=asset,
            bce_score=bce_score,
            wyckoff_structure=wyckoff_struct,
            volume_analysis=volume_score,
            selling_exhaustion=exhaustion,
            smart_money_accumulation=smart_money,
            market_structure=market_struct,
            momentum_confirmation=momentum,
            valid=valid,
        )

        logger.info(
            f"{asset} {timeframe} BCEv2: {bce_score:.3f}/1.0 "
            f"(conf={confidence}%, valid={valid})"
        )

        return signal

    def _score_wyckoff_structure_v2(self, ohlcv: List[OHLCV]) -> float:
        """
        Enhanced Wyckoff structure detection (v2).

        Looks for:
        - Support/resistance levels (repeated tests)
        - Spring pattern (break + recovery)
        - Shakeout pattern (new lows on high volume)
        - Recovery after exhaustion
        """
        recent = ohlcv[-self.lookback_medium:]
        df = pd.DataFrame([
            {"open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
            for c in recent
        ])

        lows = df["low"].values
        highs = df["high"].values
        closes = df["close"].values

        score = 0.0

        # Find support level (area where price tested multiple times)
        recent_lows = lows[-20:]
        support_level = recent_lows.min()

        # Count support tests
        support_tests = sum(1 for low in recent_lows if low <= support_level * 1.01)
        if support_tests >= 2:
            score += 0.2  # Multiple support tests = stronger structure

        # Detect spring pattern (drop below support + recovery)
        if len(closes) > 5:
            recent_closes = closes[-5:]
            if recent_closes[-1] > support_level and recent_closes[0] <= support_level:
                score += 0.2  # Spring detected

        # Higher lows formation (after spring)
        if len(lows) > 10:
            recent_5_lows = lows[-10:-5]
            last_5_lows = lows[-5:]
            if last_5_lows.min() > recent_5_lows.min():
                score += 0.2  # Higher lows = bullish structure

        # Range contraction (volatility declining into bottom)
        recent_range = df["high"] - df["low"]
        if len(recent_range) > 10:
            avg_range_20 = recent_range[-20:].mean()
            avg_range_10 = recent_range[-10:].mean()
            if avg_range_10 < avg_range_20 * 0.8:
                score += 0.2  # Range contraction = accumulation

        # Close near top of range (bullish behavior)
        if len(closes) > 0:
            last_close = closes[-1]
            last_high = highs[-1]
            last_low = lows[-1]
            if last_high > last_low:
                close_position = (last_close - last_low) / (last_high - last_low)
                if close_position >= 0.6:
                    score += 0.2  # Closing in upper half of range

        return min(score, 1.0)

    def _score_volume_analysis_v2(self, ohlcv: List[OHLCV]) -> float:
        """
        Enhanced volume analysis (v2).

        Looks for:
        - Volume climax on support
        - Relative volume declining into bottom
        - Volume expansion on break
        """
        recent = ohlcv[-self.lookback_medium:]
        df = pd.DataFrame([
            {"high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
            for c in recent
        ])

        volumes = df["volume"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        score = 0.0

        # Detect volume climax (spike followed by decline)
        if len(volumes) > 20:
            max_vol_idx = volumes[-20:].argmax() + (len(volumes) - 20)
            max_vol = volumes[max_vol_idx]
            avg_vol_before = volumes[max(0, max_vol_idx-10):max_vol_idx].mean()

            if max_vol > avg_vol_before * 1.5:
                score += 0.3  # Volume climax detected

        # Volume declining into bottom
        if len(volumes) >= 10:
            vol_recent_5 = volumes[-5:].mean()
            vol_previous_10 = volumes[-15:-5].mean()
            if vol_recent_5 < vol_previous_10 * 0.8:
                score += 0.2  # Volume declining = exhaustion near

        # Volume expansion on break above resistance
        if len(volumes) >= 2:
            recent_vol = volumes[-1]
            avg_vol = volumes[:-1].mean()
            if recent_vol > avg_vol * 1.3 and closes[-1] > closes[-2]:
                score += 0.3  # Volume expansion on up move

        return min(score, 1.0)

    def _score_selling_exhaustion_v2(self, ohlcv: List[OHLCV]) -> float:
        """
        Enhanced selling exhaustion detection (v2).

        Looks for:
        - Lower lows on lower volume (exhaustion)
        - Reversal candle patterns
        - Volume drying up
        """
        recent = ohlcv[-self.lookback_short:]
        df = pd.DataFrame([
            {"open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
            for c in recent
        ])

        lows = df["low"].values
        volumes = df["volume"].values
        opens = df["open"].values
        closes = df["close"].values

        score = 0.0

        # Lower lows on lower volume pattern
        if len(lows) >= 5:
            recent_3_lows = lows[-3:]
            prev_3_lows = lows[-6:-3]
            recent_3_vols = volumes[-3:]
            prev_3_vols = volumes[-6:-3]

            if recent_3_lows.min() < prev_3_lows.min() and recent_3_vols.mean() < prev_3_vols.mean():
                score += 0.3  # Lower lows on lower volume = strong exhaustion

        # Reversal candle (large wick up, close near top)
        if len(opens) > 0:
            last_open = opens[-1]
            last_close = closes[-1]
            last_high = df["high"].values[-1]
            last_low = lows[-1]

            if last_high > last_low:
                wick_up = last_high - max(last_open, last_close)
                body = abs(last_close - last_open)
                total_range = last_high - last_low

                if wick_up > body and wick_up > total_range * 0.3:
                    score += 0.3  # Reversal candle detected

        # Volume drying up (decreasing volume on recent candles)
        if len(volumes) >= 5:
            recent_vol = volumes[-1]
            avg_vol = volumes[-5:-1].mean()
            if recent_vol < avg_vol * 0.7:
                score += 0.2  # Volume drying up = exhaustion

        return min(score, 1.0)

    def _score_smart_money_v2(self, ohlcv: List[OHLCV]) -> float:
        """
        Enhanced smart money accumulation detection (v2).

        Infers smart money via:
        - Tight range with rising closes (accumulation)
        - Large spreads with high close (buying pressure)
        - Support holding on volume
        """
        recent = ohlcv[-self.lookback_short:]
        df = pd.DataFrame([
            {"open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
            for c in recent
        ])

        opens = df["open"].values
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        volumes = df["volume"].values

        score = 0.0

        # Tight range with rising closes (accumulation)
        if len(closes) >= 5:
            ranges = highs - lows
            avg_range = ranges[-5:].mean()
            close_trend = closes[-1] - closes[-5]

            if avg_range < ranges.mean() * 0.8 and close_trend > 0:
                score += 0.25  # Tight range with uptrend = accumulation

        # Large body on close near top (buying pressure)
        if len(opens) > 0:
            bodies = np.abs(closes - opens)
            total_ranges = highs - lows

            if len(bodies) > 0 and len(total_ranges) > 0:
                body_ratio = bodies[-1] / total_ranges[-1] if total_ranges[-1] > 0 else 0
                close_ratio = (closes[-1] - lows[-1]) / total_ranges[-1] if total_ranges[-1] > 0 else 0

                if body_ratio > 0.5 and close_ratio > 0.6:
                    score += 0.25  # Large body with high close

        # Support holding on volume
        if len(volumes) >= 10:
            lows_recent = lows[-5:].min()
            lows_prev = lows[-10:-5].min()
            vol_recent = volumes[-5:].mean()
            vol_prev = volumes[-10:-5].mean()

            if lows_recent > lows_prev * 0.99 and vol_recent > vol_prev:
                score += 0.25  # Support holding on volume

        return min(score, 1.0)

    def _score_market_structure_v2(self, ohlcv: List[OHLCV]) -> float:
        """
        Enhanced market structure analysis (v2).

        Assesses:
        - Higher lows pattern strength
        - Support/resistance clarity
        - Trend direction context
        """
        recent = ohlcv[-self.lookback_medium:]
        lows = np.array([c.low for c in recent])
        highs = np.array([c.high for c in recent])
        closes = np.array([c.close for c in recent])

        score = 0.0

        # Higher lows pattern
        if len(lows) >= 10:
            lows_10 = lows[-10:]
            # Check for uptrend in lows
            low_points = []
            for i in range(len(lows_10)):
                if i == 0 or i == len(lows_10) - 1 or (lows_10[i] < lows_10[i-1] and lows_10[i] < lows_10[i+1]):
                    low_points.append((i, lows_10[i]))

            if len(low_points) >= 2:
                # Check if lows are rising
                if low_points[-1][1] > low_points[-2][1]:
                    score += 0.3  # Higher lows = bullish structure

        # Support/resistance clarity
        if len(lows) >= 20:
            recent_min = lows[-20:].min()
            # Count how many candles test this level
            tests = sum(1 for low in lows[-20:] if low <= recent_min * 1.02)
            if tests >= 2:
                score += 0.3  # Clear support level

        # Uptrend context (close > open average)
        if len(closes) >= 10:
            recent_closes = closes[-10:]
            recent_opens = np.array([ohlcv[-(10-i)].open for i in range(10)])
            bullish_candles = sum(1 for i in range(len(recent_closes)) if recent_closes[i] > recent_opens[i])
            if bullish_candles >= 6:
                score += 0.2  # Majority bullish candles

        return min(score, 1.0)

    def _score_momentum_v2(self, ohlcv: List[OHLCV]) -> float:
        """
        Enhanced momentum confirmation (v2).

        Measures:
        - RSI position (not oversold, room to recover)
        - Momentum divergence
        - Rate of change
        """
        closes = np.array([c.close for c in ohlcv[-self.lookback_short:]])

        score = 0.0

        # RSI calculation (simplified)
        if len(closes) >= 14:
            deltas = np.diff(closes)
            gains = deltas[deltas > 0].sum() / 14
            losses = abs(deltas[deltas < 0].sum()) / 14

            if losses > 0:
                rs = gains / losses
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100 if gains > 0 else 50

            # RSI >= 40 = not oversold, room to recover
            if rsi >= 40:
                score += 0.3
            elif rsi >= 30:
                score += 0.2

        # Rate of change (momentum)
        if len(closes) >= 5:
            roc = (closes[-1] - closes[-5]) / closes[-5] if closes[-5] > 0 else 0
            if roc >= 0:  # Positive ROC
                score += 0.35
            elif roc >= -0.02:  # Minor negative = stabilizing
                score += 0.2

        return min(score, 1.0)

    def _calculate_confidence(self, components: Dict[str, float]) -> int:
        """
        Calculate confidence score (0-100).

        Higher confidence when:
        - Multiple components above threshold
        - Strong overall agreement
        """
        scores = list(components.values())

        # Count how many components exceed threshold
        above_threshold = sum(1 for s in scores if s >= 0.6)

        # Base confidence on number of strong components
        base_confidence = (above_threshold / len(scores)) * 100

        # Adjust based on consistency (std dev)
        std_dev = np.std(scores)
        consistency_bonus = (1 - min(std_dev, 0.3) / 0.3) * 15  # -15 to 0 based on consistency

        confidence = int(base_confidence + consistency_bonus)
        return max(0, min(100, confidence))

    def _empty_signal(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        timeframe: str,
    ) -> WyckoffSignal:
        """Return empty signal when data insufficient."""
        timestamp = ohlcv_data[-1].timestamp if ohlcv_data else None
        return WyckoffSignal(
            timestamp=timestamp,
            asset=asset,
            bce_score=0.0,
            wyckoff_structure=0.0,
            volume_analysis=0.0,
            selling_exhaustion=0.0,
            smart_money_accumulation=0.0,
            market_structure=0.0,
            momentum_confirmation=0.0,
            valid=False,
        )
