"""Component 1: Wyckoff Structure (Price Consolidation)."""

import logging
from typing import List
import numpy as np

from src.core.models import OHLCV

logger = logging.getLogger(__name__)


class WyckoffStructure:
    """
    Detect price consolidation (range-bound trading).

    Score 1.0: Price within 20% of range width
    Score 0.6: Price within 20–50% of range
    Score 0.0: Price outside range
    """

    LOOKBACK = 30  # days
    RANGE_TOLERANCE_TIGHT = 0.20  # 20% of range width
    RANGE_TOLERANCE_MEDIUM = 0.50  # 50% of range width

    def compute(self, ohlcv_data: List[OHLCV]) -> float:
        """
        Compute wyckoff structure score.

        Args:
            ohlcv_data: Time-series OHLCV data

        Returns:
            float: Score 0–1
        """
        if len(ohlcv_data) < self.LOOKBACK:
            logger.warning(f"Insufficient data for WS: {len(ohlcv_data)} < {self.LOOKBACK}")
            return 0.0

        # Get lookback window
        window = ohlcv_data[-self.LOOKBACK:]

        # Compute range
        highs = [c.high for c in window]
        lows = [c.low for c in window]

        support = min(lows)
        resistance = max(highs)
        current_price = ohlcv_data[-1].close

        range_width = resistance - support

        if range_width < 1e-6:  # Degenerate range
            logger.warning("Degenerate range (width ~0)")
            return 0.0

        # Distance from support
        distance_from_support = current_price - support
        distance_ratio = distance_from_support / range_width

        # Scoring
        if distance_ratio <= self.RANGE_TOLERANCE_TIGHT:
            score = 1.0
        elif distance_ratio <= self.RANGE_TOLERANCE_MEDIUM:
            # Linear interpolation between 1.0 and 0.6
            score = 1.0 - (distance_ratio - self.RANGE_TOLERANCE_TIGHT) / (self.RANGE_TOLERANCE_MEDIUM - self.RANGE_TOLERANCE_TIGHT) * 0.4
        else:
            score = 0.0

        # Validation: Price must have traded outside range in past 10 days
        recent_10d = ohlcv_data[-10:] if len(ohlcv_data) >= 10 else ohlcv_data
        recent_lows = [c.low for c in recent_10d]
        recent_highs = [c.high for c in recent_10d]

        tested_support = min(recent_lows) <= support
        tested_resistance = max(recent_highs) >= resistance

        if not (tested_support or tested_resistance):
            logger.warning(f"Range not recently tested (WS validation failed)")
            score *= 0.5  # Penalize untested range

        logger.debug(f"WS: score={score:.2f}, range=[{support:.2f}, {resistance:.2f}], current={current_price:.2f}")

        return max(0.0, min(1.0, score))
