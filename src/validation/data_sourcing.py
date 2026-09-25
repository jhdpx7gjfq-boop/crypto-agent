"""
Data sourcing pour validation Spring Detector.
Récupère BTC/USDT OHLCV depuis Binance ou yfinance.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BinanceDataSource:
    """Récupère données depuis Binance API."""

    @staticmethod
    def fetch(symbol="BTCUSDT", interval="1d", start_date="2020-01-01", end_date=None):
        """Fetch OHLCV data from Binance."""
        try:
            import ccxt
            exchange = ccxt.binance()

            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")

            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            ohlcv_data = []
            current = start_dt

            while current < end_dt:
                try:
                    candles = exchange.fetch_ohlcv(
                        symbol,
                        timeframe=interval,
                        since=exchange.parse8601(current.isoformat() + "T00:00:00Z")
                    )
                    if not candles:
                        break

                    ohlcv_data.extend(candles)
                    current = pd.to_datetime(candles[-1][0], unit="ms") + timedelta(days=1)

                    logger.info(f"Fetched {len(candles)} candles, current: {current.date()}")

                except Exception as e:
                    logger.error(f"Error fetching candles: {e}")
                    break

            if not ohlcv_data:
                logger.error("No data fetched from Binance")
                return None

            df = pd.DataFrame(
                ohlcv_data,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.sort_values("timestamp")
            df = df[~df["timestamp"].duplicated(keep='first')]
            df = df.reset_index(drop=True)

            logger.info(f"✅ Fetched {len(df)} candles from Binance ({start_date} to {end_date})")
            return df

        except ImportError:
            logger.error("ccxt not installed. Install: pip install ccxt")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch from Binance: {e}")
            return None


class YFinanceDataSource:
    """Fallback: Récupère données depuis yfinance."""

    @staticmethod
    def fetch(ticker="BTC-USD", start_date="2020-01-01", end_date=None):
        """Fetch data from yfinance."""
        try:
            import yfinance as yf

            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")

            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if df.empty:
                logger.error("No data from yfinance")
                return None

            # Handle MultiIndex columns from yfinance (single ticker gives simple cols)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Standardize column names (lowercase)
            df.columns = [c.lower() for c in df.columns]

            # Keep only required OHLCV columns
            required = ["open", "high", "low", "close", "volume"]
            available = [c for c in required if c in df.columns]
            df = df[available]

            # Add timestamp as column (detector expects it as column, not index)
            df["timestamp"] = df.index
            df = df[["timestamp"] + [c for c in df.columns if c != "timestamp"]]

            logger.info(f"✅ Fetched {len(df)} candles from yfinance ({start_date} to {end_date})")
            return df

        except ImportError:
            logger.error("yfinance not installed. Install: pip install yfinance")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch from yfinance: {e}")
            return None


class LocalDataSource:
    """Load data from local CSV file."""

    @staticmethod
    def load(filepath: str) -> pd.DataFrame:
        """Load OHLCV data from CSV."""
        try:
            df = pd.read_csv(filepath, parse_dates=["timestamp"])
            df = df.sort_values("timestamp")
            df = df.reset_index(drop=True)

            # Ensure columns
            required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
            for col in required_cols:
                if col not in df.columns:
                    logger.error(f"Missing column: {col}")
                    return None

            # Reorder columns
            df = df[required_cols]

            logger.info(f"✅ Loaded {len(df)} candles from {filepath}")
            return df

        except Exception as e:
            logger.error(f"Failed to load from CSV: {e}")
            return None


class DataValidator:
    """Vérifie la qualité des données."""

    @staticmethod
    def validate(df: pd.DataFrame) -> bool:
        """Valide les données pour Spring Detector."""

        if df is None or df.empty:
            logger.error("DataFrame is empty")
            return False

        # Check columns
        required = ["open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                logger.error(f"Missing column: {col}")
                return False

        # Check for NaN
        if df[required].isnull().any().any():
            logger.error("Found NaN values")
            return False

        # Check for duplicates
        if df.index.duplicated().any():
            logger.error("Found duplicate timestamps")
            return False

        # Check OHLC order
        invalid_ohlc = ((df["high"] < df["low"]) | (df["high"] < df["open"]) | (df["high"] < df["close"]))
        n_invalid = invalid_ohlc.astype(int).sum()
        if n_invalid > 0:
            logger.error(f"Invalid OHLC order ({int(n_invalid) if hasattr(n_invalid, '__int__') else n_invalid} rows)")
            return False

        # Check volume
        if (df["volume"] < 0).any():
            logger.error("Negative volume")
            return False

        logger.info(f"✅ Data validation passed ({len(df)} candles)")
        return True


def get_btc_data(source="binance", start_date="2021-01-01", end_date=None) -> pd.DataFrame:
    """
    Get BTC OHLCV data from preferred source.

    Args:
        source: "binance", "yfinance", or local path
        start_date: start date (YYYY-MM-DD)
        end_date: end date (YYYY-MM-DD)

    Returns:
        DataFrame with OHLCV data
    """
    df = None

    if source == "binance":
        logger.info("Fetching from Binance...")
        df = BinanceDataSource.fetch("BTCUSDT", "1d", start_date, end_date)

    elif source == "yfinance":
        logger.info("Fetching from yfinance...")
        df = YFinanceDataSource.fetch("BTC-USD", start_date, end_date)

    elif source.endswith(".csv"):
        logger.info(f"Loading from {source}...")
        df = LocalDataSource.load(source)

    else:
        logger.error(f"Unknown source: {source}")
        return None

    # Validate
    if df is not None and DataValidator.validate(df):
        return df

    return None


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    source = sys.argv[1] if len(sys.argv) > 1 else "binance"

    logger.info(f"Sourcing BTC data from: {source}")
    df = get_btc_data(source, start_date="2021-01-01")

    if df is not None:
        logger.info(f"\nData shape: {df.shape}")
        logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")
        logger.info(f"\nFirst rows:\n{df.head()}")
        logger.info(f"\nLast rows:\n{df.tail()}")
