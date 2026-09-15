"""Integrity audit (IGWT Layer 1 — audit step of RAW -> normalised).

Produces the per-symbol manifest record the registry requires, and a verdict.
The audit's job is to make a dataset's defects *countable before* anyone
computes a feature on it: a gap, a duplicate or an inconsistent bar that is
discovered after a backtest has run has already contaminated the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from igwt.data import snapshot
from igwt.data.ohlcv import OHLCVSeries

#: Cap on the enumerated missing dates, so a badly-covered symbol cannot
#: produce a megabyte of manifest. The count is always exact.
MAX_ENUMERATED_MISSING_DATES = 500


@dataclass(frozen=True)
class AcquisitionContext:
    """What the operator must state about an acquisition, not infer from it."""

    source: str
    endpoint: str
    market_type: str  # e.g. "spot", "perp"
    timeframe: str  # e.g. "1d"
    timezone: str = "UTC"
    retrieval_timestamp: str | None = None

    def stamp(self) -> str:
        return self.retrieval_timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")


def missing_dates(dates: list[date]) -> list[date]:
    """Calendar days absent from the covered range. Crypto trades every day."""
    if len(dates) < 2:
        return []
    present = set(dates)
    first, last = dates[0], dates[-1]
    span = (last - first).days + 1
    return [
        first + timedelta(days=offset)
        for offset in range(span)
        if (first + timedelta(days=offset)) not in present
    ]


def audit(
    series: OHLCVSeries,
    *,
    context: AcquisitionContext,
    raw_bytes: bytes,
    normalised_bytes: bytes,
) -> dict:
    """Build the registry's per-symbol integrity record."""
    report = series.report
    absent = missing_dates(series.dates)
    columns = series.source_columns or {}

    record = {
        "source": context.source,
        "endpoint": context.endpoint,
        "symbol": series.symbol,
        "market_type": context.market_type,
        "timeframe": context.timeframe,
        "start_date": report.get("first_date"),
        "end_date": report.get("last_date"),
        "retrieval_timestamp": context.stamp(),
        "row_count": len(series),
        "missing_dates_count": len(absent),
        "missing_dates": [day.isoformat() for day in absent[:MAX_ENUMERATED_MISSING_DATES]],
        "missing_dates_truncated": len(absent) > MAX_ENUMERATED_MISSING_DATES,
        "duplicate_rows": report.get("duplicate_rows_dropped", 0),
        "sha256_raw": snapshot.sha256_hex(raw_bytes),
        "sha256_normalized": snapshot.sha256_hex(normalised_bytes),
        "timezone": context.timezone,
        "price_field": columns.get("close") or "close",
        "volume_field": columns.get("volume"),
        "rejected": {
            "unparsable_rows": report.get("unparsable_rows_dropped", 0),
            "inconsistent_bars": report.get("inconsistent_bars_dropped", 0),
            "duplicate_rows": report.get("duplicate_rows_dropped", 0),
        },
        "out_of_order_input": report.get("out_of_order_input", False),
    }
    record["verdict"], record["findings"] = _verdict(record)
    return record


def _verdict(record: dict) -> tuple[str, list[str]]:
    """FAIL blocks the build; WARN documents a defect the operator must see."""
    findings: list[str] = []

    if record["row_count"] == 0:
        return "FAIL", ["no usable rows after normalisation"]

    rejected = record["rejected"]
    if rejected["inconsistent_bars"]:
        findings.append(
            f"{rejected['inconsistent_bars']} bars violate OHLC ordering and were dropped"
        )
    if rejected["unparsable_rows"]:
        findings.append(f"{rejected['unparsable_rows']} rows could not be parsed")
    if record["duplicate_rows"]:
        findings.append(f"{record['duplicate_rows']} duplicate dates were dropped")
    if record["missing_dates_count"]:
        findings.append(
            f"{record['missing_dates_count']} calendar days are missing inside the covered range"
        )
    if record["volume_field"] is None:
        findings.append("no base-asset volume column was found; volume is unavailable")
    # Row order is deliberately not a finding: vendor exports are conventionally
    # descending, normalisation sorts them deterministically, and flagging every
    # such file would leave WARN meaning nothing. The fact stays recorded in
    # ``out_of_order_input`` for anyone auditing the source.

    return ("WARN" if findings else "PASS"), findings


def summarise(records: dict[str, dict]) -> dict:
    """Roll the per-symbol audits into one acquisition verdict."""
    verdicts = [record["verdict"] for record in records.values()]
    if any(verdict == "FAIL" for verdict in verdicts):
        overall = "FAIL"
    elif any(verdict == "WARN" for verdict in verdicts):
        overall = "WARN"
    else:
        overall = "PASS"

    return {
        "verdict": overall,
        "symbols": len(records),
        "total_rows": sum(record["row_count"] for record in records.values()),
        "total_missing_dates": sum(record["missing_dates_count"] for record in records.values()),
        "total_duplicate_rows": sum(record["duplicate_rows"] for record in records.values()),
        "symbols_with_findings": sorted(
            symbol for symbol, record in records.items() if record["findings"]
        ),
    }
