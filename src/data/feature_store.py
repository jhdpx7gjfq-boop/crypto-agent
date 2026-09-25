"""
Feature Store - Layer 1 Data Processing
Version: 1.0.0

OHLCV ingestion → Technical indicators → Parquet storage
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import duckdb
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


class FeatureStore:
    def __init__(self, db_path: str = "data/features.duckdb"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(self.db_path)
        self._init_schema()
        logger.info(f"FeatureStore initialized (v{VERSION})")

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                coin_id VARCHAR,
                timestamp TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                market_cap DOUBLE,
                PRIMARY KEY (coin_id, timestamp)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                coin_id VARCHAR,
                timestamp TIMESTAMP,
                rsi14 DOUBLE,
                sma20 DOUBLE,
                sma50 DOUBLE,
                bb_upper DOUBLE,
                bb_lower DOUBLE,
                atr14 DOUBLE,
                volume_sma DOUBLE,
                PRIMARY KEY (coin_id, timestamp)
            )
        """)

    def ingest_ohlcv(self, coin_id: str, df: pd.DataFrame) -> None:
        """Ingest OHLCV data from DataFrame."""
        df = df.copy()
        df["coin_id"] = coin_id
        df = df[["coin_id", "timestamp", "open", "high", "low", "close", "volume", "market_cap"]]

        self.conn.execute("INSERT OR REPLACE INTO ohlcv SELECT * FROM df")
        logger.info(f"Ingested {len(df)} candles for {coin_id}")

    def calculate_indicators(self, coin_id: str, lookback: int = 90) -> pd.DataFrame:
        """Calculate technical indicators for a coin."""
        query = f"""
            SELECT * FROM ohlcv
            WHERE coin_id = '{coin_id}'
            ORDER BY timestamp DESC
            LIMIT {lookback}
        """
        df = self.conn.execute(query).fetch_df()
        df = df.sort_values("timestamp").reset_index(drop=True)

        if len(df) < 14:
            logger.warning(f"Not enough data for {coin_id}: {len(df)} < 14")
            return df

        # RSI(14)
        df["rsi14"] = self._calculate_rsi(df["close"], 14)

        # SMAs
        df["sma20"] = df["close"].rolling(20).mean()
        df["sma50"] = df["close"].rolling(50).mean()

        # Bollinger Bands(20, 2)
        sma = df["close"].rolling(20).mean()
        std = df["close"].rolling(20).std()
        df["bb_upper"] = sma + (2 * std)
        df["bb_lower"] = sma - (2 * std)

        # ATR(14)
        df["atr14"] = self._calculate_atr(df, 14)

        # Volume SMA
        df["volume_sma"] = df["volume"].rolling(20).mean()

        return df

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR indicator."""
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr

    def save_indicators(self, coin_id: str, indicators_df: pd.DataFrame) -> None:
        """Save calculated indicators to database."""
        indicators_df = indicators_df[["coin_id", "timestamp", "rsi14", "sma20", "sma50", "bb_upper", "bb_lower", "atr14", "volume_sma"]].copy()
        indicators_df = indicators_df.dropna()

        self.conn.execute("INSERT OR REPLACE INTO indicators SELECT * FROM indicators_df")
        logger.info(f"Saved {len(indicators_df)} indicator rows for {coin_id}")

    def export_parquet(self, coin_id: str, output_path: str, days: int = 365) -> None:
        """Export coin data to Parquet."""
        query = f"""
            SELECT
                o.coin_id, o.timestamp, o.open, o.high, o.low, o.close, o.volume, o.market_cap,
                i.rsi14, i.sma20, i.sma50, i.bb_upper, i.bb_lower, i.atr14, i.volume_sma
            FROM ohlcv o
            LEFT JOIN indicators i ON o.coin_id = i.coin_id AND o.timestamp = i.timestamp
            WHERE o.coin_id = '{coin_id}'
            AND o.timestamp >= NOW() - INTERVAL '{days}' DAY
            ORDER BY o.timestamp DESC
        """

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn.execute(f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)")
        logger.info(f"Exported {coin_id} to {output_path}")

    def get_latest(self, coin_id: str, limit: int = 10) -> pd.DataFrame:
        """Get latest rows with indicators."""
        query = f"""
            SELECT
                o.coin_id, o.timestamp, o.open, o.high, o.low, o.close, o.volume, o.market_cap,
                i.rsi14, i.sma20, i.sma50, i.bb_upper, i.bb_lower, i.atr14, i.volume_sma
            FROM ohlcv o
            LEFT JOIN indicators i ON o.coin_id = i.coin_id AND o.timestamp = i.timestamp
            WHERE o.coin_id = '{coin_id}'
            ORDER BY o.timestamp DESC
            LIMIT {limit}
        """
        return self.conn.execute(query).fetch_df()

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from src.data.coingecko_collector import CoinGeckoCollector

    # Test flow
    collector = CoinGeckoCollector()
    store = FeatureStore()

    # Fetch data
    print("=== Fetching BTC data ===")
    btc_df = collector.get_market_chart("bitcoin", days=90)
    btc_df["coin_id"] = "bitcoin"

    # Ingest
    store.ingest_ohlcv("bitcoin", btc_df)

    # Calculate indicators
    print("=== Calculating indicators ===")
    btc_with_indicators = store.calculate_indicators("bitcoin")
    print(btc_with_indicators[["timestamp", "close", "rsi14", "sma20", "sma50"]].tail())

    # Save indicators
    store.save_indicators("bitcoin", btc_with_indicators)

    # Export
    print("=== Exporting to Parquet ===")
    store.export_parquet("bitcoin", "data/bitcoin_features.parquet", days=90)

    store.close()
    print("✓ Feature Store test complete")
