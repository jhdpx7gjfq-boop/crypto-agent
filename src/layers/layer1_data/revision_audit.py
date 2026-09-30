"""
C1.4-IGWT: Capture-Layer Revision Audit

Detects changes between consecutive snapshots (snapshot T vs snapshot T+1).
Proves C1.4-IGWT (capture integrity), NOT C1.4-SOURCE (upstream revision history).

Key distinction:
- C1.4-SOURCE: Upstream provider exposes revision history
- C1.4-IGWT: We detect changes between our snapshots (this module)

This module does NOT claim to prove what the provider changed.
It proves what we detected changed between consecutive captures.
"""

import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class Change:
    """Single detected change (correction, addition, or deletion)."""

    type: str  # "correction", "addition", "deletion"
    asset: str  # "BTC", "ETH", etc.
    date: str  # "2026-09-28"
    field: Optional[str] = None  # "close", "volume", etc. (for corrections)
    old_value: Optional[Any] = None  # Previous value (for corrections)
    new_value: Optional[Any] = None  # Current value (for corrections)

    def __post_init__(self):
        """Validate change structure."""
        if self.type not in ("correction", "addition", "deletion"):
            raise ValueError(f"Invalid change type: {self.type}")
        if self.type == "correction" and not self.field:
            raise ValueError("Correction must specify field")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class RevisionAuditLog:
    """Immutable audit log entry for detected changes."""

    revision_id: str  # "coingecko_BTC_rev_20260929"
    asset: str  # "BTC"
    source: str  # "coingecko", "binance"
    revision_type: str  # "retroactive_correction", "data_refresh"
    detected_at: str  # ISO 8601 UTC
    snapshot_t: str  # "20260928_150000"
    snapshot_t1: str  # "20260929_150000"
    affected_dates: List[str]  # ["2026-09-28", "2026-09-27"]
    changes: List[Change]  # List of detected changes
    pit_status: str = "UNVERIFIED"  # CRITICAL: Always UNVERIFIED
    disclaimer: str = (
        "This is C1.4-IGWT (capture-layer change detection). "
        "It proves what we detected changed between snapshots, NOT what the upstream "
        "provider changed (C1.4-SOURCE). Provider may have additional revision history."
    )

    def __post_init__(self):
        """Validate audit log on creation."""
        self.validate()

    def validate(self) -> bool:
        """Validate audit log structure and invariants."""
        if self.pit_status != "UNVERIFIED":
            raise ValueError(
                "CRITICAL INVARIANT VIOLATION: PIT_STATUS must be UNVERIFIED. "
                "C1.4-IGWT does NOT prove upstream revision history."
            )
        if not self.revision_id:
            raise ValueError("revision_id required")
        if not self.asset:
            raise ValueError("asset required")
        if not self.source:
            raise ValueError("source required")
        if self.revision_type not in ("retroactive_correction", "data_refresh", "capture_update"):
            raise ValueError(f"Invalid revision_type: {self.revision_type}")
        if not self.detected_at.endswith("Z"):
            raise ValueError("detected_at must be ISO 8601 UTC (end with Z)")
        if len(self.affected_dates) == 0:
            raise ValueError("affected_dates cannot be empty")
        if len(self.changes) == 0:
            raise ValueError("changes cannot be empty")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert Change objects to dicts
        data["changes"] = [c.to_dict() if isinstance(c, Change) else c for c in self.changes]
        return data

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    def to_json_file(self, path: str) -> None:
        """Write audit log to JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RevisionAuditLog":
        """Reconstruct from dictionary."""
        changes_data = data.pop("changes", [])
        changes = [
            Change(
                type=c["type"],
                asset=c["asset"],
                date=c["date"],
                field=c.get("field"),
                old_value=c.get("old_value"),
                new_value=c.get("new_value"),
            )
            for c in changes_data
        ]
        return cls(changes=changes, **data)

    @classmethod
    def from_json(cls, json_str: str) -> "RevisionAuditLog":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_json_file(cls, path: str) -> "RevisionAuditLog":
        """Load audit log from JSON file."""
        with open(path, "r") as f:
            return cls.from_json(f.read())


class RevisionAuditEngine:
    """
    Detects and logs changes between consecutive snapshots.

    Key responsibility:
    - Compare snapshot T vs snapshot T+1
    - Detect corrections, additions, deletions
    - Log changes without claiming upstream revision proof
    """

    @staticmethod
    def compute_diff(
        snapshot_t: Dict[str, List[Dict[str, Any]]],
        snapshot_t1: Dict[str, List[Dict[str, Any]]],
    ) -> List[Change]:
        """
        Compute differences between two snapshots.

        Args:
            snapshot_t: Snapshot at time T
            snapshot_t1: Snapshot at time T+1

        Returns:
            List of detected changes (corrections, additions, deletions)
        """
        changes = []

        # Get all assets across both snapshots
        all_assets = set(snapshot_t.keys()) | set(snapshot_t1.keys())

        for asset in all_assets:
            rows_t = {
                row.get("date"): row
                for row in snapshot_t.get(asset, [])
            }
            rows_t1 = {
                row.get("date"): row
                for row in snapshot_t1.get(asset, [])
            }

            all_dates = set(rows_t.keys()) | set(rows_t1.keys())

            for date in all_dates:
                row_t = rows_t.get(date)
                row_t1 = rows_t1.get(date)

                if row_t and row_t1:
                    # Both exist: check for corrections
                    for field in row_t1:
                        if field != "date" and row_t.get(field) != row_t1.get(field):
                            changes.append(
                                Change(
                                    type="correction",
                                    asset=asset,
                                    date=date,
                                    field=field,
                                    old_value=row_t.get(field),
                                    new_value=row_t1.get(field),
                                )
                            )
                elif row_t1 and not row_t:
                    # Addition: row in T+1 but not in T
                    changes.append(
                        Change(
                            type="addition",
                            asset=asset,
                            date=date,
                        )
                    )
                elif row_t and not row_t1:
                    # Deletion: row in T but not in T+1
                    changes.append(
                        Change(
                            type="deletion",
                            asset=asset,
                            date=date,
                        )
                    )

        return changes

    @staticmethod
    def create_audit_log(
        asset: str,
        source: str,
        snapshot_t: str,
        snapshot_t1: str,
        detected_at: str,
        changes: List[Change],
    ) -> RevisionAuditLog:
        """
        Create audit log from detected changes.

        Args:
            asset: Asset symbol (e.g., "BTC")
            source: Data source (e.g., "coingecko")
            snapshot_t: Snapshot ID at time T
            snapshot_t1: Snapshot ID at time T+1
            detected_at: ISO 8601 UTC when diff was computed
            changes: List of detected changes

        Returns:
            RevisionAuditLog entry
        """
        if not changes:
            raise ValueError("Cannot create audit log with zero changes")

        revision_id = f"{source}_{asset}_rev_{snapshot_t1.split('_')[0]}"

        # Collect unique affected dates
        affected_dates = sorted(set(c.date for c in changes))

        # Determine revision type
        change_types = {c.type for c in changes}
        if len(change_types) == 1 and "correction" in change_types:
            revision_type = "retroactive_correction"
        elif "correction" in change_types:
            revision_type = "mixed_correction_and_changes"
        else:
            revision_type = "data_refresh"

        return RevisionAuditLog(
            revision_id=revision_id,
            asset=asset,
            source=source,
            revision_type=revision_type,
            detected_at=detected_at,
            snapshot_t=snapshot_t,
            snapshot_t1=snapshot_t1,
            affected_dates=affected_dates,
            changes=changes,
            pit_status="UNVERIFIED",
        )

    @staticmethod
    def batch_audit_logs(
        source: str,
        snapshot_t: str,
        snapshot_t1: str,
        snapshots_t: Dict[str, List[Dict[str, Any]]],
        snapshots_t1: Dict[str, List[Dict[str, Any]]],
    ) -> List[RevisionAuditLog]:
        """
        Create audit logs for all assets with changes.

        Args:
            source: Data source
            snapshot_t: Snapshot ID at time T
            snapshot_t1: Snapshot ID at time T+1
            snapshots_t: All snapshot data at time T
            snapshots_t1: All snapshot data at time T+1

        Returns:
            List of audit logs (one per asset with changes)
        """
        detected_at = datetime.utcnow().isoformat() + "Z"
        all_changes = RevisionAuditEngine.compute_diff(snapshots_t, snapshots_t1)

        # Group changes by asset
        changes_by_asset: Dict[str, List[Change]] = {}
        for change in all_changes:
            if change.asset not in changes_by_asset:
                changes_by_asset[change.asset] = []
            changes_by_asset[change.asset].append(change)

        # Create audit logs for each asset
        audit_logs = []
        for asset, asset_changes in changes_by_asset.items():
            log = RevisionAuditEngine.create_audit_log(
                asset=asset,
                source=source,
                snapshot_t=snapshot_t,
                snapshot_t1=snapshot_t1,
                detected_at=detected_at,
                changes=asset_changes,
            )
            audit_logs.append(log)

        return audit_logs
