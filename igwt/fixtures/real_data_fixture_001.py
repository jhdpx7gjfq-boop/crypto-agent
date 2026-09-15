"""REAL-DATA-FIXTURE-001 — builder.

Status: **LOCKED** (see ``docs/registry/REAL-DATA-FIXTURE-001.lock.json``).
This fixture is a frozen independent control. It is rebuilt, re-verified and
compared against — never overwritten. A source change belongs in a *new*
fixture, not in a retroactive edit of this one.

Builds the walk-forward-validation fixture from real, recorded market data.
Nothing here simulates, interpolates or extrapolates a price: every observation
traces back to a hashed provider snapshot under ``raw/``.

Specification: ``docs/specs/REAL-DATA-FIXTURE-001.md``.

Usage
-----
    python -m igwt.fixtures.real_data_fixture_001            # rebuild from raw/
    python -m igwt.fixtures.real_data_fixture_001 --fetch    # collect, then build
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from igwt import __version__
from igwt.data import coingecko, snapshot
from igwt.features import contract, panel

logger = logging.getLogger(__name__)

FIXTURE_ID = "REAL-DATA-FIXTURE-001"
FIXTURE_ROOT = Path("fixtures/real") / FIXTURE_ID
RAW_ROOT = FIXTURE_ROOT / "raw"

#: Registry symbol -> CoinGecko id. The registry documents these assets as
#: Binance daily datasets; the manifest's provenance note records why the
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

PARAMS = contract.FeatureParams(
    momentum_lookback_days=30,
    forward_horizon_days=7,
    volatility_window_days=30,
    min_cross_section=3,
)

# Retained as module-level names: the specification and the lock file refer to
# them, and downstream code reads them rather than reaching into PARAMS.
MOMENTUM_LOOKBACK_DAYS = PARAMS.momentum_lookback_days
FORWARD_HORIZON_DAYS = PARAMS.forward_horizon_days
VOLATILITY_WINDOW_DAYS = PARAMS.volatility_window_days
MIN_CROSS_SECTION = PARAMS.min_cross_section
CONTRACT_COLUMNS = contract.CONTRACT_COLUMNS


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
    validation_reports = []

    for symbol in universe:
        payload = snapshot.read_snapshot(raw_root, symbol)
        series = panel.parse_market_chart(symbol, payload)
        if not len(series):
            raise ValueError(f"{symbol}: snapshot produced no usable daily points")
        series_by_asset[symbol] = series
        validation_reports.append(series.report)

    rows = contract.build_observations(series_by_asset, PARAMS)
    manifest = _manifest(universe, validation_reports, rows, raw_root=raw_root)
    return rows, manifest


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
        "parameters": PARAMS.as_dict(),
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
    contract.write_observations(rows, observations_path)
    manifest["observations"]["sha256"] = snapshot.sha256_hex(observations_path.read_bytes())
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_observations(root: Path = FIXTURE_ROOT) -> list[dict]:
    """Read the fixture back in the WFV contract's types."""
    return contract.read_observations(Path(root) / "observations.csv")


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
            logger.info(
                "%s: %s (%s bytes, sha256=%s)",
                symbol,
                record["status"],
                record["bytes"],
                record["sha256"][:12],
            )

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
