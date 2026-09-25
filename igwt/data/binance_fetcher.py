"""Fetch and store Binance spot OHLCV data (PATH-A data layer).

Attempts to retrieve 1-day bars from Binance public API.
Falls back to manual file ingestion if API is blocked.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

BINANCE_API = "https://api.binance.com/api/v3"
BINANCE_VISION = "https://data-api.binance.vision/api/v3"
RAW_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "binance" / "raw"


def fetch_klines(
    symbol: str, start_date: date, end_date: date, attempt_vision: bool = True
) -> list[dict] | None:
    """Attempt to fetch 1-day klines from Binance.

    Returns list of dicts with keys: openTime, open, high, low, close, volume, closeTime.
    Returns None if both endpoints are unreachable.
    """
    start_ms = int(datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)

    params = {
        "symbol": symbol,
        "interval": "1d",
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": 1000,
    }

    endpoints = []
    if attempt_vision:
        endpoints.append(("binance-vision", BINANCE_VISION))
    endpoints.append(("binance-api", BINANCE_API))

    for name, url in endpoints:
        try:
            response = requests.get(f"{url}/klines", params=params, timeout=10)
            if response.status_code == 200:
                klines = response.json()
                return [
                    {
                        "openTime": int(k[0]),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[7]),
                        "closeTime": int(k[6]),
                    }
                    for k in klines
                ]
            elif response.status_code == 451:
                continue
        except (requests.RequestException, ValueError):
            continue

    return None


def store_raw_klines(symbol: str, klines: list[dict]) -> Path:
    """Store fetched klines as JSON."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DATA_DIR / f"{symbol}_klines.json"
    with open(path, "w") as f:
        json.dump(klines, f)
    return path


def load_raw_klines(symbol: str) -> list[dict] | None:
    """Load stored klines from JSON."""
    path = RAW_DATA_DIR / f"{symbol}_klines.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def preflight_check() -> dict:
    """Test API reachability."""
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "binance_vision": None,
        "binance_api": None,
        "file_ingress": RAW_DATA_DIR.exists(),
    }

    for name, url in [("binance-vision", BINANCE_VISION), ("binance-api", BINANCE_API)]:
        try:
            resp = requests.head(f"{url}/ping", timeout=5)
            result[name.replace("-", "_")] = resp.status_code
        except Exception as e:
            result[name.replace("-", "_")] = str(e)

    return result
