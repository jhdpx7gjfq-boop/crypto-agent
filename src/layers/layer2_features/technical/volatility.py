"""Volatility metrics: historical volatility, Parkinson volatility."""

from typing import List
import numpy as np


def calculate_volatility(closes: List[float], period: int = 20, annualize: bool = True, periods_per_year: int = 252) -> List[float]:
    """
    Calculate Historical Volatility (annualized standard deviation of returns).

    Formula:
        Returns = log(close[t] / close[t-1])
        HV = std(returns) * sqrt(periods_per_year)

    Args:
        closes: List of close prices
        period: Lookback period (default 20)
        annualize: Whether to annualize (default True)
        periods_per_year: Trading periods per year (default 252 for daily)

    Returns:
        List of volatility values, same length as input
        First (period) values are NaN (insufficient data)
    """
    closes = np.array(closes, dtype=float)
    hv = np.full(len(closes), np.nan)

    if len(closes) < period + 1:
        return hv.tolist()

    log_returns = np.diff(np.log(closes))

    for i in range(period, len(closes)):
        window_returns = log_returns[i - period : i]
        vol = np.std(window_returns)

        if annualize:
            vol = vol * np.sqrt(periods_per_year)

        hv[i] = vol

    return hv.tolist()


def calculate_parkinson_volatility(highs: List[float], lows: List[float], period: int = 20, annualize: bool = True, periods_per_year: int = 252) -> List[float]:
    """
    Calculate Parkinson Volatility (high-low range based).

    Formula:
        PV = sqrt(ln(H/L)^2 / (4*ln(2))) * sqrt(periods_per_year)

    Args:
        highs: List of high prices
        lows: List of low prices
        period: Lookback period (default 20)
        annualize: Whether to annualize (default True)
        periods_per_year: Trading periods per year (default 252 for daily)

    Returns:
        List of Parkinson volatility values, same length as input
        First (period-1) values are NaN
    """
    highs = np.array(highs, dtype=float)
    lows = np.array(lows, dtype=float)
    pv = np.full(len(highs), np.nan)

    if len(highs) < period:
        return pv.tolist()

    sqrt_ln2 = np.sqrt(np.log(2))

    for i in range(period - 1, len(highs)):
        window_highs = highs[i - period + 1 : i + 1]
        window_lows = lows[i - period + 1 : i + 1]

        hl_ratio = window_highs / window_lows
        ln_ratio = np.log(hl_ratio)
        vol = np.sqrt(np.mean(ln_ratio ** 2)) / (2 * sqrt_ln2)

        if annualize:
            vol = vol * np.sqrt(periods_per_year)

        pv[i] = vol

    return pv.tolist()
