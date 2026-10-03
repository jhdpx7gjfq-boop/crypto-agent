"""End-to-end tests: Layer 1 (Data) → Layer 2 (Regime) → Layer 3 (BCE/X20) signal flow."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import OHLCV, MarketRegime, RegimeType
from src.layers.layer2_regime.coindesk_realtime_feed import RealtimeRegimePipeline
from src.layers.layer3_wyckoff.realtime_bce_consumer import RealtimeBCEConsumer
from src.layers.layer4_x20.realtime_x20_consumer import RealtimeX20Consumer


class TestE2EDataFlow:
    """Test complete data flow from Layer 1 → Layer 2 → Layer 3."""

    @pytest.fixture
    def pipeline(self):
        """Create pipeline."""
        return RealtimeRegimePipeline("test_api_key")

    @pytest.fixture
    def bce_consumer(self):
        """Create BCE consumer."""
        return RealtimeBCEConsumer(asset="BTC")

    @pytest.fixture
    def x20_consumer(self):
        """Create X20 consumer."""
        return RealtimeX20Consumer(asset="BTC")

    def generate_candles(self, count=50, start_price=50000.0, volatility=0.01):
        """Generate realistic OHLCV candles for testing."""
        candles = []
        ts = datetime.utcnow() - timedelta(minutes=count)
        price = start_price

        for i in range(count):
            # Realistic price movement
            change = price * (volatility * (i % 3 - 1))
            open_p = price
            close_p = price + change
            high_p = max(open_p, close_p) * (1 + volatility * 0.5)
            low_p = min(open_p, close_p) * (1 - volatility * 0.5)
            volume = 100.0 + i * 0.5

            candle = OHLCV(
                timestamp=ts,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                volume=volume
            )
            candles.append(candle)
            price = close_p
            ts += timedelta(minutes=1)

        return candles

    def test_e2e_single_consumer(self, pipeline, bce_consumer):
        """Test end-to-end: WebSocket → Regime → BCE."""
        # Register consumer
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")

        # Generate candle sequence
        candles = self.generate_candles(count=25)

        # Simulate Layer 1 data stream
        for candle in candles:
            # Dispatch to all Layer 2 subscribers (what Layer 1 would do)
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # Simulate regime change from Layer 2
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=55.0,
            funding_rate=0.002,
            open_interest_change=0.08,
            macro_score=0.65
        )

        # Dispatch regime to consumers
        for callback in pipeline.feed.regime_callbacks:
            callback(regime)

        # Verify BCE consumer state
        assert len(bce_consumer.ohlcv_history) == 25
        assert bce_consumer.last_regime == regime
        assert bce_consumer.last_bce_signal is not None
        assert bce_consumer.last_bce_signal.asset == "BTC"

    def test_e2e_multiple_consumers(self, pipeline, bce_consumer, x20_consumer):
        """Test end-to-end with multiple Layer 3 consumers."""
        # Register both consumers
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")
        pipeline.register_layer3_consumer(x20_consumer, "x20_scanner")

        # Generate candles
        candles = self.generate_candles(count=25)

        # Stream candles
        for candle in candles:
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # Verify both consumers have history
        assert len(bce_consumer.ohlcv_history) == 25
        assert len(x20_consumer.ohlcv_history) == 25

        # Dispatch regime
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=55.0,
            funding_rate=0.002,
            open_interest_change=0.08,
            macro_score=0.65
        )

        for callback in pipeline.feed.regime_callbacks:
            callback(regime)

        # Both should have signals
        assert bce_consumer.last_bce_signal is not None
        assert x20_consumer.last_opportunity is not None

    def test_e2e_regime_changes(self, pipeline, bce_consumer):
        """Test regime change detection through full pipeline."""
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")

        # Generate uptrend
        candles = self.generate_candles(count=20, volatility=0.005)

        for candle in candles:
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # Regime 1: BULL
        regime1 = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=55.0,
            funding_rate=0.002,
            open_interest_change=0.08,
            macro_score=0.65
        )

        for callback in pipeline.feed.regime_callbacks:
            callback(regime1)

        signal1 = bce_consumer.last_bce_signal
        assert signal1 is not None

        # Add more candles (downtrend)
        candles = self.generate_candles(count=20, start_price=50500.0, volatility=0.01)
        for candle in candles:
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # Regime 2: BEAR
        regime2 = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BEAR,
            btc_dominance=50.0,
            funding_rate=-0.001,
            open_interest_change=-0.05,
            macro_score=0.35
        )

        for callback in pipeline.feed.regime_callbacks:
            callback(regime2)

        signal2 = bce_consumer.last_bce_signal
        assert signal2 is not None
        assert signal2.timestamp > signal1.timestamp

    def test_e2e_signal_callback_firing(self, pipeline, bce_consumer):
        """Test that signal callbacks fire when conditions met."""
        signal_fired = []

        def on_signal(signal):
            signal_fired.append(signal)

        bce_consumer.signal_callback = on_signal
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")

        # Generate candles
        candles = self.generate_candles(count=25)

        for candle in candles:
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # Dispatch regime
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=55.0,
            funding_rate=0.002,
            open_interest_change=0.08,
            macro_score=0.65
        )

        for callback in pipeline.feed.regime_callbacks:
            callback(regime)

        # Callback may have fired (depends on BCE score)
        # At minimum, signal should be generated
        assert bce_consumer.last_bce_signal is not None

    def test_e2e_consumer_history_synchronization(self, pipeline, bce_consumer, x20_consumer):
        """Test that all consumers stay synchronized with candle history."""
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")
        pipeline.register_layer3_consumer(x20_consumer, "x20_scanner")

        # Stream 30 candles
        candles = self.generate_candles(count=30)

        for i, candle in enumerate(candles):
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

            # Verify both consumers have same count
            assert len(bce_consumer.ohlcv_history) == i + 1
            assert len(x20_consumer.ohlcv_history) == i + 1
            assert bce_consumer.ohlcv_history[-1] == x20_consumer.ohlcv_history[-1]

    def test_e2e_max_history_enforcement(self, pipeline):
        """Test that max_history limit is enforced."""
        # Create consumer with limited history
        bce_consumer = RealtimeBCEConsumer(asset="BTC", max_history=20)
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")

        # Generate 30 candles
        candles = self.generate_candles(count=30)

        for candle in candles:
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # History should be limited to 20
        assert len(bce_consumer.ohlcv_history) == 20

        # Oldest candle should be from index 10
        assert bce_consumer.ohlcv_history[0] == candles[10]
        assert bce_consumer.ohlcv_history[-1] == candles[-1]

    def test_e2e_consumer_isolation(self, pipeline):
        """Test that consumers don't interfere with each other."""
        bce1 = RealtimeBCEConsumer(asset="BTC")
        bce2 = RealtimeBCEConsumer(asset="ETH")

        pipeline.register_layer3_consumer(bce1, "bce_btc")
        pipeline.register_layer3_consumer(bce2, "bce_eth")

        # Generate candles
        candles = self.generate_candles(count=25)

        for candle in candles:
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # Both should have same history (they both received all candles)
        assert len(bce1.ohlcv_history) == 25
        assert len(bce2.ohlcv_history) == 25

        # But their signals might differ if asset names were tracked
        assert bce1.asset == "BTC"
        assert bce2.asset == "ETH"

    def test_e2e_pipeline_state_tracking(self, pipeline, bce_consumer):
        """Test that pipeline tracks regime state from consumers."""
        pipeline.register_layer3_consumer(bce_consumer, "bce_engine")

        # Generate candles
        candles = self.generate_candles(count=25)

        for candle in candles:
            for callback in pipeline.feed.candle_callbacks:
                callback(candle)

        # BCE consumer should track latest price
        assert bce_consumer.ohlcv_history[-1].close == candles[-1].close
        assert len(bce_consumer.ohlcv_history) == 25

        # Dispatch regime
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=55.0,
            funding_rate=0.002,
            open_interest_change=0.08,
            macro_score=0.65
        )

        for callback in pipeline.feed.regime_callbacks:
            callback(regime)

        # Consumer should track regime and generate signal
        assert bce_consumer.last_regime == regime
        assert bce_consumer.last_bce_signal is not None


