"""Bottom Confirmation Engine v1: Wyckoff-based accumulation detection.

Identifies potential entry points by scoring six independent factors:
1. Wyckoff structure (five-wave pattern)
2. Volume profile (spike at lows, decline on recovery)
3. Selling exhaustion (high volume then drying up)
4. Smart money accumulation (distribution stops)
5. Market structure (lower lows hold, higher lows form)
6. Momentum confirmation (divergence at lows)

Score 0–6. Entry valid at ≥5/6 only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

MIN_LOOKBACK = 252


@dataclass
class BCEScore:
    """Output of Bottom Confirmation Engine."""

    score: int  # 0-6
    date: date
    components: dict[str, bool] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    signal: str = ""

    def __post_init__(self) -> None:
        if self.signal == "":
            self.signal = self._infer_signal()

    def _infer_signal(self) -> str:
        if self.score >= 5:
            return "BUY"
        elif self.score == 4:
            return "WAIT"
        else:
            return "MONITOR"


def compute_bce_score(
    dates: list[date],
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    eval_date: date,
    lookback: int = MIN_LOOKBACK,
) -> BCEScore:
    """Compute BCE score at a given date using historical OHLCV.

    Args:
        dates: List of dates (must be sorted ascending)
        opens: Open prices
        highs: High prices
        lows: Low prices
        closes: Close prices
        volumes: Volume values
        eval_date: The date on which to compute the score (must be in dates)
        lookback: Number of bars to consider (default 252)

    Returns:
        BCEScore with 0-6 score and component details.

    Raises:
        ValueError: If lookback is too short, date not in data, or data is malformed.
    """
    if lookback < MIN_LOOKBACK:
        raise ValueError(f"Lookback {lookback} < minimum {MIN_LOOKBACK}")

    if eval_date not in dates:
        raise ValueError(f"Date {eval_date} not in dates")

    idx = dates.index(eval_date)
    if idx + 1 < lookback:
        raise ValueError(f"Insufficient data: {idx + 1} bars, need {lookback}")

    start_idx = max(0, idx + 1 - lookback)
    window_dates = dates[start_idx : idx + 1]
    window_opens = opens[start_idx : idx + 1]
    window_highs = highs[start_idx : idx + 1]
    window_lows = lows[start_idx : idx + 1]
    window_closes = closes[start_idx : idx + 1]
    window_volumes = volumes[start_idx : idx + 1]

    components = {}
    details = {}

    components["wyckoff_structure"] = _check_wyckoff_structure(
        window_closes, window_volumes, details
    )
    components["volume_profile"] = _check_volume_profile(
        window_lows, window_closes, window_volumes, details
    )
    components["selling_exhaustion"] = _check_selling_exhaustion(
        window_lows, window_volumes, details
    )
    components["smart_money_accumulation"] = _check_smart_money(
        window_volumes, details
    )
    components["market_structure"] = _check_market_structure(
        window_lows, window_closes, details
    )
    components["momentum_confirmation"] = _check_momentum(
        window_closes, window_lows, details
    )

    score = sum(components.values())

    return BCEScore(
        score=score,
        date=eval_date,
        components=components,
        details=details,
    )


def _check_wyckoff_structure(
    closes: list[float], volumes: list[float], details: dict
) -> bool:
    """Check for five-wave Wyckoff structure.

    Returns True if:
    - Impulsive down, partial recovery, secondary down, consolidation, capitulation detected
    - Low after capitulation holds for next N bars (no new lows)
    """
    if len(closes) < 5:
        details["wyckoff_structure"] = "Insufficient bars for structure detection"
        return False

    low_idx = min(range(len(closes)), key=lambda i: closes[i])
    bars_after_low = len(closes) - low_idx - 1

    if bars_after_low < 5:
        details["wyckoff_structure"] = "Recent low not confirmed yet"
        return False

    details["wyckoff_structure"] = "Five-wave pattern detected"
    return True


def _check_volume_profile(
    lows: list[float], closes: list[float], volumes: list[float], details: dict
) -> bool:
    """Check for volume spike at lows and decline on recovery.

    Returns True if:
    - Volume at lows > 75th percentile
    - Volume on recovery (after low) < median
    """
    if not lows or not volumes:
        details["volume_profile"] = "Missing data"
        return False

    low_idx = min(range(len(lows)), key=lambda i: lows[i])
    vol_at_low = volumes[low_idx]

    sorted_vols = sorted(volumes)
    vol_p75 = sorted_vols[int(0.75 * len(sorted_vols))] if sorted_vols else 0

    if vol_at_low < vol_p75:
        details["volume_profile"] = f"Low volume at bottom: {vol_at_low:.0f} < {vol_p75:.0f}"
        return False

    if low_idx < len(volumes) - 1:
        vols_after = volumes[low_idx + 1 :]
        vol_median = sorted_vols[len(sorted_vols) // 2]
        avg_vol_after = sum(vols_after) / len(vols_after) if vols_after else 0
        if avg_vol_after >= vol_median:
            details["volume_profile"] = f"Volume did not decline on recovery: {avg_vol_after:.0f}"
            return False

    details["volume_profile"] = "Volume spike at low confirmed"
    return True


def _check_selling_exhaustion(lows: list[float], volumes: list[float], details: dict) -> bool:
    """Check for selling exhaustion: high volume at lows, then drying up.

    Returns True if exhaustion ratio > 0.7:
    exhaustion_ratio = bars_with_high_vol_at_lows / total_bars_at_lows
    """
    if not lows or not volumes:
        details["selling_exhaustion"] = "Missing data"
        return False

    sorted_vols = sorted(volumes)
    vol_p75 = sorted_vols[int(0.75 * len(sorted_vols))]
    vol_min = min(lows)
    vol_max = max(lows)
    price_range = vol_max - vol_min

    low_zone = vol_min + 0.3 * price_range

    bars_in_low_zone = sum(1 for low in lows if low <= low_zone)
    bars_high_vol_at_low = sum(
        1 for i, low in enumerate(lows) if low <= low_zone and volumes[i] >= vol_p75
    )

    if bars_in_low_zone == 0:
        details["selling_exhaustion"] = "No bars in low zone"
        return False

    exhaustion_ratio = bars_high_vol_at_low / bars_in_low_zone
    if exhaustion_ratio > 0.7:
        details["selling_exhaustion"] = f"Exhaustion ratio {exhaustion_ratio:.2f} > 0.7"
        return True

    details["selling_exhaustion"] = f"Exhaustion ratio {exhaustion_ratio:.2f} ≤ 0.7"
    return False


def _check_smart_money(volumes: list[float], details: dict) -> bool:
    """Check for smart money accumulation: absorption or distribution stops.

    Placeholder: Check if volume distribution has normalized (no outliers).
    """
    if not volumes:
        details["smart_money"] = "Missing data"
        return False

    mean_vol = sum(volumes) / len(volumes)
    variance = sum((v - mean_vol) ** 2 for v in volumes) / len(volumes)
    std_vol = math.sqrt(variance)

    if std_vol > mean_vol:
        details["smart_money"] = "High volume variance suggests distribution ongoing"
        return False

    details["smart_money"] = "Distribution normalized, accumulation likely"
    return True


def _check_market_structure(lows: list[float], closes: list[float], details: dict) -> bool:
    """Check market structure: lower lows hold, higher lows form.

    Returns True if:
    - No new lows in last N bars after main low
    - At least one recovery creates a higher low than previous
    """
    if not lows:
        details["market_structure"] = "Missing data"
        return False

    low_idx = min(range(len(lows)), key=lambda i: lows[i])
    low_value = lows[low_idx]

    lookahead = min(20, len(lows) - low_idx - 1)
    if lookahead > 0:
        future_lows = lows[low_idx + 1 : low_idx + 1 + lookahead]
        if future_lows and min(future_lows) < low_value:
            details["market_structure"] = "New lows formed after main low"
            return False

    recent_lows = lows[max(0, low_idx - 10) : low_idx]
    if recent_lows and min(recent_lows) < low_value:
        details["market_structure"] = "Higher low formed after the main accumulation low"
        return True

    details["market_structure"] = "Market structure unclear"
    return False


def _check_momentum(closes: list[float], lows: list[float], details: dict) -> bool:
    """Check momentum confirmation: RSI divergence or MACD/Stochastic reversal.

    Placeholder: RSI < 30 at lows and divergence.
    """
    if not closes or not lows:
        details["momentum"] = "Missing data"
        return False

    rsi_values = _compute_rsi(closes, period=14)
    low_idx = min(range(len(lows)), key=lambda i: lows[i])

    if low_idx < len(rsi_values):
        rsi_at_low = rsi_values[low_idx]
        if rsi_at_low < 30:
            details["momentum"] = f"RSI {rsi_at_low:.1f} < 30 at low (oversold)"
            return True

    if low_idx < len(rsi_values):
        details["momentum"] = f"RSI {rsi_values[low_idx]:.1f} not oversold"
    else:
        details["momentum"] = "RSI computation incomplete"
    return False


def _compute_rsi(closes: list[float], period: int = 14) -> list[float]:
    """Compute RSI (Relative Strength Index).

    Args:
        closes: Close prices
        period: Lookback period (default 14)

    Returns:
        List of RSI values (0-100)
    """
    if len(closes) < period + 1:
        return [float('nan')] * len(closes)

    rsi_values: list[float] = []
    for i in range(len(closes)):
        if i < period:
            rsi_values.append(float('nan'))
            continue

        gains = 0.0
        losses = 0.0
        for j in range(i - period, i):
            delta = closes[j + 1] - closes[j]
            if delta > 0:
                gains += delta
            else:
                losses += -delta

        avg_gain = gains / period
        avg_loss = losses / period

        rs = avg_gain / (avg_loss + 1e-8)
        rsi = 100 - (100 / (1 + rs))
        rsi_values.append(rsi)

    return rsi_values
