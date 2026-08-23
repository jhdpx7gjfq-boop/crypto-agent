from liquidation_store import LiquidationStore


def make_event(symbol="BTCUSDT", side="SELL", event_time=1000, quote_value=139.0):
    return {
        "exchange": "binance",
        "symbol": symbol,
        "side": side,
        "price": 9910.0,
        "quantity": 0.014,
        "quote_value": quote_value,
        "order_status": "FILLED",
        "event_time": event_time,
        "trade_time": event_time,
        "received_at": event_time + 1,
    }


class TestLiquidationStore:
    def test_insert_and_count(self):
        store = LiquidationStore(":memory:")
        assert store.count() == 0

        store.insert(make_event())

        assert store.count() == 1

    def test_recent_returns_latest_first(self):
        store = LiquidationStore(":memory:")
        store.insert(make_event(event_time=1000))
        store.insert(make_event(event_time=2000))

        rows = store.recent(limit=10)

        assert [r["event_time"] for r in rows] == [2000, 1000]

    def test_recent_filters_by_symbol(self):
        store = LiquidationStore(":memory:")
        store.insert(make_event(symbol="BTCUSDT", event_time=1000))
        store.insert(make_event(symbol="ETHUSDT", event_time=2000))

        rows = store.recent(symbol="BTCUSDT")

        assert len(rows) == 1
        assert rows[0]["symbol"] == "BTCUSDT"

    def test_insert_persists_all_fields(self):
        store = LiquidationStore(":memory:")
        store.insert(make_event())

        row = store.recent(limit=1)[0]

        assert row["exchange"] == "binance"
        assert row["symbol"] == "BTCUSDT"
        assert row["side"] == "SELL"
        assert row["price"] == 9910.0
        assert row["quantity"] == 0.014
        assert row["quote_value"] == 139.0
        assert row["order_status"] == "FILLED"
