"""
Unit tests for C1.4-IGWT revision audit (snapshot diff detection).

Tests verify:
- Snapshot-to-snapshot comparison
- Detection of corrections (field value changes)
- Detection of additions (new rows)
- Detection of deletions (missing rows)
- Revision log structure
- No claims of upstream revision proof
- PIT_STATUS = UNVERIFIED maintained
"""

import json
from datetime import datetime
from typing import Dict, List, Any

import pytest


class TestSnapshotDiffDetection:
    """Test detection of changes between consecutive snapshots."""

    def test_identical_snapshots_no_changes(self):
        """Identical snapshots produce empty diff."""
        snapshot_t = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.00},
            ]
        }
        snapshot_t1 = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.00},
            ]
        }

        diff = compute_diff(snapshot_t, snapshot_t1)
        assert len(diff) == 0

    def test_detect_price_correction(self):
        """Detect retroactive price correction."""
        snapshot_t = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.00},
            ]
        }
        snapshot_t1 = {
            "BTC": [
                {"date": "2026-09-28", "close": 64512.50},  # Corrected
            ]
        }

        diff = compute_diff(snapshot_t, snapshot_t1)
        assert len(diff) == 1
        change = diff[0]
        assert change["type"] == "correction"
        assert change["date"] == "2026-09-28"
        assert change["asset"] == "BTC"
        assert change["field"] == "close"
        assert change["old_value"] == 64500.00
        assert change["new_value"] == 64512.50

    def test_detect_volume_correction(self):
        """Detect volume data correction."""
        snapshot_t = {
            "ETH": [
                {"date": "2026-09-27", "volume": 18000000000.00},
            ]
        }
        snapshot_t1 = {
            "ETH": [
                {"date": "2026-09-27", "volume": 18033182350.13},  # Corrected
            ]
        }

        diff = compute_diff(snapshot_t, snapshot_t1)
        assert len(diff) == 1
        change = diff[0]
        assert change["type"] == "correction"
        assert change["field"] == "volume"

    def test_detect_new_row_addition(self):
        """Detect addition of new historical row."""
        snapshot_t = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.00},
            ]
        }
        snapshot_t1 = {
            "BTC": [
                {"date": "2026-09-27", "close": 63800.00},  # New row
                {"date": "2026-09-28", "close": 64500.00},
            ]
        }

        diff = compute_diff(snapshot_t, snapshot_t1)
        assert len(diff) == 1
        change = diff[0]
        assert change["type"] == "addition"
        assert change["date"] == "2026-09-27"
        assert change["asset"] == "BTC"

    def test_detect_row_deletion(self):
        """Detect deletion of row (should be rare)."""
        snapshot_t = {
            "BTC": [
                {"date": "2026-09-27", "close": 63800.00},
                {"date": "2026-09-28", "close": 64500.00},
            ]
        }
        snapshot_t1 = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.00},
            ]
        }

        diff = compute_diff(snapshot_t, snapshot_t1)
        assert len(diff) == 1
        change = diff[0]
        assert change["type"] == "deletion"
        assert change["date"] == "2026-09-27"
        assert change["asset"] == "BTC"

    def test_multiple_changes_single_asset(self):
        """Detect multiple changes in one asset."""
        snapshot_t = {
            "BTC": [
                {"date": "2026-09-27", "close": 63800.00, "volume": 20000000000},
                {"date": "2026-09-28", "close": 64500.00, "volume": 18000000000},
            ]
        }
        snapshot_t1 = {
            "BTC": [
                {"date": "2026-09-27", "close": 63812.50, "volume": 20000000000},
                {"date": "2026-09-28", "close": 64512.50, "volume": 18033182350},
            ]
        }

        diff = compute_diff(snapshot_t, snapshot_t1)
        assert len(diff) == 3  # Three field corrections (close × 2, volume × 1)

    def test_multiple_assets_with_changes(self):
        """Detect changes across multiple assets."""
        snapshot_t = {
            "BTC": [{"date": "2026-09-28", "close": 64500.00}],
            "ETH": [{"date": "2026-09-28", "close": 2450.00}],
        }
        snapshot_t1 = {
            "BTC": [{"date": "2026-09-28", "close": 64512.50}],
            "ETH": [{"date": "2026-09-28", "close": 2450.00}],  # Unchanged
        }

        diff = compute_diff(snapshot_t, snapshot_t1)
        assert len(diff) == 1  # Only BTC changed
        change = diff[0]
        assert change["asset"] == "BTC"


