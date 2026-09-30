"""
Feature Enrichment Pipeline (Phase 2 Component 4)
Version: 1.0.0

Orchestrates computation of Layer 1-7 features from raw OHLCV data.

Pipeline Flow:
1. Ingest raw OHLCV (Layer 1) from data source
2. Compute Layer 3 (Wyckoff BCE)
3. Compute Layer 4 (X20 opportunities)
4. Compute Layer 5 (NARM-P+)
5. Compute Layer 6 (RCM/RPM)
6. Compute Layer 7 (RRP)
7. Store all features in feature store
8. Track data lineage and compute errors
"""

import logging
from typing import Optional, Dict, List, Callable
from datetime import datetime
from dataclasses import dataclass

import pandas as pd

from src.data.feature_store import FeatureStore
from src.core.models import OHLCV

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


@dataclass
class PipelineStats:
    """Pipeline execution statistics."""

    timestamp: datetime
    asset: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    layers_computed: List[str]
    errors: List[str]
    duration_seconds: float

    @property
    def success_rate(self) -> float:
        """Percentage of successfully processed rows."""
        if self.total_rows == 0:
            return 0.0
        return (self.successful_rows / self.total_rows) * 100


class FeatureEnrichmentPipeline:
    """
    Orchestrates feature computation across all 7 layers.

    Responsibilities:
    - Validate input OHLCV data
    - Compute features layer-by-layer
    - Handle errors per row without full pipeline failure
    - Store results in feature store
    - Track lineage and statistics

    Phase 2 Requirements:
    - Process OHLCV → Layer 1-7 features
    - Support batch and streaming modes
    - Error handling with logging
    - Data quality validation
    """

    def __init__(
        self,
        feature_store: FeatureStore,
        layer_computers: Optional[Dict[str, Callable]] = None,
    ):
        """
        Initialize feature pipeline.

        Args:
            feature_store: FeatureStore instance for result storage
            layer_computers: Dict of {layer_name: compute_function}
                If None, only Layer 1 (OHLCV) is stored (no computation)
        """
        self.feature_store = feature_store
        self.layer_computers = layer_computers or {}
        self.stats: List[PipelineStats] = []

        logger.info(f"FeaturePipeline initialized (layers: {list(self.layer_computers.keys())})")

    def validate_ohlcv(self, df: pd.DataFrame) -> tuple[bool, List[str]]:
        """
        Validate OHLCV DataFrame structure and values.

        Returns: (is_valid, error_messages)
        """
        errors = []
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]

        # Check columns
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"Missing column: {col}")

        if errors:
            return False, errors

        # Check data types and values
        if not pd.api.types.is_numeric_dtype(df["timestamp"]):
            errors.append("Timestamp must be numeric (milliseconds)")

        for col in ["open", "high", "low", "close"]:
            if (df[col] <= 0).any():
                errors.append(f"{col} contains non-positive values")

        if (df["volume"] < 0).any():
            errors.append("Volume contains negative values")

        # Check OHLC validity
        if not (df["high"] >= df[["open", "close"]].max(axis=1)).all():
            errors.append("High < max(open, close) in some rows")

        if not (df["low"] <= df[["open", "close"]].min(axis=1)).all():
            errors.append("Low > min(open, close) in some rows")

        if not (df["high"] >= df["low"]).all():
            errors.append("High < Low in some rows")

        return len(errors) == 0, errors

    def process_asset(
        self,
        asset: str,
        ohlcv_df: pd.DataFrame,
        skip_layers: Optional[List[str]] = None,
    ) -> PipelineStats:
        """
        Process OHLCV data for an asset through all layers.

        Args:
            asset: Asset symbol (e.g., "BTC", "ETH")
            ohlcv_df: DataFrame with OHLCV data (must have timestamp, OHLCV columns)
            skip_layers: List of layer names to skip (for testing)

        Returns:
            PipelineStats with execution results
        """
        start_time = datetime.utcnow()
        skip_layers = skip_layers or []

        # Validate input
        is_valid, validation_errors = self.validate_ohlcv(ohlcv_df)
        if not is_valid:
            logger.error(f"Invalid OHLCV for {asset}: {validation_errors}")
            raise ValueError(f"OHLCV validation failed: {validation_errors}")

        logger.info(f"Processing {asset}: {len(ohlcv_df)} rows")

        # Layer 1: Store raw OHLCV
        try:
            self.feature_store.insert_layer1(asset, ohlcv_df)
            logger.info(f"✓ Layer 1 (OHLCV): {len(ohlcv_df)} rows stored")
        except Exception as e:
            logger.error(f"✗ Layer 1 failed: {e}")
            raise

        errors = []
        layers_computed = ["layer1"]

        # Layers 3-7: Compute features
        for layer_name in ["layer3", "layer4", "layer5", "layer6", "layer7"]:
            if layer_name in skip_layers:
                logger.debug(f"Skipping {layer_name} (user-specified)")
                continue

            if layer_name not in self.layer_computers:
                logger.warning(f"No computer for {layer_name}, skipping")
                continue

            try:
                compute_func = self.layer_computers[layer_name]
                feature_df = compute_func(asset, ohlcv_df)

                # Ensure required columns
                if feature_df.empty:
                    logger.warning(f"{layer_name}: Empty result for {asset}")
                    errors.append(f"{layer_name}_empty")
                    continue

                # Store in feature store
                self.feature_store.insert_layer_features(layer_name, asset, feature_df)
                layers_computed.append(layer_name)
                logger.info(f"✓ {layer_name}: {len(feature_df)} rows computed and stored")

            except Exception as e:
                logger.warning(f"✗ {layer_name} failed: {e}")
                errors.append(f"{layer_name}_error: {str(e)[:50]}")
                continue

        # Compute statistics
        duration = (datetime.utcnow() - start_time).total_seconds()
        successful = len(ohlcv_df) if not errors else len(ohlcv_df) - len(errors)

        stats = PipelineStats(
            timestamp=start_time,
            asset=asset,
            total_rows=len(ohlcv_df),
            successful_rows=successful,
            failed_rows=len(errors),
            layers_computed=layers_computed,
            errors=errors,
            duration_seconds=duration,
        )

        self.stats.append(stats)

        logger.info(
            f"✓ {asset} pipeline complete: {stats.success_rate:.1f}% success, "
            f"{duration:.2f}s, {len(layers_computed)} layers"
        )

        return stats

    def process_batch(
        self,
        assets_data: Dict[str, pd.DataFrame],
        skip_layers: Optional[List[str]] = None,
    ) -> List[PipelineStats]:
        """
        Process multiple assets in batch mode.

        Args:
            assets_data: Dict of {asset: OHLCV_DataFrame}
            skip_layers: Layers to skip

        Returns:
            List of PipelineStats for each asset
        """
        results = []

        logger.info(f"Starting batch processing: {len(assets_data)} assets")

        for asset, ohlcv_df in assets_data.items():
            try:
                stats = self.process_asset(asset, ohlcv_df, skip_layers)
                results.append(stats)
            except Exception as e:
                logger.error(f"Failed to process {asset}: {e}")
                continue

        logger.info(f"✓ Batch complete: {len(results)}/{len(assets_data)} successful")
        return results

    def get_pipeline_summary(self) -> Dict:
        """Get summary statistics for all pipeline runs."""
        if not self.stats:
            return {}

        total_rows = sum(s.total_rows for s in self.stats)
        successful_rows = sum(s.successful_rows for s in self.stats)

        return {
            "total_runs": len(self.stats),
            "total_assets": len(set(s.asset for s in self.stats)),
            "total_rows_processed": total_rows,
            "total_rows_successful": successful_rows,
            "overall_success_rate": (successful_rows / total_rows * 100) if total_rows > 0 else 0,
            "total_duration_seconds": sum(s.duration_seconds for s in self.stats),
            "average_duration_per_asset": sum(s.duration_seconds for s in self.stats) / len(self.stats) if self.stats else 0,
        }

    def format_report(self) -> str:
        """Generate formatted pipeline execution report."""
        summary = self.get_pipeline_summary()

        if not summary:
            return "No pipeline executions yet"

        report = f"""
{'='*70}
FEATURE PIPELINE EXECUTION REPORT
{'='*70}

Runs: {summary['total_runs']}
Assets: {summary['total_assets']}
Total Rows: {summary['total_rows_processed']}
Successful: {summary['total_rows_successful']}
Success Rate: {summary['overall_success_rate']:.2f}%
Total Time: {summary['total_duration_seconds']:.2f}s
Avg per Asset: {summary['average_duration_per_asset']:.2f}s

Run Details:
"""
        for stat in self.stats:
            report += f"\n  {stat.asset}:\n"
            report += f"    Rows: {stat.total_rows} (success: {stat.success_rate:.1f}%)\n"
            report += f"    Layers: {', '.join(stat.layers_computed)}\n"
            report += f"    Time: {stat.duration_seconds:.2f}s\n"
            if stat.errors:
                report += f"    Errors: {', '.join(stat.errors[:3])}\n"

        report += f"\n{'='*70}\n"
        return report

    def register_layer_computer(self, layer_name: str, compute_func: Callable) -> None:
        """
        Register a feature computer function for a layer.

        Args:
            layer_name: Layer identifier (e.g., "layer3")
            compute_func: Function(asset: str, ohlcv_df: pd.DataFrame) -> feature_df
        """
        self.layer_computers[layer_name] = compute_func
        logger.info(f"Registered computer for {layer_name}")
