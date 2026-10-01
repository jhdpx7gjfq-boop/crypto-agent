#!/usr/bin/env python3
"""
Phase 2: Binance C1.5-PIT Audit Data Collection

Collects daily OHLCV candles for BTC/ETH/SOL across diverse market regimes.
Documents availability_time (when we queried) and event_time (candle close time).

Methodology: https://github.com/jhdpx7gjfq-boop/crypto-agent/docs/AUDIT_BINANCE_METHODOLOGY.md
"""

import json
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import sys

# Collection parameters
ASSETS = ["BTC", "ETH", "SOL"]
PERIODS = [
    ("2020-01", "2020-01-01", "2020-01-31"),
    ("2020-02", "2020-02-01", "2020-02-29"),
    ("2020-03", "2020-03-01", "2020-03-31"),
    ("2021-01", "2021-01-01", "2021-01-31"),
    ("2021-02", "2021-02-01", "2021-02-28"),
    ("2021-03", "2021-03-01", "2021-03-31"),
    ("2022-05", "2022-05-01", "2022-05-31"),
    ("2022-06", "2022-06-01", "2022-06-30"),
    ("2022-07", "2022-07-01", "2022-07-31"),
    ("2024-01", "2024-01-01", "2024-01-31"),
    ("2024-02", "2024-02-01", "2024-02-29"),
    ("2024-03", "2024-03-01", "2024-03-31"),
    ("2025-01", "2025-01-01", "2025-01-31"),
    ("2025-02", "2025-02-01", "2025-02-28"),
    ("2025-03", "2025-03-01", "2025-03-31"),
]

BINANCE_API = "https://api.binance.com/api/v3/klines"


def timestamp_to_ms(date_str: str) -> int:
    """Convert YYYY-MM-DD to milliseconds since epoch (UTC)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp() * 1000)


def collect_asset_period(asset: str, period_label: str, start_date: str, end_date: str) -> Dict:
    """
    Collect daily OHLCV for asset during period.

    Returns:
    {
        "asset": "BTC",
        "period": "2020-01",
        "query_timestamp_utc": "2026-10-01T...",
        "status": "success" | "error",
        "candles": [...],
        "error_details": "..." | None,
        "candle_count": N,
        "availability_time": "2026-10-01T13:00:00Z" (when we got the data),
        "date_range": {"start": "2020-01-01", "end": "2020-01-31"}
    }
    """
    query_time_utc = datetime.utcnow()
    query_timestamp_str = query_time_utc.isoformat() + "Z"

    symbol = f"{asset}USDT"
    start_ms = timestamp_to_ms(start_date)
    end_ms = timestamp_to_ms(end_date) + 86400000  # Include end date

    cmd = [
        "curl",
        "-s",
        "-w", "\n%{http_code}",
        f"{BINANCE_API}?symbol={symbol}&interval=1d&startTime={start_ms}&endTime={end_ms}&limit=1000"
    ]

    result = {
        "asset": asset,
        "period": period_label,
        "query_timestamp_utc": query_timestamp_str,
        "date_range": {"start": start_date, "end": end_date},
        "status": "pending",
        "candles": [],
        "candle_count": 0,
        "availability_time": query_timestamp_str,
        "error_details": None
    }

    try:
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = process.stdout.strip()

        # Last line is HTTP status code
        lines = output.split('\n')
        http_code = lines[-1] if lines[-1].isdigit() else "000"
        response_body = '\n'.join(lines[:-1]) if len(lines) > 1 else ""

        if http_code != "200":
            result["status"] = "error"
            result["error_details"] = f"HTTP {http_code}: {response_body[:200]}"
            print(f"❌ {asset} {period_label}: HTTP {http_code}")
            return result

        data = json.loads(response_body)
        if not isinstance(data, list):
            result["status"] = "error"
            result["error_details"] = f"Unexpected response format: {str(data)[:100]}"
            print(f"❌ {asset} {period_label}: Invalid response format")
            return result

        # Parse candles: [time, open, high, low, close, volume, close_time, ...]
        candles_parsed = []
        for candle in data:
            if len(candle) >= 6:
                candles_parsed.append({
                    "event_time_ms": candle[0],
                    "event_time_utc": datetime.utcfromtimestamp(candle[0] / 1000).isoformat() + "Z",
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                })

        result["status"] = "success"
        result["candles"] = candles_parsed
        result["candle_count"] = len(candles_parsed)
        print(f"✅ {asset} {period_label}: {len(candles_parsed)} candles")
        return result

    except subprocess.TimeoutExpired:
        result["status"] = "error"
        result["error_details"] = "Request timeout (30s)"
        print(f"❌ {asset} {period_label}: Timeout")
        return result
    except Exception as e:
        result["status"] = "error"
        result["error_details"] = str(e)
        print(f"❌ {asset} {period_label}: {str(e)[:100]}")
        return result


def main():
    print("=" * 70)
    print("Phase 2: Binance C1.5-PIT Audit Data Collection")
    print(f"Started: {datetime.utcnow().isoformat()}Z")
    print("=" * 70)
    print()

    collection_results = {
        "audit_id": "binance_pit_audit_20261001_phase2",
        "phase": "Phase 2: Full Data Collection",
        "query_time_utc": datetime.utcnow().isoformat() + "Z",
        "assets": ASSETS,
        "periods": len(PERIODS),
        "collections": []
    }

    total = len(ASSETS) * len(PERIODS)
    count = 0

    for asset in ASSETS:
        for period_label, start_date, end_date in PERIODS:
            count += 1
            print(f"[{count}/{total}] Collecting {asset} {period_label}...", end=" ", flush=True)
            result = collect_asset_period(asset, period_label, start_date, end_date)
            collection_results["collections"].append(result)

    # Summary stats
    successful = sum(1 for c in collection_results["collections"] if c["status"] == "success")
    failed = sum(1 for c in collection_results["collections"] if c["status"] == "error")
    total_candles = sum(c["candle_count"] for c in collection_results["collections"])

    collection_results["summary"] = {
        "total_requests": total,
        "successful": successful,
        "failed": failed,
        "total_candles_collected": total_candles,
        "completion_pct": round(100 * successful / total, 1) if total > 0 else 0
    }

    print()
    print("=" * 70)
    print(f"Phase 2 Summary:")
    print(f"  Successful: {successful}/{total}")
    print(f"  Failed: {failed}/{total}")
    print(f"  Total candles: {total_candles}")
    print("=" * 70)

    # Save to file
    output_file = "docs/audit_binance_phase2_collection.json"
    with open(output_file, "w") as f:
        json.dump(collection_results, f, indent=2)

    print(f"✅ Results saved to {output_file}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
