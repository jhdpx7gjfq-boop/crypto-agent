"""The WFV observation contract, and the one implementation that produces it.

Every fixture — whatever its data source — goes through this module. That is
the point: if two datasets disagree, the disagreement is in the data, never in
two divergent copies of the feature code.

Frozen by ``docs/registry/WFV-V2-CONTRACT.lock.json`` and enforced by
``tests/test_registry_locks.py``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from igwt.features import panel, pit

CONTRACT_COLUMNS = ("date", "asset", "signal", "fwdRet", "regimeVol")

#: Decimal places used when serialising a float column. Fixed, so that a
#: rebuild is byte-reproducible and a lock hash means something.
DECIMALS = 10


@dataclass(frozen=True)
class FeatureParams:
    """Feature definitions. Declared before a run, never tuned against its result."""

    momentum_lookback_days: int = 30
    forward_horizon_days: int = 7
    volatility_window_days: int = 30
    min_cross_section: int = 3

    def as_dict(self) -> dict:
        return {
            "momentum_lookback_days": self.momentum_lookback_days,
            "forward_horizon_days": self.forward_horizon_days,
            "volatility_window_days": self.volatility_window_days,
            "min_cross_section": self.min_cross_section,
            "signal_definition": (
                "cross-sectional z-score, within each date, of the trailing "
                f"{self.momentum_lookback_days}-day simple return"
            ),
            "fwdRet_definition": (
                f"forward {self.forward_horizon_days}-day simple return (label)"
            ),
            "regimeVol_definition": (
                "annualised stdev of daily log returns over the trailing "
                f"{self.volatility_window_days} days"
            ),
        }


def asset_features(series: panel.AssetSeries, params: FeatureParams) -> dict:
    """Point-in-time features and label for one asset, gap-aware.

    A window measured in *rows* silently stretches past its stated horizon
    wherever the series has a calendar gap; the contiguity masks invalidate
    those values instead of letting them misreport themselves.
    """
    momentum = pit.trailing_return(series.closes, params.momentum_lookback_days)
    forward = pit.forward_return(series.closes, params.forward_horizon_days)
    volatility = pit.realized_volatility(series.closes, params.volatility_window_days)

    momentum_ok = panel.contiguous_backward_mask(series.dates, params.momentum_lookback_days)
    volatility_ok = panel.contiguous_backward_mask(series.dates, params.volatility_window_days)
    forward_ok = panel.contiguous_forward_mask(series.dates, params.forward_horizon_days)

    return {
        "momentum": [value if ok else None for value, ok in zip(momentum, momentum_ok)],
        "fwdRet": [value if ok else None for value, ok in zip(forward, forward_ok)],
        "regimeVol": [value if ok else None for value, ok in zip(volatility, volatility_ok)],
        "index_by_date": {day: i for i, day in enumerate(series.dates)},
    }


def build_observations(
    series_by_asset: dict[str, panel.AssetSeries], params: FeatureParams
) -> list[dict]:
    """Assemble the five contract columns from a validated daily panel.

    The signal is z-scored *across assets within a date*, so a market-wide move
    cannot be mistaken for cross-sectional skill. Only complete observations
    are emitted: a row missing any column is dropped, never imputed.
    """
    features_by_asset = {
        symbol: asset_features(series, params) for symbol, series in series_by_asset.items()
    }
    rows: list[dict] = []

    for day in panel.common_date_index(list(series_by_asset.values())):
        momentum_today: dict[str, float | None] = {}
        for symbol, features in features_by_asset.items():
            index = features["index_by_date"].get(day)
            momentum_today[symbol] = None if index is None else features["momentum"][index]

        signals = pit.cross_sectional_zscore(
            momentum_today, min_observations=params.min_cross_section
        )

        for symbol in sorted(series_by_asset):
            features = features_by_asset[symbol]
            index = features["index_by_date"].get(day)
            if index is None:
                continue
            signal = signals[symbol]
            forward = features["fwdRet"][index]
            volatility = features["regimeVol"][index]
            if signal is None or forward is None or volatility is None:
                continue
            rows.append(
                {
                    "date": day.isoformat(),
                    "asset": symbol,
                    "signal": signal,
                    "fwdRet": forward,
                    "regimeVol": volatility,
                }
            )

    rows.sort(key=lambda row: (row["date"], row["asset"]))
    return rows


def write_observations(rows: list[dict], path: Path) -> None:
    """Serialise to CSV with fixed precision, so a rebuild is byte-reproducible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CONTRACT_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "date": row["date"],
                    "asset": row["asset"],
                    "signal": f"{row['signal']:.{DECIMALS}f}",
                    "fwdRet": f"{row['fwdRet']:.{DECIMALS}f}",
                    "regimeVol": f"{row['regimeVol']:.{DECIMALS}f}",
                }
            )


def read_observations(path: Path) -> list[dict]:
    """Read observations back in the types the WFV contract requires."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return [
            {
                "date": date.fromisoformat(row["date"]),
                "asset": row["asset"],
                "signal": float(row["signal"]),
                "fwdRet": float(row["fwdRet"]),
                "regimeVol": float(row["regimeVol"]),
            }
            for row in csv.DictReader(handle)
        ]
