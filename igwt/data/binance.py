"""Binance public klines collector (IGWT Layer 1).

Read-only access to the public market-data endpoint: no API key, no account,
no order placement. Binance is used strictly as a public OHLCV source.

Reachability is not assumed. ``preflight`` probes the endpoints and returns a
structured diagnosis, so an acquisition that cannot run says *why* instead of
failing somewhere deep in a loop.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

#: Ordered by preference. ``data-api.binance.vision`` is the documented
#: market-data mirror and is not subject to the same regional restrictions.
ENDPOINTS = (
    "https://data-api.binance.vision/api/v3",
    "https://api.binance.com/api/v3",
)

MAX_LIMIT = 1000  # klines per request, per the API
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

# Kline tuple layout, per the API documentation.
OPEN_TIME, OPEN, HIGH, LOW, CLOSE, VOLUME = 0, 1, 2, 3, 4, 5


class BinanceError(RuntimeError):
    """Raised when the collector cannot obtain a usable response."""


class BinanceUnreachable(BinanceError):
    """Raised when no endpoint can be reached at all.

    Distinct from ``BinanceError`` on purpose: unreachable is an environment
    verdict for the operator, not a data problem to retry around.
    """


def preflight(*, session: requests.Session | None = None, timeout: float = 20.0) -> dict:
    """Probe each endpoint once and report what happened, without raising.

    Returns ``{"reachable": <url|None>, "probes": [{endpoint, status, detail}]}``.
    """
    http = session or requests.Session()
    probes = []
    reachable = None

    for base in ENDPOINTS:
        try:
            response = http.get(
                f"{base}/klines",
                params={"symbol": "BTCUSDT", "interval": "1d", "limit": 1},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            probes.append({"endpoint": base, "status": None, "detail": _describe(exc)})
            continue

        detail = {
            200: "ok",
            451: "HTTP 451 — unavailable for legal reasons in this region",
            403: "HTTP 403 — refused (endpoint policy or egress policy)",
        }.get(response.status_code, f"HTTP {response.status_code}")
        probes.append({"endpoint": base, "status": response.status_code, "detail": detail})

        if response.status_code == 200 and reachable is None:
            reachable = base

    return {"reachable": reachable, "probes": probes}


def _describe(exc: Exception) -> str:
    text = str(exc)
    if "403" in text or "CONNECT" in text:
        return f"connection refused by the egress policy ({text[:120]})"
    return text[:160]


def fetch_daily_klines(
    symbol: str,
    *,
    start: date,
    end: date | None = None,
    base_url: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
    retries: int = 4,
    backoff_seconds: float = 2.0,
    sleep: Any = time.sleep,
    max_pages: int = 100,
) -> list[list]:
    """Fetch daily klines for ``symbol`` from ``start`` to ``end`` inclusive.

    Pages forward through the API's 1000-bar limit. Raises ``BinanceUnreachable``
    when no endpoint answers, so an acquisition failure is legible.
    """
    http = session or requests.Session()
    if base_url is None:
        probe = preflight(session=http, timeout=timeout)
        base_url = probe["reachable"]
        if base_url is None:
            raise BinanceUnreachable(
                "no Binance endpoint is reachable from this environment: "
                + "; ".join(f"{item['endpoint']} -> {item['detail']}" for item in probe["probes"])
            )

    start_ms = _to_millis(start)
    end_ms = _to_millis(end) if end else _to_millis(datetime.now(timezone.utc).date())

    collected: list[list] = []
    cursor = start_ms
    for _ in range(max_pages):
        page = _request_page(
            http,
            base_url,
            symbol,
            cursor,
            end_ms,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
            sleep=sleep,
        )
        if not page:
            break
        collected.extend(page)
        if len(page) < MAX_LIMIT:
            break  # a short page means the range is exhausted
        next_cursor = int(page[-1][OPEN_TIME]) + 86_400_000
        if next_cursor <= cursor or next_cursor > end_ms:
            break
        cursor = next_cursor
    else:
        raise BinanceError(f"{symbol}: page budget of {max_pages} exhausted before reaching {end}")

    return collected


def _request_page(
    http, base_url, symbol, start_ms, end_ms, *, timeout, retries, backoff_seconds, sleep
) -> list[list]:
    params = {
        "symbol": symbol,
        "interval": "1d",
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": MAX_LIMIT,
    }
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            response = http.get(f"{base_url}/klines", params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("%s: request failed (attempt %d): %s", symbol, attempt + 1, exc)
        else:
            if response.status_code == 200:
                return _validate_klines(symbol, response.json())
            if response.status_code not in RETRYABLE_STATUS:
                raise BinanceError(f"{symbol}: HTTP {response.status_code} — {response.text[:300]}")
            last_error = BinanceError(f"{symbol}: HTTP {response.status_code}")
            logger.warning(
                "%s: retryable HTTP %d (attempt %d)", symbol, response.status_code, attempt + 1
            )

        if attempt < retries - 1:
            sleep(backoff_seconds * (2**attempt))

    raise BinanceError(f"{symbol}: retry budget exhausted ({retries} attempts)") from last_error


def _validate_klines(symbol: str, payload: Any) -> list[list]:
    if not isinstance(payload, list):
        raise BinanceError(f"{symbol}: expected a JSON array, got {type(payload).__name__}")
    for entry in payload:
        if not isinstance(entry, list) or len(entry) < 6:
            raise BinanceError(f"{symbol}: malformed kline {entry!r}")
    return payload


def klines_to_rows(klines: list[list]) -> list[dict]:
    """Project raw klines onto the OHLCV ingestion shape."""
    return [
        {
            "date": int(entry[OPEN_TIME]),
            "open": entry[OPEN],
            "high": entry[HIGH],
            "low": entry[LOW],
            "close": entry[CLOSE],
            "volume": entry[VOLUME],
        }
        for entry in klines
    ]


def _to_millis(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)
