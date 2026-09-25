"""
Integration tests for DuckDB storage.

Phase 2: Test DuckDB schema, load, query, and PIT compatibility.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.data.storage.parquet import ParquetStorage
from src.data.storage.duckdb import DuckDBStore
from src.data.schemas.types import OHLCV, Provenance


class TestDuckDBStorage:
    """DuckDB storage and query tests."""

    @pytest.fixture
    def temp_parquet(self):
        """Create a temporary parquet file with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ParquetStorage(base_dir=tmpdir)

            base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            prov = Provenance(
                source="coingecko",
                provider="CoinGecko",
                endpoint="/test",
                retrieval_timestamp=now_utc,
                event_timestamp=base_ts,
                symbol="bitcoin",
                timeframe="1d",
                schema_version="1.0",
                data_version="2026-01-01",
                availability_timestamp=now_utc,
            )

            data = []
            price = 50000.0
            for i in range(5):
                ts = base_ts + timedelta(days=i)
                candle = OHLCV(
                    timestamp=ts,
                    open=price,
                    high=price + 500,
                    low=price - 500,
                    close=price + 100,
                    volume=1000000 * (i + 1),
                    provenance=prov,
                )
                data.append(candle)
                price += 200

            output_path = storage.write_ohlcv("bitcoin", "1d", data)
            yield output_path

    @pytest.fixture
    def duckdb_store(self):
        """Create temporary DuckDB instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            store = DuckDBStore(str(db_path))
            yield store
            store.close()

    def test_duckdb_schema_exists(self, duckdb_store):
        """DuckDB should initialize with ohlcv and metadata tables."""
        symbols = duckdb_store.get_symbols()
        # Should be empty initially
        assert symbols == []

    def test_load_parquet_succeeds(self, duckdb_store, temp_parquet):
        """Load parquet file into DuckDB."""
        duckdb_store.load_parquet(str(temp_parquet), "bitcoin", "1d")

        symbols = duckdb_store.get_symbols()
        assert "bitcoin" in symbols

    def test_load_parquet_nonexistent_raises(self, duckdb_store):
        """Loading non-existent file should raise error."""
        with pytest.raises(FileNotFoundError):
            duckdb_store.load_parquet("/nonexistent/path.parquet", "bitcoin", "1d")

    def test_get_candles_returns_data(self, duckdb_store, temp_parquet):
        """Query candles after loading."""
        duckdb_store.load_parquet(str(temp_parquet), "bitcoin", "1d")

        candles = duckdb_store.get_candles("bitcoin", "1d")
        assert len(candles) == 5
        assert candles[0]["symbol"] == "bitcoin"
        assert candles[0]["timeframe"] == "1d"

    def test_get_candles_empty_timeframe(self, duckdb_store):
        """Query non-existent timeframe returns empty."""
        candles = duckdb_store.get_candles("bitcoin", "1d")
        assert candles == []

    def test_get_price_range(self, duckdb_store, temp_parquet):
        """Price range aggregation works."""
        duckdb_store.load_parquet(str(temp_parquet), "bitcoin", "1d")

        price_range = duckdb_store.get_price_range("bitcoin", "1d")
        assert "min_price" in price_range
        assert "max_price" in price_range
        assert "avg_price" in price_range
        assert "candle_count" in price_range
        assert price_range["candle_count"] == 5

    def test_get_timeframes(self, duckdb_store, temp_parquet):
        """List available timeframes."""
        duckdb_store.load_parquet(str(temp_parquet), "bitcoin", "1d")

        timeframes = duckdb_store.get_timeframes("bitcoin")
        assert "1d" in timeframes

    def test_get_timeframes_all(self, duckdb_store, temp_parquet):
        """List all timeframes."""
        duckdb_store.load_parquet(str(temp_parquet), "bitcoin", "1d")

        timeframes = duckdb_store.get_timeframes()
        assert "1d" in timeframes

    def test_metadata_recorded(self, duckdb_store, temp_parquet):
        """Metadata should be recorded after load."""
        duckdb_store.load_parquet(str(temp_parquet), "bitcoin", "1d")

        # Query metadata
        result = duckdb_store.conn.execute(
            "SELECT record_count, source FROM data_metadata WHERE symbol = ? AND timeframe = ?",
            ["bitcoin", "1d"],
        ).fetchall()

        assert len(result) == 1
        assert result[0][0] == 5
        assert result[0][1] == "coingecko"  # Should be extracted from parquet metadata

    def test_duplicate_load_raises(self, duckdb_store, temp_parquet):
        """Loading same file twice raises constraint error (PRIMARY KEY prevents duplicates)."""
        duckdb_store.load_parquet(str(temp_parquet), "bitcoin", "1d")

        # Second load should fail due to PRIMARY KEY constraint
        import duckdb as db_module
        with pytest.raises(db_module.ConstraintException):
            duckdb_store.load_parquet(str(temp_parquet), "bitcoin", "1d")

    def test_contextmanager_closes(self, temp_parquet):
        """DuckDB store works as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            with DuckDBStore(str(db_path)) as store:
                store.load_parquet(str(temp_parquet), "bitcoin", "1d")
                candles = store.get_candles("bitcoin", "1d")
                assert len(candles) == 5