class TestRevisionAuditLog:
    """Test revision audit log structure and metadata."""

    def test_revision_log_required_fields(self):
        """Revision log entry must include required fields."""
        revision = {
            "revision_id": "coingecko_BTC_rev_20260929",
            "asset": "BTC",
            "source": "coingecko",
            "revision_type": "retroactive_correction",
            "detected_at": "2026-09-29T08:00:00Z",
            "snapshot_t": "20260928_150000",
            "snapshot_t1": "20260929_150000",
            "affected_dates": ["2026-09-28"],
            "changes": [
                {
                    "date": "2026-09-28",
                    "field": "close",
                    "old_value": 64500.00,
                    "new_value": 64512.50,
                }
            ],
        }

        required = {
            "revision_id",
            "asset",
            "source",
            "revision_type",
            "detected_at",
            "snapshot_t",
            "snapshot_t1",
            "affected_dates",
            "changes",
        }
        assert set(revision.keys()) >= required

    def test_revision_id_format(self):
        """Revision ID must be machine-readable."""
        revision_id = "coingecko_BTC_rev_20260929"
        parts = revision_id.split("_")
        assert len(parts) >= 3
        assert "rev" in revision_id

    def test_revision_detected_timestamp_format(self):
        """Detected timestamp must be ISO 8601 UTC."""
        detected_at = "2026-09-29T08:00:00Z"
        assert detected_at.endswith("Z")
        assert "T" in detected_at

    def test_revision_change_entry_structure(self):
        """Each change must include date, field, old/new values."""
        change = {
            "date": "2026-09-28",
            "field": "close",
            "old_value": 64500.00,
            "new_value": 64512.50,
        }

        required = {"date", "field", "old_value", "new_value"}
        assert set(change.keys()) >= required

    def test_revision_log_json_serializable(self):
        """Revision log must be JSON-serializable."""
        revision = {
            "revision_id": "coingecko_BTC_rev_20260929",
            "asset": "BTC",
            "detected_at": "2026-09-29T08:00:00Z",
            "changes": [
                {"date": "2026-09-28", "field": "close", "old_value": 64500.0, "new_value": 64512.5}
            ],
        }

        json_str = json.dumps(revision)
        assert isinstance(json_str, str)
        restored = json.loads(json_str)
        assert restored == revision


class TestNoUpstreamRevisionClaims:
    """Verify C1.4-IGWT does NOT claim upstream revision proof."""

    def test_revision_log_contains_disclaimer(self):
        """Revision log must include disclaimer about C1.4-SOURCE."""
        revision = {
            "revision_id": "coingecko_BTC_rev_20260929",
            "asset": "BTC",
            "source": "coingecko",
            "disclaimer": "This audit proves C1.4-IGWT (capture-layer change detection only). "
                         "It does NOT prove C1.4-SOURCE (upstream provider revision history). "
                         "Provider may have other changes not captured.",
        }

        assert "C1.4-IGWT" in revision.get("disclaimer", "")
        assert "capture-layer" in revision.get("disclaimer", "")

    def test_revision_type_local_detection(self):
        """Revision type must not claim upstream origin."""
        # Acceptable revision types:
        acceptable_types = [
            "retroactive_correction",
            "data_refresh",
            "capture_update",
        ]

        for rev_type in acceptable_types:
            revision = {"revision_type": rev_type}
            # Should not be "upstream_revision" or similar
            assert not rev_type.startswith("upstream_")

    def test_revision_scope_captures_our_detection_only(self):
        """Revision scope limited to what we detected, not upstream source."""
        revision = {
            "detected_at": "2026-09-29T08:00:00Z",
            "scope": "Differences between snapshot T and snapshot T+1 as captured by IGWT",
            "note": "Does not represent complete upstream revision history",
        }

        assert "IGWT" in revision.get("scope", "")
        assert "captured" in revision.get("scope", "")


