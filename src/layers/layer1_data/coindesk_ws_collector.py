"""CoinDesk WebSocket real-time data collector."""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass
import websockets

from src.core.models import OHLCV
from src.core.config import Config


logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """Real-time tick data from CoinDesk."""
    timestamp: datetime
    instrument: str
    price: float
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    sequence: Optional[int] = None


class CoinDeskWebSocketCollector:
    """
    Collects real-time tick data from CoinDesk WebSocket API.

    Supports:
    - Live trade data
    - Order book snapshots (L1/L2)
    - Index reference rates
    - Automatic reconnection with exponential backoff
    """

    BASE_URL = "wss://data-streamer.coindesk.com"
    DEFAULT_RECONNECT_MAX = 5

    def __init__(self, api_key: str, use_header_auth: bool = False):
        """
        Initialize CoinDesk WebSocket collector.

        Args:
            api_key: CoinDesk API key
            use_header_auth: If True, use header auth (more secure). If False, use URL param.
        """
        self.api_key = api_key
        self.use_header_auth = use_header_auth
        self.socket = None
        self.is_connected = False
        self.tick_buffer: List[TickData] = []
        self.reconnect_attempts = 0
        self.callbacks: Dict[str, List[Callable]] = {}

    def _build_url(self) -> str:
        """Build WebSocket connection URL."""
        if self.use_header_auth:
            return self.BASE_URL
        return f"{self.BASE_URL}/?api_key={self.api_key}"

    async def connect(self):
        """Establish WebSocket connection."""
        url = self._build_url()
        headers = None

        if self.use_header_auth:
            headers = {"Authorization": f"Apikey {self.api_key}"}

        try:
            self.socket = await websockets.connect(url, extra_headers=headers if headers else None)
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("Connected to CoinDesk WebSocket")

            # Receive welcome message
            welcome = await asyncio.wait_for(self.socket.recv(), timeout=5.0)
            welcome_data = json.loads(welcome)
            logger.info(f"Welcome: {welcome_data.get('MESSAGE', 'UNKNOWN')}")

            # Start heartbeat monitor
            asyncio.create_task(self._heartbeat_monitor())

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.is_connected = False
            await self._handle_reconnect()

    async def _heartbeat_monitor(self):
        """Monitor heartbeat messages (every 30s)."""
        while self.is_connected:
            try:
                message = await asyncio.wait_for(self.socket.recv(), timeout=40.0)
                data = json.loads(message)
                msg_type = data.get("TYPE")

                if msg_type == "4013":
                    logger.debug(f"Heartbeat at {data.get('TIMEMS')}")
                elif msg_type == "4000":
                    logger.debug("Session welcome")
                else:
                    await self._dispatch_message(data)

            except asyncio.TimeoutError:
                logger.warning("Heartbeat timeout")
                await self.reconnect()
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await self.reconnect()

    async def _dispatch_message(self, data: Dict[str, Any]):
        """Dispatch message to registered callbacks."""
        msg_type = data.get("TYPE")

        # Emit to all subscribers
        callbacks = self.callbacks.get("*", [])
        for cb in callbacks:
            try:
                await cb(data) if asyncio.iscoroutinefunction(cb) else cb(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def subscribe(
        self,
        market: str,
        instrument: str,
        data_type: str = "1101",
        groups: Optional[List[str]] = None
    ):
        """
        Subscribe to a data stream.

        Args:
            market: Market identifier (e.g., 'cadli')
            instrument: Instrument (e.g., 'BTC-USD')
            data_type: Stream type (default 1101 for CADLI tick)
            groups: Optional groups like ['VALUE', 'CURRENT_HOUR']
        """
        if not self.is_connected:
            logger.warning("Not connected, cannot subscribe")
            return

        msg = {
            "action": "SUB_ADD",
            "type": data_type,
            "groups": groups or ["VALUE"],
            "subscriptions": [{"market": market, "instrument": instrument}]
        }

        try:
            await self.socket.send(json.dumps(msg))
            logger.info(f"Subscribed to {market}/{instrument}")
        except Exception as e:
            logger.error(f"Subscription failed: {e}")

    async def unsubscribe(
        self,
        market: str,
        instrument: str,
        data_type: str = "1101"
    ):
        """Unsubscribe from a data stream."""
        if not self.is_connected:
            return

        msg = {
            "action": "SUB_REMOVE",
            "type": data_type,
            "groups": ["VALUE"],
            "subscriptions": [{"market": market, "instrument": instrument}]
        }

        try:
            await self.socket.send(json.dumps(msg))
            logger.info(f"Unsubscribed from {market}/{instrument}")
        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")

    async def on_message(self, callback: Callable):
        """Register callback for incoming messages."""
        if "*" not in self.callbacks:
            self.callbacks["*"] = []
        self.callbacks["*"].append(callback)

    async def _handle_reconnect(self):
        """Handle reconnection with exponential backoff."""
        self.reconnect_attempts += 1
        if self.reconnect_attempts > self.DEFAULT_RECONNECT_MAX:
            logger.error("Max reconnection attempts reached")
            return

        backoff = min(2 ** self.reconnect_attempts, 60)
        logger.info(f"Reconnecting in {backoff}s (attempt {self.reconnect_attempts})")

        await asyncio.sleep(backoff)
        await self.connect()

    async def reconnect(self):
        """Force reconnection."""
        if self.socket:
            try:
                await self.socket.close()
            except Exception as e:
                logger.debug(f"Close error: {e}")

        self.is_connected = False
        await self._handle_reconnect()

    async def close(self):
        """Close WebSocket connection."""
        if self.socket:
            await self.socket.close()
        self.is_connected = False
        logger.info("WebSocket closed")

    def parse_tick_data(self, message: Dict[str, Any]) -> Optional[TickData]:
        """
        Parse tick data from CoinDesk message.

        CoinDesk sends various message types. We extract price ticks.
        """
        try:
            msg_type = message.get("TYPE")

            # Handle live trade messages (1101, 1102, etc.)
            if msg_type in ["1101", "1102"]:
                timestamp_ms = message.get("TIMEMS")
                if not timestamp_ms:
                    return None

                price = message.get("VALUE")
                if price is None:
                    return None

                instrument = message.get("INSTRUMENT", "UNKNOWN")
                volume = message.get("VOLUME")
                bid = message.get("BID")
                ask = message.get("ASK")

                return TickData(
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000),
                    instrument=instrument,
                    price=float(price),
                    volume=float(volume) if volume else None,
                    bid=float(bid) if bid else None,
                    ask=float(ask) if ask else None,
                    sequence=message.get("SEQUENCE")
                )

        except Exception as e:
            logger.debug(f"Parse error: {e}")

        return None

    def aggregate_ticks_to_ohlcv(
        self,
        ticks: List[TickData],
        instrument: str
    ) -> Optional[OHLCV]:
        """
        Aggregate tick data into OHLCV candle.

        Args:
            ticks: List of tick data points (should be from same candle period)
            instrument: Instrument identifier

        Returns:
            OHLCV candle or None if insufficient data
        """
        if not ticks:
            return None

        prices = [t.price for t in ticks]
        volumes = [t.volume for t in ticks if t.volume]

        try:
            ohlcv = OHLCV(
                timestamp=ticks[0].timestamp,
                open=prices[0],
                high=max(prices),
                low=min(prices),
                close=prices[-1],
                volume=sum(volumes) if volumes else 0.0
            )
            return ohlcv
        except ValueError as e:
            logger.warning(f"Invalid OHLCV for {instrument}: {e}")
            return None


