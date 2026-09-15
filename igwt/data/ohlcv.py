"""Normalised OHLCV bars, and ingestion of the registry's exported files.

The registry's Binance datasets arrive as vendor CSV exports whose column
names, ordering and volume units vary between vendors. This module turns any
of them into one normalised daily series, and *records which source column it
read for each field* — so the manifest states `price_field` and `volume_field`
as facts rather than assumptions.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from igwt.features import panel

#: Candidate source column names per normalised field, matched case-insensitively.
#: Volume is deliberately last-resort: a "Volume USDT" column is quote volume,
#: not base volume, and conflating the two silently rescales the series.
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    # "date" first: when an export carries both a human date and a unix stamp,
    # the human date is the one the vendor documents.
    "date": (
        "date",
        "datetime",
        "timestamp",
        "open_time",
        "opentime",
        "open time",
        "unix",
        "unix timestamp",
        "time",
    ),
    "open": ("open",),
    "high": ("high",),
    "low": ("low",),
    "close": ("close", "close/last"),
}


class IngestionError(ValueError):
    """Raised when a source file cannot be mapped onto the OHLCV contract."""


@dataclass(frozen=True)
class Bar:
    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None


@dataclass
class OHLCVSeries:
    """One symbol's normalised daily bars, ascending by date."""

    symbol: str
    bars: list[Bar]
    source_columns: dict[str, str | None] = field(default_factory=dict)
    report: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.bars)

    @property
    def dates(self) -> list[date]:
        return [bar.day for bar in self.bars]

    @property
    def closes(self) -> list[float]:
        return [bar.close for bar in self.bars]

    def to_asset_series(self) -> panel.AssetSeries:
        """Adapt to the panel type the feature builder consumes.

        This adapter is the whole reason a source swap cannot change the WFV
        contract: whatever the vendor, the features are computed by the same
        ``igwt.features.contract.build_observations``.
        """
        return panel.AssetSeries(
            asset=self.symbol,
            dates=self.dates,
            closes=self.closes,
            volumes=[bar.volume for bar in self.bars],
            report=self.report,
        )


def resolve_columns(header: list[str], *, base_asset: str | None = None) -> dict[str, str]:
    """Map normalised field names onto this file's actual column names."""
    lookup = {name.strip().lower(): name for name in header}
    resolved: dict[str, str] = {}

    for field_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lookup:
                resolved[field_name] = lookup[alias]
                break
        else:
            raise IngestionError(
                f"no column for {field_name!r}; header was {header!r}"
            )

    volume_column = _resolve_volume(lookup, base_asset)
    if volume_column:
        resolved["volume"] = volume_column
    return resolved


def _resolve_volume(lookup: dict[str, str], base_asset: str | None) -> str | None:
    """Prefer base-asset volume; never silently accept quote volume as base."""
    if base_asset:
        preferred = f"volume {base_asset.lower()}"
        if preferred in lookup:
            return lookup[preferred]
    for candidate in ("volume", "base_volume", "basevolume", "volume_base"):
        if candidate in lookup:
            return lookup[candidate]
    return None


def read_vendor_csv(
    path: Path, symbol: str, *, base_asset: str | None = None
) -> OHLCVSeries:
    """Read a vendor CSV export into normalised bars.

    Tolerates the preamble line these exports often carry above the header,
    and any row order — the series is sorted, and the fact is reported.
    """
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    start = _header_line_index(lines)
    if start is None:
        raise IngestionError(f"{path}: no header row containing the OHLC columns")

    reader = csv.DictReader(lines[start:])
    columns = resolve_columns(list(reader.fieldnames or []), base_asset=base_asset)
    rows = [
        {
            "date": row[columns["date"]],
            "open": row[columns["open"]],
            "high": row[columns["high"]],
            "low": row[columns["low"]],
            "close": row[columns["close"]],
            "volume": row.get(columns["volume"]) if "volume" in columns else None,
        }
        for row in reader
    ]
    series = normalise(symbol, rows)
    series.source_columns = {
        name: columns.get(name) for name in ("date", "open", "high", "low", "close", "volume")
    }
    series.report["source_file"] = str(path)
    return series


def _header_line_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[:10]):
        lowered = line.lower()
        if all(token in lowered for token in ("open", "high", "low", "close")):
            return index
    return None


def normalise(symbol: str, rows: list[dict]) -> OHLCVSeries:
    """Validate and normalise raw rows into ascending daily bars.

    Every rejected row is counted under a named reason. The four rejection
    reasons are distinct because they mean different things: a malformed row is
    a parsing problem, an inconsistent bar is a vendor problem, a duplicate is
    an export problem, and a gap is a market or coverage problem.
    """
    unparsable = 0
    inconsistent = 0
    duplicates = 0
    by_date: dict[date, Bar] = {}
    previous: date | None = None
    out_of_order = False

    for row in rows:
        try:
            day = parse_day(row["date"])
            bar = Bar(
                day=day,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=_optional_float(row.get("volume")),
            )
        except (KeyError, TypeError, ValueError):
            unparsable += 1
            continue

        if previous is not None and day < previous:
            out_of_order = True
        previous = day

        if not _is_consistent(bar):
            inconsistent += 1
            continue
        if bar.day in by_date:
            duplicates += 1
            continue
        by_date[bar.day] = bar

    bars = [by_date[day] for day in sorted(by_date)]
    dates = [bar.day for bar in bars]

    return OHLCVSeries(
        symbol=symbol,
        bars=bars,
        report={
            "asset": symbol,
            "raw_rows": len(rows),
            "accepted_rows": len(bars),
            "unparsable_rows_dropped": unparsable,
            "inconsistent_bars_dropped": inconsistent,
            "duplicate_rows_dropped": duplicates,
            "out_of_order_input": out_of_order,
            "first_date": dates[0].isoformat() if dates else None,
            "last_date": dates[-1].isoformat() if dates else None,
            "calendar_gaps": panel.calendar_gaps(dates),
        },
    )


def _is_consistent(bar: Bar) -> bool:
    """An OHLC bar that violates its own ordering is not a bar."""
    values = (bar.open, bar.high, bar.low, bar.close)
    if any(value != value or value <= 0 for value in values):  # NaN or non-positive
        return False
    if bar.volume is not None and (bar.volume != bar.volume or bar.volume < 0):
        return False
    return bar.low <= min(bar.open, bar.close) and bar.high >= max(bar.open, bar.close) and bar.low <= bar.high


def parse_day(value) -> date:
    """Accept the date spellings these exports actually use."""
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("empty date")

    if text.isdigit():
        number = int(text)
        # Unix seconds, milliseconds or microseconds, by magnitude.
        if number > 10**14:
            number //= 1_000_000
        elif number > 10**11:
            number //= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc).date()

    for pattern in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[: len(pattern) + 6].strip(), pattern).date()
        except ValueError:
            continue
    return date.fromisoformat(text[:10])


def _optional_float(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
