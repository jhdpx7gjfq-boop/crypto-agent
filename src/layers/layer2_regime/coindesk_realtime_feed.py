"""Real-time CoinDesk WebSocket feed for Layer 2 (Market Regime).

Streams OHLCV candles from CoinDesk into regime detection pipeline.
"""

import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime

from src.core.models import OHLCV, MarketRegime
from src.layers.layer1_data.coindesk_ws_collector import (
    CoinDeskCollectorManager,
)
from src.layers.layer2_regime.regime_engine import MarketRegimeDetector


logger = logging.getLogger(__name__)


class CoinDeskRealtimeRegimeFeed:
    """
    Real-time market regime detection from CoinDesk WebSocket.

    Pipeline:
    CoinDesk WebSocket
        ↓
    Tick parsing
        ↓
    OHLCV aggregation (100 ticks → 1 candle)
        ↓
    Regime detection (Layer 2)
        ↓
    Regime callbacks (Layer 3+)
    """

    def __init__(self, api_key: str, use_header_auth: bool = True):
        """
        Initialize real-time regime feed.

        Args:
            api_key: CoinDesk API key
            use_header_auth: Use secure header authentication
        """
        self.api_key = api_key
        self.use_header_auth = use_header_auth
        self.manager = CoinDeskCollectorManager(api_key, use_header_auth)
        self.regime_detector = MarketRegimeDetector()
        self.regime_callbacks: list[Callable[[MarketRegime], None]] = []
        self.candle_callbacks: list[Callable[[OHLCV], None]] = []
        self.is_running = False

        # State tracking
        self.current_price = None
        self.last_regime = None

    async def start(self):
        """Start real-time regime feed."""
        try:
            logger.info("Starting CoinDesk real-time regime feed...")

            # Register candle processor
            self.manager.on_candle(self._process_candle)

            # Connect and subscribe
            await self.manager.start()
            await self.manager.subscribe("cadli", "BTC-USD")

            self.is_running = True
            logger.info("✅ CoinDesk real-time feed started")

        except Exception as e:
            logger.error(f"Failed to start feed: {e}")
            raise

    async def stop(self):
        """Stop real-time feed."""
        if self.is_running:
            await self.manager.close()
            self.is_running = False
            logger.info("CoinDesk real-time feed stopped")

    def on_regime_change(self, callback: Callable[[MarketRegime], None]):
        """
        Register callback for regime changes.

        Args:
            callback: Function to call when regime updates
        """
        self.regime_callbacks.append(callback)

    def on_candle(self, callback: Callable[[OHLCV], None]):
        """
        Register callback for candle updates (Layer 3+ history).

        Args:
            callback: Function to call for each new candle
        """
        self.candle_callbacks.append(callback)

    def _process_candle(self, candle: OHLCV):
        """
        Process OHLCV candle and update regime.

        Args:
            candle: Aggregated OHLCV from CoinDesk
        """
        try:
            # Update current price
            self.current_price = candle.close

            # Dispatch candle to Layer 3+ consumers (for history tracking)
            for callback in self.candle_callbacks:
                try:
                    callback(candle)
                except Exception as e:
                    logger.error(f"Candle callback error: {e}")

            # Detect regime
            regime = self.regime_detector.detect_regime(
                btc_price=candle.close,
                # Funding rate & OI would come from derivatives feed
                # For now, detector will fetch them
            )

            # Check if regime changed
            if (self.last_regime is None or
                    self.last_regime.regime != regime.regime):
                logger.warning(
                    f"🔄 REGIME CHANGE: {self.last_regime.regime if self.last_regime else 'INIT'} "
                    f"→ {regime.regime} @ ${candle.close:.2f}"
                )

                # Emit regime callbacks (Layer 3+)
                for callback in self.regime_callbacks:
                    try:
                        callback(regime)
                    except Exception as e:
                        logger.error(f"Regime callback error: {e}")

            self.last_regime = regime

        except Exception as e:
            logger.error(f"Candle processing error: {e}")


class RealtimeRegimePipeline:
    """
    End-to-end real-time regime detection pipeline.

    Orchestrates:
    - Layer 1: CoinDesk WebSocket data collection
    - Layer 2: Market regime detection
    - Layer 3+: Downstream consumers (BCE, X20, etc.)
    """

    def __init__(self, api_key: str):
        """Initialize pipeline."""
        self.api_key = api_key
        self.feed = CoinDeskRealtimeRegimeFeed(api_key)
        self.regime_history = []

    async def start(self):
        """Start pipeline."""
        await self.feed.start()

    async def stop(self):
        """Stop pipeline."""
        await self.feed.stop()

    def register_regime_consumer(
        self,
        name: str,
        callback: Callable[[MarketRegime], None]
    ):
        """
        Register a downstream consumer (Layer 3+).

        Args:
            name: Consumer name (e.g., 'bce_engine', 'x20_scanner')
            callback: Function to call on regime updates
        """
        logger.info(f"Registered regime consumer: {name}")
        self.feed.on_regime_change(callback)

    def register_candle_consumer(
        self,
        name: str,
        callback: Callable[[OHLCV], None]
    ):
        """
        Register candle consumer for Layer 3+ history tracking.

        Args:
            name: Consumer name
            callback: Function to call for each new candle
        """
        logger.info(f"Registered candle consumer: {name}")
        self.feed.on_candle(callback)

    def register_layer3_consumer(
        self,
        consumer_obj,
        name: str = None
    ):
        """
        Register Layer 3 consumer with both regime and candle callbacks.

        Args:
            consumer_obj: Consumer with on_regime_update and add_candle methods
            name: Consumer name (defaults to class name)
        """
        name = name or consumer_obj.__class__.__name__
        logger.info(f"Registered Layer 3 consumer: {name}")
        self.feed.on_regime_change(consumer_obj.on_regime_update)
        self.feed.on_candle(consumer_obj.add_candle)

    def get_current_regime(self) -> Optional[MarketRegime]:
        """Get latest detected regime."""
        return self.feed.last_regime

    def get_current_price(self) -> Optional[float]:
        """Get latest BTC price from CoinDesk."""
        return self.feed.current_price


# Example usage
async def example_realtime_regime():
    """
    Example: Run real-time regime detection.

    Usage:
        export COINDESK_API_KEY="your_key"
        python -c "
        import asyncio
        from src.layers.layer2_regime.coindesk_realtime_feed import example_realtime_regime
        asyncio.run(example_realtime_regime())
        "
    """
    import os

    api_key = os.environ.get("COINDESK_API_KEY")
    if not api_key:
        print("❌ COINDESK_API_KEY not set")
        return

    # Create pipeline
    pipeline = RealtimeRegimePipeline(api_key)

    # Define regime consumer (e.g., BCE engine)
    def on_regime_update(regime: MarketRegime):
        print(f"\n📊 Regime Update:")
        print(f"   Time: {regime.timestamp.isoformat()}")
        print(f"   Regime: {regime.regime.value}")
        print(f"   BTC Dom: {regime.btc_dominance:.1f}%")
        print(f"   Funding Rate: {regime.funding_rate:.4f}")
        print(f"   Macro Score: {regime.macro_score:.2f}")

    # Register consumer
    pipeline.register_regime_consumer("example_consumer", on_regime_update)

    # Start pipeline
    try:
        await pipeline.start()

        # Run for 30 seconds
        print("✅ Real-time regime detection running... (30s)")
        await asyncio.sleep(30)

    finally:
        await pipeline.stop()
        print("✅ Pipeline stopped")


if __name__ == "__main__":
    asyncio.run(example_realtime_regime())