class CoinDeskCollectorManager:
    """
    Manager for CoinDesk WebSocket collector with built-in data aggregation.

    Handles:
    - Connection lifecycle
    - Subscription management
    - Tick aggregation to candles
    - Data storage
    """

    def __init__(self, api_key: str, use_header_auth: bool = False):
        self.collector = CoinDeskWebSocketCollector(api_key, use_header_auth)
        self.subscriptions: Dict[str, Dict[str, str]] = {}
        self.tick_buffers: Dict[str, List[TickData]] = {}
        self.candle_callbacks: List[Callable[[OHLCV], None]] = []

    async def start(self):
        """Start the collector."""
        await self.collector.connect()
        await self.collector.on_message(self._handle_message)

    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming messages and aggregate to candles."""
        tick = self.collector.parse_tick_data(message)
        if not tick:
            return

        # Buffer ticks by instrument
        if tick.instrument not in self.tick_buffers:
            self.tick_buffers[tick.instrument] = []

        self.tick_buffers[tick.instrument].append(tick)

        # Simple aggregation: emit every 100 ticks or on time window
        if len(self.tick_buffers[tick.instrument]) >= 100:
            self._emit_candle(tick.instrument)

    def _emit_candle(self, instrument: str):
        """Aggregate and emit OHLCV candle."""
        ticks = self.tick_buffers.get(instrument, [])
        if not ticks:
            return

        candle = self.collector.aggregate_ticks_to_ohlcv(ticks, instrument)
        if candle:
            for cb in self.candle_callbacks:
                try:
                    cb(candle)
                except Exception as e:
                    logger.error(f"Candle callback error: {e}")

        # Clear buffer
        self.tick_buffers[instrument] = []

    async def subscribe(self, market: str, instrument: str):
        """Subscribe to an instrument."""
        await self.collector.subscribe(market, instrument)
        self.subscriptions[instrument] = {"market": market}

    async def unsubscribe(self, instrument: str):
        """Unsubscribe from an instrument."""
        sub = self.subscriptions.get(instrument)
        if sub:
            await self.collector.unsubscribe(sub["market"], instrument)
            del self.subscriptions[instrument]

    def on_candle(self, callback: Callable[[OHLCV], None]):
        """Register callback for OHLCV candles."""
        self.candle_callbacks.append(callback)

    async def close(self):
        """Close the collector."""
        await self.collector.close()
