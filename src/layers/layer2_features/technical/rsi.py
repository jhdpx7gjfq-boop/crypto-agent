"""Relative Strength Index (RSI) calculation."""

from typing import List
import numpy as np


def calculate_rsi(closes: List[float], period: int = 14) -> List[float]:
    """
    Calculate Wilder's RSI (Relative Strength Index).

    Formula:
        RS = avg_gain / avg_loss
        RSI = 100 - (100 / (1 + RS))

    Args:
        closes: List of close prices
        period: Lookback period (default 14)

    Returns:
        List of RSI values (0-100), same length as input
        First (period) values are NaN (insufficient data)
    """
    closes = np.array(closes, dtype=float)
    rsi = np.full(len(closes), np.nan)

    if len(closes) < period + 1:
        return rsi.tolist()

    # Calculate price changes
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    # First RS: simple average
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    # Wilder's smoothing: subsequent averages use EMA-like calculation
    rs_values = []

    for i in range(period, len(closes)):
        if i == period:
            avg_gain = np.mean(gains[:period])
            avg_loss = np.mean(losses[:period])
        else:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

        if avg_loss == 0:
            rs_val = 100.0 if avg_gain > 0 else 0.0
        else:
            rs = avg_gain / avg_loss
            rs_val = 100 - (100 / (1 + rs))

        rs_values.append(rs_val)

    # Fill RSI array starting at period index
    rsi[period:] = rs_values

    return rsi.tolist()
