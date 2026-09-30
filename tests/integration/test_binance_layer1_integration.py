"""Integration test: Binance collector + Layer 1 validation."""

import pytest
from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.core.models import OHLCV


class TestBinanceLayer1Integration:
    """Test Binance collector integration with Layer 1."""

    def test_binance_collector_initialization(self):
        """Test collector can be instantiated."""
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        assert collector.symbol == "BTCUSDT"
        assert collector.granularity == "1d"

    def test_month_url_generation(self):
        """Test URL generation for date ranges."""
        collector = BinanceDataPortalCollector()
        urls = collector.generate_month_urls(2020, 1, 2020, 3)

        assert len(urls) == 3
        assert urls[0][0] == "2020-01"
        assert urls[-1][0] == "2020-03"
        assert all("data.binance.vision" in url for _, url in urls)

    @pytest.mark.integration
    def test_binance_fetch_real_data(self):
        """
        Integration test: fetch real BTC data from Binance.

        Note: This test downloads actual data. Skip if no network.
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")

        # Fetch just 1 month for quick test
        ohlcv_list = collector.fetch(start_year=2025, start_month=1,
                                     end_year=2025, end_month=1)

        assert len(ohlcv_list) > 0, "Should fetch at least 1 candle"

        # Validate first candle
        first = ohlcv_list[0]
        assert isinstance(first, OHLCV)
        assert first.open > 0
        assert first.high >= first.low
        assert first.close > 0
        assert first.volume >= 0

    @pytest.mark.integration
    def test_binance_full_range_2020_2025(self):
        """
        Full integration: 2020-2025 complete dataset.
        Validates P0-DATA-PILOT expectations.
        """
        collector = BinanceDataPortalCollector()
        ohlcv_list = collector.fetch(start_year=2020, start_month=1,
                                     end_year=2025, end_month=12)

        # P0-DATA-PILOT: expected ~2192 candles (100% coverage)
        assert len(ohlcv_list) >= 2100, f"Expected ~2192, got {len(ohlcv_list)}"
        assert len(ohlcv_list) <= 2300, "Too many candles (likely duplicates)"

        # Check no NaN
        for ohlcv in ohlcv_list:
            assert ohlcv.open > 0
            assert ohlcv.high >= ohlcv.low
            assert ohlcv.close > 0

    def test_data_quality_constraints(self):
        """
        Test OHLCV constraints are preserved.
        - high >= max(open, close)
        - low <= min(open, close)
        - high >= low
        - all prices > 0
        """
        collector = BinanceDataPortalCollector()
        df = collector.download_and_parse(start_year=2025, start_month=1,
                                         end_year=2025, end_month=1)

        # Verify constraints
        assert (df['high'] >= df[['open', 'close']].max(axis=1)).all()
        assert (df['low'] <= df[['open', 'close']].min(axis=1)).all()
        assert (df['high'] >= df['low']).all()
        assert (df[['open', 'high', 'low', 'close']] > 0).all().all()
        assert (df['volume'] >= 0).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
