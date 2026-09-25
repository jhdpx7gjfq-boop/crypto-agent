"""Tests for Feature Store."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.data.contracts import DataPoint, RawDataBatch
from src.feature_store.base import FeatureMetadata, FeatureSnapshot
from src.feature_store.duckdb_store import DuckDBFeatureStore


class TestDuckDBFeatureStore:
    """Tests for DuckDB Feature Store."""

    def test_init_creates_database(self, tmp_path: Path) -> None:
        """Test initialization creates database and schema."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        assert db_path.exists()
        store.close()

    def test_schema_initialization(self, tmp_path: Path) -> None:
        """Test schema tables are created."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        tables = store.conn.execute(
            "SELECT table_name FROM duckdb_tables()"
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "feature_snapshots" in table_names
        assert "feature_metadata" in table_names
        store.close()

    def test_ingest_raw_creates_snapshots(
        self, tmp_path: Path, sample_datapoint: DataPoint
    ) -> None:
        """Test ingest_raw creates feature snapshots from datapoints."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        batch = RawDataBatch(datapoints=[sample_datapoint])
        store.ingest_raw(batch)

        result = store.conn.execute(
            "SELECT COUNT(*) FROM feature_snapshots"
        ).fetchall()

        assert result[0][0] == 1
        store.close()

    def test_ingest_raw_empty_batch_raises(self, tmp_path: Path) -> None:
        """Test ingest_raw raises on empty batch."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        with pytest.raises(ValueError):
            store.ingest_raw(RawDataBatch(datapoints=[]))

        store.close()

    def test_compute_feature_returns_dataframe(
        self, tmp_path: Path, sample_datapoint: DataPoint
    ) -> None:
        """Test compute_feature returns DataFrame."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        batch = RawDataBatch(datapoints=[sample_datapoint])
        store.ingest_raw(batch)

        start = sample_datapoint.timestamp - timedelta(hours=1)
        end = sample_datapoint.timestamp + timedelta(hours=1)

        df = store.compute_feature("raw_price", "BTC", start, end)

        assert not df.empty
        assert "timestamp" in df.columns
        assert "value" in df.columns
        assert len(df) == 1
        store.close()

    def test_compute_feature_invalid_window_raises(self, tmp_path: Path) -> None:
        """Test compute_feature raises on invalid time window."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        start = datetime.now(UTC)
        end = start - timedelta(hours=1)

        with pytest.raises(ValueError):
            store.compute_feature("raw_price", "BTC", start, end)

        store.close()

    def test_persist_snapshot_creates_record(self, tmp_path: Path) -> None:
        """Test persist_snapshot creates feature snapshot."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        ts = datetime.now(UTC)
        snapshot = FeatureSnapshot(
            feature_name="test_feature",
            asset="BTC",
            timestamp=ts,
            value=42.0,
            compute_timestamp=ts,
        )

        store.persist_snapshot(snapshot)

        result = store.conn.execute(
            "SELECT COUNT(*) FROM feature_snapshots"
        ).fetchall()

        assert result[0][0] == 1
        store.close()

    def test_get_provenance_returns_metadata(self, tmp_path: Path) -> None:
        """Test get_provenance returns snapshot provenance."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        ts = datetime.now(UTC)
        snapshot = FeatureSnapshot(
            feature_name="test_feature",
            asset="BTC",
            timestamp=ts,
            value=42.0,
            compute_timestamp=ts,
            provenance={"source": "test", "version": "1.0"},
        )

        store.persist_snapshot(snapshot)
        prov = store.get_provenance("test_feature", "BTC", ts)

        assert prov["source"] == "test"
        assert "compute_timestamp" in prov
        store.close()

    def test_get_provenance_not_found_raises(self, tmp_path: Path) -> None:
        """Test get_provenance raises when snapshot not found."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        ts = datetime.now(UTC)

        with pytest.raises(ValueError):
            store.get_provenance("nonexistent", "BTC", ts)

        store.close()

    def test_register_feature_metadata(self, tmp_path: Path) -> None:
        """Test register_feature_metadata stores metadata."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        metadata = FeatureMetadata(
            feature_name="test_feature",
            description="Test feature",
            computation_spec={"method": "raw", "source": "coingecko"},
        )

        store.register_feature_metadata(metadata)

        result = store.conn.execute(
            "SELECT COUNT(*) FROM feature_metadata"
        ).fetchall()

        assert result[0][0] == 1
        store.close()

    def test_retrieve_features_with_lookback(
        self, tmp_path: Path, sample_datapoint: DataPoint
    ) -> None:
        """Test retrieve_features respects lookback period."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)

        batch = RawDataBatch(datapoints=[sample_datapoint])
        store.ingest_raw(batch)

        start = sample_datapoint.timestamp
        end = sample_datapoint.timestamp + timedelta(hours=1)
        lookback = timedelta(hours=2)

        features = store.retrieve_features(
            assets=["BTC"],
            features=["raw_price"],
            start_timestamp=start,
            end_timestamp=end,
            lookback=lookback,
        )

        assert "BTC" in features
        assert not features["BTC"].empty
        store.close()

    def test_close_closes_connection(self, tmp_path: Path) -> None:
        """Test close() closes database connection."""
        db_path = tmp_path / "test.db"
        store = DuckDBFeatureStore(db_path)
        store.close()

        with pytest.raises(Exception):  # noqa: B017
            store.conn.execute("SELECT 1")