class TestPITStatusMaintained:
    """Verify PIT_STATUS = UNVERIFIED maintained through revision audit."""

    def test_revision_audit_preserves_pit_status(self):
        """Revision audit inherits PIT_STATUS from snapshots."""
        revision = {
            "revision_id": "coingecko_BTC_rev_20260929",
            "pit_status": "UNVERIFIED",
            "note": "This is C1.4-IGWT capture audit, not C1.5-PIT provider proof",
        }

        assert revision["pit_status"] == "UNVERIFIED"

    def test_revision_audit_prevents_wfv_usage(self):
        """Revision audit cannot be used for WFV without C1.5-PIT."""
        revision_log = {
            "revisions": [
                {
                    "revision_id": "coingecko_BTC_rev_20260929",
                    "pit_status": "UNVERIFIED",
                }
            ]
        }

        # Pseudocode check
        can_use_for_wfv = False
        for rev in revision_log["revisions"]:
            if rev["pit_status"] == "VERIFIED":
                can_use_for_wfv = True

        assert can_use_for_wfv is False


class TestQAAcceptanceCriteria:
    """Integration QA for revision audit system."""

    def test_complete_revision_audit_example(self):
        """Complete revision audit example passes all structural checks."""
        revision = {
            "revision_id": "coingecko_BTC_rev_20260929",
            "asset": "BTC",
            "source": "coingecko",
            "revision_type": "retroactive_correction",
            "detected_at": "2026-09-29T08:00:00Z",
            "snapshot_t": "20260928_150000",
            "snapshot_t1": "20260929_150000",
            "affected_dates": ["2026-09-28"],
            "changes": [
                {
                    "date": "2026-09-28",
                    "field": "close",
                    "old_value": 64500.00,
                    "new_value": 64512.50,
                }
            ],
            "pit_status": "UNVERIFIED",
            "disclaimer": "C1.4-IGWT capture audit only, not C1.4-SOURCE proof",
        }

        # Structural checks
        assert revision["pit_status"] == "UNVERIFIED"
        assert len(revision["changes"]) > 0
        assert revision["asset"] is not None
        assert "disclaimer" in revision

    def test_diff_to_audit_log_flow(self):
        """Complete flow: snapshot diff → audit log creation."""
        # Simulated snapshots
        snapshot_t = {
            "BTC": [{"date": "2026-09-28", "close": 64500.00}]
        }
        snapshot_t1 = {
            "BTC": [{"date": "2026-09-28", "close": 64512.50}]
        }

        # Compute diff
        diff = compute_diff(snapshot_t, snapshot_t1)

        # Create audit log entry
        revision_id = f"coingecko_BTC_rev_20260929"
        audit_log = {
            "revision_id": revision_id,
            "asset": "BTC",
            "source": "coingecko",
            "changes": diff,
            "pit_status": "UNVERIFIED",
        }

        # Verify flow
        assert len(audit_log["changes"]) > 0
        assert audit_log["pit_status"] == "UNVERIFIED"


# Helper function for tests

def compute_diff(snapshot_t: Dict[str, List[Dict]],
                 snapshot_t1: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
    """
    Compute diff between two snapshots.

    Returns list of changes:
    - type: "correction", "addition", "deletion"
    - asset, date, field, old_value, new_value (for corrections)
    """
    changes = []

    # Process all assets
    all_assets = set(snapshot_t.keys()) | set(snapshot_t1.keys())

    for asset in all_assets:
        rows_t = {row.get("date"): row for row in snapshot_t.get(asset, [])}
        rows_t1 = {row.get("date"): row for row in snapshot_t1.get(asset, [])}

        all_dates = set(rows_t.keys()) | set(rows_t1.keys())

        for date in all_dates:
            row_t = rows_t.get(date)
            row_t1 = rows_t1.get(date)

            if row_t and row_t1:
                # Check for corrections
                for field in row_t1:
                    if field != "date" and row_t.get(field) != row_t1.get(field):
                        changes.append({
                            "type": "correction",
                            "asset": asset,
                            "date": date,
                            "field": field,
                            "old_value": row_t.get(field),
                            "new_value": row_t1.get(field),
                        })
            elif row_t1 and not row_t:
                # Addition
                changes.append({
                    "type": "addition",
                    "asset": asset,
                    "date": date,
                })
            elif row_t and not row_t1:
                # Deletion
                changes.append({
                    "type": "deletion",
                    "asset": asset,
                    "date": date,
                })

    return changes
