"""Bollinger Bands calculation."""

from typing import List, Tuple
import numpy as np
from .ma import calculate_sma


def calculate_bb_width(closes: List[float], period: int = 20, std_dev: float = 2.0) -> List[float]:
    """
    Calculate Bollinger Band width.

    Formula:
        Mid = SMA(20)
        Upper = Mid + (StdDev * 2.0)
        Lower = Mid - (StdDev * 2.0)
        Width = Upper - Lower = 2 * StdDev * σ

    Args:
        closes: List of close prices
        period: Lookback period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)

    Returns:
        List of BB width values, same length as input
        First (period-1) values are NaN
    """
    closes = np.array(closes, dtype=float)
    width = np.full(len(closes), np.nan)

    if len(closes) < period:
        return width.tolist()

    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        std = np.std(window)
        width[i] = 2 * std_dev * std

    return width.tolist()


def calculate_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate Bollinger Bands (upper, middle, lower).

    Args:
        closes: List of close prices
        period: Lookback period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)

    Returns:
        (upper_band, middle_band, lower_band) — all same length as input
        First (period-1) values are NaN
    """
    closes = np.array(closes, dtype=float)
    n = len(closes)
    middle = np.array(calculate_sma(closes.tolist(), period))
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)

    if n < period:
        return upper.tolist(), middle.tolist(), lower.tolist()

    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        std = np.std(window)
        upper[i] = middle[i] + (std_dev * std)
        lower[i] = middle[i] - (std_dev * std)

    return upper.tolist(), middle.tolist(), lower.tolist()
