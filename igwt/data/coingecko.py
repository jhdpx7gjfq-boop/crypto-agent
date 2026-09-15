"""CoinGecko public-API collector (IGWT Layer 1 — Data Intelligence).

Read-only access to a public market-data endpoint. No credentials, no exchange
account, no order placement.

Endpoint used
-------------
``GET /coins/{id}/market_chart?vs_currency=usd&days=N&interval=daily``

Returns three parallel series (``prices``, ``market_caps``, ``total_volumes``),
each a list of ``[unix_ms, value]``. Daily points are stamped at 00:00:00 UTC;
the last element of a live response is an intraday snapshot of the *current,
incomplete* day and must be discarded by the caller (see
``igwt.features.panel``).

Known limitation (documented, not worked around): the public tier refuses any
window older than 365 days with error code 10012.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.coingecko.com/api/v3"
PUBLIC_TIER_MAX_DAYS = 365

#: Retry only on throttling and transient upstream failures.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class CoinGeckoError(RuntimeError):
    """Raised when the collector cannot obtain a usable response."""


def fetch_market_chart(
    coin_id: str,
    *,
    days: int = PUBLIC_TIER_MAX_DAYS,
    vs_currency: str = "usd",
    session: requests.Session | None = None,
    timeout: float = 30.0,
    retries: int = 4,
    backoff_seconds: float = 2.0,
    sleep: Any = time.sleep,
) -> dict:
    """Fetch one coin's daily market chart.

    Raises ``CoinGeckoError`` on an exhausted retry budget, a non-retryable
    HTTP status, or a payload that does not carry the three expected series.
    """
    if days > PUBLIC_TIER_MAX_DAYS:
        raise CoinGeckoError(
            f"days={days} exceeds the public-tier limit of {PUBLIC_TIER_MAX_DAYS}; "
            "a paid plan is required for deeper history"
        )

    url = f"{API_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": str(days), "interval": "daily"}
    http = session or requests.Session()

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = http.get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("%s: request failed (attempt %d): %s", coin_id, attempt + 1, exc)
        else:
            if response.status_code == 200:
                return _validate_payload(coin_id, response.json())
            if response.status_code not in RETRYABLE_STATUS:
                raise CoinGeckoError(
                    f"{coin_id}: HTTP {response.status_code} — {response.text[:300]}"
                )
            last_error = CoinGeckoError(f"{coin_id}: HTTP {response.status_code}")
            logger.warning(
                "%s: retryable HTTP %d (attempt %d)", coin_id, response.status_code, attempt + 1
            )

        if attempt < retries - 1:
            sleep(backoff_seconds * (2**attempt))

    raise CoinGeckoError(f"{coin_id}: retry budget exhausted ({retries} attempts)") from last_error


def _validate_payload(coin_id: str, payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise CoinGeckoError(f"{coin_id}: expected a JSON object, got {type(payload).__name__}")

    for key in ("prices", "market_caps", "total_volumes"):
        series = payload.get(key)
        if not isinstance(series, list) or not series:
            raise CoinGeckoError(f"{coin_id}: payload field {key!r} is missing or empty")
        for point in series:
            if not (isinstance(point, list) and len(point) == 2):
                raise CoinGeckoError(f"{coin_id}: malformed point in {key!r}: {point!r}")

    return payload
