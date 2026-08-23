"""Client for the CoinGlass V4 API (https://docs.coinglass.com).

Covers the P0 data categories for IGWT's market-microstructure research:
open interest, funding rate, liquidations, CVD (spot & futures) and
spot coin netflow. Each method returns the API response's `data` payload.
"""

import logging
import os
import time

import requests

from http_retry import RateLimitError, backoff_wait, parse_retry_after

logger = logging.getLogger(__name__)

BASE_URL = "https://open-api-v4.coinglass.com"

# Verification ladder for this data source, tracked in
# research/candidates/DATA-SRC-003_COINGLASS_API_V4/ENDPOINT_VALIDATION.md.
# Only bump COINGLASS_DATA_STATUS once the evidence for that stage is
# recorded there — passing unit tests (mocked responses) never promotes it.
#   UNVERIFIED             -- client written and unit-tested against mocks only
#   API_VERIFIED           -- real key, real HTTP call, per endpoint, succeeded
#   SCHEMA_VERIFIED         -- response fields match DATA_DICTIONARY.md
#   DATA_QUALITY_VERIFIED  -- gaps/timezone/resolution/nulls checked over a real range
#   RESEARCH_READY          -- cleared to feed FeatureRecord construction
STATUS_LEVELS = (
    "UNVERIFIED",
    "API_VERIFIED",
    "SCHEMA_VERIFIED",
    "DATA_QUALITY_VERIFIED",
    "RESEARCH_READY",
)

COINGLASS_DATA_STATUS = "UNVERIFIED"


class CoinGlassAPIError(Exception):
    """Raised when the CoinGlass API responds with a non-success code."""


class CoinGlassClient:
    """CoinGlass V4 API client.

    Rate limiting follows the plan's own quota, read from the
    `API-KEY-MAX-LIMIT` / `API-KEY-USE-LIMIT` response headers (exposed as
    `rate_limit_max` / `rate_limit_used`) rather than hardcoded plan
    numbers -- CoinGlass's server is the operational authority; this client
    only adapts to what it reports. On HTTP 429 it backs off exponentially
    (capped at `backoff_max`), honoring `Retry-After` when present, up to
    `max_retries` attempts before raising `RateLimitError`.
    """

    def __init__(
        self,
        api_key=None,
        base_url=BASE_URL,
        timeout=10,
        max_retries=5,
        backoff_base=1.0,
        backoff_max=60.0,
        min_request_interval=0.0,
    ):
        self.api_key = api_key or os.environ["COINGLASS_API_KEY"]
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.min_request_interval = min_request_interval

        self.rate_limit_max = None
        self.rate_limit_used = None
        self._last_request_time = None

    def _throttle(self):
        if self.min_request_interval <= 0 or self._last_request_time is None:
            return
        remaining = self.min_request_interval - (time.monotonic() - self._last_request_time)
        if remaining > 0:
            time.sleep(remaining)

    def _record_quota(self, headers, path):
        max_limit = headers.get("API-KEY-MAX-LIMIT")
        use_limit = headers.get("API-KEY-USE-LIMIT")
        if max_limit is not None:
            self.rate_limit_max = max_limit
        if use_limit is not None:
            self.rate_limit_used = use_limit
        if max_limit is not None or use_limit is not None:
            logger.info(
                "coinglass_quota endpoint=%s use=%s max=%s", path, self.rate_limit_used, self.rate_limit_max
            )

    def _get(self, path, **params):
        params = {k: v for k, v in params.items() if v is not None}
        attempt = 0
        while True:
            self._throttle()
            response = requests.get(
                f"{self.base_url}{path}",
                headers={"CG-API-KEY": self.api_key, "accept": "application/json"},
                params=params,
                timeout=self.timeout,
            )
            self._last_request_time = time.monotonic()
            self._record_quota(response.headers, path)

            if response.status_code == 429:
                retry_after = parse_retry_after(response.headers.get("Retry-After"))
                attempt += 1
                if attempt > self.max_retries:
                    raise RateLimitError("CoinGlass rate limit exceeded (429)", retry_after=retry_after)
                wait = backoff_wait(attempt, self.backoff_base, self.backoff_max, retry_after)
                logger.warning(
                    "coinglass_rate_limited endpoint=%s attempt=%d/%d wait=%.2fs",
                    path, attempt, self.max_retries, wait,
                )
                time.sleep(wait)
                continue

            response.raise_for_status()
            payload = response.json()
            if str(payload.get("code")) != "0":
                raise CoinGlassAPIError(payload.get("msg", "unknown error"))
            return payload["data"]

    # --- Open Interest ---

    def open_interest_history(self, exchange, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/futures/open-interest/history",
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    def open_interest_aggregated_history(self, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/futures/open-interest/aggregated-history",
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    # --- Funding Rate ---

    def funding_rate_history(self, exchange, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/futures/funding-rate/history",
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    def funding_rate_oi_weighted_history(self, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/futures/funding-rate/oi-weight-history",
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    def funding_rate_vol_weighted_history(self, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/futures/funding-rate/vol-weight-history",
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    # --- Liquidations ---

    def liquidation_history(self, exchange, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/futures/liquidation/history",
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    def liquidation_aggregated_history(self, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/futures/liquidation/aggregated-history",
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    # --- CVD (Cumulative Volume Delta) ---

    def spot_cvd_history(self, exchange, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/spot/cvd/history",
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    def futures_cvd_history(self, exchange, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/futures/cvd/history",
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    # --- NetFlow ---

    def spot_coin_netflow(self, symbol, interval, limit=None, start_time=None, end_time=None):
        return self._get(
            "/api/spot/coin/netflow",
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
