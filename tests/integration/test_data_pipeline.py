"""
Integration tests for data pipeline.

Phase 2: Test full flow datasource → validation → storage.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.data.adapters.coingecko import CoinGeckoAdapter
from src.data.storage.parquet import ParquetStorage
from src.data.schemas.types import OHLCV, Provenance


class TestDataPipeline:
    """End-to-end data pipeline tests."""

    @pytest.fixture
    def adapter(self):
        return CoinGeckoAdapter()

    @pytest.fixture
    def temp_storage(self):
        """Temporary storage for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ParquetStorage(base_dir=tmpdir)

    @pytest.fixture
    def mock_ohlcv_data(self):
        """Generate mock OHLCV data for testing without live API."""
        base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        prov = Provenance(
            source="coingecko",
            provider="CoinGecko",
            endpoint="/coins/{id}/market_chart/range",
            retrieval_timestamp=datetime.now(timezone.utc),
            event_timestamp=base_ts,
            symbol="bitcoin",
            timeframe="1d",
            schema_version="1.0",
            data_version="2026-01-01",
            availability_timestamp=datetime.now(timezone.utc),
        )

        data = []
        price = 50000.0
        for i in range(10):
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

        return data

    def test_full_pipeline_fetch_validate_store(self, adapter, temp_storage):
        """
        Full pipeline: fetch → validate → store.

        Note: This test hits live CoinGecko API.
        Skipped in CI without network access.
        """
        # Fetch
        end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=5)

        data = adapter.fetch_ohlcv("bitcoin", "1d", start, end)
        assert len(data) > 0, "No data fetched"

        # Validate
        adapter.validate_data(data)

        # Store
        output_path = temp_storage.write_ohlcv("bitcoin", "1d", data)
        assert output_path.exists(), "File not written"

        # Verify structure
        assert "coingecko" in str(output_path)
        assert "bitcoin" in str(output_path)
        assert "1d" in str(output_path)
        assert output_path.suffix == ".parquet"

    def test_parquet_write_creates_directories(self, temp_storage, mock_ohlcv_data):
        """Parquet writer should create nested directories."""
        output_path = temp_storage.write_ohlcv("ethereum", "1d", mock_ohlcv_data)

        # Check directory structure: provider/symbol/timeframe/date.parquet
        assert output_path.parent.name == "1d"  # timeframe
        assert output_path.parent.parent.name == "ethereum"  # symbol
        assert "coingecko" in str(output_path.parent.parent.parent)  # provider

    def test_parquet_preserves_ohlcv_values(self, temp_storage, mock_ohlcv_data):
        """Stored parquet should preserve OHLCV values."""
        original_close = mock_ohlcv_data[0].close
        original_volume = mock_ohlcv_data[0].volume

        output_path = temp_storage.write_ohlcv("bitcoin", "1d", mock_ohlcv_data)

        # Read back
        import pyarrow.parquet as pq

        table = pq.read_table(str(output_path))
        stored_close = table["close"][0].as_py()
        stored_volume = table["volume"][0].as_py()

        assert abs(stored_close - original_close) < 0.01
        assert abs(stored_volume - original_volume) < 1

    def test_parquet_metadata_preserved(self, temp_storage, mock_ohlcv_data):
        """Parquet metadata should include provenance info."""
        output_path = temp_storage.write_ohlcv("bitcoin", "1d", mock_ohlcv_data)

        # Read metadata
        import pyarrow.parquet as pq

        table = pq.read_table(str(output_path))
        metadata = table.schema.metadata

        assert metadata[b"provider"] == b"coingecko"
        assert metadata[b"symbol"] == b"bitcoin"
        assert metadata[b"timeframe"] == b"1d"
        assert b"first_timestamp" in metadata
        assert b"first_provenance" in metadata
