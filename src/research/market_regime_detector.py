"""Market Regime Detection (Priority 1: Context)

Trend + Volatility classification, no look-ahead.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
from enum import Enum


class Trend(Enum):
    """Market trend direction."""
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"


class VolRegime(Enum):
    """Volatility regime."""
    HIGH_VOL = "HIGH_VOL"
    LOW_VOL = "LOW_VOL"


class MarketRegimeDetector:
    """Detects market regime at each timestamp (PIT-safe)."""

    def __init__(self, sma_period: int = 20, atr_period: int = 14):
        self.sma_period = sma_period
        self.atr_period = atr_period

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range."""
        df_copy = df.copy()
        df_copy["tr"] = np.maximum(
            df_copy["high"] - df_copy["low"],
            np.maximum(
                abs(df_copy["high"] - df_copy["close"].shift(1)),
                abs(df_copy["low"] - df_copy["close"].shift(1))
            )
        )
        return df_copy["tr"].rolling(period).mean()

    def _calculate_trend(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Trend: close above/below SMA."""
        sma = df["close"].rolling(period).mean()
        trend = (df["close"] > sma).astype(int)  # 1 = Bull, 0 = Bear
        return trend

    def _calculate_vol_regime(self, atr: pd.Series, period: int = 14) -> pd.Series:
        """Vol regime: ATR above/below median."""
        atr_median = atr.rolling(period).median()
        vol_regime = (atr > atr_median).astype(int)  # 1 = High vol, 0 = Low vol
        return vol_regime

    def classify_row(self, df: pd.DataFrame, idx: int) -> Tuple[Trend, VolRegime]:
        """
        Classify market regime at row `idx` using only data up to `idx` (PIT-safe).

        Args:
            df: OHLCV DataFrame
            idx: Row index

        Returns:
            (Trend, VolRegime)
        """
        if idx < self.sma_period:
            return Trend.SIDEWAYS, VolRegime.LOW_VOL

        # Use only data up to idx
        pit_df = df.iloc[:idx + 1]

        # Trend: SMA
        sma = pit_df["close"].iloc[-self.sma_period:].mean()
        close = pit_df["close"].iloc[-1]
        trend = Trend.BULL if close > sma else Trend.BEAR

        # Vol: ATR vs recent median
        atr = self._calculate_atr(pit_df, self.atr_period)
        atr_recent = atr.iloc[-self.atr_period:].dropna()

        if len(atr_recent) < 2:
            vol_regime = VolRegime.LOW_VOL
        else:
            atr_median = atr_recent.median()
            atr_current = atr.iloc[-1]
            vol_regime = VolRegime.HIGH_VOL if atr_current > atr_median else VolRegime.LOW_VOL

        return trend, vol_regime

    def classify_series(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify entire series (for analysis; slower).

        Returns:
            DataFrame with columns: trend, vol_regime
        """
        trends = []
        vol_regimes = []

        for idx in range(len(df)):
            trend, vol = self.classify_row(df, idx)
            trends.append(trend.value)
            vol_regimes.append(vol.value)

        result = pd.DataFrame({
            "trend": trends,
            "vol_regime": vol_regimes
        }, index=df.index)

        return result
