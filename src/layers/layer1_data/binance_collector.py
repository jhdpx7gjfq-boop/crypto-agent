"""Binance Data Portal collector for OHLCV data (Layer 1)."""

import logging
import zipfile
import io
from datetime import datetime
from typing import List, Tuple
from pathlib import Path

import requests
import pandas as pd

from src.core.models import OHLCV
from src.core.config import Config

logger = logging.getLogger(__name__)

BINANCE_VISION_BASE = "https://data.binance.vision/data/spot/monthly/klines"
TIMEOUT = 30


class BinanceDataPortalCollector:
    """
    Fetches OHLCV data from Binance Data Portal (data.binance.vision).

    Supports:
    - Monthly ZIP downloads (validated by P0-DATA-PILOT)
    - BTCUSDT 1d (production-ready)
    - Extensible to other symbols/granularities

    No CEX API, no authentication needed.
    """

    def __init__(self, symbol: str = "BTCUSDT", granularity: str = "1d"):
        self.config = Config
        self.symbol = symbol
        self.granularity = granularity
        self.base_url = f"{BINANCE_VISION_BASE}/{symbol}/{granularity}"

    def generate_month_urls(self, start_year: int, start_month: int,
                           end_year: int, end_month: int) -> List[Tuple[str, str]]:
        """Generate URLs for all months in range."""
        urls = []
        year, month = start_year, start_month

        while (year, month) <= (end_year, end_month):
            year_month = f"{year:04d}-{month:02d}"
            filename = f"{self.symbol}-{self.granularity}-{year_month}.zip"
            url = f"{self.base_url}/{filename}"
            urls.append((year_month, url))

            month += 1
            if month > 12:
                month = 1
                year += 1

        return urls

    def download_and_parse(self, start_year: int = 2020, start_month: int = 1,
                          end_year: int = 2025, end_month: int = 12) -> pd.DataFrame:
        """
        Download and parse OHLCV data for date range.

        Returns:
            DataFrame with columns: open_time, open, high, low, close, volume
        """
        urls = self.generate_month_urls(start_year, start_month, end_year, end_month)
        all_data = []
        missing_months = []

        logger.info(f"Downloading {len(urls)} months from Binance Data Portal...")

        for year_month, url in urls:
            try:
                response = requests.get(url, timeout=TIMEOUT, verify=False)

                if response.status_code == 404:
                    missing_months.append(year_month)
                    logger.warning(f"Missing: {year_month}")
                    continue

                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")

                # Extract and parse CSV
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                    if not csv_files:
                        raise ValueError(f"No CSV in {year_month}")

                    data = z.read(csv_files[0]).decode('utf-8')
                    all_data.append(data)
                    logger.debug(f"OK: {year_month}")

            except Exception as e:
                logger.error(f"Error {year_month}: {e}")
                continue

        if not all_data:
            raise ValueError("No data downloaded")

        # Parse
        binance_cols = [
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ]

        combined_csv = "\n".join(all_data)
        df = pd.read_csv(io.StringIO(combined_csv), header=None, names=binance_cols)

        # Convert timestamp to datetime
        df['open_time'] = pd.to_numeric(df['open_time'], errors='coerce')

        # Fix timestamps >1e15 (corrupted to microseconds)
        mask = df['open_time'] > 1e15
        if mask.any():
            df.loc[mask, 'open_time'] /= 1000
            logger.warning(f"Fixed {mask.sum()} corrupted timestamps")

        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', errors='coerce')

        # Convert OHLCV
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Clean
        df = df.dropna(subset=['open_time', 'open', 'high', 'low', 'close'])
        df = df.sort_values('open_time').reset_index(drop=True)

        logger.info(f"Parsed {len(df)} candles, {len(missing_months)} months missing")

        return df[['open_time', 'open', 'high', 'low', 'close', 'volume']]

    def to_ohlcv_list(self, df: pd.DataFrame) -> List[OHLCV]:
        """Convert DataFrame to OHLCV model list."""
        ohlcv_list = []

        for _, row in df.iterrows():
            ohlcv = OHLCV(
                timestamp=int(row['open_time'].timestamp() * 1000),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume'])
            )
            ohlcv_list.append(ohlcv)

        return ohlcv_list

    def fetch(self, start_year: int = 2020, start_month: int = 1,
              end_year: int = 2025, end_month: int = 12) -> List[OHLCV]:
        """
        Fetch OHLCV data and return as OHLCV objects.

        Args:
            start_year, start_month, end_year, end_month: Date range

        Returns:
            List of OHLCV objects
        """
        df = self.download_and_parse(start_year, start_month, end_year, end_month)
        return self.to_ohlcv_list(df)
