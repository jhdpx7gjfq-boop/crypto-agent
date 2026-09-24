import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd
from src.data.store import ParquetStore


class TestParquetStore:
    @pytest.fixture
    def temp_store(self):
        """Temporary store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ParquetStore(data_dir=tmpdir)

    def test_save_and_load_ohlcv(self, temp_store):
        df = pd.DataFrame({
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "source": ["binance", "binance"],
            "timeframe": ["daily", "daily"],
            "timestamp": [datetime(2024, 1, 1, 0, 0, 0), datetime(2024, 1, 2, 0, 0, 0)],
            "open": [40000, 41000],
            "high": [42000, 43000],
            "low": [39000, 40000],
            "close": [41000, 42000],
            "volume": [100, 110],
        })

        temp_store.save_ohlcv("BTCUSDT", "daily", df)
        loaded = temp_store.load_ohlcv("BTCUSDT", "daily")

        assert len(loaded) == 2
        assert loaded["close"].tolist() == [41000, 42000]

    def test_load_nonexistent_returns_empty(self, temp_store):
        loaded = temp_store.load_ohlcv("NONEXIST", "daily")
        assert len(loaded) == 0

    def test_save_metadata(self, temp_store):
        df = pd.DataFrame({
            "symbol": ["BTC", "ETH"],
            "name": ["Bitcoin", "Ethereum"],
            "source": ["coingecko", "coingecko"],
            "timestamp": [datetime(2024, 1, 1, 0, 0, 0), datetime(2024, 1, 1, 0, 0, 0)],
            "market_cap": [1000000000000, 500000000000],
            "fdv": [1000000000000, 500000000000],
            "circulating_supply": [21000000, 120000000],
            "total_supply": [21000000, 120000000],
            "volume_24h": [50000000000, 25000000000],
            "rank": [1, 2],
        })

        temp_store.save_metadata(df)
        loaded = temp_store.load_metadata()

        assert len(loaded) == 2
        assert loaded["symbol"].tolist() == ["BTC", "ETH"]

    def test_validate_no_duplicates(self, temp_store):
        df = pd.DataFrame({
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
            "source": ["binance", "binance", "binance"],
            "timeframe": ["daily", "daily", "daily"],
            "timestamp": [
                datetime(2024, 1, 1, 0, 0, 0),
                datetime(2024, 1, 2, 0, 0, 0),
                datetime(2024, 1, 2, 0, 0, 0),  # Duplicate
            ],
            "open": [40000, 41000, 41000],
            "high": [42000, 43000, 43000],
            "low": [39000, 40000, 40000],
            "close": [41000, 42000, 42000],
            "volume": [100, 110, 110],
        })

        assert not temp_store.validate_no_duplicates(df)

    def test_validate_monotonic_timestamps(self, temp_store):
        df_monotonic = pd.DataFrame({
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "timestamp": [
                datetime(2024, 1, 1, 0, 0, 0),
                datetime(2024, 1, 2, 0, 0, 0),
            ],
        })

        assert temp_store.validate_monotonic_timestamps(df_monotonic)

        df_not_monotonic = pd.DataFrame({
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "timestamp": [
                datetime(2024, 1, 2, 0, 0, 0),
                datetime(2024, 1, 1, 0, 0, 0),  # Going backwards
            ],
        })

        assert not temp_store.validate_monotonic_timestamps(df_not_monotonic)

    def test_missing_columns_raises(self, temp_store):
        df = pd.DataFrame({
            "symbol": ["BTCUSDT"],
            "timestamp": [datetime(2024, 1, 1, 0, 0, 0)],
            # Missing required columns
        })

        with pytest.raises(ValueError):
            temp_store.save_ohlcv("BTCUSDT", "daily", df)

    def test_save_sorts_by_timestamp(self, temp_store):
        df = pd.DataFrame({
            "symbol": ["BTCUSDT", "BTCUSDT"],
            "source": ["binance", "binance"],
            "timeframe": ["daily", "daily"],
            "timestamp": [
                datetime(2024, 1, 2, 0, 0, 0),  # Out of order
                datetime(2024, 1, 1, 0, 0, 0),
            ],
            "open": [41000, 40000],
            "high": [43000, 42000],
            "low": [40000, 39000],
            "close": [42000, 41000],
            "volume": [110, 100],
        })

        temp_store.save_ohlcv("BTCUSDT", "daily", df)
        loaded = temp_store.load_ohlcv("BTCUSDT", "daily")

        assert loaded["timestamp"].is_monotonic_increasing
        assert loaded["close"].tolist() == [41000, 42000]
