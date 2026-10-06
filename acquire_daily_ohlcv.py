#!/usr/bin/env python3
"""
Acquire daily OHLCV data from CoinGecko free API.
No auth required, public endpoint.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests

# Configuration
COINGECKO_API = "https://api.coingecko.com/api/v3"
SYMBOLS = ["bitcoin", "ethereum", "solana", "avalanche-2"]
SYMBOL_NAMES = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "avalanche-2": "AVAX"}
DAYS = 730  # 2 years
OUTPUT_DIR = Path(__file__).parent / "real_market_data"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_daily_ohlcv(coin_id: str) -> Optional[Dict]:
    """Fetch daily OHLCV from CoinGecko (free tier, public data)."""
    print(f"Fetching daily OHLCV for {coin_id} ({DAYS} days)...")

    try:
        # CoinGecko free API: market_chart endpoint with daily granularity
        url = f"{COINGECKO_API}/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": DAYS,
            "interval": "daily"  # Request daily data (free API supports this)
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if "prices" not in data or "volumes" not in data:
            print(f"  ❌ Invalid response for {coin_id}")
            return None

        prices = data.get("prices", [])
        volumes = data.get("volumes", [])

        if not prices or not volumes:
            print(f"  ❌ No data returned for {coin_id}")
            return None

        print(f"  ✅ Retrieved {len(prices)} price candles, {len(volumes)} volume candles")

        # Convert to OHLCV format
        # CoinGecko returns [timestamp_ms, price] and [timestamp_ms, volume]
        # We need to group them and compute OHLCV (CoinGecko only gives close + volume)
        candles = []

        for i, (ts_ms, close) in enumerate(prices):
            if i >= len(volumes):
                break

            vol = volumes[i][1]
            ts_sec = int(ts_ms / 1000)

            # CoinGecko free API only gives close price, not OHLC
            # Use close as proxy for all (limitation of free API)
            candle = {
                "timestamp": ts_sec,
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": vol
            }
            candles.append(candle)

        return {
            "symbol": SYMBOL_NAMES.get(coin_id, coin_id.upper()),
            "coin_id": coin_id,
            "source": "CoinGecko Free API",
            "data_note": "Daily closes (OHLC uses close as proxy due to API limitation)",
            "count": len(candles),
            "date_range": {
                "start": candles[0]["timestamp"] if candles else None,
                "end": candles[-1]["timestamp"] if candles else None,
                "days_coverage": len(candles)
            },
            "candles": candles
        }

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Network error for {coin_id}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Error for {coin_id}: {e}")
        return None


def save_daily_data():
    """Fetch all symbols and save to JSON files."""
    print(f"\n{'='*60}")
    print(f"Daily OHLCV Acquisition — CoinGecko Free API")
    print(f"{'='*60}\n")

    results = {}

    for coin_id in SYMBOLS:
        symbol = SYMBOL_NAMES.get(coin_id, coin_id.upper())

        # Rate limit: CoinGecko free API has rate limits, be respectful
        time.sleep(1)

        data = fetch_daily_ohlcv(coin_id)

        if data:
            output_file = OUTPUT_DIR / f"{symbol}_coingecko_daily_{DAYS}d.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)
            print(f"  📁 Saved to {output_file.name}")
            results[symbol] = {"status": "success", "candles": len(data["candles"])}
        else:
            results[symbol] = {"status": "failed"}

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"{'='*60}")
    for symbol, result in results.items():
        status = "✅" if result["status"] == "success" else "❌"
        candles = result.get("candles", 0)
        print(f"{status} {symbol}: {candles} candles" if candles else f"{status} {symbol}: Failed")

    return results


if __name__ == "__main__":
    results = save_daily_data()

    # Exit code: 0 if all succeeded, 1 if any failed
    failed = sum(1 for r in results.values() if r["status"] == "failed")
    exit(0 if failed == 0 else 1)