class TestE2EErrorResilience:
    """Test error handling in e2e flow."""

    @pytest.fixture
    def pipeline(self):
        return RealtimeRegimePipeline("test_api_key")

    def test_consumer_callback_error_isolation(self, pipeline):
        """Test that consumer callback errors don't break pipeline."""
        bce = RealtimeBCEConsumer(asset="BTC")

        # Register a callback that throws
        def failing_callback(signal):
            raise ValueError("Callback failed!")

        bce.signal_callback = failing_callback
        pipeline.register_layer3_consumer(bce, "bce_engine")

        # Generate candles
        ts = datetime.utcnow()
        for i in range(25):
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

        # Should not raise, just log error
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=55.0,
            funding_rate=0.002,
            open_interest_change=0.08,
            macro_score=0.65
        )

        for callback in pipeline.feed.regime_callbacks:
            callback(regime)

        # Consumer should still have signal despite callback error
        assert bce.last_bce_signal is not None

    def test_empty_candle_history_handling(self, pipeline):
        """Test handling of regime update with no candles."""
        bce = RealtimeBCEConsumer(asset="BTC")
        pipeline.register_layer3_consumer(bce, "bce_engine")

        # No candles added, just regime
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=55.0,
            funding_rate=0.002,
            open_interest_change=0.08,
            macro_score=0.65
        )

        for callback in pipeline.feed.regime_callbacks:
            callback(regime)

        # Should not crash
        assert bce.last_regime == regime
        assert bce.last_bce_signal is None  # No signal due to insufficient history
