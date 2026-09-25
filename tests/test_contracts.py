"""Tests for data contracts (schemas)."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.data.contracts import DataPoint, DataSourceType, RawDataBatch


class TestDataPoint:
    """Tests for DataPoint schema."""

    def test_datapoint_valid(self, sample_datapoint: DataPoint):
        """Test valid DataPoint creation."""
        assert sample_datapoint.asset == "BTC"
        assert sample_datapoint.value == 65432.50
        assert sample_datapoint.source == DataSourceType.COINGECKO
        assert sample_datapoint.timestamp is not None

    def test_datapoint_missing_required_field(self):
        """Test DataPoint validation on missing required field."""
        with pytest.raises(ValidationError) as exc_info:
            DataPoint(
                timestamp=datetime.utcnow(),
                value=65000,
                asset="BTC",
                # Missing 'source'
                metric="price",
            )
        assert "source" in str(exc_info.value)

    def test_datapoint_invalid_value_type(self):
        """Test DataPoint validation on invalid value type."""
        with pytest.raises(ValidationError):
            DataPoint(
                timestamp=datetime.utcnow(),
                value="not_a_number",  # Invalid type
                asset="BTC",
                source=DataSourceType.COINGECKO,
                metric="price",
            )

    def test_datapoint_defaults(self, sample_datapoint: DataPoint):
        """Test DataPoint default values."""
        assert sample_datapoint.currency == "USD"
        assert sample_datapoint.source_version == "1.0"
        assert sample_datapoint.data_quality == "raw"

    def test_datapoint_custom_currency(self):
        """Test DataPoint with custom currency."""
        point = DataPoint(
            timestamp=datetime.utcnow(),
            value=65000,
            asset="BTC",
            currency="EUR",
            source=DataSourceType.COINGECKO,
            metric="price",
        )
        assert point.currency == "EUR"

    def test_datapoint_json_serializable(self, sample_datapoint: DataPoint):
        """Test DataPoint can be serialized to JSON."""
        json_data = sample_datapoint.model_dump_json()
        assert "BTC" in json_data
        assert "coingecko" in json_data


class TestRawDataBatch:
    """Tests for RawDataBatch schema."""

    def test_batch_valid(self, sample_batch: RawDataBatch):
        """Test valid RawDataBatch creation."""
        assert len(sample_batch.datapoints) == 1
        assert sample_batch.ingestion_timestamp is not None

    def test_batch_multiple_points(self, sample_datapoint: DataPoint):
        """Test RawDataBatch with multiple data points."""
        points = [sample_datapoint, sample_datapoint]
        batch = RawDataBatch(datapoints=points)
        assert len(batch.datapoints) == 2

    def test_batch_min_length_one(self):
        """Test RawDataBatch requires at least one datapoint."""
        with pytest.raises(ValidationError):
            RawDataBatch(datapoints=[])

    def test_batch_ingestion_timestamp_auto(self):
        """Test RawDataBatch auto-sets ingestion_timestamp."""
        before = datetime.utcnow()
        point = DataPoint(
            timestamp=before,
            value=1000,
            asset="TEST",
            source=DataSourceType.COINGECKO,
            metric="test",
        )
        batch = RawDataBatch(datapoints=[point])
        after = datetime.utcnow()
        assert before <= batch.ingestion_timestamp <= after
