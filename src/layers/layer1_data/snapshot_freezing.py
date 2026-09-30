"""
C1.5-IGWT: Snapshot Freezing & Hash Verification

Freezes snapshots with immutable timestamps and SHA256 hashes.
Proves C1.5-IGWT (capture reproducibility), NOT C1.5-PIT (provider availability).

Key distinction:
- C1.5-IGWT: We froze what we captured, with hash verification (this module)
- C1.5-PIT: Provider exposes versioned API or signed attestation (independent, BLOCKED)

This module does NOT claim provider point-in-time availability.
It proves deterministic reconstruction of what we captured.
"""

import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def compute_content_hash(data: Any, sort_keys: bool = False) -> str:
    """Compute SHA256 hash of data content."""
    json_str = json.dumps(data, sort_keys=sort_keys)
    content_bytes = json_str.encode("utf-8")
    return hashlib.sha256(content_bytes).hexdigest()


def compute_manifest_hash(manifest: Dict[str, Any]) -> str:
    """Compute root hash of manifest."""
    return compute_content_hash(manifest, sort_keys=True)


def compute_snapshot_hash(snapshot_params: Dict[str, Any]) -> str:
    """Compute hash of snapshot parameters."""
    return compute_content_hash(snapshot_params, sort_keys=True)


@dataclass
class FrozenSnapshot:
    """Immutable snapshot capture with hash verification."""

    snapshot_id: str  # "20260929_150000"
    frozen_at: str  # ISO 8601 UTC
    data_hash: str  # SHA256 hex digest
    data: Dict[str, List[Dict[str, Any]]]  # Frozen data
    pit_status: str = "UNVERIFIED"  # CRITICAL: Always UNVERIFIED
    is_frozen: bool = True
    disclaimer: str = (
        "This is C1.5-IGWT (our frozen capture with hash verification). "
        "It proves reproducibility of what we captured. "
        "It does NOT prove C1.5-PIT (provider had this available)."
    )

    def __post_init__(self):
        """Validate frozen snapshot on creation."""
        self.validate()

    def validate(self) -> bool:
        """Validate frozen snapshot structure and invariants."""
        if self.pit_status != "UNVERIFIED":
            raise ValueError(
                "CRITICAL INVARIANT VIOLATION: PIT_STATUS must be UNVERIFIED. "
                "C1.5-IGWT does NOT prove provider point-in-time availability."
            )
        if not self.snapshot_id:
            raise ValueError("snapshot_id required")
        if not self.frozen_at.endswith("Z"):
            raise ValueError("frozen_at must be ISO 8601 UTC (end with Z)")
        if not self.is_frozen:
            raise ValueError("is_frozen must be True for frozen snapshot")
        if len(self.data_hash) != 64:
            raise ValueError("data_hash must be 64-character SHA256 hex digest")
        return True

    def verify_hash(self) -> bool:
        """Verify data hash matches current state."""
        reconstructed_hash = compute_content_hash(self.data)
        return reconstructed_hash == self.data_hash

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    def to_json_file(self, path: str) -> None:
        """Write to JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrozenSnapshot":
        """Reconstruct from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "FrozenSnapshot":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_json_file(cls, path: str) -> "FrozenSnapshot":
        """Load from JSON file."""
        with open(path, "r") as f:
            return cls.from_json(f.read())

    def get_data_as_of(self, asset: str, query_date: str) -> Dict[str, Any]:
        """
        Query frozen data with hash verification.

        Args:
            asset: Asset symbol (e.g., "BTC")
            query_date: Query date (e.g., "2026-03-31")

        Returns:
            Dict with data, hash_verified, pit_status, warning
        """
        if not self.verify_hash():
            raise ValueError("Hash verification failed: data may be tampered")

        # Find data for asset and date
        asset_data = self.data.get(asset, [])
        matching_row = None
        for row in asset_data:
            if row.get("date") == query_date:
                matching_row = row
                break

        return {
            "asset": asset,
            "query_date": query_date,
            "snapshot_date": self.frozen_at,
            "snapshot_hash": self.data_hash,
            "data": matching_row if matching_row else None,
            "hash_verified": True,
            "pit_status": "UNVERIFIED",
            "warning": (
                "This data is C1.5-IGWT frozen capture (reproducible snapshot). "
                "Cannot be used for WFV without C1.5-PIT verification."
            ),
        }


class SnapshotFreezer:
    """
    Freezes snapshots with immutable timestamps and hash verification.

    Responsibility:
    - Capture data state with timestamp
    - Compute SHA256 hash for tamper evidence
    - Enforce immutability and PIT_STATUS invariant
    - Provide deterministic reconstruction with verification
    """

    @staticmethod
    def freeze(
        snapshot_id: str,
        data: Dict[str, List[Dict[str, Any]]],
    ) -> FrozenSnapshot:
        """
        Freeze snapshot with immutable timestamp and hash.

        Args:
            snapshot_id: Unique snapshot identifier
            data: Data to freeze

        Returns:
            FrozenSnapshot with hash and timestamp
        """
        frozen_at = datetime.utcnow().isoformat() + "Z"
        data_hash = compute_content_hash(data)

        return FrozenSnapshot(
            snapshot_id=snapshot_id,
            frozen_at=frozen_at,
            data_hash=data_hash,
            data=data,
            pit_status="UNVERIFIED",
        )

    @staticmethod
    def freeze_with_timestamp(
        snapshot_id: str,
        data: Dict[str, List[Dict[str, Any]]],
        frozen_at: str,
    ) -> FrozenSnapshot:
        """
        Freeze snapshot with explicit timestamp (for testing).

        Args:
            snapshot_id: Unique snapshot identifier
            data: Data to freeze
            frozen_at: ISO 8601 UTC timestamp

        Returns:
            FrozenSnapshot with hash and timestamp
        """
        data_hash = compute_content_hash(data)

        return FrozenSnapshot(
            snapshot_id=snapshot_id,
            frozen_at=frozen_at,
            data_hash=data_hash,
            data=data,
            pit_status="UNVERIFIED",
        )

    @staticmethod
    def reconstruct_and_verify(frozen: FrozenSnapshot) -> bool:
        """
        Reconstruct snapshot and verify hash matches.

        Args:
            frozen: FrozenSnapshot to verify

        Returns:
            True if hash verification passes
        """
        return frozen.verify_hash()

    @staticmethod
    def detect_tampering(frozen: FrozenSnapshot) -> bool:
        """
        Detect if snapshot has been tampered with.

        Args:
            frozen: FrozenSnapshot to check

        Returns:
            True if tampering detected (hash mismatch), False if valid
        """
        return not frozen.verify_hash()
