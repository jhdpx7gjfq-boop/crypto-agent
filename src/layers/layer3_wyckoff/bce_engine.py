"""Bottom Confirmation Engine — Wyckoff Analysis (Layer 3)."""

import logging
from typing import List, Optional

from src.core.models import OHLCV, WyckoffSignal
from src.core.config import Config


logger = logging.getLogger(__name__)


class BottomConfirmationEngine:
    """
    Wyckoff-based Bottom Confirmation Engine (BCE).

    Detects accumulation zones via:
    1. Wyckoff structure (support/resistance, swings)
    2. Volume analysis (relative volume patterns)
    3. Selling exhaustion (low volume, bouncing)
    4. Smart money accumulation (tight range + volume)
    5. Market structure (higher lows pattern)
    6. Momentum confirmation (directional strength)

    Output: Combined score 0-6, ≥5 required for entry.
    """

    def __init__(self):
        self.config = Config

    def analyze(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
    ) -> WyckoffSignal:
        """
        Analyze OHLCV data for Wyckoff bottom confirmation.

        Returns: WyckoffSignal with all components scored.
        """

        if not ohlcv_data or len(ohlcv_data) < 20:
            logger.warning(f"{asset}: Insufficient data for BCE (need 20+ candles)")
            return WyckoffSignal(
                timestamp=ohlcv_data[-1].timestamp if ohlcv_data else None,
                asset=asset,
                bce_score=0,
                wyckoff_structure=0,
                volume_analysis=0,
                selling_exhaustion=0,
                smart_money_accumulation=0,
                market_structure=0,
                momentum_confirmation=0,
                valid=False,
            )

        timestamp = ohlcv_data[-1].timestamp

        # Component scoring (each 0-1 scale)
        wyckoff_struct = self._score_wyckoff_structure(ohlcv_data)
        volume_score = self._score_volume_analysis(ohlcv_data)
        exhaustion = self._score_selling_exhaustion(ohlcv_data)
        smart_money = self._score_smart_money_accumulation(ohlcv_data)
        market_struct = self._score_market_structure(ohlcv_data)
        momentum = self._score_momentum_confirmation(ohlcv_data)

        signal = WyckoffSignal(
            timestamp=timestamp,
            asset=asset,
            bce_score=0,  # Will be computed in __post_init__
            wyckoff_structure=wyckoff_struct,
            volume_analysis=volume_score,
            selling_exhaustion=exhaustion,
            smart_money_accumulation=smart_money,
            market_structure=market_struct,
            momentum_confirmation=momentum,
            valid=False,  # Will be set in __post_init__
        )

        logger.info(
            f"{asset} BCE: {signal.bce_score:.2f}/6 "
            f"(Struct={wyckoff_struct:.1f}, Vol={volume_score:.1f}, "
            f"Exhaust={exhaustion:.1f}, Smart={smart_money:.1f}, "
            f"MkrStruct={market_struct:.1f}, Mom={momentum:.1f})"
        )

        return signal

    @staticmethod
    def _score_wyckoff_structure(ohlcv: List[OHLCV]) -> float:
        """
        Score Wyckoff structure (0-1).

        Looks for: defined lows (support), resistance levels,
        and swing formation typical of accumulation.
        """

        recent = ohlcv[-20:]
        lows = [c.low for c in recent]
        highs = [c.high for c in recent]

        # Detect double/triple bottom pattern
        sorted_lows = sorted(lows)
        min_low = sorted_lows[0]
        second_min = sorted_lows[1] if len(sorted_lows) > 1 else min_low

        near_min_count = sum(1 for l in lows if abs(l - min_low) / min_low < 0.02)

        if near_min_count >= 2:
            return 0.8  # Multiple tests of low = accumulation
        elif near_min_count >= 1:
            return 0.5
        else:
            return 0.2

    @staticmethod
    def _score_volume_analysis(ohlcv: List[OHLCV]) -> float:
        """
        Score volume patterns (0-1).

        High volume on bounces from lows + low volume on further declines.
        """

        if len(ohlcv) < 10:
            return 0.0

        recent = ohlcv[-10:]
        volumes = [c.volume for c in recent]
        closes = [c.close for c in recent]
        lows = [c.low for c in recent]

        avg_vol = sum(volumes) / len(volumes)
        min_low = min(lows)

        # Count high-volume candles near the low
        near_low_high_vol = 0
        for i, c in enumerate(recent):
            if c.low <= min_low * 1.02 and c.volume > avg_vol * 1.5:
                near_low_high_vol += 1

        vol_declining = volumes[-3] > volumes[-1]

        if near_low_high_vol >= 2 and vol_declining:
            return 0.9  # Classic accumulation volume signature
        elif near_low_high_vol >= 1 or vol_declining:
            return 0.5
        else:
            return 0.2

    @staticmethod
    def _score_selling_exhaustion(ohlcv: List[OHLCV]) -> float:
        """
        Score selling exhaustion (0-1).

        Selling pressure taper + bounces on low volume.
        """

        if len(ohlcv) < 5:
            return 0.0

        recent = ohlcv[-5:]
        volumes = [c.volume for c in recent]
        closes = [c.close for c in recent]

        avg_recent_vol = sum(volumes[-3:]) / 3
        avg_prior_vol = sum(volumes[:2]) / 2 if len(volumes) >= 2 else avg_recent_vol

        vol_declining = avg_recent_vol < avg_prior_vol
        is_bouncing = closes[-1] > closes[-2]

        if vol_declining and is_bouncing:
            return 0.9
        elif vol_declining or is_bouncing:
            return 0.5
        else:
            return 0.1

    @staticmethod
    def _score_smart_money_accumulation(ohlcv: List[OHLCV]) -> float:
        """
        Score smart money patterns (0-1).

        Tight price range (low volatility) + consistent volume.
        """

        if len(ohlcv) < 10:
            return 0.0

        recent = ohlcv[-10:]
        price_range = max(c.high for c in recent) - min(c.low for c in recent)
        avg_price = sum(c.close for c in recent) / len(recent)

        range_pct = (price_range / avg_price) * 100 if avg_price > 0 else 100

        up_candles = sum(1 for c in recent if c.close > c.open)
        avg_vol = sum(c.volume for c in recent) / len(recent)
        consistent_vol = sum(1 for c in recent if abs(c.volume - avg_vol) / avg_vol < 0.5)

        tight_range = range_pct < 3
        balanced_closes = 3 <= up_candles <= 7
        vol_consistency = consistent_vol >= 6

        if tight_range and balanced_closes and vol_consistency:
            return 0.95
        elif (tight_range and balanced_closes) or (balanced_closes and vol_consistency):
            return 0.65
        elif tight_range or balanced_closes:
            return 0.4
        else:
            return 0.1

    @staticmethod
    def _score_market_structure(ohlcv: List[OHLCV]) -> float:
        """
        Score market structure (0-1).

        Higher lows (bullish structure) vs lower lows (bearish).
        """

        if len(ohlcv) < 10:
            return 0.5

        recent = ohlcv[-10:]
        lows = [c.low for c in recent]

        # Check trend: are lows rising?
        low_trend = lows[::2]  # Every other low

        if len(low_trend) >= 3:
            rising_lows = all(low_trend[i] < low_trend[i+1] for i in range(len(low_trend)-1))
            if rising_lows:
                return 0.9

        # Check if at least not making new lows
        if lows[-1] >= min(lows[:-1]):
            return 0.6
        else:
            return 0.2

    @staticmethod
    def _score_momentum_confirmation(ohlcv: List[OHLCV]) -> float:
        """
        Score momentum/RSI confirmation (0-1).

        Rising momentum from oversold conditions.
        """

        if len(ohlcv) < 14:
            return 0.5

        recent = ohlcv[-14:]
        closes = [c.close for c in recent]

        # Simple RSI approximation
        gains = sum(max(closes[i] - closes[i-1], 0) for i in range(1, len(closes)))
        losses = sum(max(closes[i-1] - closes[i], 0) for i in range(1, len(closes)))

        if losses == 0:
            rsi = 100 if gains > 0 else 50
        else:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))

        # Momentum rising from oversold
        if 30 <= rsi <= 50:
            return 0.8  # Oversold but bouncing
        elif rsi < 30:
            return 0.6  # Severely oversold
        elif 50 < rsi < 70:
            return 0.5  # Neutral momentum
        else:
            return 0.2  # Overbought
