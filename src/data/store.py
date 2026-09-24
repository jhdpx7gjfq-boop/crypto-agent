import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class ParquetStore:
    """Local Parquet storage for OHLCV and metadata."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.ohlcv_dir = self.data_dir / "ohlcv"
        self.metadata_dir = self.data_dir / "metadata"
        self.ohlcv_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def save_ohlcv(self, symbol: str, timeframe: str, df: pd.DataFrame) -> Path:
        """Save OHLCV DataFrame to Parquet."""
        # Ensure columns
        required_cols = ["symbol", "source", "timeframe", "timestamp", "open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns. Got: {df.columns.tolist()}")

        # Validate timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Sort by timestamp
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Save
        path = self.ohlcv_dir / f"{symbol}_{timeframe}.parquet"
        df.to_parquet(path, index=False, compression="snappy")
        logger.info(f"Saved {len(df)} candles to {path}")
        return path

    def load_ohlcv(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load OHLCV DataFrame from Parquet."""
        path = self.ohlcv_dir / f"{symbol}_{timeframe}.parquet"
        if not path.exists():
            logger.warning(f"File not found: {path}")
            return pd.DataFrame()
        df = pd.read_parquet(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def save_metadata(self, df: pd.DataFrame) -> Path:
        """Save universe metadata to Parquet."""
        # Validate
        required_cols = ["symbol", "name", "source", "timestamp"]
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns. Got: {df.columns.tolist()}")

        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        path = self.metadata_dir / "universe.parquet"
        df.to_parquet(path, index=False, compression="snappy")
        logger.info(f"Saved {len(df)} metadata records to {path}")
        return path

    def load_metadata(self) -> pd.DataFrame:
        """Load universe metadata from Parquet."""
        path = self.metadata_dir / "universe.parquet"
        if not path.exists():
            logger.warning(f"File not found: {path}")
            return pd.DataFrame()
        df = pd.read_parquet(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def validate_no_duplicates(self, df: pd.DataFrame, key_cols: list[str] = None) -> bool:
        """Check for duplicate candles (same symbol/timeframe/timestamp)."""
        if key_cols is None:
            key_cols = ["symbol", "timeframe", "timestamp"]
        duplicates = df.duplicated(subset=key_cols, keep=False)
        if duplicates.any():
            logger.warning(f"Found {duplicates.sum()} duplicate rows")
            return False
        return True

    def validate_monotonic_timestamps(self, df: pd.DataFrame) -> bool:
        """Check timestamps are strictly increasing."""
        if df.empty:
            return True
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        is_monotonic = df["timestamp"].is_monotonic_increasing
        if not is_monotonic:
            logger.warning("Timestamps are not strictly monotonic increasing")
            return False
        return True
