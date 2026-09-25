"""
CoinGecko Data Collector - Layer 1 Data Intelligence
Version: 1.0.0

Collects price, market cap, and volume data from CoinGecko API.
Raw Data → Validation → Parquet Export
"""

import logging
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

VERSION = "1.0.0"
API_BASE = "https://api.coingecko.com/api/v3"
MAX_RETRIES = 3
RETRY_BACKOFF = 2
TIMEOUT = 10


class CoinGeckoCollector:
    def __init__(self, api_base: str = API_BASE):
        self.api_base = api_base
        self.session = self._create_session()
        logger.info(f"CoinGeckoCollector initialized (v{VERSION})")

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _fetch(self, endpoint: str, params: dict) -> dict:
        """Fetch from API with retry logic."""
        url = f"{self.api_base}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def get_price(self, coins: list, vs_currency: str = "usd") -> dict:
        """
        Get current price, market cap, 24h volume.

        Args:
            coins: List of coin IDs (e.g., ["bitcoin", "ethereum"])
            vs_currency: Target currency (default: usd)

        Returns:
            Dict with price data
        """
        data = self._fetch(
            "simple/price",
            {
                "ids": ",".join(coins),
                "vs_currencies": vs_currency,
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            },
        )

        self._validate_price(data, coins)
        logger.info(f"Fetched prices for {len(data)} coins")
        return data

    def _validate_price(self, data: dict, expected_coins: list) -> None:
        """Validate price data structure."""
        for coin in expected_coins:
            if coin not in data:
                raise ValueError(f"Missing coin: {coin}")
            if "usd" not in data[coin]:
                raise ValueError(f"Missing USD price for {coin}")

    def get_market_chart(
        self, coin: str, days: int = 30, vs_currency: str = "usd"
    ) -> pd.DataFrame:
        """
        Get historical price data.

        Args:
            coin: Coin ID (e.g., "bitcoin")
            days: Number of days to fetch (1-max 365)
            vs_currency: Target currency

        Returns:
            DataFrame with columns: timestamp, price, market_cap, volume
        """
        data = self._fetch(
            f"coins/{coin}/market_chart",
            {"vs_currency": vs_currency, "days": days},
        )

        self._validate_market_chart(data)

        df = pd.DataFrame(
            {
                "timestamp": [datetime.fromtimestamp(t / 1000) for t in [p[0] for p in data["prices"]]],
                "price": [p[1] for p in data["prices"]],
                "market_cap": [m[1] for m in data["market_caps"]],
                "volume": [v[1] for v in data["total_volumes"]],
            }
        )

        logger.info(f"Fetched {len(df)} candles for {coin}")
        return df

    def _validate_market_chart(self, data: dict) -> None:
        """Validate market chart data structure."""
        required_keys = ["prices", "market_caps", "total_volumes"]
        for key in required_keys:
            if key not in data or not data[key]:
                raise ValueError(f"Missing or empty key: {key}")

    def get_global(self) -> dict:
        """Get global market data (total cap, BTC dominance)."""
        data = self._fetch("global", {})
        logger.info("Fetched global market data")
        return data

    def search(self, query: str) -> list:
        """
        Search coins by name/symbol.

        Returns:
            List of matching coins with id, name, symbol
        """
        data = self._fetch("search", {"query": query})
        results = data.get("coins", [])
        logger.info(f"Search '{query}': found {len(results)} coins")
        return results


def export_to_parquet(df: pd.DataFrame, path: str) -> None:
    """Export DataFrame to Parquet with metadata."""
    df.to_parquet(path, compression="snappy", index=False)
    logger.info(f"Exported {len(df)} rows to {path}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    collector = CoinGeckoCollector()

    # Test 1: Current price
    price_data = collector.get_price(["bitcoin", "ethereum"])
    print("\n=== Current Prices ===")
    for coin, data in price_data.items():
        print(f"{coin}: ${data['usd']:,.2f} (market_cap: ${data['usd_market_cap']:,.0f})")

    # Test 2: Historical data
    df = collector.get_market_chart("bitcoin", days=7)
    print("\n=== BTC 7-Day History ===")
    print(df.head())

    # Test 3: Global data
    global_data = collector.get_global()
    print("\n=== Global Market ===")
    print(f"Total Market Cap: ${global_data['data']['total_market_cap']['usd']:,.0f}")
    btc_dominance = global_data['data']['market_cap_percentage'].get('btc', 0)
    print(f"BTC Dominance: {btc_dominance:.2f}%")

    # Test 4: Search
    results = collector.search("Bitcoin")
    print(f"\n=== Search 'Bitcoin' ===")
    for coin in results[:3]:
        print(f"  {coin['name']} ({coin['symbol'].upper()})")
