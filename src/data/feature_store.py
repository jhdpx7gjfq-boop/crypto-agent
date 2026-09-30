"""
Feature Store - Centralized feature repository for Layers 1-7
Version: 2.0.0

DuckDB-backed storage for OHLCV, Layer 1-7 features, and backtest results.
Supports multi-asset, walk-forward validation, and schema versioning.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from uuid import uuid4

import duckdb
import pandas as pd

from src.data.feature_schema import (
    SCHEMA_VERSION,
    get_schema,
    get_all_schemas,
    get_constraints,
    validate_layer_data,
)

logger = logging.getLogger(__name__)

VERSION = "2.0.0"


class FeatureStore:
    """
    Centralized feature store for all 7 layers.

    Manages:
    - Layer 1 (OHLCV): Raw market data
    - Layer 3 (BCE): Wyckoff bottom confirmation scores
    - Layer 4 (X20): Opportunity detection scores
    - Layer 5 (NARM): Narrative + adoption + rotation
    - Layer 6 (RCM): Capital rotation with walk-forward validation
    - Layer 7 (RRP): Revival radar scores
    - Backtest results with validation constraints
    """

    def __init__(self, db_path: str = "data/features.duckdb"):
        self.db_path = db_path
        self.version = VERSION
        self.schema_version = SCHEMA_VERSION

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(self.db_path)
        self._init_schemas()
        logger.info(f"FeatureStore initialized (v{VERSION}, schema v{SCHEMA_VERSION})")

    def _init_schemas(self):
        """Initialize all layer schemas."""
        schemas = get_all_schemas()
        for layer_key, schema_meta in schemas.items():
            try:
                self.conn.execute(schema_meta["definition"])
                logger.debug(f"Schema initialized: {schema_meta['name']}")
            except Exception as e:
                logger.error(f"Failed to initialize {schema_meta['name']}: {e}")
                raise

    # Layer 1: OHLCV
    def insert_layer1(self, asset: str, df: pd.DataFrame) -> int:
        """Insert OHLCV data for an asset."""
        df = df.copy()
        df["asset"] = asset
        df = df[["timestamp", "asset", "open", "high", "low", "close", "volume"]]

        # Validate rows
        errors = []
        for idx, row in df.iterrows():
            valid, row_errors = validate_layer_data("layer1", row.to_dict())
            if not valid:
                errors.extend([f"Row {idx}: {e}" for e in row_errors])

        if errors:
            logger.warning(f"Layer1 validation warnings for {asset}: {errors[:3]}")

        self.conn.execute("INSERT OR REPLACE INTO features_layer1 SELECT * FROM df")
        logger.info(f"Ingested {len(df)} Layer1 candles for {asset}")
        return len(df)

    def query_layer1(
        self,
        asset: str,
        start_ms: int = None,
        end_ms: int = None,
        limit: int = None,
    ) -> pd.DataFrame:
        """Query OHLCV data for an asset."""
        query = "SELECT * FROM features_layer1 WHERE asset = $1"
        params = [asset]

        if start_ms:
            query += f" AND timestamp >= $2"
            params.append(start_ms)

        if end_ms:
            query += f" AND timestamp <= ${len(params) + 1}"
            params.append(end_ms)

        query += " ORDER BY timestamp ASC"

        if limit:
            query += f" LIMIT {limit}"

        return self.conn.execute(query, params).fetch_df()

    # Generic Layer CRUD
    def insert_layer_features(self, layer: str, asset: str, df: pd.DataFrame) -> int:
        """Insert features for any layer."""
        if layer not in ["layer3", "layer4", "layer5", "layer6", "layer7"]:
            raise ValueError(f"Invalid layer: {layer}")

        schema = get_schema(layer)
        table_name = schema["name"]
        df = df.copy()
        df["asset"] = asset

        # Validate
        errors = []
        for idx, row in df.iterrows():
            valid, row_errors = validate_layer_data(layer, row.to_dict())
            if not valid:
                errors.extend([f"Row {idx}: {e}" for e in row_errors])

        if errors:
            logger.warning(f"{layer} validation warnings: {errors[:3]}")

        self.conn.execute(f"INSERT OR REPLACE INTO {table_name} SELECT * FROM df")
        logger.info(f"Ingested {len(df)} {layer} features for {asset}")
        return len(df)

    def query_layer_features(
        self,
        layer: str,
        asset: str,
        start_ms: int = None,
        end_ms: int = None,
        min_score: float = None,
        valid_only: bool = False,
    ) -> pd.DataFrame:
        """Query features for any layer."""
        if layer not in ["layer3", "layer4", "layer5", "layer6", "layer7"]:
            raise ValueError(f"Invalid layer: {layer}")

        schema = get_schema(layer)
        table_name = schema["name"]
        score_field = f"{layer.replace('layer', '')}_score"

        query = f"SELECT * FROM {table_name} WHERE asset = $1"
        params = [asset]

        if start_ms:
            query += f" AND timestamp >= ${len(params) + 1}"
            params.append(start_ms)

        if end_ms:
            query += f" AND timestamp <= ${len(params) + 1}"
            params.append(end_ms)

        if min_score is not None and score_field in ["3_score", "4_score", "5_score", "6_score", "7_score"]:
            actual_field = f"{['bce', 'x20', 'narm', 'rcm', 'rrp'][int(layer[-1]) - 3]}_score"
            query += f" AND {actual_field} >= ${len(params) + 1}"
            params.append(min_score)

        if valid_only:
            query += " AND valid = TRUE"

        query += " ORDER BY timestamp ASC"

        return self.conn.execute(query, params).fetch_df()

    def get_stats(self, layer: str, asset: str) -> Dict:
        """Get statistics for a layer/asset."""
        if layer == "layer1":
            query = """
            SELECT
              COUNT(*) as total_records,
              MIN(timestamp) as earliest,
              MAX(timestamp) as latest,
              MIN(close) as min_price,
              MAX(close) as max_price,
              AVG(volume) as avg_volume
            FROM features_layer1
            WHERE asset = $1
            """
        else:
            schema = get_schema(layer)
            table_name = schema["name"]
            score_field = {"layer3": "bce_score", "layer4": "x20_score", "layer5": "narm_score",
                         "layer6": "rcm_score", "layer7": "rrp_score"}[layer]

            query = f"""
            SELECT
              COUNT(*) as total_records,
              SUM(CASE WHEN valid = TRUE THEN 1 ELSE 0 END) as valid_records,
              MIN(timestamp) as earliest,
              MAX(timestamp) as latest,
              MIN({score_field}) as min_score,
              MAX({score_field}) as max_score,
              AVG({score_field}) as avg_score
            FROM {table_name}
            WHERE asset = $1
            """

        result = self.conn.execute(query, [asset]).fetch_df()
        if result.empty:
            return {}

        return result.iloc[0].to_dict()

    # Backtest Results
    def insert_backtest_result(
        self,
        asset: str,
        start_date: str,
        end_date: str,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        profit_factor: float,
        max_drawdown: float,
        sharpe_ratio: float,
        wfv_pass: bool = False,
    ) -> str:
        """Insert a backtest result. Returns test_id."""
        test_id = str(uuid4())
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # Validate constraints
        constraints = get_constraints("backtest")["validation"]
        status = "PASS" if (
            total_trades >= constraints["min_trades"]
            and profit_factor > constraints["profit_factor"][1]
            and max_drawdown < constraints["max_drawdown"][1]
            and wfv_pass
        ) else "FAIL"

        query = """
        INSERT INTO backtest_results (
            test_id, asset, start_date, end_date,
            total_trades, winning_trades, losing_trades,
            profit_factor, max_drawdown, sharpe_ratio, win_rate,
            wfv_pass, validation_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.conn.execute(
            query,
            [
                test_id, asset, start_date, end_date,
                total_trades, winning_trades, losing_trades,
                profit_factor, max_drawdown, sharpe_ratio, win_rate,
                wfv_pass, status,
            ],
        )

        logger.info(f"Backtest result saved: {test_id} ({asset}, {status})")
        return test_id

    def get_backtest_results(
        self,
        asset: str = None,
        status: str = None,
        wfv_pass_only: bool = False,
    ) -> pd.DataFrame:
        """Query backtest results."""
        query = "SELECT * FROM backtest_results WHERE 1=1"
        params = []

        if asset:
            query += " AND asset = ?"
            params.append(asset)

        if status:
            query += " AND validation_status = ?"
            params.append(status)

        if wfv_pass_only:
            query += " AND wfv_pass = TRUE"

        query += " ORDER BY created_at DESC"

        return self.conn.execute(query, params).fetch_df()

    def export_layer_parquet(
        self,
        layer: str,
        asset: str,
        output_path: str,
    ) -> None:
        """Export layer features to Parquet."""
        if layer == "layer1":
            table_name = "features_layer1"
        else:
            table_name = get_schema(layer)["name"]

        query = f"SELECT * FROM {table_name} WHERE asset = '{asset}' ORDER BY timestamp"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn.execute(f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)")
        logger.info(f"Exported {layer} ({asset}) to {output_path}")

    def export_merged_parquet(
        self,
        asset: str,
        output_path: str,
        include_layers: List[str] = None,
    ) -> None:
        """Export merged view of multiple layers to Parquet."""
        if include_layers is None:
            include_layers = ["layer1", "layer3", "layer4", "layer5", "layer6", "layer7"]

        # Start with layer1
        query = "SELECT * FROM features_layer1 WHERE asset = $1"
        params = [asset]

        # Left join other layers
        join_index = 2
        for layer in include_layers:
            if layer == "layer1":
                continue
            table_name = get_schema(layer)["name"]
            query += f"""
            LEFT JOIN {table_name} l{join_index}
              ON features_layer1.timestamp = l{join_index}.timestamp
              AND features_layer1.asset = l{join_index}.asset
            """
            join_index += 1

        query += " ORDER BY features_layer1.timestamp"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn.execute(f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)", params)
        logger.info(f"Exported merged view ({asset}, {include_layers}) to {output_path}")

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
