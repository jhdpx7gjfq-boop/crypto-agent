"""Phase A -- API Reality Check for the free Binance public data path
(DATA-SRC-004). No API key needed, unlike scripts/coinglass_verify.py.

Calls each of the 4 methods BinancePublicClient implements and prints a
report: STATUS, HTTP, SCHEMA (top-level keys of the first record / the
response itself), and a basic DATA QUALITY check for the history/CVD
methods. Run it manually, then copy the output into
research/candidates/DATA-SRC-004_BINANCE_PUBLIC_FREE/OVERVIEW.md.

Usage:
    python scripts/binance_verify.py
"""

import requests

from binance_public import BinanceAPIError, BinancePublicClient
from http_retry import RateLimitError

TIMESTAMP_KEYS = ("time", "timestamp", "openTime", "open_time")

CHECKS = [
    ("Open Interest (current)", "open_interest", dict(symbol="BTCUSDT")),
    ("Open Interest (history)", "open_interest_history", dict(symbol="BTCUSDT", period="1h", limit=5)),
    ("Funding Rate (history)", "funding_rate_history", dict(symbol="BTCUSDT", limit=5)),
    ("Futures CVD (from klines)", "futures_cvd_history", dict(symbol="BTCUSDT", interval="1h", limit=5)),
    ("Spot CVD (from klines)", "spot_cvd_history", dict(symbol="BTCUSDT", interval="1h", limit=5)),
]


def check_data_quality(data):
    records = data if isinstance(data, list) else [data]
    if not records:
        return "FAIL (empty)"
    ts_key = next((k for k in TIMESTAMP_KEYS if k in records[0]), None)
    if ts_key is None:
        return "n/a (single object)" if not isinstance(data, list) else "WARN (no timestamp field found)"
    timestamps = [r[ts_key] for r in records]
    if timestamps != sorted(timestamps) and timestamps != sorted(timestamps, reverse=True):
        return "WARN (timestamps not monotonic)"
    return "OK"


def run_check(client, name, method_name, kwargs):
    method = getattr(client, method_name)
    row = {"endpoint": name, "status": "?", "http": "?", "schema": "?", "data_quality": "?"}
    try:
        data = method(**kwargs)
    except requests.HTTPError as exc:
        row["status"] = "FAIL"
        row["http"] = str(exc.response.status_code if exc.response is not None else exc)
        return row
    except RateLimitError as exc:
        row["status"] = "FAIL"
        row["http"] = "429/418 (retries exhausted)"
        row["schema"] = f"retry_after={exc.retry_after}"
        return row
    except BinanceAPIError as exc:
        row["status"] = "FAIL"
        row["http"] = "200 (Binance error payload)"
        row["schema"] = str(exc)
        return row

    row["status"] = "PASS"
    row["http"] = "200"
    records = data if isinstance(data, list) else [data]
    row["schema"] = sorted(records[0].keys()) if records else "(empty payload)"
    row["data_quality"] = check_data_quality(data)
    return row


def main():
    client = BinancePublicClient(min_request_interval=0.3)
    results = [run_check(client, name, method_name, kwargs) for name, method_name, kwargs in CHECKS]

    header = f"| {'Endpoint':<26} | {'Status':<6} | {'HTTP':<24} | {'Data quality':<24} |"
    print(header)
    print("|" + "-" * (len(header) - 2) + "|")
    for row in results:
        print(f"| {row['endpoint']:<26} | {row['status']:<6} | {str(row['http']):<24} | {str(row['data_quality']):<24} |")

    print()
    print("Schema (first record's keys) per endpoint -- paste into OVERVIEW.md:")
    for row in results:
        print(f"- {row['endpoint']}: {row['schema']}")


if __name__ == "__main__":
    main()
