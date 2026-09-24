import pytest
from datetime import datetime
from src.data.schema import OHLCVCandle, TokenMetadata


class TestOHLCVCandle:
    def test_valid_candle(self):
        candle = OHLCVCandle(
            symbol="BTCUSDT",
            source="binance",
            timeframe="daily",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            open=40000,
            high=42000,
            low=39000,
            close=41000,
            volume=1000,
        )
        assert candle.close == 41000
        assert candle.high >= candle.low

    def test_high_must_be_max(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OHLCVCandle(
                symbol="BTCUSDT",
                source="binance",
                timeframe="daily",
                timestamp=datetime(2024, 1, 1, 0, 0, 0),
                open=40000,
                high=38000,  # Lower than low!
                low=39000,
                close=41000,
                volume=1000,
            )

    def test_low_must_be_min(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OHLCVCandle(
                symbol="BTCUSDT",
                source="binance",
                timeframe="daily",
                timestamp=datetime(2024, 1, 1, 0, 0, 0),
                open=40000,
                high=42000,
                low=43000,  # Higher than high!
                close=41000,
                volume=1000,
            )

    def test_volume_can_be_zero(self):
        candle = OHLCVCandle(
            symbol="BTCUSDT",
            source="binance",
            timeframe="daily",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            open=40000,
            high=42000,
            low=39000,
            close=41000,
            volume=0,
        )
        assert candle.volume == 0

    def test_negative_prices_rejected(self):
        with pytest.raises(ValueError):
            OHLCVCandle(
                symbol="BTCUSDT",
                source="binance",
                timeframe="daily",
                timestamp=datetime(2024, 1, 1, 0, 0, 0),
                open=-40000,
                high=42000,
                low=39000,
                close=41000,
                volume=1000,
            )


class TestTokenMetadata:
    def test_valid_metadata(self):
        meta = TokenMetadata(
            symbol="BTC",
            name="Bitcoin",
            source="coingecko",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            market_cap=1000000000,
            fdv=1000000000,
            circulating_supply=21000000,
            total_supply=21000000,
            volume_24h=50000000,
            rank=1,
        )
        assert meta.symbol == "BTC"
        assert meta.rank == 1

    def test_none_market_cap_allowed(self):
        meta = TokenMetadata(
            symbol="BTC",
            name="Bitcoin",
            source="coingecko",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            market_cap=None,
        )
        assert meta.market_cap is None

    def test_zero_market_cap_becomes_none(self):
        meta = TokenMetadata(
            symbol="BTC",
            name="Bitcoin",
            source="coingecko",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            market_cap=0.0,
        )
        assert meta.market_cap is None

    def test_negative_market_cap_rejected(self):
        with pytest.raises(ValueError):
            TokenMetadata(
                symbol="BTC",
                name="Bitcoin",
                source="coingecko",
                timestamp=datetime(2024, 1, 1, 0, 0, 0),
                market_cap=-1000000,
            )
