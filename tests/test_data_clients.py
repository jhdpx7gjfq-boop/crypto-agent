import pytest
from datetime import datetime
from unittest.mock import patch, Mock
from src.data.binance_client import BinanceClient
from src.data.coingecko_client import CoinGeckoClient


class TestBinanceClient:
    def test_fetch_ohlcv_basic(self):
        client = BinanceClient()
        klines_response = [
            [1704067200000, "40000", "42000", "39000", "41000", "100", "1704153600000", "4100000"],
            [1704153600000, "41000", "43000", "40000", "42000", "110", "1704240000000", "4620000"],
        ]

        with patch.object(client, "_request", return_value=klines_response):
            candles = client.fetch_ohlcv("BTCUSDT", timeframe="daily", limit=2)
            assert len(candles) == 2
            assert candles[0].close == 41000
            assert candles[1].close == 42000
            assert candles[0].timestamp < candles[1].timestamp

    def test_ohlcv_sorted_by_timestamp(self):
        client = BinanceClient()
        # Return klines in reverse order
        klines_response = [
            [1704153600000, "41000", "43000", "40000", "42000", "110", "1704240000000", "4620000"],
            [1704067200000, "40000", "42000", "39000", "41000", "100", "1704153600000", "4100000"],
        ]

        with patch.object(client, "_request", return_value=klines_response):
            candles = client.fetch_ohlcv("BTCUSDT", timeframe="daily", limit=2)
            # Should be sorted by timestamp
            assert candles[0].timestamp < candles[1].timestamp

    def test_unsupported_timeframe_raises(self):
        client = BinanceClient()
        with pytest.raises(ValueError):
            client.fetch_ohlcv("BTCUSDT", timeframe="invalid")

    def test_to_dataframe(self):
        client = BinanceClient()
        from src.data.schema import OHLCVCandle
        candles = [
            OHLCVCandle(
                symbol="BTCUSDT",
                source="binance",
                timeframe="daily",
                timestamp=datetime(2024, 1, 1, 0, 0, 0),
                open=40000,
                high=42000,
                low=39000,
                close=41000,
                volume=100,
            ),
            OHLCVCandle(
                symbol="BTCUSDT",
                source="binance",
                timeframe="daily",
                timestamp=datetime(2024, 1, 2, 0, 0, 0),
                open=41000,
                high=43000,
                low=40000,
                close=42000,
                volume=110,
            ),
        ]

        df = client.to_dataframe(candles)
        assert len(df) == 2
        assert list(df.columns) == ["symbol", "source", "timeframe", "timestamp", "open", "high", "low", "close", "volume"]
        assert df["timestamp"].is_monotonic_increasing


class TestCoinGeckoClient:
    def test_fetch_top_500_basic(self):
        client = CoinGeckoClient()

        page1_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "market_cap": 1000000000000,
                "market_cap_rank": 1,
                "fully_diluted_valuation": 1000000000000,
                "circulating_supply": 21000000,
                "total_supply": 21000000,
                "total_volume": 50000000000,
            },
        ]
        page2_response = []

        with patch.object(client, "_request") as mock_request:
            mock_request.side_effect = [page1_response, page2_response]
            results = client.fetch_top_500()
            assert len(results) == 1
            assert results[0].symbol == "BTC"
            assert results[0].rank == 1

    def test_fetch_top_500_filters_by_rank(self):
        client = CoinGeckoClient()

        page1_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "market_cap": 1000000000000,
                "market_cap_rank": 1,
                "fully_diluted_valuation": 1000000000000,
                "circulating_supply": 21000000,
                "total_supply": 21000000,
                "total_volume": 50000000000,
            },
        ]
        page2_response = [
            {
                "id": "token999",
                "symbol": "t999",
                "name": "Token 999",
                "market_cap": 1000000,
                "market_cap_rank": 999,  # Should be filtered out
                "fully_diluted_valuation": 1000000,
                "circulating_supply": 1000000000,
                "total_supply": 1000000000,
                "total_volume": 100000,
            },
        ]

        with patch.object(client, "_request") as mock_request:
            mock_request.side_effect = [page1_response, page2_response]
            results = client.fetch_top_500()
            assert len(results) == 1
            assert results[0].rank == 1
