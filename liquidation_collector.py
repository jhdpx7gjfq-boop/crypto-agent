"""Continuous collector for Binance USD-M futures liquidations.

CoinGlass has no free liquidation endpoint, and Binance itself has no free
REST history for it either (the old public `/fapi/v1/allForceOrders` is
gone) -- see
research/candidates/DATA-SRC-004_BINANCE_PUBLIC_FREE/OVERVIEW.md. The only
free path for this P0 data category is Binance's public `!forceOrder@arr`
WebSocket stream (all symbols, no key needed), persisted here as it arrives.

This only builds history forward from whenever it started -- there is no
backfill for a gap while disconnected, so it's meant to run continuously as
its own worker process (see Procfile), not on demand like the REST clients.
"""

import json
import logging
import os
import time

import websocket

from liquidation_store import LiquidationStore

logger = logging.getLogger(__name__)

STREAM_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"


def parse_liquidation_event(raw_message):
    """Parse one Binance forceOrder WebSocket message into a flat record.

    Example message:
    {"e":"forceOrder","E":1568014460893,"o":{"s":"BTCUSDT","S":"SELL",
    "o":"LIMIT","f":"IOC","q":"0.014","p":"9910","ap":"9910","X":"FILLED",
    "l":"0.014","z":"0.014","T":1568014460893}}
    """
    payload = json.loads(raw_message)
    order = payload["o"]
    price = float(order["ap"])
    quantity = float(order["q"])
    return {
        "exchange": "binance",
        "symbol": order["s"],
        "side": order["S"],
        "price": price,
        "quantity": quantity,
        "quote_value": price * quantity,
        "order_status": order.get("X"),
        "event_time": payload["E"],
        "trade_time": order.get("T"),
        "received_at": int(time.time() * 1000),
    }


class LiquidationCollector:
    def __init__(self, store=None, url=STREAM_URL):
        self.store = store or LiquidationStore()
        self.url = url

    def _on_message(self, _ws, message):
        try:
            event = parse_liquidation_event(message)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Failed to parse liquidation message: %s", exc)
            return
        self.store.insert(event)
        logger.info(
            "liquidation exchange=%s symbol=%s side=%s quote_value=%.2f",
            event["exchange"], event["symbol"], event["side"], event["quote_value"],
        )

    def _on_error(self, _ws, error):
        logger.warning("Liquidation stream error: %s", error)

    def _on_close(self, _ws, status_code, msg):
        logger.warning("Liquidation stream closed: %s %s", status_code, msg)

    def _on_open(self, _ws):
        logger.info("Liquidation stream connected: %s", self.url)

    def run_forever(self, reconnect_delay=5):
        app = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )
        app.run_forever(reconnect=reconnect_delay)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db_path = os.environ.get("LIQUIDATION_DB_PATH", "liquidations.db")
    LiquidationCollector(store=LiquidationStore(db_path)).run_forever()


if __name__ == "__main__":
    main()
