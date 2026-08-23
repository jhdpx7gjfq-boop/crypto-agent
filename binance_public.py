"""Free, key-less alternative to CoinGlassClient for some of IGWT's P0
microstructure data, using Binance's public REST APIs directly.

No subscription or API key needed for market data. Covers:
- Open Interest (current + historical, futures only)
- Funding Rate (history, futures only)
- CVD proxy for spot & futures -- Binance has no CVD endpoint, so this is
  computed locally from klines' taker buy/sell volume fields.

Data is single-exchange (Binance only), not the cross-exchange aggregates
CoinGlass provides. Liquidations and cross-exchange NetFlow have no free
public REST equivalent -- see
research/candidates/DATA-SRC-004_BINANCE_PUBLIC_FREE/OVERVIEW.md for why,
and what a real implementation of each would require.

Public endpoints are unauthenticated but still rate-limited by IP: Binance
returns 429 (soft limit) or 418 (IP auto-banned) with a Retry-After header,
handled the same way as CoinGlassClient (see http_retry.py).
"""

import logging
import time

import requests

from http_retry import RateLimitError, backoff_wait, parse_retry_after

logger = logging.getLogger(__name__)

FUTURES_BASE_URL = "https://fapi.binance.com"
SPOT_BASE_URL = "https://api.binance.com"


class BinanceAPIError(Exception):
    """Raised when Binance responds with an error payload (e.g. bad symbol)."""


class BinancePublicClient:
    def __init__(self, timeout=10, max_retries=5, backoff_base=1.0, backoff_max=60.0, min_request_interval=0.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.min_request_interval = min_request_interval
        self._last_request_time = None

    def _throttle(self):
        if self.min_request_interval <= 0 or self._last_request_time is None:
            return
        remaining = self.min_request_interval - (time.monotonic() - self._last_request_time)
        if remaining > 0:
            time.sleep(remaining)

    def _get(self, base_url, path, **params):
        params = {k: v for k, v in params.items() if v is not None}
        attempt = 0
        while True:
            self._throttle()
            response = requests.get(f"{base_url}{path}", params=params, timeout=self.timeout)
            self._last_request_time = time.monotonic()

            if response.status_code in (429, 418):
                retry_after = parse_retry_after(response.headers.get("Retry-After"))
                attempt += 1
                if attempt > self.max_retries:
                    raise RateLimitError(
                        f"Binance rate limit exceeded ({response.status_code})", retry_after=retry_after
                    )
                wait = backoff_wait(attempt, self.backoff_base, self.backoff_max, retry_after)
                logger.warning(
                    "binance_rate_limited endpoint=%s status=%d attempt=%d/%d wait=%.2fs",
                    path, response.status_code, attempt, self.max_retries, wait,
                )
                time.sleep(wait)
                continue

            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and "code" in payload and "msg" in payload:
                raise BinanceAPIError(f"{payload['code']}: {payload['msg']}")
            return payload

    # --- Open Interest (futures only) ---

    def open_interest(self, symbol):
        return self._get(FUTURES_BASE_URL, "/fapi/v1/openInterest", symbol=symbol)

    def open_interest_history(self, symbol, period, limit=None, start_time=None, end_time=None):
        return self._get(
            FUTURES_BASE_URL,
            "/futures/data/openInterestHist",
            symbol=symbol,
            period=period,
            limit=limit,
            startTime=start_time,
            endTime=end_time,
        )

    # --- Funding Rate (futures only) ---

    def funding_rate_history(self, symbol, limit=None, start_time=None, end_time=None):
        return self._get(
            FUTURES_BASE_URL,
            "/fapi/v1/fundingRate",
            symbol=symbol,
            limit=limit,
            startTime=start_time,
            endTime=end_time,
        )

    # --- CVD (computed locally from klines' taker buy/sell volume) ---

    def futures_cvd_history(self, symbol, interval, limit=None, start_time=None, end_time=None):
        klines = self._get(
            FUTURES_BASE_URL,
            "/fapi/v1/klines",
            symbol=symbol,
            interval=interval,
            limit=limit,
            startTime=start_time,
            endTime=end_time,
        )
        return cvd_from_klines(klines)

    def spot_cvd_history(self, symbol, interval, limit=None, start_time=None, end_time=None):
        klines = self._get(
            SPOT_BASE_URL,
            "/api/v3/klines",
            symbol=symbol,
            interval=interval,
            limit=limit,
            startTime=start_time,
            endTime=end_time,
        )
        return cvd_from_klines(klines)


def cvd_from_klines(klines):
    """Cumulative Volume Delta from Binance klines.

    Each kline is [open_time, open, high, low, close, volume, close_time,
    quote_volume, num_trades, taker_buy_base_volume, taker_buy_quote_volume,
    ignore]. Binance doesn't split out "taker sell" directly, but total
    volume minus taker buy volume is exactly that.
    """
    cvd = 0.0
    records = []
    for k in klines:
        open_time, close_time, volume, taker_buy_base = k[0], k[6], float(k[5]), float(k[9])
        taker_sell = volume - taker_buy_base
        delta = taker_buy_base - taker_sell
        cvd += delta
        records.append(
            {
                "open_time": open_time,
                "close_time": close_time,
                "taker_buy_volume": taker_buy_base,
                "taker_sell_volume": taker_sell,
                "delta": delta,
                "cvd": cvd,
            }
        )
    return records
