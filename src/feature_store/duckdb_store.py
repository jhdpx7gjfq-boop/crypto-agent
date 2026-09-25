"""DuckDB-based Feature Store implementation."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.data.contracts import RawDataBatch
from src.utils.logging import get_logger

from .base import FeatureMetadata, FeatureSnapshot, FeatureStore

logger = get_logger(__name__)


class DuckDBFeatureStore(FeatureStore):
    """Feature Store backed by DuckDB."""

    def __init__(self, db_path: Path) -> None:
        """Initialize DuckDB Feature Store.

        Args:
            db_path: Path to DuckDB database file.
        """
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize DuckDB schema."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feature_snapshots (
                feature_name VARCHAR NOT NULL,
                asset VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                value DOUBLE NOT NULL,
                compute_timestamp TIMESTAMP NOT NULL,
                source_version VARCHAR NOT NULL,
                provenance VARCHAR,
                PRIMARY KEY (feature_name, asset, timestamp)
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feature_metadata (
                feature_name VARCHAR PRIMARY KEY,
                description VARCHAR NOT NULL,
                computation_spec VARCHAR NOT NULL,
                source_table VARCHAR NOT NULL,
                created_timestamp TIMESTAMP NOT NULL,
                version VARCHAR NOT NULL
            )
            """
        )
        logger.info("Feature Store schema initialized")

    def ingest_raw(self, batch: RawDataBatch) -> None:
        """Ingest raw data batch.

        Args:
            batch: RawDataBatch.
        """
        if not batch.datapoints:
            raise ValueError("Batch must contain at least one datapoint")

        for point in batch.datapoints:
            try:
                self.conn.execute(
                    """
                    INSERT INTO feature_snapshots
                    (feature_name, asset, timestamp, value, compute_timestamp,
                     source_version, provenance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        "raw_" + point.metric,
                        point.asset,
                        point.timestamp,
                        point.value,
                        datetime.now(UTC),
                        point.source_version,
                        f'{{"source": "{point.source}", '
                        f'"metric": "{point.metric}", '
                        f'"currency": "{point.currency}"}}',
                    ],
                )
            except Exception as e:
                logger.warning(
                    "Failed to ingest datapoint",
                    extra={
                        "extra_fields": {
                            "asset": point.asset,
                            "metric": point.metric,
                            "timestamp": point.timestamp.isoformat(),
                            "error": str(e),
                        }
                    },
                )

    def compute_feature(
        self,
        feature_name: str,
        asset: str,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> pd.DataFrame:
        """Compute feature over window.

        Args:
            feature_name: Feature name.
            asset: Asset.
            start_timestamp: Window start.
            end_timestamp: Window end.

        Returns:
            DataFrame with timestamp, value columns.
        """
        if start_timestamp >= end_timestamp:
            raise ValueError("start_timestamp must be < end_timestamp")

        result = self.conn.execute(
            """
            SELECT timestamp, value
            FROM feature_snapshots
            WHERE feature_name = ? AND asset = ?
                AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            [feature_name, asset, start_timestamp, end_timestamp],
        ).fetchall()

        if not result:
            return pd.DataFrame(columns=["timestamp", "value"])

        return pd.DataFrame(result, columns=["timestamp", "value"])

    def retrieve_features(
        self,
        assets: list[str],
        features: list[str],
        start_timestamp: datetime,
        end_timestamp: datetime,
        lookback: timedelta | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Retrieve features.

        Args:
            assets: List of assets.
            features: List of feature names.
            start_timestamp: Window start.
            end_timestamp: Window end.
            lookback: Optional lookback period.

        Returns:
            Dict mapping asset -> DataFrame with feature columns.
        """
        if start_timestamp >= end_timestamp:
            raise ValueError("start_timestamp must be < end_timestamp")

        actual_start = start_timestamp
        if lookback:
            actual_start = start_timestamp - lookback

        result_dict: dict[str, pd.DataFrame] = {}

        for asset in assets:
            dfs = []
            for feature in features:
                df = self.compute_feature(
                    feature, asset, actual_start, end_timestamp
                )
                if not df.empty:
                    df = df.rename(columns={"value": feature})
                    df = df[["timestamp", feature]]
                    dfs.append(df)

            if dfs:
                merged = dfs[0]
                for df in dfs[1:]:
                    merged = merged.merge(
                        df, on="timestamp", how="outer"
                    )
                result_dict[asset] = merged.sort_values("timestamp")
            else:
                result_dict[asset] = pd.DataFrame(columns=["timestamp", *features])

        return result_dict

    def persist_snapshot(
        self,
        snapshot: FeatureSnapshot,
    ) -> None:
        """Persist feature snapshot.

        Args:
            snapshot: FeatureSnapshot.
        """
        try:
            import json

            self.conn.execute(
                """
                INSERT INTO feature_snapshots
                (feature_name, asset, timestamp, value, compute_timestamp,
                 source_version, provenance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    snapshot.feature_name,
                    snapshot.asset,
                    snapshot.timestamp,
                    snapshot.value,
                    snapshot.compute_timestamp,
                    snapshot.source_version,
                    json.dumps(snapshot.provenance),
                ],
            )
        except Exception as e:
            logger.warning(
                "Failed to persist feature snapshot",
                extra={
                    "extra_fields": {
                        "feature": snapshot.feature_name,
                        "asset": snapshot.asset,
                        "timestamp": snapshot.timestamp.isoformat(),
                        "error": str(e),
                    }
                },
            )

    def get_provenance(
        self,
        feature_name: str,
        asset: str,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """Get provenance for a snapshot.

        Args:
            feature_name: Feature name.
            asset: Asset.
            timestamp: Timestamp.

        Returns:
            Provenance dict.
        """
        result = self.conn.execute(
            """
            SELECT provenance, compute_timestamp, source_version
            FROM feature_snapshots
            WHERE feature_name = ? AND asset = ? AND timestamp = ?
            """,
            [feature_name, asset, timestamp],
        ).fetchall()

        if not result:
            raise ValueError(f"Snapshot not found: {feature_name}/{asset}/{timestamp}")

        import json

        prov_str, compute_ts, version = result[0]
        prov = json.loads(prov_str) if prov_str else {}
        prov["compute_timestamp"] = compute_ts.isoformat()
        prov["source_version"] = version
        return prov

    def register_feature_metadata(self, metadata: FeatureMetadata) -> None:
        """Register feature metadata.

        Args:
            metadata: FeatureMetadata.
        """
        import json

        try:
            self.conn.execute(
                """
                INSERT INTO feature_metadata
                (feature_name, description, computation_spec, source_table,
                 created_timestamp, version)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    metadata.feature_name,
                    metadata.description,
                    json.dumps(metadata.computation_spec),
                    metadata.source_table,
                    metadata.created_timestamp,
                    metadata.version,
                ],
            )
        except Exception as e:
            logger.warning(
                "Failed to register feature metadata",
                extra={
                    "extra_fields": {
                        "feature": metadata.feature_name,
                        "error": str(e),
                    }
                },
            )

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
