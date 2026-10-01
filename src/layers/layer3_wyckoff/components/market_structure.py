"""Component 5: Market Structure (Trend Alignment)."""

import logging
from typing import List
import numpy as np

from src.core.models import OHLCV

logger = logging.getLogger(__name__)


class MarketStructure:
    """
    Ensure local trend supports accumulation (avoid downtrends).

    Score 1.0: Price > 20SMA > 50SMA > 200SMA (bullish structure)
    Score 0.7: Price > 50SMA > 200SMA (bullish bias)
    Score 0.5: 20SMA < 50SMA < 200SMA AND price near 50SMA (neutral)
    Score 0.0: Bearish structure (20SMA < 50SMA < 200SMA AND price < 50SMA)
    """

    SMA_20 = 20
    SMA_50 = 50
    SMA_200 = 200

    def _compute_sma(self, closes: List[float], period: int) -> float:
        """Compute simple moving average."""
        if len(closes) < period:
            return closes[-1] if closes else 0.0
        return np.mean(closes[-period:])

    def compute(self, ohlcv_data: List[OHLCV]) -> float:
        """
        Compute market structure score.

        Args:
            ohlcv_data: Time-series OHLCV data

        Returns:
            float: Score 0–1
        """
        if len(ohlcv_data) < self.SMA_200:
            logger.warning(f"Insufficient data for MS: {len(ohlcv_data)} < {self.SMA_200}")
            return 0.0

        closes = [c.close for c in ohlcv_data]

        # SMAs
        sma_20 = self._compute_sma(closes, self.SMA_20)
        sma_50 = self._compute_sma(closes, self.SMA_50)
        sma_200 = self._compute_sma(closes, self.SMA_200)
        current_price = closes[-1]

        # Scoring
        if current_price > sma_20 > sma_50 > sma_200:
            score = 1.0  # Bullish structure
        elif current_price > sma_50 > sma_200:
            score = 0.7  # Bullish bias
        elif sma_20 < sma_50 < sma_200 and current_price >= sma_50 * 0.98:
            score = 0.5  # Neutral, testing support
        else:
            score = 0.0  # Bearish structure

        logger.debug(
            f"MS: score={score:.2f}, price={current_price:.2f}, "
            f"SMA20={sma_20:.2f}, SMA50={sma_50:.2f}, SMA200={sma_200:.2f}"
        )

        return max(0.0, min(1.0, score))
