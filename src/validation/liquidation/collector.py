"""Binance liquidation collector — real-time WebSocket data collection.

Point-in-Time compliance:
- Exact millisecond timestamps on every event
- No future peeking
- Event source tracked (binance_websocket)
- Unique source IDs for deduplication
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

import websockets

from src.validation.liquidation.contracts import LiquidationBatch, LiquidationEvent

logger = logging.getLogger(__name__)


class BinanceLiquidationCollector:
    """Collect liquidation events from Binance WebSocket (forceOrder stream).

    Stream: wss://fstream.binance.com/ws/!forceOrder@arr
    Reference: https://binance-docs.github.io/apidocs/futures/en/#liquidation-order-streams

    Binance message format:
    {
      "e":"forceOrder",
      "E":1568014460893,
      "o":{
        "s":"BTCUSDT",
        "S":"SELL",
        "o":"LIQUIDATION",
        "f":"IOC",
        "q":"0.001",
        "p":"7365.52",
        "ap":"7365.41",
        "X":"FILLED",
        "l":"0.001",
        "z":"0.001",
        "T":1568014460893
      }
    }
    """

    def __init__(
        self,
        stream_url: str = "wss://fstream.binance.com/ws/!forceOrder@arr",
        reconnect_attempts: int = 10,
        reconnect_delay: int = 5,
    ) -> None:
        """Initialize Binance liquidation collector.

        Args:
            stream_url: WebSocket endpoint
            reconnect_attempts: Max reconnection attempts
            reconnect_delay: Seconds between reconnection attempts
        """
        self.stream_url = stream_url
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.events: list[LiquidationEvent] = []
        self.connected = False

    async def connect_and_collect(self, duration_seconds: int = 3600) -> LiquidationBatch:
        """Connect to Binance and collect liquidations for specified duration.

        Args:
            duration_seconds: How long to collect (default 1 hour)

        Returns:
            LiquidationBatch with all collected events

        Raises:
            ConnectionError: If connection fails after all retry attempts
            ValueError: If no events collected
        """
        logger.info(f"Connecting to {self.stream_url}")
        start_time = datetime.now(UTC)
        attempt = 0

        while attempt < self.reconnect_attempts:
            try:
                async with websockets.connect(self.stream_url) as websocket:
                    logger.info("WebSocket connected")
                    self.connected = True
                    attempt = 0  # Reset on successful connection

                    while (datetime.now(UTC) - start_time).total_seconds() < duration_seconds:
                        try:
                            message = await websocket.recv()
                            self._process_message(message)
                        except asyncio.TimeoutError:
                            continue

            except Exception as e:
                attempt += 1
                logger.warning(f"Connection error: {e} - reconnect attempt {attempt}")
                if attempt < self.reconnect_attempts:
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    raise ConnectionError(
                        f"Failed to connect after {self.reconnect_attempts} attempts"
                    )

        self.connected = False
        return self._create_batch()

    def _process_message(self, message: str) -> None:
        """Parse Binance liquidation message and add to events.

        Args:
            message: Raw WebSocket message (JSON)
        """
        try:
            data = json.loads(message)

            # Binance sends array of force orders
            if isinstance(data, list):
                for order in data:
                    self._parse_force_order(order)
            else:
                self._parse_force_order(data)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Message processing error: {e}")

    def _parse_force_order(self, order: dict[str, Any]) -> None:
        """Parse single force order from Binance message.

        Args:
            order: Binance force order object
        """
        try:
            # Extract outer event metadata
            event_type = order.get("e")
            event_time_ms = order.get("E")  # Milliseconds (UTC)

            if event_type != "forceOrder":
                return

            # Extract order details
            o = order.get("o", {})
            symbol = o.get("s")
            side_str = o.get("S")  # SELL = long liquidation, BUY = short
            quantity = float(o.get("q", 0))
            price = float(o.get("p", 0))
            order_id = o.get("i", "unknown")

            # Normalize side
            if side_str == "SELL":
                side = "long"  # Seller gets liquidated (was long)
            elif side_str == "BUY":
                side = "short"  # Buyer gets liquidated (was short)
            else:
                logger.warning(f"Unknown side: {side_str}")
                return

            # Create timestamp (Binance uses milliseconds)
            timestamp = datetime.fromtimestamp(event_time_ms / 1000, tz=UTC)

            # Create LiquidationEvent
            event = LiquidationEvent(
                timestamp=timestamp,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                source="binance_websocket",
                source_id=f"{symbol}_{order_id}_{event_time_ms}",
            )

            self.events.append(event)
            logger.debug(
                f"Liquidation: {symbol} {side} {quantity} @ {price} "
                f"(${event.usd_value:.2f})"
            )

        except Exception as e:
            logger.error(f"Error parsing force order: {e}")

    def _create_batch(self) -> LiquidationBatch:
        """Create LiquidationBatch from collected events.

        Returns:
            LiquidationBatch containing all events

        Raises:
            ValueError: If no events collected
        """
        if not self.events:
            raise ValueError("No liquidation events collected")

        batch_id = datetime.now(UTC).strftime("batch_%Y%m%d_%H%M%S")
        total_volume = sum(e.usd_value for e in self.events)

        return LiquidationBatch(
            batch_id=batch_id,
            events=self.events,
            batch_timestamp=datetime.now(UTC),
            source="binance_websocket",
            total_usd_volume=total_volume,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get collection statistics."""
        if not self.events:
            return {"total_events": 0, "total_usd_volume": 0, "symbols": []}

        total_volume = sum(e.usd_value for e in self.events)
        symbols = set(e.symbol for e in self.events)
        sides = {side: sum(1 for e in self.events if e.side == side) for side in ["long", "short"]}

        return {
            "total_events": len(self.events),
            "total_usd_volume": total_volume,
            "symbols": sorted(list(symbols)),
            "long_liquidations": sides.get("long", 0),
            "short_liquidations": sides.get("short", 0),
            "avg_usd_per_event": total_volume / len(self.events) if self.events else 0,
        }
