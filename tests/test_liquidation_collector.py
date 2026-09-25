"""Tests for liquidation collector — Binance WebSocket data collection."""

from datetime import UTC, datetime

import pytest

from src.validation.liquidation.contracts import (
    LiquidationBatch,
    LiquidationEvent,
    LiquidationQAReport,
)
from src.validation.liquidation.collector import BinanceLiquidationCollector
from src.validation.liquidation.persistence import LiquidationStore


class TestLiquidationEvent:
    """LiquidationEvent Pydantic contract tests."""

    def test_create_long_liquidation(self) -> None:
        """Create long liquidation event."""
        event = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 8, 532000, tzinfo=UTC),
            symbol="BTCUSDT",
            side="long",
            quantity=1.5,
            price=65000.0,
            source="binance_websocket",
            source_id="evt_123456",
        )

        assert event.symbol == "BTCUSDT"
        assert event.side == "long"
        assert event.usd_value == 97500.0

    def test_create_short_liquidation(self) -> None:
        """Create short liquidation event."""
        event = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 8, 532000, tzinfo=UTC),
            symbol="ETHUSDT",
            side="short",
            quantity=10.0,
            price=2500.0,
            source="binance_websocket",
            source_id="evt_789012",
        )

        assert event.side == "short"
        assert event.usd_value == 25000.0

    def test_timestamp_pit_compliance(self) -> None:
        """Verify timestamp is PIT-compliant (UTC, exact)."""
        ts = datetime(2026, 9, 25, 18, 31, 8, 532000, tzinfo=UTC)
        event = LiquidationEvent(
            timestamp=ts,
            symbol="BTCUSDT",
            side="long",
            quantity=1.0,
            price=65000.0,
            source="binance_websocket",
            source_id="evt_123",
        )

        assert event.timestamp.tzinfo == UTC
        assert event.timestamp == ts
        assert event.timestamp.microsecond == 532000


class TestLiquidationBatch:
    """LiquidationBatch contract tests."""

    def test_create_batch_with_events(self) -> None:
        """Create batch with multiple events."""
        event1 = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 8, 532000, tzinfo=UTC),
            symbol="BTCUSDT",
            side="long",
            quantity=1.5,
            price=65000.0,
            source="binance_websocket",
            source_id="evt_1",
        )
        event2 = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 9, 100000, tzinfo=UTC),
            symbol="ETHUSDT",
            side="short",
            quantity=10.0,
            price=2500.0,
            source="binance_websocket",
            source_id="evt_2",
        )

        batch = LiquidationBatch(
            batch_id="batch_test_001",
            events=[event1, event2],
            batch_timestamp=datetime.now(UTC),
            source="binance_websocket",
            total_usd_volume=97500.0 + 25000.0,
        )

        assert len(batch.events) == 2
        assert batch.total_usd_volume == 122500.0

    def test_batch_volume_validation(self) -> None:
        """Verify batch total volume validation."""
        event = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 8, 532000, tzinfo=UTC),
            symbol="BTCUSDT",
            side="long",
            quantity=1.0,
            price=65000.0,
            source="binance_websocket",
            source_id="evt_1",
        )

        # Incorrect volume should raise
        with pytest.raises(ValueError, match="Total USD volume mismatch"):
            LiquidationBatch(
                batch_id="batch_test_001",
                events=[event],
                batch_timestamp=datetime.now(UTC),
                source="binance_websocket",
                total_usd_volume=50000.0,  # Wrong!
            )

    def test_batch_source_consistency(self) -> None:
        """Verify all events must be from same source."""
        event1 = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 8, 532000, tzinfo=UTC),
            symbol="BTCUSDT",
            side="long",
            quantity=1.0,
            price=65000.0,
            source="binance_websocket",
            source_id="evt_1",
        )
        event2 = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 9, 100000, tzinfo=UTC),
            symbol="ETHUSDT",
            side="short",
            quantity=1.0,
            price=2500.0,
            source="coinglass",  # Different source!
            source_id="evt_2",
        )

        with pytest.raises(ValueError, match="must be from same source"):
            LiquidationBatch(
                batch_id="batch_test_001",
                events=[event1, event2],
                batch_timestamp=datetime.now(UTC),
                source="binance_websocket",
                total_usd_volume=67500.0,
            )


