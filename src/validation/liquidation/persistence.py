"""Liquidation event persistence — DuckDB storage for raw events.

Tables:
- liquidation_raw: Immutable raw events (append-only)
- liquidation_qa_reports: QA audit trail

PIT compliance:
- All timestamps preserved (millisecond precision)
- Immutable raw store (no updates, only inserts)
- Audit trail for all operations
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from src.validation.liquidation.contracts import LiquidationBatch, LiquidationQAReport

logger = logging.getLogger(__name__)


class LiquidationStore:
    """DuckDB storage for liquidation events."""

    def __init__(self, db_path: str = "data/liquidation.duckdb") -> None:
        """Initialize DuckDB connection.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        # Raw liquidation events (immutable, append-only)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS liquidation_raw (
                timestamp TIMESTAMP,
                symbol VARCHAR,
                side VARCHAR,  -- 'long' or 'short'
                quantity DOUBLE,
                price DOUBLE,
                usd_value DOUBLE,
                source VARCHAR,
                source_id VARCHAR PRIMARY KEY,
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # QA reports audit trail
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS liquidation_qa_reports (
                qa_id VARCHAR PRIMARY KEY,
                total_events BIGINT,
                duplicates_found BIGINT,
                outliers_flagged BIGINT,
                gaps_identified BIGINT,
                source_reliability_score DOUBLE,
                data_quality_score DOUBLE,
                timestamp TIMESTAMP,
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        logger.info("Liquidation schema initialized")

    def insert_batch(self, batch: LiquidationBatch) -> int:
        """Insert liquidation batch (immutable append).

        Args:
            batch: LiquidationBatch to insert

        Returns:
            Number of rows inserted

        Raises:
            ValueError: If duplicate source_ids found
        """
        # Check for duplicates in batch
        source_ids = [e.source_id for e in batch.events]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Batch contains duplicate source_ids")

        # Check for duplicates in database
        placeholders = ",".join([f"'{sid}'" for sid in source_ids])
        existing = self.conn.execute(
            f"SELECT COUNT(*) as cnt FROM liquidation_raw WHERE source_id IN ({placeholders})"
        ).fetchall()

        if existing[0][0] > 0:
            logger.warning(f"Skipping {existing[0][0]} duplicate events")

        # Insert new events
        inserted = 0
        for event in batch.events:
            try:
                self.conn.execute(
                    """
                    INSERT INTO liquidation_raw
                    (timestamp, symbol, side, quantity, price, usd_value, source, source_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                    """,
                    [
                        event.timestamp,
                        event.symbol,
                        event.side,
                        event.quantity,
                        event.price,
                        event.usd_value,
                        event.source,
                        event.source_id,
                    ],
                )
                inserted += 1
            except Exception as e:
                logger.error(f"Error inserting event {event.source_id}: {e}")

        self.conn.commit()
        logger.info(f"Inserted {inserted} liquidation events")
        return inserted

    def insert_qa_report(self, report: LiquidationQAReport) -> None:
        """Insert QA report (audit trail).

        Args:
            report: LiquidationQAReport to insert
        """
        qa_id = f"qa_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        self.conn.execute(
            """
            INSERT INTO liquidation_qa_reports
            (qa_id, total_events, duplicates_found, outliers_flagged, gaps_identified,
             source_reliability_score, data_quality_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                qa_id,
                report.total_events,
                report.duplicates_found,
                report.outliers_flagged,
                report.gaps_identified,
                report.source_reliability_score,
                report.data_quality_score,
                report.timestamp,
            ],
        )
        self.conn.commit()
        logger.info(f"QA report {qa_id} inserted")

    def get_raw_events(self, limit: int = 1000) -> list[dict]:
        """Get raw liquidation events (PIT compliance).

        Args:
            limit: Max rows to return

        Returns:
            List of liquidation events
        """
        result = self.conn.execute(
            f"SELECT * FROM liquidation_raw ORDER BY timestamp DESC LIMIT {limit}"
        ).fetchall()

        columns = ["timestamp", "symbol", "side", "quantity", "price", "usd_value", "source", "source_id", "inserted_at"]
        return [dict(zip(columns, row)) for row in result]

    def get_stats(self) -> dict:
        """Get liquidation store statistics.

        Returns:
            Stats including total events, date range, volume
        """
        result = self.conn.execute(
            """
            SELECT
                COUNT(*) as total_events,
                MIN(timestamp) as first_timestamp,
                MAX(timestamp) as last_timestamp,
                SUM(usd_value) as total_usd_volume,
                COUNT(DISTINCT symbol) as unique_symbols,
                SUM(CASE WHEN side = 'long' THEN 1 ELSE 0 END) as long_count,
                SUM(CASE WHEN side = 'short' THEN 1 ELSE 0 END) as short_count
            FROM liquidation_raw
            """
        ).fetchall()

        row = result[0]
        return {
            "total_events": row[0],
            "first_timestamp": row[1],
            "last_timestamp": row[2],
            "total_usd_volume": row[3],
            "unique_symbols": row[4],
            "long_liquidations": row[5],
            "short_liquidations": row[6],
        }

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
        logger.info("Database connection closed")
