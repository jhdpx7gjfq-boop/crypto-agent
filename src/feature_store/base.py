"""Feature Store abstraction and base classes."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from src.data.contracts import RawDataBatch


class FeatureSnapshot(BaseModel):
    """Immutable snapshot of a computed feature."""

    feature_name: str = Field(..., description="Feature identifier")
    asset: str = Field(..., description="Asset (e.g., BTC, ETH)")
    timestamp: datetime = Field(..., description="Feature timestamp (when computed)")
    value: float = Field(..., description="Feature value")
    compute_timestamp: datetime = Field(
        ..., description="Server timestamp when feature was computed"
    )
    source_version: str = Field(default="1.0", description="Version of computation")
    provenance: dict[str, Any] = Field(
        default_factory=dict, description="Metadata: source table, dependencies, etc."
    )


class FeatureMetadata(BaseModel):
    """Metadata for a feature definition."""

    feature_name: str = Field(..., description="Feature identifier")
    description: str = Field(..., description="Human-readable description")
    computation_spec: dict[str, Any] = Field(
        ..., description="How feature is computed (serializable config)"
    )
    source_table: str = Field(default="raw_data", description="Source table")
    created_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When feature def was created",
    )
    version: str = Field(default="1.0", description="Feature version")


class FeatureStore(ABC):
    """Abstraction for feature computation, retrieval, and persistence."""

    @abstractmethod
    def ingest_raw(self, batch: RawDataBatch) -> None:
        """Ingest raw data and trigger feature computation pipeline.

        Args:
            batch: RawDataBatch with datapoints.

        Raises:
            ValueError: If batch is invalid.
        """

    @abstractmethod
    def compute_feature(
        self,
        feature_name: str,
        asset: str,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> pd.DataFrame:
        """Compute feature over a time window.

        Args:
            feature_name: Name of feature to compute.
            asset: Asset identifier.
            start_timestamp: Start of window (inclusive).
            end_timestamp: End of window (inclusive).

        Returns:
            DataFrame with columns: timestamp, value

        Raises:
            ValueError: If feature not found or window invalid.
        """

    @abstractmethod
    def retrieve_features(
        self,
        assets: list[str],
        features: list[str],
        start_timestamp: datetime,
        end_timestamp: datetime,
        lookback: timedelta | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Retrieve computed features.

        Args:
            assets: List of assets to retrieve.
            features: List of feature names.
            start_timestamp: Start of retrieval window.
            end_timestamp: End of retrieval window.
            lookback: Optional additional lookback period.

        Returns:
            Dict mapping asset -> DataFrame with features as columns.

        Raises:
            ValueError: If window or lookback invalid.
        """

    @abstractmethod
    def persist_snapshot(
        self,
        snapshot: FeatureSnapshot,
    ) -> None:
        """Persist feature snapshot (immutable append-only).

        Args:
            snapshot: FeatureSnapshot to persist.

        Raises:
            ValueError: If snapshot invalid.
        """

    @abstractmethod
    def get_provenance(
        self,
        feature_name: str,
        asset: str,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """Retrieve provenance for a feature snapshot.

        Args:
            feature_name: Name of feature.
            asset: Asset.
            timestamp: Snapshot timestamp.

        Returns:
            Dict with source, version, compute_timestamp, dependencies.

        Raises:
            ValueError: If snapshot not found.
        """

    @abstractmethod
    def register_feature_metadata(self, metadata: FeatureMetadata) -> None:
        """Register feature definition metadata.

        Args:
            metadata: FeatureMetadata.

        Raises:
            ValueError: If metadata invalid or duplicate.
        """

    @abstractmethod
    def close(self) -> None:
        """Clean up resources."""
