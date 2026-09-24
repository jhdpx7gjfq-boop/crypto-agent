import logging
import time
from datetime import datetime
from typing import Optional
import requests
from src.data.schema import TokenMetadata

logger = logging.getLogger(__name__)


class CoinGeckoClient:
    """Fetch Top 500 universe metadata from CoinGecko."""
    BASE_URL = "https://api.coingecko.com/api/v3"
    TIMEOUT = 10

    def __init__(self, max_retries=3, retry_delay=1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _request(self, endpoint: str, params: dict = None) -> dict:
        """Execute request with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}"
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, params=params, timeout=self.TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {self.retry_delay}s: {e}")
                time.sleep(self.retry_delay)

    def fetch_top_500(self) -> list[TokenMetadata]:
        """
        Fetch Top 500 by market cap from CoinGecko.
        Paginate through all 500.
        """
        results = []
        per_page = 250
        pages_needed = 2  # 500 / 250

        for page in range(1, pages_needed + 1):
            logger.info(f"Fetching page {page}/{pages_needed}...")
            try:
                data = self._request("markets", {
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": per_page,
                    "page": page,
                    "sparkline": False,
                })
                for coin in data:
                    if coin["market_cap_rank"] and coin["market_cap_rank"] <= 500:
                        results.append(TokenMetadata(
                            symbol=coin["symbol"].upper(),
                            name=coin["name"],
                            source="coingecko",
                            timestamp=datetime.utcnow(),
                            market_cap=coin.get("market_cap"),
                            fdv=coin.get("fully_diluted_valuation"),
                            circulating_supply=coin.get("circulating_supply"),
                            total_supply=coin.get("total_supply"),
                            volume_24h=coin.get("total_volume"),
                            rank=coin.get("market_cap_rank"),
                        ))
                logger.info(f"Page {page} returned {len(data)} coins")
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                raise

        logger.info(f"Fetched {len(results)} tokens total")
        return results
