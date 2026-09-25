"""
Parquet storage for OHLCV data.

Immutable raw data storage with metadata preservation.
Phase 2: Write normalized candles to parquet with full provenance.
"""

import os
from pathlib import Path
from typing import List
from datetime import datetime, timezone
import json

import pyarrow as pa
import pyarrow.parquet as pq

from src.data.schemas.types import OHLCV, Provenance
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
        availability_ts = prov.availability_timestamp.isoformat() if prov.availability_timestamp else None
        metadata = {
            "provider": provider.encode(),
            "symbol": symbol.encode(),
            "timeframe": timeframe.encode(),
            "record_count": str(len(ohlcv_list)).encode(),
            "first_timestamp": timestamps[0].isoformat().encode(),
            "last_timestamp": timestamps[-1].isoformat().encode(),
            "first_provenance": json.dumps(provenance_jsons[0]).encode(),
            "availability_timestamp": availability_ts.encode() if availability_ts else b"",
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
        """
        Read OHLCV from parquet file with full provenance reconstruction.

        Returns OHLCV list with provenance restored from metadata.
        """
        table = pq.read_table(str(path))
        metadata = table.schema.metadata or {}

        # Reconstruct provenance from metadata
        prov_dict = json.loads(metadata.get(b"first_provenance", b"{}").decode())

        # Parse optional timestamps with fallback
        def parse_ts(ts_str):
            return datetime.fromisoformat(ts_str) if ts_str else None

        retrieval_ts = parse_ts(prov_dict.get("retrieval_timestamp"))
        availability_ts = parse_ts(metadata.get(b"availability_timestamp", b"").decode()) or prov_dict.get("availability_timestamp")
        if isinstance(availability_ts, str):
            availability_ts = parse_ts(availability_ts)
        event_ts = parse_ts(prov_dict.get("event_timestamp"))

        # Build base provenance (all candles share source/endpoint info)
        base_prov = Provenance(
            source=prov_dict.get("source", "unknown"),
            provider=prov_dict.get("provider", "unknown"),
            endpoint=prov_dict.get("endpoint", "unknown"),
            retrieval_timestamp=retrieval_ts or datetime.now(timezone.utc),
            event_timestamp=event_ts or datetime.now(timezone.utc),
            availability_timestamp=availability_ts,
            symbol=prov_dict.get("symbol", "unknown"),
            timeframe=prov_dict.get("timeframe", "unknown"),
            schema_version=prov_dict.get("schema_version", "1.0"),
            data_version=prov_dict.get("data_version", ""),
            caveats=prov_dict.get("caveats"),
        )

        ohlcv_list = []
        for i in range(len(table)):
            ts = table["timestamp"][i].as_py()

            # Create per-candle provenance with event_timestamp from row
            prov = Provenance(
                source=base_prov.source,
                provider=base_prov.provider,
                endpoint=base_prov.endpoint,
                retrieval_timestamp=base_prov.retrieval_timestamp,
                event_timestamp=ts,
                availability_timestamp=base_prov.availability_timestamp,
                symbol=base_prov.symbol,
                timeframe=base_prov.timeframe,
                schema_version=base_prov.schema_version,
                data_version=base_prov.data_version,
                caveats=base_prov.caveats,
            )

            candle = OHLCV(
                timestamp=ts,
                open=table["open"][i].as_py(),
                high=table["high"][i].as_py(),
                low=table["low"][i].as_py(),
                close=table["close"][i].as_py(),
                volume=table["volume"][i].as_py(),
                provenance=prov,
            )
            ohlcv_list.append(candle)

        return sorted(ohlcv_list, key=lambda x: x.timestamp)
