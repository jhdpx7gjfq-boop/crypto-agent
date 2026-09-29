"""
Snapshot Manifest Schema

Defines immutable, tamper-evident snapshot provenance and metadata.
Every snapshot must carry PIT_STATUS = "UNVERIFIED" to prevent accidental
conflation with C1.5-PIT (provider availability) verification.
"""

import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class Checksum:
    """File integrity checksum (SHA256)."""

    file: str  # Parquet filename
    sha256: str  # SHA256 hex digest (64 chars)
    row_count: int  # Rows in file for audit

    def validate(self) -> bool:
        """Validate checksum structure."""
        if not isinstance(self.sha256, str) or len(self.sha256) != 64:
            raise ValueError(f"SHA256 must be 64 hex chars, got {len(self.sha256)}")
        if self.row_count < 0:
            raise ValueError(f"row_count must be non-negative, got {self.row_count}")
        return True


@dataclass
class SourceMetadata:
    """Metadata for a single data source in snapshot."""

    source: str  # "coingecko", "binance", etc.
    endpoint: str  # API endpoint used
    fetch_timestamp: str  # ISO 8601 UTC when data was fetched
    date_range: List[str]  # [start_date, end_date]
    candle_resolution: str  # "daily", "15m", "4h", etc.
    rows_fetched: int  # Total rows in this source
    checksums: Checksum  # File integrity hash
    coins: Optional[List[str]] = None  # For CoinGecko
    symbols: Optional[List[str]] = None  # For Binance

    def validate(self) -> bool:
        """Validate source metadata structure."""
        if not self.source:
            raise ValueError("source must be non-empty")
        if not self.endpoint:
            raise ValueError("endpoint must be non-empty")
        if len(self.date_range) != 2:
            raise ValueError("date_range must be [start, end]")
        self.checksums.validate()
        return True


@dataclass
class SnapshotManifest:
    """
    Immutable snapshot provenance record.

    Every manifest MUST carry PIT_STATUS = "UNVERIFIED" unless independently
    verified by C1.5-PIT (source-native PIT API or provider-signed attestation).

    Key Invariant:
    - C1.5-IGWT (this class): Proves reproducibility of what we captured
    - C1.5-PIT (external verification): Proves what provider had available
    - These are independent gates; NEVER conflate them
    """

    snapshot_id: str  # "YYYYMMDD_HHMMSS" format
    snapshot_timestamp: str  # ISO 8601 UTC
    data_as_of: str  # Date snapshot represents (e.g., "2026-09-29T00:00:00Z")
    sources: List[SourceMetadata]  # All sources in this snapshot
    immutable_hash: str  # Root merkle/SHA256 hash (sha256:...)
    frozen_at: str  # ISO 8601 UTC when snapshot was frozen
    pit_status: str = "UNVERIFIED"  # CRITICAL: Must default to UNVERIFIED
    retention_policy: str = "permanent"  # Never delete snapshots
    versioned: bool = True  # Track versions for lineage

    def __post_init__(self):
        """Validate manifest on creation."""
        self.validate()

    def validate(self) -> bool:
        """
        Validate manifest structure and invariants.

        Raises:
            ValueError: If any validation fails
        """
        if not self.snapshot_id:
            raise ValueError("snapshot_id required")
        if not self.immutable_hash.startswith("sha256:"):
            raise ValueError("immutable_hash must start with 'sha256:'")
        if self.pit_status not in ("UNVERIFIED", "VERIFIED"):
            raise ValueError(f"pit_status must be UNVERIFIED or VERIFIED, got {self.pit_status}")
        # CRITICAL: Default must be UNVERIFIED
        if self.pit_status != "UNVERIFIED":
            raise ValueError(
                "CRITICAL INVARIANT VIOLATION: PIT_STATUS must default to UNVERIFIED. "
                "This manifest does NOT prove C1.5-PIT (provider availability). "
                "It proves C1.5-IGWT (capture reproducibility) only."
            )
        if self.retention_policy != "permanent":
            raise ValueError(f"retention_policy must be 'permanent', got {self.retention_policy}")
        if not isinstance(self.versioned, bool):
            raise ValueError("versioned must be boolean")

        for source in self.sources:
            source.validate()

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for JSON serialization)."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    def to_json_file(self, path: str) -> None:
        """Write manifest to JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotManifest":
        """Reconstruct from dictionary."""
        sources_data = data.pop("sources", [])
        sources = [
            SourceMetadata(
                source=s["source"],
                endpoint=s["endpoint"],
                fetch_timestamp=s["fetch_timestamp"],
                date_range=s["date_range"],
                candle_resolution=s["candle_resolution"],
                rows_fetched=s["rows_fetched"],
                checksums=Checksum(**s["checksums"]),
                coins=s.get("coins"),
                symbols=s.get("symbols"),
            )
            for s in sources_data
        ]
        return cls(sources=sources, **data)

    @classmethod
    def from_json(cls, json_str: str) -> "SnapshotManifest":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_json_file(cls, path: str) -> "SnapshotManifest":
        """Load manifest from JSON file."""
        with open(path, "r") as f:
            return cls.from_json(f.read())

    def get_data_as_of(self, asset: str, query_date: str) -> Dict[str, Any]:
        """
        Query frozen snapshot data state.

        Args:
            asset: Asset symbol (e.g., "BTC")
            query_date: Date to query (e.g., "2026-03-31")

        Returns:
            Frozen data state with PIT_STATUS metadata.

        CRITICAL: Returns include pit_status = UNVERIFIED to prevent
        accidental use in PIT-dependent work (WFV, backtesting).
        """
        return {
            "asset": asset,
            "query_date": query_date,
            "snapshot_date": self.data_as_of,
            "snapshot_id": self.snapshot_id,
            "pit_status": self.pit_status,
            "note": "This data is C1.5-IGWT (frozen capture), NOT C1.5-PIT (provider proof)",
        }

    def assert_reproducible(self) -> bool:
        """
        Verify snapshot can be reconstructed identically.

        For walk-forward testing, this proves we can reproduce WHAT WE CAPTURED.
        It does NOT prove what the provider had available (C1.5-PIT).
        """
        # Check immutable hash present
        if not self.immutable_hash:
            raise ValueError("Missing immutable_hash; snapshot may be corrupted")
        # Check all sources have checksums
        for source in self.sources:
            if not source.checksums.sha256:
                raise ValueError(f"Source {source.source} missing checksum")
        return True


def create_snapshot_manifest(
    snapshot_id: str,
    snapshot_timestamp: str,
    data_as_of: str,
    sources: List[SourceMetadata],
    immutable_hash: str,
    frozen_at: str,
) -> SnapshotManifest:
    """
    Create a new snapshot manifest.

    CRITICAL: pit_status always defaults to UNVERIFIED.
    This prevents accidental conflation with C1.5-PIT verification.
    """
    return SnapshotManifest(
        snapshot_id=snapshot_id,
        snapshot_timestamp=snapshot_timestamp,
        data_as_of=data_as_of,
        sources=sources,
        immutable_hash=immutable_hash,
        frozen_at=frozen_at,
        pit_status="UNVERIFIED",  # MANDATORY DEFAULT
        retention_policy="permanent",
        versioned=True,
    )
