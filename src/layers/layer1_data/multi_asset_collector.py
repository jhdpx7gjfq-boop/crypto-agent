"""
Multi-Asset OHLCV Collector (Phase 2 Component 3)
Version: 1.0.0

Extends BinanceDataPortalCollector to support multiple assets.
Fetches OHLCV for BTC, ETH, SOL, and top 10 by market cap.
Integrates with feature store for Layer 1 storage.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import time

import pandas as pd

from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.core.models import OHLCV
from src.data.feature_store import FeatureStore

logger = logging.getLogger(__name__)

VERSION = "1.0.0"

# Phase 2: Multi-asset target list
DEFAULT_ASSETS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    # Top 10 by market cap (as of 2024)
    "LINK": "LINKUSDT",
    "DOGE": "DOGEUSDT",
    "ADA": "ADAUSDT",
    "MATIC": "MATICUSDT",
    "POLKADOT": "DOTUSDT",
    "TRX": "TRXUSDT",
    "XRP": "XRPUSDT",
}

# Rate limiting (Binance doesn't rate-limit data.binance.vision, but be respectful)
RATE_LIMIT_DELAY = 0.5  # seconds between requests


class MultiAssetCollector:
    """
    Collects OHLCV data for multiple assets from Binance Data Portal.

    Features:
    - Parallel asset fetching with rate limiting
    - Direct integration with FeatureStore
    - Configurable asset list
    - Data consistency validation
    - Comprehensive logging

    Phase 2 Requirements:
    - BTC (already validated in Phase 1)
    - ETH (Ethereum)
    - SOL (Solana)
    - Top 7 by market cap (LINK, DOGE, ADA, etc.)
    """

    def __init__(
        self,
        assets: Optional[Dict[str, str]] = None,
        feature_store: Optional[FeatureStore] = None,
        granularity: str = "1d",
    ):
        """
        Initialize multi-asset collector.

        Args:
            assets: Dict of {symbol: USDT_pair}. Defaults to DEFAULT_ASSETS.
            feature_store: FeatureStore instance for Layer 1 storage. If None, not used.
            granularity: Candle granularity (default "1d")
        """
        self.assets = assets or DEFAULT_ASSETS
        self.feature_store = feature_store
        self.granularity = granularity
        self.collectors = {
            symbol: BinanceDataPortalCollector(pair, granularity)
            for symbol, pair in self.assets.items()
        }
        self.results: Dict[str, pd.DataFrame] = {}

        logger.info(
            f"MultiAssetCollector initialized with {len(self.assets)} assets "
            f"(granularity: {granularity})"
        )

    def fetch_asset(
        self,
        symbol: str,
        start_year: int = 2020,
        start_month: int = 1,
        end_year: int = 2025,
        end_month: int = 12,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a single asset.

        Args:
            symbol: Asset symbol (e.g., "BTC", "ETH")
            start_year, start_month, end_year, end_month: Date range

        Returns:
            DataFrame with columns: open_time, open, high, low, close, volume
        """
        if symbol not in self.collectors:
            raise ValueError(f"Unknown symbol: {symbol}. Available: {list(self.collectors.keys())}")

        collector = self.collectors[symbol]
        logger.info(f"Fetching {symbol} ({collector.symbol}) from {start_year}-{start_month} to {end_year}-{end_month}")

        try:
            df = collector.download_and_parse(start_year, start_month, end_year, end_month)

            # Add symbol column
            df["symbol"] = symbol
            self.results[symbol] = df

            logger.info(f"✓ Fetched {symbol}: {len(df)} candles")
            return df

        except Exception as e:
            logger.error(f"✗ Failed to fetch {symbol}: {e}")
            raise

    def fetch_all(
        self,
        symbols: Optional[List[str]] = None,
        start_year: int = 2020,
        start_month: int = 1,
        end_year: int = 2025,
        end_month: int = 12,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for all or specified assets.

        Args:
            symbols: List of symbols to fetch. If None, fetch all.
            start_year, start_month, end_year, end_month: Date range

        Returns:
            Dict of {symbol: DataFrame}
        """
        symbols_to_fetch = symbols or list(self.assets.keys())

        logger.info(f"Fetching {len(symbols_to_fetch)} assets (rate limit: {RATE_LIMIT_DELAY}s)")

        for i, symbol in enumerate(symbols_to_fetch):
            try:
                self.fetch_asset(symbol, start_year, start_month, end_year, end_month)

                # Rate limiting
                if i < len(symbols_to_fetch) - 1:
                    time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                logger.warning(f"Skipping {symbol}: {e}")
                continue

        logger.info(f"✓ Fetch complete: {len(self.results)}/{len(symbols_to_fetch)} successful")
        return self.results

    def ingest_to_feature_store(
        self,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Ingest fetched data to feature store (Layer 1).

        Args:
            symbols: List of symbols to ingest. If None, ingest all fetched.

        Returns:
            Dict of {symbol: row_count}
        """
        if not self.feature_store:
            raise RuntimeError("FeatureStore not initialized")

        symbols_to_ingest = symbols or list(self.results.keys())
        ingested = {}

        logger.info(f"Ingesting {len(symbols_to_ingest)} assets to feature store...")

        for symbol in symbols_to_ingest:
            if symbol not in self.results:
                logger.warning(f"No data for {symbol}, skipping")
                continue

            df = self.results[symbol]

            # Prepare for feature store (rename timestamp column)
            df_store = df.copy()
            df_store["timestamp"] = pd.to_datetime(df_store["open_time"]).astype('int64') // 10**6
            df_store = df_store[["timestamp", "open", "high", "low", "close", "volume"]]

            try:
                row_count = self.feature_store.insert_layer1(symbol, df_store)
                ingested[symbol] = row_count
                logger.info(f"✓ Ingested {symbol}: {row_count} rows")

            except Exception as e:
                logger.error(f"✗ Failed to ingest {symbol}: {e}")
                continue

        return ingested

    def validate_data_consistency(self) -> Dict[str, Dict]:
        """
        Validate data quality for all fetched assets.

        Checks:
        - High >= max(open, close)
        - Low <= min(open, close)
        - High >= Low
        - All prices > 0
        - Volume >= 0
        - No gaps > threshold

        Returns:
            Dict of {symbol: {metric: value}}
        """
        validation_results = {}

        for symbol, df in self.results.items():
            issues = []

            # OHLC validity
            high_low_valid = (df["high"] >= df["low"]).all()
            high_oc = (df["high"] >= df[["open", "close"]].max(axis=1)).all()
            low_oc = (df["low"] <= df[["open", "close"]].min(axis=1)).all()

            if not (high_low_valid and high_oc and low_oc):
                issues.append("OHLC_validity_failed")

            # Price positivity
            prices_positive = (df[["open", "high", "low", "close"]] > 0).all().all()
            if not prices_positive:
                issues.append("Negative_prices")

            # Volume non-negative
            volume_ok = (df["volume"] >= 0).all()
            if not volume_ok:
                issues.append("Negative_volume")

            # Time gaps (rough check)
            if len(df) > 1:
                time_diffs = df["open_time"].diff().dt.total_seconds().dropna()
                expected_gap = 86400  # 1 day in seconds
                gap_violations = (time_diffs > expected_gap * 1.5).sum()
                if gap_violations > 0:
                    issues.append(f"Time_gaps: {gap_violations}")

            validation_results[symbol] = {
                "total_candles": len(df),
                "is_valid": len(issues) == 0,
                "issues": issues,
                "first_timestamp": df["open_time"].min() if len(df) > 0 else None,
                "last_timestamp": df["open_time"].max() if len(df) > 0 else None,
            }

            status = "✓" if len(issues) == 0 else "✗"
            logger.info(f"{status} {symbol}: {len(df)} candles, issues: {issues or 'none'}")

        return validation_results

    def get_stats(self) -> Dict[str, Dict]:
        """Get summary statistics for all fetched assets."""
        stats = {}

        for symbol, df in self.results.items():
            stats[symbol] = {
                "total_rows": len(df),
                "date_range": f"{df['open_time'].min()} to {df['open_time'].max()}",
                "price_min": df["close"].min(),
                "price_max": df["close"].max(),
                "volume_avg": df["volume"].mean(),
                "price_range": f"{df['close'].min():.2f} - {df['close'].max():.2f}",
            }

        return stats

    def export_summary(self) -> str:
        """Generate summary report of all assets."""
        stats = self.get_stats()

        report = f"""
{'='*70}
MULTI-ASSET COLLECTION SUMMARY
{'='*70}

Assets Fetched: {len(self.results)} / {len(self.assets)}

"""
        for symbol, stat in stats.items():
            report += f"\n{symbol}:\n"
            for key, val in stat.items():
                report += f"  {key:20s}: {val}\n"

        report += f"\n{'='*70}\n"
        return report
