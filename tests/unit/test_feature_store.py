"""Unit tests for FeatureStore."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from unittest.mock import Mock, MagicMock

from src.layers.layer2_features.store import FeatureStore
from src.layers.layer2_features.contract import RSI_14, SMA_20, EMA_12, MACD_LINE, BB_WIDTH, VOLATILITY_HV
from src.data.schemas.types import OHLCV, Provenance


@pytest.fixture
def temp_db():
    """Create temporary DuckDB for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        from src.data.storage.duckdb import DuckDBStore
        with DuckDBStore(db_path) as store:
            yield store


@pytest.fixture
def feature_store(temp_db):
    """Create FeatureStore with temporary DB."""
    store = FeatureStore(temp_db)
    store.register_contract(RSI_14)
    store.register_contract(SMA_20)
    store.register_contract(EMA_12)
    store.register_contract(MACD_LINE)
    store.register_contract(BB_WIDTH)
    store.register_contract(VOLATILITY_HV)
    return store


@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV data."""
    data = []
    base_price = 100.0
    for i in range(50):
        close = base_price + i * 0.5
        data.append(
            OHLCV(
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() + i * 86400,
                open=close - 0.2,
                high=close + 0.5,
                low=close - 0.5,
                close=close,
                volume=1000000 + i * 10000,
            )
        )
    return data


class TestFeatureStore:
    def test_register_contract(self, feature_store):
        """Test contract registration."""
        assert RSI_14.name in feature_store.contracts
        assert feature_store.contracts[RSI_14.name] == RSI_14

    def test_get_feature_info(self, feature_store):
        """Test retrieving feature info."""
        info = feature_store.get_feature_info("rsi_14")
        assert info is not None
        assert info.name == "rsi_14"
        assert info.version == "1.0"

    def test_register_unknown_contract(self, feature_store):
        """Test registering custom contract."""
        from dataclasses import dataclass
        from src.layers.layer2_features.contract import FeatureContract

        custom = FeatureContract(
            name="test_feature",
            version="1.0",
            source="test",
            timestamp_semantics="bar-close",
            lookback_bars=5,
            parameters={},
            dtype="float",
            valid_range=(0.0, 100.0),
            missing_policy="forward_fill",
            calculation="Test feature",
        )
        feature_store.register_contract(custom)
        assert feature_store.get_feature_info("test_feature") is not None

    def test_validate_feature_rsi(self, feature_store):
        """Test RSI validation against contract."""
        values = [None] * 14 + [45.0, 50.0, 55.0, 60.0]
        is_valid, invalid = feature_store.validate_feature("rsi_14", values)
        assert is_valid or len(invalid) <= 14

    def test_validate_feature_with_out_of_range(self, feature_store):
        """Test validation detects out-of-range values."""
        values = [50.0, 60.0, 150.0, 40.0]
        is_valid, invalid = feature_store.validate_feature("rsi_14", values)
        assert not is_valid
        assert 2 in invalid

    def test_calculate_feature_requires_data(self, feature_store):
        """Test feature calculation fails without data."""
        with pytest.raises(ValueError, match="No data"):
            feature_store.calculate_feature("BTC", "1d", "rsi_14")

    def test_unknown_feature_name(self, feature_store):
        """Test unknown feature raises error."""
        with pytest.raises(ValueError, match="Unknown feature"):
            feature_store.calculate_feature("BTC", "1d", "unknown_feature")

    def test_unknown_contract_for_validation(self, feature_store):
        """Test validation with unknown contract raises error."""
        with pytest.raises(ValueError, match="Unknown feature"):
            feature_store.validate_feature("unknown", [1.0, 2.0])

    def test_feature_store_with_mock_data(self, feature_store):
        """Test feature calculation with mocked OHLCV data."""
        mock_data = [
            {"timestamp": 0, "close": 100.0, "high": 101.0, "low": 99.0, "open": 100.0, "volume": 1e6},
            {"timestamp": 1, "close": 101.0, "high": 102.0, "low": 100.0, "open": 100.0, "volume": 1e6},
            {"timestamp": 2, "close": 102.0, "high": 103.0, "low": 101.0, "open": 101.0, "volume": 1e6},
        ]

        feature_store.ohlcv_data.get_candles = Mock(return_value=mock_data * 10)

        result = feature_store.calculate_feature("BTC", "1d", "rsi_14")

        assert "values" in result
        assert "timestamps" in result
        assert "closes" in result
        assert len(result["values"]) == 30

    def test_feature_result_structure(self, feature_store):
        """Test calculate_feature returns correct structure."""
        mock_data = [
            {"timestamp": 0, "close": 100.0 + i, "high": 101.0 + i, "low": 99.0 + i, "open": 100.0 + i, "volume": 1e6}
            for i in range(50)
        ]
        feature_store.ohlcv_data.get_candles = Mock(return_value=mock_data)

        result = feature_store.calculate_feature("BTC", "1d", "sma_20")

        assert result["symbol"] == "BTC"
        assert result["timeframe"] == "1d"
        assert result["feature_name"] == "sma_20"
        assert len(result["values"]) == 50
        assert len(result["timestamps"]) == 50
        assert len(result["closes"]) == 50

    def test_sma_feature_calculation(self, feature_store):
        """Test SMA feature calculation."""
        mock_data = [
            {"timestamp": i, "close": 100.0, "high": 101.0, "low": 99.0, "open": 100.0, "volume": 1e6}
            for i in range(50)
        ]
        feature_store.ohlcv_data.get_candles = Mock(return_value=mock_data)

        result = feature_store.calculate_feature("BTC", "1d", "sma_20")

        assert result["feature_name"] == "sma_20"
        assert all(v is None or v == 100.0 for v in result["values"][19:])

    def test_rsi_feature_calculation(self, feature_store):
        """Test RSI feature calculation."""
        closes = [100.0 + i * 0.5 for i in range(50)]
        mock_data = [
            {"timestamp": i, "close": c, "high": c + 1, "low": c - 1, "open": c, "volume": 1e6}
            for i, c in enumerate(closes)
        ]
        feature_store.ohlcv_data.get_candles = Mock(return_value=mock_data)

        result = feature_store.calculate_feature("BTC", "1d", "rsi_14")

        assert result["feature_name"] == "rsi_14"
        assert all(v is None or 0 <= v <= 100 for v in result["values"][14:])

    def test_macd_feature_calculation(self, feature_store):
        """Test MACD feature calculation."""
        closes = [100.0 + i * 0.5 for i in range(50)]
        mock_data = [
            {"timestamp": i, "close": c, "high": c + 1, "low": c - 1, "open": c, "volume": 1e6}
            for i, c in enumerate(closes)
        ]
        feature_store.ohlcv_data.get_candles = Mock(return_value=mock_data)

        result = feature_store.calculate_feature("BTC", "1d", "macd_line")

        assert result["feature_name"] == "macd_line"
        assert len(result["values"]) == 50

    def test_bb_width_feature_calculation(self, feature_store):
        """Test Bollinger Band width calculation."""
        closes = [100.0 + i * 0.5 for i in range(50)]
        mock_data = [
            {"timestamp": i, "close": c, "high": c + 1, "low": c - 1, "open": c, "volume": 1e6}
            for i, c in enumerate(closes)
        ]
        feature_store.ohlcv_data.get_candles = Mock(return_value=mock_data)

        result = feature_store.calculate_feature("BTC", "1d", "bb_width")

        assert result["feature_name"] == "bb_width"
        assert all(v is None or v >= 0 for v in result["values"][19:])

    def test_volatility_feature_calculation(self, feature_store):
        """Test Historical Volatility calculation."""
        closes = [100.0 + i * 0.5 for i in range(50)]
        mock_data = [
            {"timestamp": i, "close": c, "high": c + 1, "low": c - 1, "open": c, "volume": 1e6}
            for i, c in enumerate(closes)
        ]
        feature_store.ohlcv_data.get_candles = Mock(return_value=mock_data)

        result = feature_store.calculate_feature("BTC", "1d", "volatility_hv")

        assert result["feature_name"] == "volatility_hv"
        assert all(v is None or v >= 0 for v in result["values"][20:])
