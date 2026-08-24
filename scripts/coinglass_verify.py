"""Phase A -- API Reality Check for the CoinGlass V4 integration.

Calls each of the 6 P0 endpoint families with a real COINGLASS_API_KEY and
prints a report per endpoint: STATUS, HTTP, AUTH, quota headers observed
(API-KEY-MAX-LIMIT / API-KEY-USE-LIMIT), whether a 429/Retry-After was hit,
SCHEMA (top-level keys of the first record), and a basic DATA QUALITY check
(non-empty, timestamps present and sorted).

Deliberately conservative: one shared client, 300ms spacing between calls,
only the 8 P0 methods below. The goal is to prove the client talks to
CoinGlass correctly, not to probe how far their API can be pushed -- this
is not a load/stress test.

This does not run in CI and is not a pytest test: it makes real network
calls and costs real API quota. Run it manually, then copy the output table
into research/candidates/DATA-SRC-003_COINGLASS_API_V4/ENDPOINT_VALIDATION.md
before promoting COINGLASS_DATA_STATUS past UNVERIFIED.

Usage:
    COINGLASS_API_KEY=... python scripts/coinglass_verify.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from coinglass import CoinGlassAPIError, CoinGlassClient, RateLimitError

TIMESTAMP_KEYS = ("time", "timestamp", "t", "ts", "createTime")

CHECKS = [
    ("Open Interest", "open_interest_history", dict(exchange="Binance", symbol="BTCUSDT", interval="1h", limit=5)),
    ("Funding (raw)", "funding_rate_history", dict(exchange="Binance", symbol="BTCUSDT", interval="8h", limit=5)),
    ("Funding (OI-weighted)", "funding_rate_oi_weighted_history", dict(symbol="BTC", interval="8h", limit=5)),
    ("Funding (vol-weighted)", "funding_rate_vol_weighted_history", dict(symbol="BTC", interval="8h", limit=5)),
    ("Liquidations", "liquidation_history", dict(exchange="Binance", symbol="BTCUSDT", interval="1h", limit=5)),
    ("Spot CVD", "spot_cvd_history", dict(exchange="Binance", symbol="BTCUSDT", interval="1h", limit=5)),
    ("Futures CVD", "futures_cvd_history", dict(exchange="Binance", symbol="BTCUSDT", interval="1h", limit=5)),
    ("Spot NetFlow", "spot_coin_netflow", dict(symbol="BTC", interval="1h", limit=5)),
]


def check_data_quality(records):
    if not records:
        return "FAIL (empty)"
    ts_key = next((k for k in TIMESTAMP_KEYS if k in records[0]), None)
    if ts_key is None:
        return "WARN (no timestamp field found)"
    timestamps = [r[ts_key] for r in records]
    if timestamps != sorted(timestamps) and timestamps != sorted(timestamps, reverse=True):
        return "WARN (timestamps not monotonic)"
    return "OK"


def run_check(client, name, method_name, kwargs):
    method = getattr(client, method_name)
    row = {
        "endpoint": name,
        "status": "?",
        "http": "?",
        "auth": "?",
        "quota": "?",
        "schema": "?",
        "data_quality": "?",
    }
    try:
        data = method(**kwargs)
    except requests.HTTPError as exc:
        row["status"] = "FAIL"
        row["http"] = str(exc.response.status_code if exc.response is not None else exc)
        row["auth"] = "REJECTED" if exc.response is not None and exc.response.status_code in (401, 403) else "?"
        return row
    except RateLimitError as exc:
        row["status"] = "FAIL"
        row["http"] = "429 (retries exhausted)"
        row["auth"] = "OK"
        row["quota"] = f"retry_after={exc.retry_after}"
        return row
    except CoinGlassAPIError as exc:
        row["status"] = "FAIL"
        row["http"] = "200 (API error envelope)"
        row["auth"] = "OK"
        row["schema"] = f"error: {exc}"
        return row

    row["status"] = "PASS"
    row["http"] = "200"
    row["auth"] = "OK"
    row["quota"] = f"{client.rate_limit_used}/{client.rate_limit_max}"
    row["schema"] = sorted(data[0].keys()) if data else "(empty payload)"
    row["data_quality"] = check_data_quality(data)
    return row


def main():
    # One shared client so quota tracking accumulates across calls, with a
    # conservative fixed spacing and a modest retry budget -- see the
    # module docstring on why this deliberately stays gentle.
    client = CoinGlassClient(min_request_interval=0.3, max_retries=3)
    results = [run_check(client, name, method_name, kwargs) for name, method_name, kwargs in CHECKS]

    header = f"| {'Endpoint':<24} | {'Status':<6} | {'HTTP':<24} | {'Auth':<9} | {'Quota (use/max)':<16} |"
    print(header)
    print("|" + "-" * (len(header) - 2) + "|")
    for row in results:
        print(
            f"| {row['endpoint']:<24} | {row['status']:<6} | {str(row['http']):<24} "
            f"| {row['auth']:<9} | {str(row['quota']):<16} |"
        )

    print()
    print("Schema (first record's keys) per endpoint -- paste into DATA_DICTIONARY.md:")
    for row in results:
        print(f"- {row['endpoint']}: {row['schema']} (data quality: {row['data_quality']})")


if __name__ == "__main__":
    main()
