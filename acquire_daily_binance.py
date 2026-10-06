#!/usr/bin/env python3
"""
Acquire daily OHLCV from Binance public API (no auth required).
Falls back to alternative sources if needed.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests

BINANCE_API = "https://api.binance.com/api/v3"
SYMBOLS = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "SOLUSDT": "SOL",
    "AVAXUSDT": "AVAX"
}
OUTPUT_DIR = Path(__file__).parent / "real_market_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Proxy settings from environment
import os
proxies = {}
if "HTTPS_PROXY" in os.environ:
    proxies["https"] = os.environ["HTTPS_PROXY"]
if "HTTP_PROXY" in os.environ:
    proxies["http"] = os.environ["HTTP_PROXY"]

# Use CA bundle if available
verify_ssl = True
if os.path.exists("/root/.ccr/ca-bundle.crt"):
    verify_ssl = "/root/.ccr/ca-bundle.crt"

print(f"Proxy config: {bool(proxies)}")
print(f"SSL verify: {verify_ssl}\n")


def fetch_daily_klines(symbol: str, days: int = 730) -> Optional[Dict]:
    """Fetch daily klines (OHLCV candles) from Binance."""
    print(f"Fetching daily klines for {symbol}...")

    try:
        # Binance klines endpoint: public, no auth required
        url = f"{BINANCE_API}/klines"

        # Calculate time range
        end_time = int(datetime.utcnow().timestamp() * 1000)
        start_time = end_time - (days * 24 * 60 * 60 * 1000)

        params = {
            "symbol": symbol,
            "interval": "1d",  # Daily
            "startTime": start_time,
            "endTime": end_time,
            "limit": 1000  # Max limit per request
        }

        print(f"  URL: {url}")
        print(f"  Params: {params}")

        response = requests.get(
            url,
            params=params,
            timeout=30,
            proxies=proxies,
            verify=verify_ssl
        )

        print(f"  Status: {response.status_code}")

        if response.status_code == 403:
            print(f"  ⚠️  Forbidden (451 expected if proxy blocks). Response: {response.text[:200]}")
            return None

        response.raise_for_status()

        klines = response.json()

        if not klines:
            print(f"  ❌ No klines returned")
            return None

        print(f"  ✅ Retrieved {len(klines)} daily candles")

        # Binance kline format: [open_time, open, high, low, close, volume, ...]
        candles = []
        for kline in klines:
            candle = {
                "timestamp": int(kline[0] / 1000),  # Convert ms to seconds
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[7])  # Quote asset volume
            }
            candles.append(candle)

        return {
            "symbol": SYMBOLS.get(symbol, symbol),
            "trading_pair": symbol,
            "source": "Binance Public API",
            "data_note": "Daily OHLCV (no auth required, public endpoint)",
            "count": len(candles),
            "date_range": {
                "start": candles[0]["timestamp"] if candles else None,
                "end": candles[-1]["timestamp"] if candles else None,
                "days_coverage": len(candles)
            },
            "candles": candles
        }

    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ Connection error (proxy issue?): {e}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"  ❌ HTTP error: {response.status_code} {response.text[:200] if response else e}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def save_daily_data():
    """Fetch all symbols and save to JSON."""
    print(f"\n{'='*60}")
    print(f"Daily OHLCV Acquisition — Binance Public API")
    print(f"{'='*60}\n")

    results = {}

    for symbol in SYMBOLS.keys():
        time.sleep(0.5)  # Rate limit respect
        data = fetch_daily_klines(symbol, days=730)

        if data:
            output_file = OUTPUT_DIR / f"{data['symbol']}_binance_daily_730d.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)
            print(f"  📁 Saved: {output_file.name}\n")
            results[data['symbol']] = {"status": "success", "candles": len(data["candles"])}
        else:
            results[SYMBOLS.get(symbol, symbol)] = {"status": "failed"}
            print()

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"{'='*60}")
    for symbol, result in results.items():
        status = "✅" if result["status"] == "success" else "❌"
        candles = result.get("candles", 0)
        msg = f"{candles} daily candles" if candles else "Failed"
        print(f"{status} {symbol}: {msg}")

    return results


if __name__ == "__main__":
    results = save_daily_data()
    failed = sum(1 for r in results.values() if r["status"] == "failed")
    exit(0 if failed == 0 else 1)
