"""
DuckDB schema and query interface for OHLCV data.

Phase 2: Analytical queries over raw data.
"""

import duckdb
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

from src.common.logging import get_logger

logger = get_logger(__name__)


class DuckDBStore:
    """DuckDB interface for analytical queries."""

    def __init__(self, db_path: str = "data/duckdb/igwt.duckdb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))

        # Enable extensions
        self.conn.execute("INSTALL json")
        self.conn.execute("LOAD json")

        self._init_schema()

    def _init_schema(self):
        """Create tables if they don't exist."""
        # Raw OHLCV data
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                timestamp TIMESTAMP NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume DOUBLE NOT NULL,
                source VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)

        # Metadata and versioning
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS data_metadata (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_metadata'),
                symbol VARCHAR NOT NULL,
                timeframe VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                loaded_timestamp TIMESTAMP NOT NULL DEFAULT now(),
                record_count INTEGER NOT NULL,
                first_timestamp TIMESTAMP NOT NULL,
                last_timestamp TIMESTAMP NOT NULL,
                file_path VARCHAR
            )
        """)

        logger.info("DuckDB schema initialized", extra={"event": "schema_init", "status": "success"})

    def load_parquet(self, parquet_path: str, symbol: str, timeframe: str):
        """Load parquet file into DuckDB."""
        parquet_path = Path(parquet_path)
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        # Insert from parquet
        self.conn.execute(f"""
            INSERT INTO ohlcv
            SELECT timestamp, open, high, low, close, volume, source, symbol, timeframe
            FROM read_parquet('{parquet_path}')
        """)

        # Record metadata
        result = self.conn.execute("""
            SELECT COUNT(*) as cnt, MIN(timestamp) as first, MAX(timestamp) as last
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
        """, [symbol, timeframe]).fetchall()

        if result:
            cnt, first, last = result[0]
            self.conn.execute("""
                INSERT INTO data_metadata
                (symbol, timeframe, source, record_count, first_timestamp, last_timestamp, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [symbol, timeframe, "coingecko", cnt, first, last, str(parquet_path)])

        logger.info(
            "Parquet loaded to DuckDB",
            extra={
                "event": "parquet_load",
                "status": "success",
                "symbol": symbol,
                "file_path": str(parquet_path),
            },
        )

    def get_candles(self, symbol: str, timeframe: str, limit: int = None) -> List[Dict[str, Any]]:
        """Fetch candles for a symbol/timeframe."""
        query = f"""
            SELECT timestamp, open, high, low, close, volume, source
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            {f"LIMIT {limit}" if limit else ""}
        """

        results = self.conn.execute(query, [symbol, timeframe]).fetchall()

        return [
            {
                "timestamp": r[0],
                "open": r[1],
                "high": r[2],
                "low": r[3],
                "close": r[4],
                "volume": r[5],
                "source": r[6],
            }
            for r in results
        ]

    def get_symbols(self) -> List[str]:
        """List all available symbols."""
        results = self.conn.execute(
            "SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol"
        ).fetchall()
        return [r[0] for r in results]

    def get_timeframes(self, symbol: str = None) -> List[str]:
        """List available timeframes."""
        if symbol:
            results = self.conn.execute(
                "SELECT DISTINCT timeframe FROM ohlcv WHERE symbol = ? ORDER BY timeframe",
                [symbol],
            ).fetchall()
        else:
            results = self.conn.execute(
                "SELECT DISTINCT timeframe FROM ohlcv ORDER BY timeframe"
            ).fetchall()

        return [r[0] for r in results]

    def get_price_range(self, symbol: str, timeframe: str) -> Dict[str, float]:
        """Get min/max/avg price for a symbol."""
        result = self.conn.execute(
            """
            SELECT MIN(low), MAX(high), AVG(close), COUNT(*)
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
        """,
            [symbol, timeframe],
        ).fetchone()

        if not result or result[0] is None:
            return {}

        return {
            "min_price": result[0],
            "max_price": result[1],
            "avg_price": result[2],
            "candle_count": result[3],
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
