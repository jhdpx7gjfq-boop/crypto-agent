import json
from unittest.mock import Mock, patch

import pytest

from liquidation_collector import LiquidationCollector, parse_liquidation_event

RAW_MESSAGE = json.dumps(
    {
        "e": "forceOrder",
        "E": 1568014460893,
        "o": {
            "s": "BTCUSDT",
            "S": "SELL",
            "o": "LIMIT",
            "f": "IOC",
            "q": "0.014",
            "p": "9910",
            "ap": "9910",
            "X": "FILLED",
            "l": "0.014",
            "z": "0.014",
            "T": 1568014460893,
        },
    }
)


class TestParseLiquidationEvent:
    def test_parses_expected_fields(self):
        event = parse_liquidation_event(RAW_MESSAGE)

        assert event["exchange"] == "binance"
        assert event["symbol"] == "BTCUSDT"
        assert event["side"] == "SELL"
        assert event["price"] == 9910.0
        assert event["quantity"] == 0.014
        assert event["quote_value"] == pytest.approx(9910.0 * 0.014)
        assert event["order_status"] == "FILLED"
        assert event["event_time"] == 1568014460893
        assert event["trade_time"] == 1568014460893
        assert isinstance(event["received_at"], int)

    def test_raises_on_malformed_json(self):
        with pytest.raises(json.JSONDecodeError):
            parse_liquidation_event("not json")

    def test_raises_on_missing_fields(self):
        with pytest.raises(KeyError):
            parse_liquidation_event(json.dumps({"e": "forceOrder"}))


class TestLiquidationCollectorOnMessage:
    def test_valid_message_is_stored(self):
        store = Mock()
        collector = LiquidationCollector(store=store)

        collector._on_message(None, RAW_MESSAGE)

        store.insert.assert_called_once()
        stored_event = store.insert.call_args[0][0]
        assert stored_event["symbol"] == "BTCUSDT"

    def test_malformed_message_is_logged_not_raised(self):
        store = Mock()
        collector = LiquidationCollector(store=store)

        collector._on_message(None, "not json")  # must not raise

        store.insert.assert_not_called()

    def test_message_missing_fields_is_logged_not_raised(self):
        store = Mock()
        collector = LiquidationCollector(store=store)

        collector._on_message(None, json.dumps({"e": "forceOrder"}))  # must not raise

        store.insert.assert_not_called()


class TestRunForever:
    @patch("liquidation_collector.websocket.WebSocketApp")
    def test_wires_up_callbacks_and_reconnect(self, mock_app_cls):
        mock_app = Mock()
        mock_app_cls.return_value = mock_app
        collector = LiquidationCollector(store=Mock())

        collector.run_forever(reconnect_delay=7)

        args, kwargs = mock_app_cls.call_args
        assert args[0] == collector.url
        assert kwargs["on_message"] == collector._on_message
        assert kwargs["on_error"] == collector._on_error
        assert kwargs["on_close"] == collector._on_close
        assert kwargs["on_open"] == collector._on_open
        mock_app.run_forever.assert_called_once_with(reconnect=7)
