"""Component 3: Selling Exhaustion (Weakness Confirmation)."""

import logging
from typing import List, Tuple
import numpy as np

from src.core.models import OHLCV

logger = logging.getLogger(__name__)


class SellingExhaustion:
    """
    Detect weak hands capitulating via RSI, MACD, range expansion.

    Score 1.0: RSI < 30, MACD < 0, range > 2x avg
    Score 0.7: RSI < 35, MACD < -0.5
    Score 0.4: RSI < 40
    Score 0.0: Otherwise
    """

    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    RANGE_LOOKBACK = 20

    def _compute_rsi(self, closes: List[float], period: int = 14) -> float:
        """Compute RSI (14-period)."""
        if len(closes) < period + 1:
            return 50.0  # Neutral if insufficient data

        deltas = np.diff(closes[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi

    def _compute_macd(self, closes: List[float]) -> Tuple[float, float, float]:
        """Compute MACD histogram."""
        if len(closes) < self.MACD_SLOW + self.MACD_SIGNAL:
            return 0.0, 0.0, 0.0

        closes_arr = np.array(closes)

        # EMA fast
        ema_fast = closes_arr[-self.MACD_FAST:].mean()  # Simplified
        # EMA slow
        ema_slow = closes_arr[-self.MACD_SLOW:].mean()  # Simplified

        macd_line = ema_fast - ema_slow

        # Signal line (EMA of MACD)
        signal_line = macd_line  # Simplified
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def compute(self, ohlcv_data: List[OHLCV]) -> float:
        """
        Compute selling exhaustion score.

        Args:
            ohlcv_data: Time-series OHLCV data

        Returns:
            float: Score 0–1
        """
        if len(ohlcv_data) < self.MACD_SLOW + self.MACD_SIGNAL:
            logger.warning(f"Insufficient data for SE: {len(ohlcv_data)}")
            return 0.0

        closes = [c.close for c in ohlcv_data]

        # RSI
        rsi = self._compute_rsi(closes, self.RSI_PERIOD)

        # MACD
        macd_line, signal_line, histogram = self._compute_macd(closes)

        # Range analysis
        recent_candles = ohlcv_data[-self.RANGE_LOOKBACK:]
        recent_ranges = [c.high - c.low for c in recent_candles]
        avg_range = np.mean(recent_ranges) if recent_ranges else 1.0
        current_range = ohlcv_data[-1].high - ohlcv_data[-1].low

        # Scoring
        if rsi < 30 and histogram < 0 and current_range > 2 * avg_range:
            score = 1.0
        elif rsi < 35 and histogram < -0.5:
            score = 0.7
        elif rsi < 40:
            score = 0.4
        else:
            score = 0.0

        logger.debug(f"SE: score={score:.2f}, RSI={rsi:.1f}, MACD_hist={histogram:.4f}, range_ratio={current_range/avg_range:.2f}")

        return max(0.0, min(1.0, score))
