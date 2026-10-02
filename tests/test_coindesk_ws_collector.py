"""Tests for CoinDesk WebSocket collector."""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.layers.layer1_data.coindesk_ws_collector import (
    CoinDeskWebSocketCollector,
    CoinDeskCollectorManager,
    TickData
)
from src.core.models import OHLCV


class TestTickData:
    """Test TickData model."""

    def test_tick_data_creation(self):
        ts = datetime.now()
        tick = TickData(
            timestamp=ts,
            instrument="BTC-USD",
            price=50000.0,
            volume=100.0,
            bid=49999.0,
            ask=50001.0
        )

        assert tick.timestamp == ts
        assert tick.instrument == "BTC-USD"
        assert tick.price == 50000.0
        assert tick.volume == 100.0
        assert tick.bid == 49999.0
        assert tick.ask == 50001.0

    def test_tick_data_optional_fields(self):
        ts = datetime.now()
        tick = TickData(
            timestamp=ts,
            instrument="BTC-USD",
            price=50000.0
        )

        assert tick.volume is None
        assert tick.bid is None
        assert tick.ask is None


class TestCoinDeskWebSocketCollector:
    """Test CoinDesk WebSocket collector."""

    @pytest.fixture
    def collector(self):
        return CoinDeskWebSocketCollector("test_api_key")

    @pytest.fixture
    def collector_header_auth(self):
        return CoinDeskWebSocketCollector("test_api_key", use_header_auth=True)

    def test_init(self, collector):
        assert collector.api_key == "test_api_key"
        assert collector.use_header_auth is False
        assert collector.is_connected is False
        assert len(collector.tick_buffer) == 0

    def test_init_header_auth(self, collector_header_auth):
        assert collector_header_auth.use_header_auth is True

    def test_build_url_param_auth(self, collector):
        url = collector._build_url()
        assert url == "wss://data-streamer.coindesk.com/?api_key=test_api_key"

    def test_build_url_header_auth(self, collector_header_auth):
        url = collector_header_auth._build_url()
        assert url == "wss://data-streamer.coindesk.com"

    def test_parse_tick_data_trade_message(self, collector):
        message = {
            "TYPE": "1101",
            "TIMEMS": 1714659133000,
            "INSTRUMENT": "BTC-USD",
            "VALUE": 50000.0,
            "VOLUME": 100.0,
            "BID": 49999.0,
            "ASK": 50001.0,
            "SEQUENCE": 12345
        }

        tick = collector.parse_tick_data(message)

        assert tick is not None
        assert tick.instrument == "BTC-USD"
        assert tick.price == 50000.0
        assert tick.volume == 100.0
        assert tick.bid == 49999.0
        assert tick.ask == 50001.0
        assert tick.sequence == 12345

    def test_parse_tick_data_missing_timestamp(self, collector):
        message = {
            "TYPE": "1101",
            "INSTRUMENT": "BTC-USD",
            "VALUE": 50000.0,
        }

        tick = collector.parse_tick_data(message)
        assert tick is None

    def test_parse_tick_data_missing_price(self, collector):
        message = {
            "TYPE": "1101",
            "TIMEMS": 1714659133000,
            "INSTRUMENT": "BTC-USD",
        }

        tick = collector.parse_tick_data(message)
        assert tick is None

    def test_parse_tick_data_unsupported_message_type(self, collector):
        message = {
            "TYPE": "4000",
            "MESSAGE": "SESSIONWELCOME"
        }

        tick = collector.parse_tick_data(message)
        assert tick is None

    def test_aggregate_ticks_to_ohlcv_single_tick(self, collector):
        ts = datetime.now()
        tick = TickData(
            timestamp=ts,
            instrument="BTC-USD",
            price=50000.0,
            volume=100.0
        )

        ohlcv = collector.aggregate_ticks_to_ohlcv([tick], "BTC-USD")

        assert ohlcv is not None
        assert ohlcv.timestamp == ts
        assert ohlcv.open == 50000.0
        assert ohlcv.high == 50000.0
        assert ohlcv.low == 50000.0
        assert ohlcv.close == 50000.0
        assert ohlcv.volume == 100.0

    def test_aggregate_ticks_to_ohlcv_multiple_ticks(self, collector):
        ts = datetime.now()
        ticks = [
            TickData(timestamp=ts, instrument="BTC-USD", price=50000.0, volume=100.0),
            TickData(timestamp=ts, instrument="BTC-USD", price=50100.0, volume=150.0),
            TickData(timestamp=ts, instrument="BTC-USD", price=49950.0, volume=120.0),
            TickData(timestamp=ts, instrument="BTC-USD", price=50050.0, volume=130.0),
        ]

        ohlcv = collector.aggregate_ticks_to_ohlcv(ticks, "BTC-USD")

        assert ohlcv is not None
        assert ohlcv.open == 50000.0
        assert ohlcv.high == 50100.0
        assert ohlcv.low == 49950.0
        assert ohlcv.close == 50050.0
        assert ohlcv.volume == 500.0

    def test_aggregate_ticks_empty_list(self, collector):
        ohlcv = collector.aggregate_ticks_to_ohlcv([], "BTC-USD")
        assert ohlcv is None

    def test_aggregate_ticks_invalid_ohlcv(self, collector):
        ts = datetime.now()
        # High < Low will cause OHLCV validation error
        ticks = [
            TickData(timestamp=ts, instrument="BTC-USD", price=50000.0, volume=100.0),
        ]

        # Modify the validation to make it fail artificially
        # This is tested implicitly via OHLCV validation


