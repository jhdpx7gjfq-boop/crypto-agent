"""PATH-A runner: orchestrate liquidation-independent alpha pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from igwt.data.binance_audit import audit_binance_klines
from igwt.data.binance_fetcher import fetch_klines, load_raw_klines, store_raw_klines
from igwt.features.liquidation_alpha_signals import build_path_a_observations
from igwt.features.pit import forward_return

FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "real" / "PATH-A-LIQUIDATION-ALPHA"


@dataclass
class PathARunResult:
    """Result of a PATH-A pipeline run."""

    symbol: str
    audit_passed: bool
    audit_verdict: str
    observations_count: int
    date_range: tuple[str, str] | None
    manifest: dict


def run_path_a_single_symbol(
    symbol: str,
    start_date: date,
    end_date: date,
    horizon_days: int = 5,
    fetch_fresh: bool = False,
) -> PathARunResult:
    """Run PATH-A pipeline for one symbol.

    Steps:
    1. Fetch or load Binance OHLCV
    2. Audit integrity
    3. Build PIT features
    4. Construct WFV observations
    5. Save to fixture
    """
    print(f"\n[PATH-A] {symbol} starting...")

    # Step 1: Data acquisition
    klines = None
    if fetch_fresh:
        print(f"  Fetching {symbol} from Binance...")
        klines = fetch_klines(symbol, start_date, end_date)
        if klines:
            store_raw_klines(symbol, klines)
            print(f"    ✓ Fetched {len(klines)} raw klines")
    else:
        klines = load_raw_klines(symbol)
        if klines:
            print(f"  ✓ Loaded {len(klines)} cached klines")

    if not klines:
        print(f"  ✗ No data available for {symbol}")
        return PathARunResult(
            symbol=symbol,
            audit_passed=False,
            audit_verdict="FAIL",
            observations_count=0,
            date_range=None,
            manifest={"error": "no_data"},
        )

    # Step 2: Audit
    print(f"  Auditing {symbol}...")
    audit, normalized = audit_binance_klines(symbol, klines)
    print(f"    Raw: {audit.raw_row_count} → Accepted: {audit.accepted_rows} ({audit.verdict})")

    if audit.verdict == "FAIL":
        return PathARunResult(
            symbol=symbol,
            audit_passed=False,
            audit_verdict=audit.verdict,
            observations_count=0,
            date_range=None,
            manifest=asdict(audit),
        )

    # Step 3: Extract OHLCV
    dates = [row["date"] for row in normalized]
    closes = [row["close"] for row in normalized]
    volumes = [row["volume"] for row in normalized]

    # Step 4: Features PIT
    print(f"  Building PIT features for {symbol}...")
    fwd_rets = forward_return(closes, horizon=horizon_days)

    # Step 5: Observations
    observations = build_path_a_observations(dates, closes, volumes, fwd_rets, horizon_days)
    print(f"    ✓ {len(observations)} valid observations")

    if not observations:
        return PathARunResult(
            symbol=symbol,
            audit_passed=True,
            audit_verdict=audit.verdict,
            observations_count=0,
            date_range=None,
            manifest=asdict(audit),
        )

    # Step 6: Save fixture
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    obs_file = FIXTURE_DIR / f"{symbol}_observations.json"
    with open(obs_file, "w") as f:
        json.dump(
            [
                {
                    "date": obs["date"].isoformat(),
                    "signal": obs["signal"],
                    "fwdRet": obs["fwdRet"],
                    "regimeVol": obs["regimeVol"],
                }
                for obs in observations
            ],
            f,
        )

    date_range = (observations[0]["date"].isoformat(), observations[-1]["date"].isoformat())

    manifest = {
        "symbol": symbol,
        "audit": asdict(audit),
        "observations_file": str(obs_file.relative_to(FIXTURE_DIR.parent.parent)),
        "observations_count": len(observations),
        "horizon_days": horizon_days,
    }

    return PathARunResult(
        symbol=symbol,
        audit_passed=audit.verdict in ("PASS", "WARN"),
        audit_verdict=audit.verdict,
        observations_count=len(observations),
        date_range=date_range,
        manifest=manifest,
    )


def run_path_a_full(
    symbols: list[str] = None,
    start_date: date = None,
    end_date: date = None,
    horizon_days: int = 5,
    fetch_fresh: bool = False,
) -> dict:
    """Run PATH-A for all symbols. Save manifest."""
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"]
    if start_date is None:
        start_date = date.today() - timedelta(days=365)
    if end_date is None:
        end_date = date.today()

    print(f"\n[PATH-A] Running full pipeline:")
    print(f"  Symbols: {symbols}")
    print(f"  Period: {start_date} to {end_date}")
    print(f"  Horizon: {horizon_days} days")

    results = {}
    for symbol in symbols:
        result = run_path_a_single_symbol(symbol, start_date, end_date, horizon_days, fetch_fresh)
        results[symbol] = result

    # Save manifest
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    manifest_file = FIXTURE_DIR / "manifest.json"
    manifest = {
        "fixture_id": "PATH-A-LIQUIDATION-ALPHA",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "symbols": symbols,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "horizon_days": horizon_days,
        "results": {
            symbol: {
                "audit_passed": r.audit_passed,
                "audit_verdict": r.audit_verdict,
                "observations_count": r.observations_count,
                "date_range": r.date_range,
            }
            for symbol, r in results.items()
        },
    }
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n[PATH-A] Manifest saved: {manifest_file}")
    print(f"  Summary: {sum(1 for r in results.values() if r.audit_passed)}/{len(results)} symbols passed")

    return results


if __name__ == "__main__":
    import sys
    fetch = "--fetch" in sys.argv
    run_path_a_full(fetch_fresh=fetch)
