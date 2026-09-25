"""Moving Average calculations: SMA, EMA, WMA."""

from typing import List
import numpy as np


def calculate_sma(closes: List[float], period: int = 20) -> List[float]:
    """
    Calculate Simple Moving Average.

    Args:
        closes: List of close prices
        period: Lookback period (default 20)

    Returns:
        List of SMA values, same length as input
        First (period-1) values are NaN (insufficient data)
    """
    closes = np.array(closes, dtype=float)
    sma = np.full(len(closes), np.nan)

    if len(closes) < period:
        return sma.tolist()

    for i in range(period - 1, len(closes)):
        sma[i] = np.mean(closes[i - period + 1 : i + 1])

    return sma.tolist()


def calculate_ema(closes: List[float], period: int = 12) -> List[float]:
    """
    Calculate Exponential Moving Average.

    Args:
        closes: List of close prices
        period: Lookback period (default 12)

    Returns:
        List of EMA values, same length as input
        First (period) values are NaN (insufficient data)
    """
    closes = np.array(closes, dtype=float)
    ema = np.full(len(closes), np.nan)

    if len(closes) < period:
        return ema.tolist()

    alpha = 2.0 / (period + 1)
    ema[period - 1] = np.mean(closes[:period])

    for i in range(period, len(closes)):
        ema[i] = closes[i] * alpha + ema[i - 1] * (1 - alpha)

    return ema.tolist()


def calculate_wma(closes: List[float], period: int = 10) -> List[float]:
    """
    Calculate Weighted Moving Average.

    Args:
        closes: List of close prices
        period: Lookback period (default 10)

    Returns:
        List of WMA values, same length as input
        First (period-1) values are NaN (insufficient data)
    """
    closes = np.array(closes, dtype=float)
    wma = np.full(len(closes), np.nan)

    if len(closes) < period:
        return wma.tolist()

    weights = np.arange(1, period + 1)
    weight_sum = np.sum(weights)

    for i in range(period - 1, len(closes)):
        wma[i] = np.sum(closes[i - period + 1 : i + 1] * weights) / weight_sum

    return wma.tolist()
