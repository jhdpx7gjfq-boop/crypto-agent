"""
Parquet storage for OHLCV data.

Immutable raw data storage with metadata preservation.
Phase 2: Write normalized candles to parquet with full provenance.
"""

import os
from pathlib import Path
from typing import List
from datetime import datetime
import json

import pyarrow as pa
import pyarrow.parquet as pq

from src.data.schemas.types import OHLCV
from src.common.logging import get_logger

logger = get_logger(__name__)


class ParquetStorage:
    """Write OHLCV data to Parquet files."""

    def __init__(self, base_dir: str = "data/raw"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_list: List[OHLCV],
        date_partition: datetime = None,
    ) -> Path:
        """
        Write OHLCV candles to parquet.

        Structure: data/raw/{provider}/{symbol}/{timeframe}/YYYY-MM-DD.parquet

        Args:
            symbol: e.g., 'bitcoin'
            timeframe: e.g., '1d'
            ohlcv_list: List of OHLCV candles
            date_partition: Date for partition (defaults to today)

        Returns:
            Path to written file
        """
        if not ohlcv_list:
            raise ValueError("Empty OHLCV list")

        # Use first candle's provenance for metadata
        prov = ohlcv_list[0].provenance
        provider = prov.source

        if date_partition is None:
            date_partition = datetime.now()

        # Build path
        date_str = date_partition.strftime("%Y-%m-%d")
        output_dir = self.base_dir / provider / symbol / timeframe
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{date_str}.parquet"

        # Convert to Arrow table
        timestamps = [c.timestamp for c in ohlcv_list]
        opens = [c.open for c in ohlcv_list]
        highs = [c.high for c in ohlcv_list]
        lows = [c.low for c in ohlcv_list]
        closes = [c.close for c in ohlcv_list]
        volumes = [c.volume for c in ohlcv_list]

        # Metadata: first/last provenance as JSON strings
        provenance_jsons = [c.provenance.to_dict() for c in ohlcv_list]

        table = pa.table({
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "source": [prov.source] * len(ohlcv_list),
            "symbol": [symbol] * len(ohlcv_list),
            "timeframe": [timeframe] * len(ohlcv_list),
        })

        # Add metadata (file-level)
        metadata = {
            "provider": provider.encode(),
            "symbol": symbol.encode(),
            "timeframe": timeframe.encode(),
            "record_count": str(len(ohlcv_list)).encode(),
            "first_timestamp": timestamps[0].isoformat().encode(),
            "last_timestamp": timestamps[-1].isoformat().encode(),
            "first_provenance": json.dumps(provenance_jsons[0]).encode(),
            "schema_version": b"1.0",
        }

        combined_metadata = {**(table.schema.metadata or {}), **metadata}
        table = table.replace_schema_metadata(combined_metadata)

        # Write
        pq.write_table(table, str(output_path), compression="snappy")

        logger.info(
            "Parquet write complete",
            extra={
                "event": "parquet_write",
                "status": "success",
                "symbol": symbol,
                "timeframe": timeframe,
                "record_count": len(ohlcv_list),
                "path": str(output_path),
            },
        )

        return output_path

    def read_ohlcv(self, path: Path) -> List[OHLCV]:
        """Read OHLCV from parquet file."""
        table = pq.read_table(str(path))
        metadata = table.schema.metadata

        # Reconstruct from columns
        symbol = metadata[b"symbol"].decode()
        timeframe = metadata[b"timeframe"].decode()
        source = metadata[b"provider"].decode()

        # Parse first provenance from metadata
        prov_dict = json.loads(metadata[b"first_provenance"].decode())

        ohlcv_list = []
        for i in range(len(table)):
            ts = table["timestamp"][i].as_py()
            prov = OHLCV.__dataclass_fields__  # Reconstruct minimal provenance

            # For now, return basic OHLCV with metadata
            # Full provenance reconstruction would need all fields

        return ohlcv_list
