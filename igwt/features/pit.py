"""Point-in-time feature primitives (IGWT — Feature Engineering).

Every function here takes a series ordered by ascending date and states, in its
contract, exactly which observations it reads. Two kinds exist and they are
never mixed:

* **Features** (``trailing_return``, ``realized_volatility``) read index
  ``<= i`` only. They are safe to use as model inputs.
* **Labels** (``forward_return``) read index ``> i``. They are the target and
  must never be fed back as an input.

``None`` marks an undefined value (insufficient history, or insufficient
future for a label) — it is never silently forward-filled, because a filled
value would import information the point-in-time observer did not have.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

TRADING_DAYS_PER_YEAR = 365  # crypto trades every calendar day


def trailing_return(closes: Sequence[float], lookback: int) -> list[float | None]:
    """Simple return over ``lookback`` periods. Reads closes[i-lookback : i+1]."""
    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    out: list[float | None] = []
    for i, close in enumerate(closes):
        past = closes[i - lookback] if i >= lookback else None
        out.append(close / past - 1.0 if past not in (None, 0) else None)
    return out


def forward_return(closes: Sequence[float], horizon: int) -> list[float | None]:
    """LABEL. Return over the next ``horizon`` periods. Reads closes[i + horizon]."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    n = len(closes)
    out: list[float | None] = []
    for i, close in enumerate(closes):
        future = closes[i + horizon] if i + horizon < n else None
        out.append(future / close - 1.0 if future is not None and close else None)
    return out


def realized_volatility(
    closes: Sequence[float], window: int, *, annualise: bool = True
) -> list[float | None]:
    """Annualised stdev of daily log returns over the trailing ``window``.

    Reads closes[i-window : i+1] — the window ends at ``i`` inclusive.
    """
    if window < 2:
        raise ValueError("window must be >= 2")

    log_returns: list[float | None] = [None]
    for i in range(1, len(closes)):
        previous, current = closes[i - 1], closes[i]
        log_returns.append(math.log(current / previous) if previous > 0 and current > 0 else None)

    scale = math.sqrt(TRADING_DAYS_PER_YEAR) if annualise else 1.0
    out: list[float | None] = []
    for i in range(len(closes)):
        window_slice = log_returns[i - window + 1 : i + 1] if i >= window else []
        if len(window_slice) < window or any(value is None for value in window_slice):
            out.append(None)
            continue
        out.append(_stdev(window_slice) * scale)
    return out


def cross_sectional_zscore(
    values: dict[str, float | None], *, min_observations: int = 3
) -> dict[str, float | None]:
    """Z-score across assets **within a single date**.

    Cross-sectional only: it reads no other date, so it cannot leak forward.
    Returns all-``None`` when fewer than ``min_observations`` assets are
    present or the cross-section has no dispersion.
    """
    present = {asset: value for asset, value in values.items() if value is not None}
    if len(present) < min_observations:
        return dict.fromkeys(values)

    mean = sum(present.values()) / len(present)
    stdev = _stdev(list(present.values()))
    if stdev == 0:
        return dict.fromkeys(values)

    return {
        asset: ((value - mean) / stdev if value is not None else None)
        for asset, value in values.items()
    }


def _stdev(values: Sequence[float]) -> float:
    """Sample standard deviation (n-1)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (n - 1))
