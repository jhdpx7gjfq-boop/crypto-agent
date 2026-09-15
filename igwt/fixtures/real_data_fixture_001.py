"""REAL-DATA-FIXTURE-001 — builder.

Builds the walk-forward-validation fixture from *real, recorded* market data.
Nothing in this module simulates, interpolates or extrapolates a price: every
observation traces back to a hashed provider snapshot under ``raw/``.

Specification: ``docs/specs/REAL-DATA-FIXTURE-001.md``.

Usage
-----
    python -m igwt.fixtures.real_data_fixture_001 --fetch   # collect + build
    python -m igwt.fixtures.real_data_fixture_001           # rebuild from raw
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from datetime import date, datetime, timezone
from pathlib import Path

from igwt import __version__
from igwt.data import coingecko, snapshot
from igwt.features import panel, pit

logger = logging.getLogger(__name__)

FIXTURE_ID = "REAL-DATA-FIXTURE-001"
FIXTURE_ROOT = Path("fixtures/real") / FIXTURE_ID
RAW_ROOT = FIXTURE_ROOT / "raw"

#: Registry symbol -> CoinGecko id. The registry documents these assets as
#: Binance daily datasets; see the manifest's provenance note for why the
#: prices below come from CoinGecko instead.
UNIVERSE: dict[str, str] = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin",
    "XRPUSDT": "ripple",
    "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin",
}

# Feature parameters. Fixed, declared, and never tuned against the outcome:
# this fixture exists to exercise the validator, not to find a strategy.
MOMENTUM_LOOKBACK_DAYS = 30
FORWARD_HORIZON_DAYS = 7
VOLATILITY_WINDOW_DAYS = 30
MIN_CROSS_SECTION = 3

CONTRACT_COLUMNS = ("date", "asset", "signal", "fwdRet", "regimeVol")


def fetch_raw(
    universe: dict[str, str] = UNIVERSE,
    *,
    days: int = 365,
    pause: float = 8.0,
    overwrite: bool = False,
) -> dict:
    """Collect one snapshot per asset into the immutable raw store.

    Without ``overwrite`` a snapshot whose content has changed raises
    ``SnapshotConflict`` rather than being replaced: refreshing recorded
    history is a deliberate act, not a side effect of re-running a script.
    """
    records = {}
    for index, (symbol, coin_id) in enumerate(universe.items()):
        logger.info("fetching %s (%s)", symbol, coin_id)
        payload = coingecko.fetch_market_chart(coin_id, days=days)
        records[symbol] = snapshot.write_snapshot(
            RAW_ROOT, symbol, payload, overwrite=overwrite
        )
        records[symbol]["coingecko_id"] = coin_id
        if index < len(universe) - 1:
            time.sleep(pause)  # stay inside the public tier's rate limit
    return records


def build(
    universe: dict[str, str] = UNIVERSE, *, raw_root: Path = RAW_ROOT
) -> tuple[list[dict], dict]:
    """Rebuild the fixture from the raw store. Returns ``(rows, manifest)``."""
    series_by_asset: dict[str, panel.AssetSeries] = {}
    features_by_asset: dict[str, dict] = {}
    validation_reports = []

    for symbol in universe:
        payload = snapshot.read_snapshot(raw_root, symbol)
        series = panel.parse_market_chart(symbol, payload)
        if not len(series):
            raise ValueError(f"{symbol}: snapshot produced no usable daily points")
        series_by_asset[symbol] = series
        validation_reports.append(series.report)
        features_by_asset[symbol] = _asset_features(series)

    rows = _assemble_rows(series_by_asset, features_by_asset)
    manifest = _manifest(universe, validation_reports, rows, raw_root=raw_root)
    return rows, manifest


def _asset_features(series: panel.AssetSeries) -> dict:
    """Point-in-time features and label for one asset, gap-aware."""
    momentum = pit.trailing_return(series.closes, MOMENTUM_LOOKBACK_DAYS)
    forward = pit.forward_return(series.closes, FORWARD_HORIZON_DAYS)
    volatility = pit.realized_volatility(series.closes, VOLATILITY_WINDOW_DAYS)

    momentum_ok = panel.contiguous_backward_mask(series.dates, MOMENTUM_LOOKBACK_DAYS)
    volatility_ok = panel.contiguous_backward_mask(series.dates, VOLATILITY_WINDOW_DAYS)
    forward_ok = panel.contiguous_forward_mask(series.dates, FORWARD_HORIZON_DAYS)

    return {
        "momentum": [value if ok else None for value, ok in zip(momentum, momentum_ok)],
        "fwdRet": [value if ok else None for value, ok in zip(forward, forward_ok)],
        "regimeVol": [value if ok else None for value, ok in zip(volatility, volatility_ok)],
        "index_by_date": {day: i for i, day in enumerate(series.dates)},
    }


def _assemble_rows(
    series_by_asset: dict[str, panel.AssetSeries], features_by_asset: dict[str, dict]
) -> list[dict]:
    """Cross-sectional z-score per date, then emit only complete observations."""
    all_dates = panel.common_date_index(list(series_by_asset.values()))
    rows: list[dict] = []

    for day in all_dates:
        momentum_today: dict[str, float | None] = {}
        for symbol, features in features_by_asset.items():
            index = features["index_by_date"].get(day)
            momentum_today[symbol] = None if index is None else features["momentum"][index]

        signals = pit.cross_sectional_zscore(momentum_today, min_observations=MIN_CROSS_SECTION)

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


def _manifest(
    universe: dict[str, str],
    validation_reports: list[dict],
    rows: list[dict],
    *,
    raw_root: Path = RAW_ROOT,
) -> dict:
    raw_files = {}
    for symbol in universe:
        path = raw_root / f"{symbol}.json"
        data = path.read_bytes()
        raw_files[symbol] = {
            "file": f"raw/{path.name}",
            "sha256": snapshot.sha256_hex(data),
            "bytes": len(data),
            "coingecko_id": universe[symbol],
        }

    dates = sorted({row["date"] for row in rows})
    per_asset_counts: dict[str, int] = {}
    for row in rows:
        per_asset_counts[row["asset"]] = per_asset_counts.get(row["asset"], 0) + 1

    return {
        "fixture_id": FIXTURE_ID,
        "igwt_version": __version__,
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": {
            "provider": "CoinGecko",
            "endpoint": "/coins/{id}/market_chart?vs_currency=usd&days=365&interval=daily",
            "fields_available": ["close", "market_cap", "total_volume"],
            "fields_unavailable": ["open", "high", "low", "per-candle volume"],
            "history_limit_days": coingecko.PUBLIC_TIER_MAX_DAYS,
            "synthetic_data": False,
        },
        "provenance_note": (
            "The IGWT registry documents this fixture's assets as Binance daily "
            "datasets (BTCUSDT_Daily_2017-2026.xlsx, Binance_*USDT_d.csv). Those "
            "files were not reachable from this environment, and the Binance "
            "public API is not reachable either (api.binance.com answers HTTP 451 "
            "for this region; data-api.binance.vision is refused by the network "
            "policy). CoinGecko — IGWT Layer 1 source #1 — was used instead. "
            "Prices are therefore CoinGecko's cross-venue composite, not Binance "
            "spot, and the history is capped at 365 days by the public tier. "
            "No value in this fixture is simulated."
        ),
        "parameters": {
            "momentum_lookback_days": MOMENTUM_LOOKBACK_DAYS,
            "forward_horizon_days": FORWARD_HORIZON_DAYS,
            "volatility_window_days": VOLATILITY_WINDOW_DAYS,
            "min_cross_section": MIN_CROSS_SECTION,
            "signal_definition": (
                "cross-sectional z-score, within each date, of the trailing "
                f"{MOMENTUM_LOOKBACK_DAYS}-day simple return"
            ),
            "fwdRet_definition": f"forward {FORWARD_HORIZON_DAYS}-day simple return (label)",
            "regimeVol_definition": (
                f"annualised stdev of daily log returns over the trailing "
                f"{VOLATILITY_WINDOW_DAYS} days"
            ),
        },
        "raw_snapshots": raw_files,
        "snapshot_validation": validation_reports,
        "observations": {
            "rows": len(rows),
            "columns": list(CONTRACT_COLUMNS),
            "assets": sorted(per_asset_counts),
            "rows_per_asset": per_asset_counts,
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "distinct_dates": len(dates),
        },
    }


def write_outputs(rows: list[dict], manifest: dict, root: Path = FIXTURE_ROOT) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    observations_path = root / "observations.csv"

    with observations_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CONTRACT_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "date": row["date"],
                    "asset": row["asset"],
                    "signal": f"{row['signal']:.10f}",
                    "fwdRet": f"{row['fwdRet']:.10f}",
                    "regimeVol": f"{row['regimeVol']:.10f}",
                }
            )

    manifest["observations"]["sha256"] = snapshot.sha256_hex(observations_path.read_bytes())
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_observations(root: Path = FIXTURE_ROOT) -> list[dict]:
    """Read the fixture back in the WFV contract's types."""
    with (Path(root) / "observations.csv").open(newline="", encoding="utf-8") as handle:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Build {FIXTURE_ID}")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="collect fresh snapshots before building (otherwise rebuild from raw/)",
    )
    parser.add_argument("--days", type=int, default=coingecko.PUBLIC_TIER_MAX_DAYS)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="allow --fetch to replace existing raw snapshots (append-only otherwise)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.fetch:
        for symbol, record in fetch_raw(days=args.days, overwrite=args.refresh).items():
            logger.info("%s: %s (%s bytes, sha256=%s)", symbol, record["status"],
                        record["bytes"], record["sha256"][:12])

    rows, manifest = build()
    write_outputs(rows, manifest)
    logger.info(
        "%s: %d observations, %s -> %s",
        FIXTURE_ID,
        manifest["observations"]["rows"],
        manifest["observations"]["first_date"],
        manifest["observations"]["last_date"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
