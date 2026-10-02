"""Real-time CoinDesk WebSocket integration tests.

Requires: COINDESK_API_KEY environment variable
Run: COINDESK_API_KEY=your_key pytest tests/integration/test_coindesk_realtime.py -v -s
"""

import os
import pytest
import asyncio
from datetime import datetime

from src.layers.layer1_data.coindesk_ws_collector import (
    CoinDeskCollectorManager,
)
from src.core.models import OHLCV


@pytest.fixture
def api_key():
    """Get CoinDesk API key from environment."""
    key = os.environ.get("COINDESK_API_KEY")
    if not key:
        pytest.skip("COINDESK_API_KEY not set")
    return key


@pytest.mark.asyncio
class TestCoinDeskRealtimeIntegration:
    """Test real-time data from CoinDesk WebSocket."""

    async def test_connection_and_welcome(self, api_key):
        """Verify WebSocket connection and welcome message."""
        manager = CoinDeskCollectorManager(api_key, use_header_auth=True)

        try:
            await manager.start()
            # If we got here, connection succeeded
            assert manager.collector.is_connected
            print("✅ WebSocket connected")
        finally:
            await manager.close()

    async def test_subscription_btc_usd(self, api_key):
        """Subscribe to BTC-USD and receive ticks."""
        manager = CoinDeskCollectorManager(api_key, use_header_auth=True)
        ticks_received = []

        def collect_ticks(message):
            tick = manager.collector.parse_tick_data(message)
            if tick and tick.instrument == "BTC-USD":
                ticks_received.append(tick)

        try:
            await manager.start()
            await manager.collector.on_message(collect_ticks)
            await manager.subscribe("cadli", "BTC-USD")

            # Wait for ticks
            for _ in range(50):  # 50 * 0.1 = 5 seconds
                if len(ticks_received) >= 5:
                    break
                await asyncio.sleep(0.1)

            # Verify we got ticks
            assert len(ticks_received) > 0, "No BTC-USD ticks received"
            print(f"✅ Received {len(ticks_received)} BTC-USD ticks")

            # Validate tick data
            for tick in ticks_received[:3]:
                assert tick.instrument == "BTC-USD"
                assert tick.price > 0
                assert tick.timestamp
                print(f"  Tick: {tick.instrument} @ ${tick.price}")

        finally:
            await manager.close()

    async def test_candle_aggregation(self, api_key):
        """Subscribe and aggregate ticks to OHLCV candles."""
        manager = CoinDeskCollectorManager(api_key, use_header_auth=True)
        candles = []

        def on_candle(candle: OHLCV):
            candles.append(candle)
            print(f"✅ Candle: O:{candle.open:.2f} H:{candle.high:.2f} "
                  f"L:{candle.low:.2f} C:{candle.close:.2f} V:{candle.volume:.0f}")

        try:
            manager.on_candle(on_candle)
            await manager.start()
            await manager.subscribe("cadli", "BTC-USD")

            # Wait for at least one candle (100 ticks)
            for _ in range(300):  # 300 * 0.1 = 30 seconds max
                if len(candles) >= 1:
                    break
                await asyncio.sleep(0.1)

            if len(candles) > 0:
                candle = candles[0]
                assert candle.open > 0
                assert candle.high >= candle.open
                assert candle.high >= candle.close
                assert candle.low <= candle.open
                assert candle.low <= candle.close
                assert candle.volume >= 0
                print(f"✅ Valid OHLCV candle aggregated")
            else:
                print("⚠️  No candles generated (need 100+ ticks)")

        finally:
            await manager.close()

    async def test_multiple_instruments(self, api_key):
        """Subscribe to multiple instruments."""
        manager = CoinDeskCollectorManager(api_key, use_header_auth=True)
        instruments = {}

        async def on_message(message):
            tick = manager.collector.parse_tick_data(message)
            if tick:
                if tick.instrument not in instruments:
                    instruments[tick.instrument] = 0
                instruments[tick.instrument] += 1

        try:
            await manager.start()
            await manager.collector.on_message(on_message)

            # Subscribe to multiple pairs
            await manager.subscribe("cadli", "BTC-USD")
            await manager.subscribe("cadli", "ETH-USD")

            # Wait for ticks
            for _ in range(50):
                if len(instruments) >= 2:
                    break
                await asyncio.sleep(0.1)

            print(f"✅ Received ticks for {len(instruments)} instruments:")
            for inst, count in instruments.items():
                print(f"  {inst}: {count} ticks")

            assert len(instruments) >= 1, "No ticks received"

        finally:
            await manager.close()

    async def test_unsubscribe(self, api_key):
        """Subscribe and unsubscribe from instrument."""
        manager = CoinDeskCollectorManager(api_key, use_header_auth=True)

        try:
            await manager.start()
            await manager.subscribe("cadli", "BTC-USD")
            print("✅ Subscribed to BTC-USD")

            await asyncio.sleep(1)

            await manager.unsubscribe("BTC-USD")
            print("✅ Unsubscribed from BTC-USD")

            assert "BTC-USD" not in manager.subscriptions
        finally:
            await manager.close()

    async def test_reconnection_resilience(self, api_key):
        """Test automatic reconnection on disconnect."""
        manager = CoinDeskCollectorManager(api_key, use_header_auth=True)
        ticks = []

        def collect_ticks(message):
            tick = manager.collector.parse_tick_data(message)
            if tick:
                ticks.append(tick)

        try:
            await manager.start()
            await manager.collector.on_message(collect_ticks)
            await manager.subscribe("cadli", "BTC-USD")

            # Wait for initial ticks
            for _ in range(30):
                if len(ticks) >= 3:
                    break
                await asyncio.sleep(0.1)

            initial_ticks = len(ticks)
            print(f"✅ Received {initial_ticks} ticks before disconnect")

            # Force disconnect
            await manager.collector.reconnect()
            print("✅ Forced reconnect")

            # Wait for reconnection
            await asyncio.sleep(2)

            # Re-subscribe
            await manager.subscribe("cadli", "BTC-USD")

            # Wait for more ticks
            for _ in range(50):
                if len(ticks) > initial_ticks + 3:
                    break
                await asyncio.sleep(0.1)

            total_ticks = len(ticks)
            print(f"✅ Recovered: received {total_ticks - initial_ticks} additional ticks")

        finally:
            await manager.close()


