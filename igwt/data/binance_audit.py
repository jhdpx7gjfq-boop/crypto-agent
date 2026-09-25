"""Integrity audit for Binance OHLCV data (PATH-A validation layer)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

MILLISECONDS_PER_DAY = 86_400_000


@dataclass
class BinanceOHLCVAudit:
    """Audit report for one symbol's Binance OHLCV series."""

    symbol: str
    source: str = "binance-spot"
    retrieval_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    raw_row_count: int = 0
    accepted_rows: int = 0

    start_date: str | None = None
    end_date: str | None = None

    intraday_points_dropped: int = 0
    duplicate_dates: int = 0
    cohesion_failures: int = 0
    invalid_prices: int = 0

    missing_dates: list[dict] = field(default_factory=list)
    missing_dates_count: int = 0

    sha256_raw: str | None = None
    sha256_normalized: str | None = None

    verdict: str = "PENDING"
    details: dict = field(default_factory=dict)


def audit_binance_klines(symbol: str, klines: list[dict]) -> tuple[BinanceOHLCVAudit, list[dict]]:
    """Audit raw Binance klines and return clean series.

    Returns:
        (audit_report, normalized_series_as_dicts)

    normalized_series has keys: date, open, high, low, close, volume
    """
    report = BinanceOHLCVAudit(symbol=symbol)
    report.raw_row_count = len(klines)

    # Hash raw input
    raw_str = "\n".join(str(k) for k in klines)
    report.sha256_raw = hashlib.sha256(raw_str.encode()).hexdigest()

    by_date: dict[date, dict] = {}
    previous_ts: int | None = None
    out_of_order = False

    for kline in klines:
        timestamp_ms = int(kline["openTime"])
        open_price = float(kline["open"])
        high_price = float(kline["high"])
        low_price = float(kline["low"])
        close_price = float(kline["close"])
        volume = float(kline["volume"])

        # Check order
        if previous_ts is not None and timestamp_ms < previous_ts:
            out_of_order = True
        previous_ts = timestamp_ms

        # Check alignment to 00:00:00 UTC
        if timestamp_ms % MILLISECONDS_PER_DAY != 0:
            report.intraday_points_dropped += 1
            continue

        # Convert to date
        bar_date = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).date()

        # Check for duplicate
        if bar_date in by_date:
            report.duplicate_dates += 1
            continue

        # Check price validity and cohesion
        if not _is_valid_price(open_price) or not _is_valid_price(high_price) or \
           not _is_valid_price(low_price) or not _is_valid_price(close_price):
            report.invalid_prices += 1
            continue

        # Check OHLC cohesion: low <= min(open, close), high >= max(open, close)
        min_oc = min(open_price, close_price)
        max_oc = max(open_price, close_price)
        if low_price > min_oc or high_price < max_oc or low_price > high_price:
            report.cohesion_failures += 1
            continue

        by_date[bar_date] = {
            "date": bar_date,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
        }

    # Sort and extract series
    ordered_dates = sorted(by_date.keys())
    normalized_series = [by_date[d] for d in ordered_dates]
    report.accepted_rows = len(normalized_series)

    if normalized_series:
        report.start_date = normalized_series[0]["date"].isoformat()
        report.end_date = normalized_series[-1]["date"].isoformat()

    # Detect calendar gaps
    for i in range(len(ordered_dates) - 1):
        delta = (ordered_dates[i + 1] - ordered_dates[i]).days
        if delta > 1:
            report.missing_dates.append({
                "after": ordered_dates[i].isoformat(),
                "before": ordered_dates[i + 1].isoformat(),
                "missing_days": delta - 1,
            })
            report.missing_dates_count += delta - 1

    # Hash normalized
    norm_str = "\n".join(str(row) for row in normalized_series)
    report.sha256_normalized = hashlib.sha256(norm_str.encode()).hexdigest()

    # Verdict
    if report.accepted_rows == 0:
        report.verdict = "FAIL"
        report.details["reason"] = "No valid rows"
    elif report.intraday_points_dropped > 0 or report.duplicate_dates > 0 or \
         report.cohesion_failures > 0 or report.invalid_prices > 0 or \
         report.missing_dates_count > 0:
        report.verdict = "WARN"
        report.details["reason"] = "Defects counted and published"
    else:
        report.verdict = "PASS"

    report.details["out_of_order_input"] = out_of_order

    return report, normalized_series


def _is_valid_price(price: float) -> bool:
    """Check if price is finite and positive."""
    return price == price and price not in (float("inf"), float("-inf")) and price > 0
