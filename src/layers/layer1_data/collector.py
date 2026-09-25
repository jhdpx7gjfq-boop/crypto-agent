"""Data collection from public sources (Layer 1)."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from src.core.models import OHLCV
from src.core.config import Config


logger = logging.getLogger(__name__)


class DataCollector:
    """
    Collects OHLCV data from public sources.

    Sources:
    - CoinGecko (free, no API key needed for basic access)
    - Binance public API (free, rate limited)
    - Local storage (Parquet fallback)
    """

    def __init__(self, use_mock: bool = False):
        self.config = Config
        self.use_mock = use_mock

    def fetch_coingecko(
        self,
        asset_id: str,
        days: int = 365,
        vs_currency: str = "usd"
    ) -> List[OHLCV]:
        """
        Fetch OHLCV from CoinGecko API.

        Args:
            asset_id: CoinGecko asset ID (e.g., 'bitcoin', 'ethereum')
            days: Number of days to fetch
            vs_currency: Quote currency (default USD)

        Returns:
            List of OHLCV candles
        """

        if self.use_mock:
            return self._generate_mock_ohlcv(asset_id, days)

        try:
            import requests
        except ImportError:
            logger.error("requests library required for API calls")
            return self._generate_mock_ohlcv(asset_id, days)

        url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/market_chart"
        params = {
            "vs_currency": vs_currency,
            "days": days,
            "interval": "daily",
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            prices = data.get("prices", [])
            if not prices:
                logger.warning(f"No price data from CoinGecko for {asset_id}")
                return []

            ohlcv_list = []
            for i, (timestamp_ms, close) in enumerate(prices):
                ts = datetime.fromtimestamp(timestamp_ms / 1000)

                # CoinGecko only gives close prices, approximate OHLC
                volatility = 0.02 if i == 0 else 0.01
                open_price = close * (1 - volatility)
                high_price = close * (1 + volatility)
                low_price = close * (1 - volatility)

                volume = 1e9  # Placeholder

                try:
                    ohlcv = OHLCV(
                        timestamp=ts,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close,
                        volume=volume,
                    )
                    ohlcv_list.append(ohlcv)
                except ValueError as e:
                    logger.warning(f"Invalid OHLCV at {ts}: {e}")
                    continue

            logger.info(f"Fetched {len(ohlcv_list)} candles from CoinGecko for {asset_id}")
            return ohlcv_list

        except Exception as e:
            logger.error(f"CoinGecko fetch failed: {e}")
            return self._generate_mock_ohlcv(asset_id, days)

    def fetch_binance(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1d",
        limit: int = 1000
    ) -> List[OHLCV]:
        """
        Fetch OHLCV from Binance public API (no auth needed).

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Candle interval (default '1d')
            limit: Number of candles (max 1000)

        Returns:
            List of OHLCV candles
        """

        if self.use_mock:
            return self._generate_mock_ohlcv(symbol, limit)

        try:
            import requests
        except ImportError:
            logger.error("requests library required for API calls")
            return self._generate_mock_ohlcv(symbol, limit)

        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            klines = resp.json()

            ohlcv_list = []
            for kline in klines:
                ts = datetime.fromtimestamp(kline[0] / 1000)
                open_price = float(kline[1])
                high_price = float(kline[2])
                low_price = float(kline[3])
                close_price = float(kline[4])
                volume = float(kline[7])

                try:
                    ohlcv = OHLCV(
                        timestamp=ts,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                    )
                    ohlcv_list.append(ohlcv)
                except ValueError as e:
                    logger.warning(f"Invalid OHLCV at {ts}: {e}")
                    continue

            logger.info(f"Fetched {len(ohlcv_list)} candles from Binance for {symbol}")
            return ohlcv_list

        except Exception as e:
            logger.error(f"Binance fetch failed: {e}")
            return self._generate_mock_ohlcv(symbol, limit)

    def fetch_local_parquet(self, filepath: str) -> List[OHLCV]:
        """Load OHLCV from local Parquet file."""
        try:
            import pandas as pd
            df = pd.read_parquet(filepath)
            ohlcv_list = []

            for _, row in df.iterrows():
                try:
                    ohlcv = OHLCV(
                        timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                    ohlcv_list.append(ohlcv)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping row: {e}")
                    continue

            logger.info(f"Loaded {len(ohlcv_list)} candles from {filepath}")
            return ohlcv_list

        except ImportError:
            logger.error("pandas required for Parquet read")
            return []
        except Exception as e:
            logger.error(f"Parquet read failed: {e}")
            return []

    @staticmethod
    def _generate_mock_ohlcv(
        symbol: str,
        count: int = 100
    ) -> List[OHLCV]:
        """Generate synthetic OHLCV for testing."""
        import random

        ohlcv_list = []
        current_price = 50000.0
        now = datetime.utcnow()

        for i in range(count):
            timestamp = now - timedelta(days=count - i)

            # Random walk
            change = random.uniform(-0.02, 0.03)
            current_price *= (1 + change)

            volatility = random.uniform(0.005, 0.02)
            open_price = current_price * (1 - volatility / 2)
            high_price = current_price * (1 + volatility)
            low_price = current_price * (1 - volatility)
            close_price = current_price
            volume = random.uniform(1e8, 5e9)

            try:
                ohlcv = OHLCV(
                    timestamp=timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                )
                ohlcv_list.append(ohlcv)
            except ValueError:
                continue

        logger.debug(f"Generated {len(ohlcv_list)} mock candles for {symbol}")
        return ohlcv_list


class DataStore:
    """Manages persistent storage of OHLCV data."""

    def __init__(self, store_dir: str = None):
        self.store_dir = store_dir or str(Config.RAW_DATA_DIR)

    def save_ohlcv_parquet(
        self,
        data: List[OHLCV],
        asset: str,
        filename: str = None
    ) -> str:
        """Save OHLCV list to Parquet file."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas required for Parquet save")
            return ""

        try:
            df = pd.DataFrame([
                {
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in data
            ])

            if filename is None:
                filename = f"{asset}_{datetime.utcnow().isoformat()}.parquet"

            filepath = f"{self.store_dir}/{filename}"
            df.to_parquet(filepath, index=False)

            logger.info(f"Saved {len(data)} candles to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Parquet save failed: {e}")
            return ""

    def save_ohlcv_json(
        self,
        data: List[OHLCV],
        asset: str,
        filename: str = None
    ) -> str:
        """Save OHLCV to JSON (human-readable)."""
        try:
            if filename is None:
                filename = f"{asset}_{datetime.utcnow().isoformat()}.json"

            filepath = f"{self.store_dir}/{filename}"
            serialized = [
                {
                    "timestamp": c.timestamp.isoformat(),
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in data
            ]

            with open(filepath, "w") as f:
                json.dump(serialized, f, indent=2)

            logger.info(f"Saved {len(data)} candles to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"JSON save failed: {e}")
            return ""
