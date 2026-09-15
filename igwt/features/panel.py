"""Panel assembly and snapshot validation (IGWT Layer 1 — Validation).

Turns raw CoinGecko ``market_chart`` payloads into a validated daily panel.
Every row that is dropped is counted and reported: a dataset whose rejects are
invisible cannot be audited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

MILLISECONDS_PER_DAY = 86_400_000


@dataclass
class AssetSeries:
    """One asset's validated daily series, ascending by date."""

    asset: str
    dates: list[date]
    closes: list[float]
    volumes: list[float | None]
    report: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.dates)


def parse_market_chart(asset: str, payload: dict) -> AssetSeries:
    """Extract the daily close/volume series from one raw payload.

    Drops, and counts, the four irregularities that are actually present in
    live responses:

    1. the trailing intraday point (timestamp not aligned to 00:00:00 UTC),
       which would otherwise inject a partial, still-moving day;
    2. duplicate dates (first occurrence wins);
    3. non-positive or non-finite prices;
    4. out-of-order points (the series is re-sorted, and the fact is recorded).

    Calendar gaps are *reported, never filled*.
    """
    prices = payload["prices"]
    volumes_by_ts = {int(ts): value for ts, value in payload.get("total_volumes", [])}

    intraday_dropped = 0
    invalid_price_dropped = 0
    by_date: dict[date, tuple[float, float | None]] = {}
    duplicate_dropped = 0
    previous_ts: int | None = None
    out_of_order = False

    for timestamp, price in prices:
        timestamp = int(timestamp)
        if previous_ts is not None and timestamp < previous_ts:
            out_of_order = True
        previous_ts = timestamp

        if timestamp % MILLISECONDS_PER_DAY != 0:
            intraday_dropped += 1
            continue
        if price is None or not _is_finite_positive(price):
            invalid_price_dropped += 1
            continue

        day = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date()
        if day in by_date:
            duplicate_dropped += 1
            continue
        by_date[day] = (float(price), volumes_by_ts.get(timestamp))

    ordered = sorted(by_date)
    dates = list(ordered)
    closes = [by_date[day][0] for day in ordered]
    volumes = [by_date[day][1] for day in ordered]

    report = {
        "asset": asset,
        "raw_points": len(prices),
        "accepted_points": len(dates),
        "intraday_points_dropped": intraday_dropped,
        "duplicate_dates_dropped": duplicate_dropped,
        "invalid_prices_dropped": invalid_price_dropped,
        "out_of_order_input": out_of_order,
        "first_date": dates[0].isoformat() if dates else None,
        "last_date": dates[-1].isoformat() if dates else None,
        "calendar_gaps": _calendar_gaps(dates),
    }
    return AssetSeries(asset=asset, dates=dates, closes=closes, volumes=volumes, report=report)


def _calendar_gaps(dates: list[date]) -> list[dict]:
    """Missing calendar days inside the covered range (crypto trades 24/7)."""
    gaps = []
    for previous, current in zip(dates, dates[1:]):
        delta = (current - previous).days
        if delta > 1:
            gaps.append(
                {
                    "after": previous.isoformat(),
                    "before": current.isoformat(),
                    "missing_days": delta - 1,
                }
            )
    return gaps


def common_date_index(series: list[AssetSeries]) -> list[date]:
    """Union of every asset's dates, ascending.

    A union — not an intersection — keeps the panel honestly ragged: an asset
    that is missing on a date is absent from that date, not back-filled.
    """
    days: set[date] = set()
    for item in series:
        days.update(item.dates)
    return sorted(days)


def _is_finite_positive(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf")) and value > 0


def date_range(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def contiguous_backward_mask(dates: list[date], span: int) -> list[bool]:
    """``True`` where ``dates[i-span : i+1]`` are consecutive calendar days.

    A trailing feature computed over ``span`` *rows* silently stretches over a
    longer wall-clock window whenever the series has a gap. This mask is how
    such values get invalidated instead of quietly mis-stated.
    """
    if span < 1:
        raise ValueError("span must be >= 1")
    return [
        i >= span and (dates[i] - dates[i - span]).days == span for i in range(len(dates))
    ]


def contiguous_forward_mask(dates: list[date], span: int) -> list[bool]:
    """``True`` where ``dates[i : i+span+1]`` are consecutive calendar days.

    The label-side counterpart: a forward return whose window straddles a gap
    is not the horizon it claims to be.
    """
    if span < 1:
        raise ValueError("span must be >= 1")
    n = len(dates)
    return [
        i + span < n and (dates[i + span] - dates[i]).days == span for i in range(n)
    ]
