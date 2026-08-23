"""Client for the CoinGlass V4 API (https://docs.coinglass.com).

Covers the P0 data categories for IGWT's market-microstructure research:
open interest, funding rate, liquidations, CVD (spot & futures) and
spot coin netflow. Each method returns the API response's `data` payload.
"""

import os

import requests

BASE_URL = "https://open-api-v4.coinglass.com"


class CoinGlassAPIError(Exception):
    """Raised when the CoinGlass API responds with a non-success code."""


class CoinGlassClient:
    def __init__(self, api_key=None, base_url=BASE_URL, timeout=10):
        self.api_key = api_key or os.environ["COINGLASS_API_KEY"]
        self.base_url = base_url
        self.timeout = timeout

    def _get(self, path, **params):
        response = requests.get(
            f"{self.base_url}{path}",
            headers={"CG-API-KEY": self.api_key, "accept": "application/json"},
            params={k: v for k, v in params.items() if v is not None},
            timeout=self.timeout,
        )
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
