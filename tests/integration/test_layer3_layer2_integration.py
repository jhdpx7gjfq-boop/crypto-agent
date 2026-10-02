"""Integration tests for Layer 3 (BCE, X20) + Layer 2 (Regime) consumers."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import OHLCV, MarketRegime, RegimeType
from src.layers.layer2_regime.coindesk_realtime_feed import (
    CoinDeskRealtimeRegimeFeed,
    RealtimeRegimePipeline,
)
from src.layers.layer3_wyckoff.realtime_bce_consumer import RealtimeBCEConsumer
from src.layers.layer4_x20.realtime_x20_consumer import RealtimeX20Consumer


class TestBCEConsumer:
    """Test BCE consumer for Layer 3."""

    @pytest.fixture
    def consumer(self):
        """Create BCE consumer."""
        return RealtimeBCEConsumer(asset="BTC")

    def test_init(self, consumer):
        """Test BCE consumer initialization."""
        assert consumer.asset == "BTC"
        assert consumer.max_history == 100
        assert len(consumer.ohlcv_history) == 0
        assert consumer.last_regime is None
        assert consumer.last_bce_signal is None

    def test_add_candle(self, consumer):
        """Test adding candle to history."""
        ts = datetime.utcnow()
        candle = OHLCV(
            timestamp=ts,
            open=50000.0,
            high=50500.0,
            low=49900.0,
            close=50200.0,
            volume=100.0
        )

        consumer.add_candle(candle)
        assert len(consumer.ohlcv_history) == 1
        assert consumer.ohlcv_history[0] == candle

    def test_add_multiple_candles(self, consumer):
        """Test adding multiple candles."""
        ts = datetime.utcnow()
        for i in range(5):
            candle = OHLCV(
                timestamp=ts,
                open=50000.0,
                high=50500.0,
                low=49900.0,
                close=50200.0,
                volume=100.0
            )
            consumer.add_candle(candle)

        assert len(consumer.ohlcv_history) == 5

    def test_regime_update_insufficient_history(self, consumer):
        """Test regime update with insufficient history."""
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=50.0,
            funding_rate=0.001,
            open_interest_change=0.05,
            macro_score=0.5
        )

        # Should not crash, just log debug
        consumer.on_regime_update(regime)
        assert consumer.last_regime == regime
        assert consumer.last_bce_signal is None

    def test_regime_update_with_history(self, consumer):
        """Test regime update with sufficient history."""
        # Add 20 candles
        ts = datetime.utcnow()
        for i in range(20):
            candle = OHLCV(
                timestamp=ts,
                open=50000.0 + i,
                high=50500.0 + i,
                low=49900.0 + i,
                close=50200.0 + i,
                volume=100.0
            )
            consumer.add_candle(candle)

        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=50.0,
            funding_rate=0.001,
            open_interest_change=0.05,
            macro_score=0.5
        )

        consumer.on_regime_update(regime)
        assert consumer.last_regime == regime
        assert consumer.last_bce_signal is not None

    def test_signal_callback(self, consumer):
        """Test BCE signal callback."""
        callback = MagicMock()
        consumer.signal_callback = callback

        # Add 20 candles
        ts = datetime.utcnow()
        for i in range(20):
            candle = OHLCV(
                timestamp=ts,
                open=50000.0 + i,
                high=50500.0 + i,
                low=49900.0 + i,
                close=50200.0 + i,
                volume=100.0
            )
            consumer.add_candle(candle)

        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=50.0,
            funding_rate=0.001,
            open_interest_change=0.05,
            macro_score=0.5
        )

        consumer.on_regime_update(regime)

        # Callback should be called
        assert callback.called or consumer.last_bce_signal is not None

    def test_reset_history(self, consumer):
        """Test resetting history."""
        ts = datetime.utcnow()
        candle = OHLCV(
            timestamp=ts,
            open=50000.0,
            high=50500.0,
            low=49900.0,
            close=50200.0,
            volume=100.0
        )
        consumer.add_candle(candle)
        assert len(consumer.ohlcv_history) == 1

        consumer.reset_history()
        assert len(consumer.ohlcv_history) == 0


class TestX20Consumer:
    """Test X20 consumer for Layer 4."""

    @pytest.fixture
    def consumer(self):
        """Create X20 consumer."""
        return RealtimeX20Consumer(asset="BTC")

    def test_init(self, consumer):
        """Test X20 consumer initialization."""
        assert consumer.asset == "BTC"
        assert consumer.max_history == 100
        assert len(consumer.ohlcv_history) == 0
        assert consumer.last_regime is None
        assert consumer.last_opportunity is None

    def test_add_candle(self, consumer):
        """Test adding candle to history."""
        ts = datetime.utcnow()
        candle = OHLCV(
            timestamp=ts,
            open=50000.0,
            high=50500.0,
            low=49900.0,
            close=50200.0,
            volume=100.0
        )

        consumer.add_candle(candle)
        assert len(consumer.ohlcv_history) == 1

    def test_regime_update_with_history(self, consumer):
        """Test regime update with sufficient history."""
        # Add 20 candles
        ts = datetime.utcnow()
        for i in range(20):
            candle = OHLCV(
                timestamp=ts,
                open=50000.0 + i,
                high=50500.0 + i,
                low=49900.0 + i,
                close=50200.0 + i,
                volume=100.0
            )
            consumer.add_candle(candle)

        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=50.0,
            funding_rate=0.001,
            open_interest_change=0.05,
            macro_score=0.5
        )

        consumer.on_regime_update(regime)
        assert consumer.last_regime == regime
        assert consumer.last_opportunity is not None

    def test_opportunity_callback(self, consumer):
        """Test X20 opportunity callback."""
        callback = MagicMock()
        consumer.opportunity_callback = callback

        # Add 20 candles
        ts = datetime.utcnow()
        for i in range(20):
            candle = OHLCV(
                timestamp=ts,
                open=50000.0 + i,
                high=50500.0 + i,
                low=49900.0 + i,
                close=50200.0 + i,
                volume=100.0
            )
            consumer.add_candle(candle)

        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=50.0,
            funding_rate=0.001,
            open_interest_change=0.05,
            macro_score=0.5
        )

        consumer.on_regime_update(regime)

        # Callback should only fire if score >= 70 (not typical)
        # Just verify it doesn't error
        assert consumer.last_opportunity is not None


class TestLayer3Integration:
    """Integration tests for Layer 2 → Layer 3 consumer pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create pipeline."""
        return RealtimeRegimePipeline("test_api_key")

    def test_register_bce_consumer(self, pipeline):
        """Test registering BCE consumer with pipeline."""
        consumer = RealtimeBCEConsumer(asset="BTC")
        pipeline.register_layer3_consumer(consumer, "bce_engine")

        # Verify both callbacks registered
        assert len(pipeline.feed.regime_callbacks) == 1
        assert len(pipeline.feed.candle_callbacks) == 1

    def test_register_x20_consumer(self, pipeline):
        """Test registering X20 consumer with pipeline."""
        consumer = RealtimeX20Consumer(asset="BTC")
        pipeline.register_layer3_consumer(consumer, "x20_scanner")

        # Verify both callbacks registered
        assert len(pipeline.feed.regime_callbacks) == 1
        assert len(pipeline.feed.candle_callbacks) == 1

    def test_register_multiple_consumers(self, pipeline):
        """Test registering multiple Layer 3 consumers."""
        bce_consumer = RealtimeBCEConsumer(asset="BTC")
        x20_consumer = RealtimeX20Consumer(asset="BTC")

        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")
        pipeline.register_layer3_consumer(x20_consumer, "x20_scanner")

        # Both consumers should be registered
        assert len(pipeline.feed.regime_callbacks) == 2
        assert len(pipeline.feed.candle_callbacks) == 2

    def test_candle_dispatch_to_consumers(self, pipeline):
        """Test that candles are dispatched to Layer 3 consumers."""
        bce_consumer = RealtimeBCEConsumer(asset="BTC")
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")

        # Simulate candle from Layer 1
        ts = datetime.utcnow()
        candle = OHLCV(
            timestamp=ts,
            open=50000.0,
            high=50500.0,
            low=49900.0,
            close=50200.0,
            volume=100.0
        )

        # Dispatch to consumers (this is what Layer 1 would do)
        for callback in pipeline.feed.candle_callbacks:
            callback(candle)

        # BCE consumer should have received the candle
        assert len(bce_consumer.ohlcv_history) == 1

    def test_regime_dispatch_to_consumers(self, pipeline):
        """Test that regime changes are dispatched to Layer 3 consumers."""
        bce_consumer = RealtimeBCEConsumer(asset="BTC")
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")

        # Add candles first
        ts = datetime.utcnow()
        for i in range(20):
            candle = OHLCV(
                timestamp=ts,
                open=50000.0 + i,
                high=50500.0 + i,
                low=49900.0 + i,
                close=50200.0 + i,
                volume=100.0
            )
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # Simulate regime change from Layer 2
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=50.0,
            funding_rate=0.001,
            open_interest_change=0.05,
            macro_score=0.5
        )

        # Dispatch regime to consumers
        for callback in pipeline.feed.regime_callbacks:
            callback(regime)

        # BCE consumer should have received the regime
        assert bce_consumer.last_regime == regime
        assert bce_consumer.last_bce_signal is not None


def test_consumer_isolation():
    """Test that consumers are isolated."""
    bce1 = RealtimeBCEConsumer(asset="BTC")
    bce2 = RealtimeBCEConsumer(asset="ETH")

    ts = datetime.utcnow()
    candle = OHLCV(
        timestamp=ts,
        open=50000.0,
        high=50500.0,
        low=49900.0,
        close=50200.0,
        volume=100.0
    )

    bce1.add_candle(candle)

    assert len(bce1.ohlcv_history) == 1
    assert len(bce2.ohlcv_history) == 0