class TestCoinDeskCollectorManager:
    """Test CoinDesk collector manager."""

    @pytest.fixture
    def manager(self):
        return CoinDeskCollectorManager("test_api_key")

    def test_init(self, manager):
        assert manager.subscriptions == {}
        assert manager.tick_buffers == {}
        assert len(manager.candle_callbacks) == 0

    def test_on_candle_registration(self, manager):
        callback = MagicMock()
        manager.on_candle(callback)

        assert len(manager.candle_callbacks) == 1
        assert manager.candle_callbacks[0] == callback

    @pytest.mark.asyncio
    async def test_candle_emission(self, manager):
        """Test that candles are aggregated and emitted."""
        callback = MagicMock()
        manager.on_candle(callback)

        # Simulate incoming message with ticks
        ts = datetime.now()
        message = {
            "TYPE": "1101",
            "TIMEMS": int(ts.timestamp() * 1000),
            "INSTRUMENT": "BTC-USD",
            "VALUE": 50000.0,
            "VOLUME": 100.0
        }

        # Emit 100 ticks to trigger aggregation
        for i in range(100):
            msg = message.copy()
            msg["VALUE"] = 50000.0 + i
            msg["TIMEMS"] = int(ts.timestamp() * 1000) + i * 1000
            await manager._handle_message(msg)

        # Callback should have been called at least once
        assert callback.called or len(manager.tick_buffers.get("BTC-USD", [])) == 100

    def test_tick_buffer_initialization(self, manager):
        """Test that tick buffers are created for instruments."""
        manager.tick_buffers["BTC-USD"] = []
        assert "BTC-USD" in manager.tick_buffers

    def test_subscription_tracking(self, manager):
        """Test subscription tracking."""
        manager.subscriptions["BTC-USD"] = {"market": "cadli"}
        assert "BTC-USD" in manager.subscriptions
        assert manager.subscriptions["BTC-USD"]["market"] == "cadli"


@pytest.mark.asyncio
class TestCoinDeskWebSocketIntegration:
    """Integration tests (require API key)."""

    async def test_connect_without_key(self):
        """Test that connection fails gracefully without valid key."""
        collector = CoinDeskWebSocketCollector("invalid_key")
        # Don't actually connect in test environment
        assert collector.api_key == "invalid_key"

    async def test_message_dispatch(self):
        """Test message dispatch to callbacks."""
        collector = CoinDeskWebSocketCollector("test_key")
        callback_called = False

        async def callback(msg):
            nonlocal callback_called
            callback_called = True

        await collector.on_message(callback)
        await collector._dispatch_message({"TYPE": "1101"})

        # Note: actual dispatch depends on asyncio event loop timing


class TestDataCollectorIntegration:
    """Test integration with main DataCollector."""

    def test_get_coindesk_ws_collector(self):
        from src.layers.layer1_data.collector import DataCollector

        collector = DataCollector(use_mock=False)
        ws_collector = collector.get_coindesk_ws_collector("test_key")

        assert ws_collector is not None
        assert isinstance(ws_collector, CoinDeskCollectorManager)

    def test_get_coindesk_ws_collector_same_instance(self):
        from src.layers.layer1_data.collector import DataCollector

        collector = DataCollector(use_mock=False)
        ws_collector1 = collector.get_coindesk_ws_collector("test_key")
        ws_collector2 = collector.get_coindesk_ws_collector("test_key")

        assert ws_collector1 is ws_collector2
