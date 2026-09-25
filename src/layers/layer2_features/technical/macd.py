"""MACD (Moving Average Convergence Divergence) calculation."""

from typing import List, Tuple
import numpy as np
from .ma import calculate_ema


def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate MACD line, signal line, and histogram.

    Formula:
        MACD = EMA(12) - EMA(26)
        Signal = EMA(9) of MACD
        Histogram = MACD - Signal

    Args:
        closes: List of close prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)

    Returns:
        (macd_line, signal_line, histogram) — all same length as input
        First (slow) values are NaN
    """
    closes_arr = np.array(closes, dtype=float)
    n = len(closes_arr)

    ema_fast = np.array(calculate_ema(closes, fast))
    ema_slow = np.array(calculate_ema(closes, slow))

    macd_line = ema_fast - ema_slow

    signal_arr = np.full(n, np.nan)
    valid_macd = macd_line[~np.isnan(macd_line)]

    if len(valid_macd) >= signal:
        signal_ema = calculate_ema(valid_macd.tolist(), signal)
        valid_idx = np.where(~np.isnan(macd_line))[0]
        for i, sig_val in enumerate(signal_ema):
            if i < len(valid_idx):
                signal_arr[valid_idx[i]] = sig_val

    histogram = macd_line - signal_arr

    return macd_line.tolist(), signal_arr.tolist(), histogram.tolist()
