"""SQLite-backed store for liquidation events collected by
liquidation_collector.py.

SQLite (stdlib, no extra dependency) is enough here: one writer (the
collector), simple queries, durable across restarts via a file on disk.
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS liquidations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    quantity REAL NOT NULL,
    quote_value REAL NOT NULL,
    order_status TEXT,
    event_time INTEGER NOT NULL,
    trade_time INTEGER,
    received_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_liquidations_symbol_time ON liquidations (symbol, event_time);
"""


class LiquidationStore:
    def __init__(self, path="liquidations.db"):
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def insert(self, event):
        self._conn.execute(
            """
            INSERT INTO liquidations
                (exchange, symbol, side, price, quantity, quote_value, order_status, event_time, trade_time, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["exchange"],
                event["symbol"],
                event["side"],
                event["price"],
                event["quantity"],
                event["quote_value"],
                event.get("order_status"),
                event["event_time"],
                event.get("trade_time"),
                event["received_at"],
            ),
        )
        self._conn.commit()

    def count(self):
        return self._conn.execute("SELECT COUNT(*) FROM liquidations").fetchone()[0]

    def recent(self, symbol=None, limit=100):
        if symbol:
            rows = self._conn.execute(
                "SELECT * FROM liquidations WHERE symbol = ? ORDER BY event_time DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM liquidations ORDER BY event_time DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        self._conn.close()
