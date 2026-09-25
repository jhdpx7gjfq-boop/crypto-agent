"""Signal construction for PATH-A — Liquidation Independent Alpha.

This module defines the alpha hypothesis and its point-in-time features.
All calculations are strictly PIT: data_used ≤ point_in_time_date.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from igwt.features.pit import realized_volatility, trailing_return


def volatility_regimesshift_signal(
    closes: Sequence[float],
    volumes: Sequence[float],
    window_short: int = 10,
    window_long: int = 30,
) -> list[float | None]:
    """Liquidation-independent alpha hypothesis.

    Signal = volatility expansion ratio × volume trend.
    Rationale: markets with expanding volatility and supportive volume
    experience mean reversion; liquidation cascades are independent phenomena.

    Returns PIT signal values, one per close.
    """
    if window_short < 2 or window_long < window_short:
        raise ValueError("window_short >= 2 and window_long >= window_short")

    vols_short = realized_volatility(closes, window_short, annualise=False)
    vols_long = realized_volatility(closes, window_long, annualise=False)

    vol_ratios: list[float | None] = []
    for i in range(len(closes)):
        short_vol = vols_short[i]
        long_vol = vols_long[i]
        if short_vol is not None and long_vol is not None and long_vol > 0:
            vol_ratios.append(short_vol / long_vol)
        else:
            vol_ratios.append(None)

    volume_trend = _volume_zscore_trend(volumes, window=10)

    signal: list[float | None] = []
    for i in range(len(closes)):
        vol_ratio = vol_ratios[i]
        vol_trend = volume_trend[i]

        if vol_ratio is not None and vol_trend is not None:
            signal.append(vol_ratio * vol_trend)
        else:
            signal.append(None)

    return signal


def _volume_zscore_trend(volumes: Sequence[float], window: int = 10) -> list[float | None]:
    """Z-score of current volume vs. trailing average (normalized to [-1, 1])."""
    if window < 2:
        raise ValueError("window >= 2")

    result: list[float | None] = []
    for i in range(len(volumes)):
        if i < window:
            result.append(None)
            continue

        slice_vol = volumes[i - window : i]
        mean_vol = sum(slice_vol) / len(slice_vol)
        if mean_vol == 0:
            result.append(None)
            continue

        stdev = math.sqrt(sum((v - mean_vol) ** 2 for v in slice_vol) / (len(slice_vol) - 1))
        if stdev == 0:
            result.append(0.0)
            continue

        z_score = (volumes[i] - mean_vol) / stdev
        normalized = max(-1.0, min(1.0, z_score / 3.0))
        result.append(normalized)

    return result


def build_path_a_observations(
    dates: list,
    closes: Sequence[float],
    volumes: Sequence[float],
    forward_returns: Sequence[float | None],
    horizon_days: int = 5,
) -> list[dict]:
    """Build WFV-compliant observations for PATH-A signal.

    Each observation is:
    {
        "date": date object,
        "asset": str (inferred from symbol context),
        "signal": float (PIT, calculated ≤ date),
        "fwdRet": float | None (forward return over horizon),
        "regimeVol": float (volatility regime, annualised)
    }
    """
    signal = volatility_regimesshift_signal(closes, volumes)
    regime_vols = realized_volatility(closes, window=30, annualise=True)

    observations: list[dict] = []
    for i, date in enumerate(dates):
        if signal[i] is None or regime_vols[i] is None or forward_returns[i] is None:
            continue

        obs = {
            "date": date,
            "signal": signal[i],
            "fwdRet": forward_returns[i],
            "regimeVol": regime_vols[i],
        }
        observations.append(obs)

    return observations
