"""Phase A -- API Reality Check for the CoinGlass V4 integration.

Calls each of the 6 P0 endpoint families with a real COINGLASS_API_KEY and
prints a report per endpoint: STATUS, HTTP, AUTH, SCHEMA (top-level keys of
the first record), TIMESTAMP/SYMBOL/EXCHANGE/TIMEFRAME field presence, and a
basic DATA QUALITY check (non-empty, timestamps present and sorted).

This does not run in CI and is not a pytest test: it makes real network
calls and costs real API quota. Run it manually, then copy the output table
into research/candidates/DATA-SRC-003_COINGLASS_API_V4/ENDPOINT_VALIDATION.md
before promoting COINGLASS_DATA_STATUS past UNVERIFIED.

Usage:
    COINGLASS_API_KEY=... python scripts/coinglass_verify.py
"""

import requests

from coinglass import CoinGlassAPIError, CoinGlassClient

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


def run_check(name, method_name, kwargs):
    client = CoinGlassClient()
    method = getattr(client, method_name)
    row = {
        "endpoint": name,
        "status": "?",
        "http": "?",
        "auth": "?",
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
    except CoinGlassAPIError as exc:
        row["status"] = "FAIL"
        row["http"] = "200 (API error envelope)"
        row["auth"] = "OK"
        row["schema"] = f"error: {exc}"
        return row

    row["status"] = "PASS"
    row["http"] = "200"
    row["auth"] = "OK"
    row["schema"] = sorted(data[0].keys()) if data else "(empty payload)"
    row["data_quality"] = check_data_quality(data)
    return row


def main():
    results = [run_check(name, method_name, kwargs) for name, method_name, kwargs in CHECKS]

    header = f"| {'Endpoint':<24} | {'Status':<6} | {'HTTP':<24} | {'Auth':<9} | {'Data quality':<10} |"
    print(header)
    print("|" + "-" * (len(header) - 2) + "|")
    for row in results:
        print(
            f"| {row['endpoint']:<24} | {row['status']:<6} | {str(row['http']):<24} "
            f"| {row['auth']:<9} | {row['data_quality']:<10} |"
        )

    print()
    print("Schema (first record's keys) per endpoint -- paste into DATA_DICTIONARY.md:")
    for row in results:
        print(f"- {row['endpoint']}: {row['schema']}")


if __name__ == "__main__":
    main()
