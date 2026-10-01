"""Component 2: Volume Analysis (Capitulation Detection)."""

import logging
from typing import List
import numpy as np

from src.core.models import OHLCV

logger = logging.getLogger(__name__)


class VolumeAnalysis:
    """
    Detect selling capitulation via volume spikes on downside.

    Score 1.0: Down-volume ≥1.5x avg, Up-volume ≤1.0x avg
    Score 0.7: Down-volume ≥1.2x avg, Up-volume ≤1.2x avg
    Score 0.5: Down-volume ≥1.0x avg, Up-volume ≤1.5x avg
    Score 0.0: Otherwise
    """

    AVG_LOOKBACK = 20  # days for average volume
    RECENT_LOOKBACK = 5  # days for recent volume

    def compute(self, ohlcv_data: List[OHLCV]) -> float:
        """
        Compute volume analysis score.

        Args:
            ohlcv_data: Time-series OHLCV data

        Returns:
            float: Score 0–1
        """
        if len(ohlcv_data) < self.AVG_LOOKBACK + self.RECENT_LOOKBACK:
            logger.warning(f"Insufficient data for VA: {len(ohlcv_data)} < {self.AVG_LOOKBACK + self.RECENT_LOOKBACK}")
            return 0.0

        # Average volume (exclude recent to avoid look-ahead)
        avg_window = ohlcv_data[-(self.AVG_LOOKBACK + self.RECENT_LOOKBACK):-self.RECENT_LOOKBACK]
        avg_volumes = [c.volume for c in avg_window]
        avg_volume = np.mean(avg_volumes) if avg_volumes else 1.0

        if avg_volume < 1e-6:
            logger.warning("Average volume is zero")
            return 0.0

        # Recent volume breakdown (last 5 days)
        recent = ohlcv_data[-self.RECENT_LOOKBACK:]

        down_volume = sum(c.volume for c in recent if c.close < c.open)
        up_volume = sum(c.volume for c in recent if c.close >= c.open)

        # Ratios
        down_volume_ratio = down_volume / (avg_volume * self.RECENT_LOOKBACK) if (avg_volume * self.RECENT_LOOKBACK) > 0 else 0.0
        up_volume_ratio = up_volume / (avg_volume * self.RECENT_LOOKBACK) if (avg_volume * self.RECENT_LOOKBACK) > 0 else 0.0

        # Scoring
        if down_volume_ratio >= 1.5 and up_volume_ratio <= 1.0:
            score = 1.0
        elif down_volume_ratio >= 1.2 and up_volume_ratio <= 1.2:
            score = 0.7
        elif down_volume_ratio >= 1.0 and up_volume_ratio <= 1.5:
            score = 0.5
        else:
            score = 0.0

        # Validation: Down-volume spike must be near support
        window = ohlcv_data[-30:]
        support = min(c.low for c in window)
        recent_lows = [c.low for c in recent]

        if min(recent_lows) > support * 1.02:  # Not near support
            logger.warning(f"Volume spike not near support (VA validation failed)")
            score *= 0.5  # Penalize

        logger.debug(f"VA: score={score:.2f}, down_ratio={down_volume_ratio:.2f}, up_ratio={up_volume_ratio:.2f}")

        return max(0.0, min(1.0, score))