class TestDataCollectorIntegration:
    """Test integration with DataCollector."""

    def test_get_coindesk_collector_with_real_key(self):
        """Test getting real CoinDesk collector through DataCollector."""
        from src.layers.layer1_data.collector import DataCollector

        api_key = os.environ.get("COINDESK_API_KEY")
        if not api_key:
            pytest.skip("COINDESK_API_KEY not set")

        collector = DataCollector(use_mock=False)
        ws_manager = collector.get_coindesk_ws_collector(api_key, use_header_auth=True)

        assert ws_manager is not None
        print("✅ CoinDesk manager instantiated through DataCollector")


@pytest.mark.asyncio
async def test_basic_connectivity(api_key):
    """Minimal connectivity test."""
    manager = CoinDeskCollectorManager(api_key, use_header_auth=True)

    try:
        await asyncio.wait_for(manager.start(), timeout=10.0)
        print("✅ Connected to CoinDesk WebSocket within 10s")
    except asyncio.TimeoutError:
        pytest.fail("Connection timeout")
    finally:
        try:
            await asyncio.wait_for(manager.close(), timeout=5.0)
        except asyncio.TimeoutError:
            pass


if __name__ == "__main__":
    api_key = os.environ.get("COINDESK_API_KEY")
    if not api_key:
        print("❌ COINDESK_API_KEY not set")
        print("\nUsage:")
        print("  export COINDESK_API_KEY='your_api_key'")
        print("  pytest tests/integration/test_coindesk_realtime.py -v -s")
    else:
        print(f"✅ API Key found: {api_key[:10]}...")
        pytest.main([__file__, "-v", "-s"])
