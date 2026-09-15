"""REAL-DATA-FULL-001 — Binance full-history OHLCV fixture.

Status: **PENDING ACQUISITION**. This module is the acquisition and audit
pipeline; the dataset itself does not exist until Binance data is reachable.
It is a *new* artefact and never an edit of REAL-DATA-FIXTURE-001, which stays
locked as an independent control.

Pipeline
--------
    RAW -> integrity audit -> normalisation -> PIT validation
        -> feature construction -> WFV

Feature construction is ``igwt.features.contract.build_observations`` — the
same function REAL-DATA-FIXTURE-001 uses. That is deliberate and is what makes
a source comparison meaningful: if the two fixtures disagree, the disagreement
is in the data, not in two copies of the feature code.

Two ingress paths, because two are plausible:

    --fetch              Binance public klines API (blocked in some networks)
    --from-files DIR     the registry's vendor CSV exports

Usage
-----
    python -m igwt.fixtures.real_data_full_001 --preflight
    python -m igwt.fixtures.real_data_full_001 --from-files data/binance/
    python -m igwt.fixtures.real_data_full_001 --fetch --start 2017-01-01
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from igwt import __version__
from igwt.data import binance, integrity, ohlcv, snapshot
from igwt.features import contract

logger = logging.getLogger(__name__)

FIXTURE_ID = "REAL-DATA-FULL-001"
FIXTURE_ROOT = Path("fixtures/real") / FIXTURE_ID
RAW_ROOT = FIXTURE_ROOT / "raw"
NORMALISED_ROOT = FIXTURE_ROOT / "normalized"

CONTROL_FIXTURE = "REAL-DATA-FIXTURE-001"

#: Registry symbol -> base asset, used to resolve a vendor file's base-volume
#: column (``Volume BTC``) rather than its quote-volume column (``Volume USDT``).
UNIVERSE: dict[str, str] = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "SOLUSDT": "SOL",
    "BNBUSDT": "BNB",
    "XRPUSDT": "XRP",
    "ADAUSDT": "ADA",
    "DOGEUSDT": "DOGE",
}

DEFAULT_START = date(2017, 1, 1)

#: Identical to the control fixture's parameters, so the two are comparable.
PARAMS = contract.FeatureParams(
    momentum_lookback_days=30,
    forward_horizon_days=7,
    volatility_window_days=30,
    min_cross_section=3,
)


class AcquisitionBlocked(RuntimeError):
    """Raised when no ingress path can supply the data."""


def preflight() -> dict:
    """Report whether an acquisition can run at all, and from where."""
    probe = binance.preflight()
    return {
        "fixture_id": FIXTURE_ID,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "api_reachable": probe["reachable"] is not None,
        "api_endpoint": probe["reachable"],
        "probes": probe["probes"],
        "file_ingress_available": True,
        "verdict": "READY" if probe["reachable"] else "BLOCKED — API unreachable; use --from-files",
    }


def acquire_from_api(
    universe: dict[str, str] = UNIVERSE, *, start: date = DEFAULT_START, end: date | None = None
) -> tuple[dict[str, ohlcv.OHLCVSeries], dict[str, bytes], integrity.AcquisitionContext]:
    probe = binance.preflight()
    if probe["reachable"] is None:
        raise AcquisitionBlocked(
            "Binance is unreachable from this environment: "
            + "; ".join(f"{item['endpoint']} -> {item['detail']}" for item in probe["probes"])
        )

    context = integrity.AcquisitionContext(
        source="Binance",
        endpoint=f"{probe['reachable']}/klines?interval=1d",
        market_type="spot",
        timeframe="1d",
    )
    series_by_symbol, raw_by_symbol = {}, {}

    for symbol in universe:
        logger.info("fetching %s", symbol)
        klines = binance.fetch_daily_klines(
            symbol, start=start, end=end, base_url=probe["reachable"]
        )
        raw_by_symbol[symbol] = snapshot.canonical_bytes(klines)
        series = ohlcv.normalise(symbol, binance.klines_to_rows(klines))
        series.source_columns = {
            "date": "openTime",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        }
        series_by_symbol[symbol] = series

    return series_by_symbol, raw_by_symbol, context


def acquire_from_files(
    directory: Path, universe: dict[str, str] = UNIVERSE
) -> tuple[dict[str, ohlcv.OHLCVSeries], dict[str, bytes], integrity.AcquisitionContext]:
    """Ingest the registry's vendor CSV exports from ``directory``."""
    directory = Path(directory)
    context = integrity.AcquisitionContext(
        source="Binance (vendor CSV export)",
        endpoint=str(directory),
        market_type="spot",
        timeframe="1d",
    )
    series_by_symbol, raw_by_symbol = {}, {}
    missing = []

    for symbol, base_asset in universe.items():
        path = _find_export(directory, symbol)
        if path is None:
            missing.append(symbol)
            continue
        raw_by_symbol[symbol] = path.read_bytes()
        series_by_symbol[symbol] = ohlcv.read_vendor_csv(path, symbol, base_asset=base_asset)

    if missing:
        raise AcquisitionBlocked(
            f"no export found in {directory} for: {', '.join(missing)}. "
            "Expected a CSV whose name contains the symbol."
        )
    return series_by_symbol, raw_by_symbol, context


