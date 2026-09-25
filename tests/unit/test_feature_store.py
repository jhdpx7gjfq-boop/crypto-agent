"""Unit tests for feature store."""

import pytest
from datetime import datetime

from src.utils.feature_store import FeatureVector, FeatureStore
from tests.fixtures.market_data import generate_mock_ohlcv, generate_accumulation_ohlcv


class TestFeatureVector:
    """Tests for FeatureVector dataclass."""

    def test_feature_vector_creation(self):
        """FeatureVector should store features correctly."""
        fv = FeatureVector(
            timestamp=datetime.utcnow(),
            asset="BTC",
            close=100.0,
            sma20=95.0,
            rsi14=50.0,
        )
        assert fv.asset == "BTC"
        assert fv.close == 100.0
        assert fv.sma20 == 95.0

    def test_feature_vector_to_dict(self):
        """Should serialize to dict."""
        fv = FeatureVector(
            timestamp=datetime.utcnow(),
            asset="ETH",
            close=2000.0,
            volatility20=0.02,
        )
        d = fv.to_dict()

        assert d["asset"] == "ETH"
        assert d["close"] == 2000.0
        assert isinstance(d["timestamp"], str)

    def test_feature_vector_from_dict(self):
        """Should deserialize from dict."""
        original = FeatureVector(
            timestamp=datetime.utcnow(),
            asset="SOL",
            close=150.0,
            rsi14=60.0,
        )
        d = original.to_dict()
        reconstructed = FeatureVector.from_dict(d)

        assert reconstructed.asset == original.asset
        assert reconstructed.close == original.close
        assert reconstructed.rsi14 == original.rsi14


class TestFeatureStore:
    """Tests for FeatureStore."""

    def test_feature_store_creation(self):
        """FeatureStore should initialize."""
        fs = FeatureStore()
        assert fs.store_path is not None

    def test_compute_features_basic(self):
        """Should compute features from OHLCV."""
        fs = FeatureStore()
        ohlcv = generate_accumulation_ohlcv(100)

        features = fs.compute_features("BTC", ohlcv)

        assert len(features) == len(ohlcv)
        assert features[-1].asset == "BTC"
        assert features[-1].close == ohlcv[-1].close

    def test_compute_features_sma(self):
        """SMA features should be computed."""
        fs = FeatureStore()
        ohlcv = generate_mock_ohlcv(100, start_price=100.0)

        features = fs.compute_features("BTC", ohlcv)

        # SMA20 should be computed starting at index 19
        assert features[19].sma20 is not None
        assert features[18].sma20 is None  # Before window

    def test_compute_features_rsi(self):
        """RSI should be computed."""
        fs = FeatureStore()
        ohlcv = generate_accumulation_ohlcv(50)

        features = fs.compute_features("BTC", ohlcv)

        # RSI14 should be computed from index 14
        assert any(f.rsi14 is not None for f in features), "RSI should have non-None values"
        assert all(0 <= f.rsi14 <= 100 for f in features if f.rsi14 is not None), "RSI should be 0-100"

    def test_compute_features_insufficient_data(self):
        """Should handle insufficient data gracefully."""
        fs = FeatureStore()
        short_data = generate_mock_ohlcv(10)  # Less than 50

        features = fs.compute_features("BTC", short_data)

        assert len(features) == 0, "Should return empty list for insufficient data"

    def test_compute_features_momentum(self):
        """Momentum should be computed when requested."""
        fs = FeatureStore()
        ohlcv = generate_mock_ohlcv(100)

        features_with_momentum = fs.compute_features("BTC", ohlcv, compute_momentum=True)
        assert any(f.momentum is not None for f in features_with_momentum), "Momentum should be computed"


class TestFeatureStoreComputation:
    """Tests for individual feature computations."""

    def test_sma_computation(self):
        """SMA should be correct."""
        ohlcv = generate_mock_ohlcv(50)
        sma = FeatureStore._compute_sma(ohlcv, 10)

        # Length should match OHLCV
        assert len(sma) == len(ohlcv)

        # First 9 should be None
        assert all(s is None for s in sma[:9])

        # From index 9 onwards should have values
        assert all(s is not None for s in sma[9:])

        # SMA[9] should be average of first 10 closes
        expected = sum(c.close for c in ohlcv[:10]) / 10
        assert sma[9] == pytest.approx(expected, abs=0.01)

    def test_rsi_bounds(self):
        """RSI should always be 0-100."""
        ohlcv = generate_accumulation_ohlcv(50)
        rsi = FeatureStore._compute_rsi(ohlcv, 14)

        # All non-None RSI values should be 0-100
        for r in rsi:
            if r is not None:
                assert 0 <= r <= 100, f"RSI {r} out of bounds"

    def test_volatility_increases_on_trending_data(self):
        """Volatility should increase on trending data."""
        bull = generate_mock_ohlcv(100, start_price=100.0, volatility=0.05)
        sideways = generate_mock_ohlcv(100, start_price=100.0, volatility=0.005)

        vol_bull = FeatureStore._compute_volatility(bull, 20)
        vol_sideways = FeatureStore._compute_volatility(sideways, 20)

        # Filter None values
        vol_bull_clean = [v for v in vol_bull if v is not None]
        vol_sideways_clean = [v for v in vol_sideways if v is not None]

        # Average volatility should be higher for bull
        if vol_bull_clean and vol_sideways_clean:
            assert sum(vol_bull_clean) / len(vol_bull_clean) > sum(vol_sideways_clean) / len(vol_sideways_clean)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