class TestBinanceLiquidationCollector:
    """Binance liquidation collector tests (mocked data)."""

    def test_collector_initialization(self) -> None:
        """Initialize collector."""
        collector = BinanceLiquidationCollector()

        assert collector.stream_url == "wss://fstream.binance.com/ws/!forceOrder@arr"
        assert collector.reconnect_attempts == 10
        assert len(collector.events) == 0
        assert not collector.connected

    def test_parse_binance_message_long_liquidation(self) -> None:
        """Parse Binance long liquidation message."""
        collector = BinanceLiquidationCollector()

        # Binance SELL liquidation (long gets liquidated)
        message = """{
            "e": "forceOrder",
            "E": 1695552668532,
            "o": {
                "s": "BTCUSDT",
                "S": "SELL",
                "o": "LIQUIDATION",
                "f": "IOC",
                "q": "1.5",
                "p": "65000.00",
                "ap": "64999.50",
                "X": "FILLED",
                "l": "1.5",
                "z": "1.5",
                "T": 1695552668532,
                "i": 12345
            }
        }"""

        collector._process_message(message)

        assert len(collector.events) == 1
        event = collector.events[0]
        assert event.symbol == "BTCUSDT"
        assert event.side == "long"
        assert event.quantity == 1.5
        assert event.price == 65000.0

    def test_parse_binance_message_short_liquidation(self) -> None:
        """Parse Binance short liquidation message."""
        collector = BinanceLiquidationCollector()

        # Binance BUY liquidation (short gets liquidated)
        message = """{
            "e": "forceOrder",
            "E": 1695552668532,
            "o": {
                "s": "ETHUSDT",
                "S": "BUY",
                "o": "LIQUIDATION",
                "q": "10.0",
                "p": "2500.00",
                "i": 12346
            }
        }"""

        collector._process_message(message)

        assert len(collector.events) == 1
        event = collector.events[0]
        assert event.symbol == "ETHUSDT"
        assert event.side == "short"
        assert event.quantity == 10.0

    def test_parse_binance_message_array(self) -> None:
        """Parse Binance message with array of force orders."""
        collector = BinanceLiquidationCollector()

        message = """[
            {
                "e": "forceOrder",
                "E": 1695552668532,
                "o": {"s": "BTCUSDT", "S": "SELL", "q": "1.5", "p": "65000.00", "i": 1}
            },
            {
                "e": "forceOrder",
                "E": 1695552668533,
                "o": {"s": "ETHUSDT", "S": "BUY", "q": "10.0", "p": "2500.00", "i": 2}
            }
        ]"""

        collector._process_message(message)

        assert len(collector.events) == 2

    def test_collector_get_stats(self) -> None:
        """Get collection statistics."""
        collector = BinanceLiquidationCollector()

        # Add events
        for i in range(5):
            event = LiquidationEvent(
                timestamp=datetime.now(UTC),
                symbol="BTCUSDT" if i % 2 == 0 else "ETHUSDT",
                side="long" if i % 2 == 0 else "short",
                quantity=1.0,
                price=65000.0 if i % 2 == 0 else 2500.0,
                source="binance_websocket",
                source_id=f"evt_{i}",
            )
            collector.events.append(event)

        stats = collector.get_stats()

        assert stats["total_events"] == 5
        assert "BTCUSDT" in stats["symbols"]
        assert "ETHUSDT" in stats["symbols"]
        assert stats["long_liquidations"] == 3
        assert stats["short_liquidations"] == 2
        assert stats["total_usd_volume"] > 0


class TestLiquidationStore:
    """LiquidationStore DuckDB persistence tests."""

    def test_store_initialization(self, tmp_path) -> None:
        """Initialize store."""
        db_path = str(tmp_path / "test.duckdb")
        store = LiquidationStore(db_path=db_path)

        stats = store.get_stats()
        assert stats["total_events"] == 0

        store.close()

    def test_insert_batch(self, tmp_path) -> None:
        """Insert liquidation batch."""
        db_path = str(tmp_path / "test.duckdb")
        store = LiquidationStore(db_path=db_path)

        event = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 8, 532000, tzinfo=UTC),
            symbol="BTCUSDT",
            side="long",
            quantity=1.5,
            price=65000.0,
            source="binance_websocket",
            source_id="evt_1",
        )

        batch = LiquidationBatch(
            batch_id="batch_001",
            events=[event],
            batch_timestamp=datetime.now(UTC),
            source="binance_websocket",
            total_usd_volume=97500.0,
        )

        inserted = store.insert_batch(batch)

        assert inserted == 1
        stats = store.get_stats()
        assert stats["total_events"] == 1
        assert stats["long_liquidations"] == 1

        store.close()

    def test_duplicate_prevention(self, tmp_path) -> None:
        """Verify duplicate source_ids are prevented."""
        db_path = str(tmp_path / "test.duckdb")
        store = LiquidationStore(db_path=db_path)

        event = LiquidationEvent(
            timestamp=datetime(2026, 9, 25, 18, 31, 8, 532000, tzinfo=UTC),
            symbol="BTCUSDT",
            side="long",
            quantity=1.5,
            price=65000.0,
            source="binance_websocket",
            source_id="evt_unique",
        )

        batch1 = LiquidationBatch(
            batch_id="batch_001",
            events=[event],
            batch_timestamp=datetime.now(UTC),
            source="binance_websocket",
            total_usd_volume=97500.0,
        )

        batch2 = LiquidationBatch(
            batch_id="batch_002",
            events=[event],  # Same source_id!
            batch_timestamp=datetime.now(UTC),
            source="binance_websocket",
            total_usd_volume=97500.0,
        )

        # First insert succeeds
        store.insert_batch(batch1)
        stats1 = store.get_stats()
        assert stats1["total_events"] == 1

        # Second insert is skipped (duplicate) — verify via stats
        store.insert_batch(batch2)
        stats2 = store.get_stats()
        assert stats2["total_events"] == 1  # Still 1, not 2 (duplicate prevented)

        store.close()

    def test_get_raw_events(self, tmp_path) -> None:
        """Retrieve raw events from store."""
        db_path = str(tmp_path / "test.duckdb")
        store = LiquidationStore(db_path=db_path)

        events = [
            LiquidationEvent(
                timestamp=datetime(2026, 9, 25, 18, 31, i, tzinfo=UTC),
                symbol="BTCUSDT",
                side="long",
                quantity=1.0,
                price=65000.0,
                source="binance_websocket",
                source_id=f"evt_{i}",
            )
            for i in range(3)
        ]

        batch = LiquidationBatch(
            batch_id="batch_001",
            events=events,
            batch_timestamp=datetime.now(UTC),
            source="binance_websocket",
            total_usd_volume=3 * 65000.0,
        )

        store.insert_batch(batch)
        retrieved = store.get_raw_events(limit=10)

        assert len(retrieved) == 3
        assert all(e["symbol"] == "BTCUSDT" for e in retrieved)

        store.close()