def _find_export(directory: Path, symbol: str) -> Path | None:
    candidates = sorted(
        path
        for path in directory.glob("*.csv")
        if symbol.lower() in path.name.lower().replace("_", "").replace("-", "")
    )
    return candidates[0] if candidates else None


def build(
    series_by_symbol: dict[str, ohlcv.OHLCVSeries],
    raw_by_symbol: dict[str, bytes],
    context: integrity.AcquisitionContext,
    *,
    root: Path = FIXTURE_ROOT,
) -> tuple[list[dict], dict]:
    """Audit, normalise, build observations, and assemble the manifest."""
    root = Path(root)
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "normalized").mkdir(parents=True, exist_ok=True)

    audits: dict[str, dict] = {}
    for symbol, series in series_by_symbol.items():
        raw_path = root / "raw" / f"{symbol}.raw"
        raw_path.write_bytes(raw_by_symbol[symbol])

        normalised_path = root / "normalized" / f"{symbol}.csv"
        normalised_bytes = _write_normalised(series, normalised_path)

        audits[symbol] = integrity.audit(
            series,
            context=context,
            raw_bytes=raw_by_symbol[symbol],
            normalised_bytes=normalised_bytes,
        )

    summary = integrity.summarise(audits)
    if summary["verdict"] == "FAIL":
        raise AcquisitionBlocked(
            f"integrity audit failed for: {', '.join(summary['symbols_with_findings'])}"
        )

    rows = contract.build_observations(
        {symbol: series.to_asset_series() for symbol, series in series_by_symbol.items()},
        PARAMS,
    )

    dates = sorted({row["date"] for row in rows})
    per_asset_counts: dict[str, int] = {}
    for row in rows:
        per_asset_counts[row["asset"]] = per_asset_counts.get(row["asset"], 0) + 1

    manifest = {
        "fixture_id": FIXTURE_ID,
        "igwt_version": __version__,
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "control_fixture": CONTROL_FIXTURE,
        "relationship_to_control": (
            f"{CONTROL_FIXTURE} is locked and is not modified by this build. The two "
            "are separate datasets built by the same feature code, to be compared."
        ),
        "data_source": {
            "provider": context.source,
            "endpoint": context.endpoint,
            "market_type": context.market_type,
            "timeframe": context.timeframe,
            "timezone": context.timezone,
            "fields_available": ["open", "high", "low", "close", "volume"],
            "synthetic_data": False,
        },
        "parameters": PARAMS.as_dict(),
        "integrity_audit": audits,
        "integrity_summary": summary,
        "observations": {
            "rows": len(rows),
            "columns": list(contract.CONTRACT_COLUMNS),
            "assets": sorted(per_asset_counts),
            "rows_per_asset": per_asset_counts,
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "distinct_dates": len(dates),
        },
        "ohlc_available": True,
        "bce_compatible": True,
    }
    return rows, manifest


def _write_normalised(series: ohlcv.OHLCVSeries, path: Path) -> bytes:
    lines = ["date,open,high,low,close,volume"]
    for bar in series.bars:
        volume = "" if bar.volume is None else f"{bar.volume:.8f}"
        lines.append(
            f"{bar.day.isoformat()},{bar.open:.8f},{bar.high:.8f},"
            f"{bar.low:.8f},{bar.close:.8f},{volume}"
        )
    data = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(data)
    return data


def write_outputs(rows: list[dict], manifest: dict, root: Path = FIXTURE_ROOT) -> dict:
    root = Path(root)
    observations_path = root / "observations.csv"
    contract.write_observations(rows, observations_path)
    manifest["observations"]["sha256"] = snapshot.sha256_hex(observations_path.read_bytes())
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_observations(root: Path = FIXTURE_ROOT) -> list[dict]:
    return contract.read_observations(Path(root) / "observations.csv")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Build {FIXTURE_ID}")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true", help="report acquisition readiness")
    group.add_argument("--fetch", action="store_true", help="acquire from the Binance public API")
    group.add_argument("--from-files", type=Path, help="ingest vendor CSV exports from a directory")
    parser.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--root", type=Path, default=FIXTURE_ROOT)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.preflight:
        report = preflight()
        print(json.dumps(report, indent=2))
        return 0 if report["api_reachable"] else 1

    try:
        if args.fetch:
            acquired = acquire_from_api(start=args.start, end=args.end)
        else:
            acquired = acquire_from_files(args.from_files)
    except AcquisitionBlocked as exc:
        logger.error("%s: acquisition blocked — %s", FIXTURE_ID, exc)
        return 1

    rows, manifest = build(*acquired, root=args.root)
    write_outputs(rows, manifest, root=args.root)

    summary = manifest["integrity_summary"]
    logger.info("integrity audit: %s (%d rows across %d symbols)",
                summary["verdict"], summary["total_rows"], summary["symbols"])
    for symbol in summary["symbols_with_findings"]:
        for finding in manifest["integrity_audit"][symbol]["findings"]:
            logger.warning("  %s: %s", symbol, finding)
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
