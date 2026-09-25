"""Pytest fixtures for data and persistence layer tests."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.data.contracts import DataPoint, DataSourceType, RawDataBatch
from src.data.persistence import DuckDBStore
from src.utils.logging import get_logger


@pytest.fixture
def temp_db() -> Path:
    """Create temporary DuckDB database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def duckdb_store(temp_db: Path) -> DuckDBStore:
    """Create DuckDBStore instance with temp database."""
    store = DuckDBStore(temp_db)
    yield store
    store.close()


@pytest.fixture
def sample_datapoint() -> DataPoint:
    """Create sample DataPoint for testing."""
    from datetime import datetime

    return DataPoint(
        timestamp=datetime.utcnow(),
        value=65432.50,
        asset="BTC",
        currency="USD",
        source=DataSourceType.COINGECKO,
        source_version="1.0",
        metric="price",
        data_quality="raw",
    )


@pytest.fixture
def sample_batch(sample_datapoint: DataPoint) -> RawDataBatch:
    """Create sample RawDataBatch for testing."""
    return RawDataBatch(datapoints=[sample_datapoint])


@pytest.fixture
def mock_coingecko_response() -> Mock:
    """Create mock successful CoinGecko API response."""
    mock = Mock()
    mock.json.return_value = {"bitcoin": {"usd": 65000.0}}
    mock.raise_for_status.return_value = None
    return mock


@pytest.fixture
def logger():
    """Get test logger."""
    return get_logger(__name__, json_format=False)
