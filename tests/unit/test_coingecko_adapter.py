"""
Unit tests for CoinGecko adapter.

Phase 1: Test adapter interface and data validation.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.data.adapters.coingecko import CoinGeckoAdapter
from src.data.schemas.types import OHLCV, Provenance


class TestCoinGeckoAdapter:
    """CoinGecko adapter unit tests."""

    @pytest.fixture
    def adapter(self):
        return CoinGeckoAdapter(timeout_seconds=10)

    def test_get_name(self, adapter):
        """Adapter should identify itself."""
        assert adapter.get_name() == "coingecko"

    def test_symbol_mapping(self, adapter):
        """Symbol mapping should resolve known symbols."""
        assert adapter.SYMBOL_MAP["bitcoin"] == "bitcoin"
        assert adapter.SYMBOL_MAP["BTC"] == "bitcoin"
        assert adapter.SYMBOL_MAP["ethereum"] == "ethereum"

    def test_invalid_symbol_raises(self, adapter):
        """Unknown symbol should raise ValueError."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="Unknown symbol"):
            adapter.fetch_ohlcv("INVALID", "1d", start, end)

    def test_invalid_timeframe_raises(self, adapter):
        """Non-1d timeframe should raise ValueError in free tier."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="only '1d' timeframe"):
            adapter.fetch_ohlcv("bitcoin", "1h", start, end)

        with pytest.raises(ValueError, match="only '1d' timeframe"):
            adapter.fetch_ohlcv("bitcoin", "4h", start, end)

    def test_validate_data_rejects_invalid_ohlc_order(self, adapter):
        """OHLC ordering must satisfy L <= O,C <= H."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        prov = Provenance(
            source="test",
            provider="Test",
            endpoint="/test",
            retrieval_timestamp=ts,
            event_timestamp=ts,
            symbol="BTC",
            timeframe="1d",
            schema_version="1.0",
            data_version="2025-01-01",
        )

        # Invalid: Open > High
        invalid_candle = OHLCV(
            timestamp=ts,
            open=105.0,
            high=100.0,
            low=100.0,
            close=102.0,
            volume=1000.0,
            provenance=prov,
        )

        with pytest.raises(ValueError, match="not between L and H"):
            adapter.validate_data([invalid_candle])

    def test_validate_data_rejects_negative_volume(self, adapter):
        """Volume must be non-negative."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        prov = Provenance(
            source="test",
            provider="Test",
            endpoint="/test",
            retrieval_timestamp=ts,
            event_timestamp=ts,
            symbol="BTC",
            timeframe="1d",
            schema_version="1.0",
            data_version="2025-01-01",
        )

        invalid_candle = OHLCV(
            timestamp=ts,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=-1000.0,  # Negative
            provenance=prov,
        )

        with pytest.raises(ValueError, match="Negative volume"):
            adapter.validate_data([invalid_candle])

    def test_validate_data_rejects_non_monotonic_timestamps(self, adapter):
        """Timestamps must be strictly increasing."""
        ts1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
        ts3 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # Out of order

        prov = Provenance(
            source="test",
            provider="Test",
            endpoint="/test",
            retrieval_timestamp=ts1,
            event_timestamp=ts1,
            symbol="BTC",
            timeframe="1d",
            schema_version="1.0",
            data_version="2025-01-01",
        )

        candles = [
            OHLCV(ts1, 100, 105, 95, 102, 1000, prov),
            OHLCV(ts2, 102, 110, 100, 108, 1500, prov),
            OHLCV(ts3, 108, 112, 106, 110, 1200, prov),  # Out of order
        ]

        with pytest.raises(ValueError, match="Non-monotonic timestamp"):
            adapter.validate_data(candles)

    def test_validate_data_accepts_valid_candles(self, adapter):
        """Valid candles should pass validation."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        prov = Provenance(
            source="test",
            provider="Test",
            endpoint="/test",
            retrieval_timestamp=ts,
            event_timestamp=ts,
            symbol="BTC",
            timeframe="1d",
            schema_version="1.0",
            data_version="2025-01-01",
        )

        candle = OHLCV(
            timestamp=ts,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
            provenance=prov,
        )

        assert adapter.validate_data([candle]) is True

    def test_validate_empty_list(self, adapter):
        """Empty list should be valid."""
        assert adapter.validate_data([]) is True
