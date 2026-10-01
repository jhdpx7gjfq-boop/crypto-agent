"""Component 6: Momentum Confirmation (Emerging Strength)."""

import logging
from typing import List
import numpy as np

from src.core.models import OHLCV

logger = logging.getLogger(__name__)


class MomentumConfirmation:
    """
    Confirm emerging upside momentum (avoid overbought/false breakouts).

    Score 1.0: MACD hist > 0, Stochastic < 80, ADX > 20
    Score 0.7: MACD hist > 0, Stochastic < 70
    Score 0.4: MACD hist transitioning to positive
    Score 0.0: Otherwise
    """

    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    RSI_PERIOD = 14
    ADX_PERIOD = 14

    def _compute_macd_histogram(self, closes: List[float]) -> float:
        """Compute MACD histogram (simplified)."""
        if len(closes) < self.MACD_SLOW:
            return 0.0

        # Simplified: just use difference of recent EMAs
        fast_avg = np.mean(closes[-self.MACD_FAST:])
        slow_avg = np.mean(closes[-self.MACD_SLOW:])

        histogram = fast_avg - slow_avg
        return histogram

    def _compute_stochastic(self, ohlcv: List[OHLCV], period: int = 14) -> float:
        """Compute stochastic K (simplified)."""
        if len(ohlcv) < period:
            return 50.0

        window = ohlcv[-period:]
        lows = [c.low for c in window]
        highs = [c.high for c in window]

        period_low = min(lows)
        period_high = max(highs)
        current = ohlcv[-1].close

        range_val = period_high - period_low
        if range_val < 1e-6:
            return 50.0

        k = 100.0 * (current - period_low) / range_val
        return k

    def _compute_adx(self, ohlcv: List[OHLCV], period: int = 14) -> float:
        """Compute ADX (simplified)."""
        if len(ohlcv) < period + 1:
            return 0.0

        window = ohlcv[-period:]

        # Up moves
        up_moves = sum(1 for i in range(1, len(window)) if window[i].high > window[i-1].high)
        # Down moves
        down_moves = sum(1 for i in range(1, len(window)) if window[i].low < window[i-1].low)

        # Directional movement (simplified)
        di_diff = abs(up_moves - down_moves)
        adx = (di_diff / period) * 100 if period > 0 else 0.0

        return adx

    def compute(self, ohlcv_data: List[OHLCV]) -> float:
        """
        Compute momentum confirmation score.

        Args:
            ohlcv_data: Time-series OHLCV data

        Returns:
            float: Score 0–1
        """
        if len(ohlcv_data) < self.MACD_SLOW:
            logger.warning(f"Insufficient data for MC: {len(ohlcv_data)} < {self.MACD_SLOW}")
            return 0.0

        closes = [c.close for c in ohlcv_data]

        # Momentum indicators
        macd_hist = self._compute_macd_histogram(closes)
        stochastic = self._compute_stochastic(ohlcv_data, 14)
        adx = self._compute_adx(ohlcv_data, 14)

        # Recent SMA alignment
        sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else closes[-1]
        above_sma = closes[-1] > sma_20

        # Scoring
        if macd_hist > 0 and stochastic < 80 and adx > 20:
            score = 1.0  # Strong emerging momentum
        elif macd_hist > 0 and stochastic < 70:
            score = 0.7  # Moderate momentum
        elif macd_hist > -0.01 and macd_hist < 0.01 and above_sma:
            score = 0.4  # Weak transitioning signal
        else:
            score = 0.0

        logger.debug(
            f"MC: score={score:.2f}, MACD_hist={macd_hist:.4f}, "
            f"Stoch={stochastic:.1f}, ADX={adx:.1f}, above_SMA20={above_sma}"
        )

        return max(0.0, min(1.0, score))
