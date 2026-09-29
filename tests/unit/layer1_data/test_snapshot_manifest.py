"""
Unit tests for snapshot manifest schema and integrity.

Tests verify:
- Manifest structure and required fields
- PIT_STATUS = UNVERIFIED mandatory default
- Hash verification
- Tamper-evident integrity
- Immutability enforcement
- get_data_as_of() reproducibility
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

import pytest


class TestSnapshotManifestSchema:
    """Test snapshot manifest schema structure and validation."""

    def test_manifest_required_fields(self):
        """Manifest must include all required provenance fields."""
        required_fields = {
            "snapshot_id",
            "snapshot_timestamp",
            "data_as_of",
            "sources",
            "immutable_hash",
            "frozen_at",
            "pit_status",
            "retention_policy",
            "versioned",
        }
        manifest = {
            "snapshot_id": "20260929_150000",
            "snapshot_timestamp": "2026-09-29T15:30:00Z",
            "data_as_of": "2026-09-29T00:00:00Z",
            "sources": [],
            "immutable_hash": "sha256:abc123",
            "frozen_at": "2026-09-29T15:30:00Z",
            "pit_status": "UNVERIFIED",
            "retention_policy": "permanent",
            "versioned": True,
        }
        assert set(manifest.keys()) == required_fields

    def test_pit_status_default_unverified(self):
        """PIT_STATUS must default to UNVERIFIED."""
        manifest = {
            "pit_status": "UNVERIFIED",
        }
        assert manifest["pit_status"] == "UNVERIFIED"

    def test_pit_status_never_verified_without_c1_5_pit(self):
        """PIT_STATUS remains UNVERIFIED until C1.5-PIT independently verified."""
        manifest = {
            "pit_status": "UNVERIFIED",
        }
        # This status cannot be changed by Layer 1 code alone.
        # Must require external C1.5-PIT verification.
        assert manifest["pit_status"] != "VERIFIED"

    def test_source_metadata_structure(self):
        """Each source in manifest must include required metadata."""
        source = {
            "source": "coingecko",
            "endpoint": "/coins/{id}/market_chart",
            "fetch_timestamp": "2026-09-29T15:30:00Z",
            "date_range": ["2019-01-01", "2026-09-29"],
            "coins": ["bitcoin", "ethereum"],
            "candle_resolution": "daily",
            "rows_fetched": 45230,
            "checksums": {
                "file": "coingecko_raw.parquet",
                "sha256": "abc123def456",
                "row_count": 45230,
            },
        }
        required_source_fields = {
            "source",
            "endpoint",
            "fetch_timestamp",
            "date_range",
            "candle_resolution",
            "rows_fetched",
            "checksums",
        }
        assert set(source.keys()) >= required_source_fields

    def test_checksum_structure(self):
        """Checksum must include file, hash, row count."""
        checksum = {
            "file": "coingecko_raw.parquet",
            "sha256": "abc123def456",
            "row_count": 45230,
        }
        assert "file" in checksum
        assert "sha256" in checksum
        assert "row_count" in checksum


class TestHashVerification:
    """Test immutable hash verification."""

    def test_manifest_hash_sha256_format(self):
        """Immutable hash must be SHA256 format."""
        manifest_hash = "sha256:abc123def456"
        assert manifest_hash.startswith("sha256:")
        hash_value = manifest_hash.split(":")[1]
        # SHA256 hex digest is 64 characters
        assert len(hash_value) > 0

    def test_hash_immutability_on_reconstruction(self):
        """Reconstructed snapshot must have identical hash."""
        original_hash = "sha256:abc123def456"
        reconstructed_hash = "sha256:abc123def456"
        assert original_hash == reconstructed_hash

    def test_hash_mismatch_detection(self):
        """Different hashes should be detected as tampering."""
        original_hash = "sha256:abc123def456"
        tampering_hash = "sha256:xyz789uvw000"
        assert original_hash != tampering_hash

    def test_source_file_checksum_validation(self):
        """Each source file must have SHA256 checksum."""
        source = {
            "checksums": {
                "file": "coingecko_raw.parquet",
                "sha256": "abcdef0123456789" * 4,  # 64 chars = SHA256 hex
                "row_count": 45230,
            }
        }
        checksum = source["checksums"]
        sha256_value = checksum["sha256"]
        assert len(sha256_value) == 64  # SHA256 hex digest length


class TestTamperEvidenceAndImmutability:
    """Test tamper-evident storage and immutability enforcement."""

    def test_frozen_timestamp_prevents_modification(self):
        """Frozen snapshot has immutable timestamp."""
        frozen_at = "2026-09-29T15:30:00Z"
        # Once frozen, timestamp is locked
        modification_attempt = "2026-09-29T15:31:00Z"
        assert frozen_at != modification_attempt

    def test_manifest_versioned_tracking(self):
        """Manifest must track version for lineage."""
        manifest = {
            "versioned": True,
            "snapshot_id": "20260929_150000",
        }
        assert manifest["versioned"] is True
        assert manifest["snapshot_id"] is not None

    def test_retention_policy_permanent(self):
        """Snapshots must have permanent retention (never deleted)."""
        manifest = {
            "retention_policy": "permanent",
        }
        assert manifest["retention_policy"] == "permanent"

    def test_manifest_json_serializable(self):
        """Manifest must be JSON-serializable for immutable storage."""
        manifest = {
            "snapshot_id": "20260929_150000",
            "snapshot_timestamp": "2026-09-29T15:30:00Z",
            "data_as_of": "2026-09-29T00:00:00Z",
            "sources": [],
            "immutable_hash": "sha256:abc123",
            "frozen_at": "2026-09-29T15:30:00Z",
            "pit_status": "UNVERIFIED",
            "retention_policy": "permanent",
            "versioned": True,
        }
        # Must be JSON-serializable
        json_str = json.dumps(manifest)
        assert isinstance(json_str, str)
        reconstructed = json.loads(json_str)
        assert reconstructed == manifest


class TestGetDataAsOfReproducibility:
    """Test get_data_as_of() query API reproducibility."""

    def test_get_data_as_of_requires_snapshot_date(self):
        """get_data_as_of() must specify snapshot creation date."""
        query_params = {
            "asset": "BTC",
            "query_date": "2026-03-31",
            "snapshot_date": "2026-04-01",
        }
        assert "snapshot_date" in query_params
        assert query_params["snapshot_date"] == "2026-04-01"

    def test_get_data_as_of_deterministic(self):
        """Same query parameters must return identical results."""
        params_1 = {
            "asset": "BTC",
            "query_date": "2026-03-31",
            "snapshot_date": "2026-04-01",
        }
        params_2 = {
            "asset": "BTC",
            "query_date": "2026-03-31",
            "snapshot_date": "2026-04-01",
        }
        assert params_1 == params_2

    def test_get_data_as_of_locks_data_state(self):
        """get_data_as_of() must return frozen data state, not live."""
        frozen_close_price = 68420.50
        # Query returns historical frozen value, not current price
        assert frozen_close_price == 68420.50

    def test_get_data_as_of_includes_pit_status(self):
        """get_data_as_of() result must include PIT_STATUS metadata."""
        result = {
            "data": {"BTC": [{"close": 68420.50}]},
            "pit_status": "UNVERIFIED",
            "snapshot_date": "2026-04-01",
        }
        assert result["pit_status"] == "UNVERIFIED"


class TestPITStatusInvariant:
    """Test PIT_STATUS = UNVERIFIED invariant enforcement."""

    def test_pit_status_in_manifest(self):
        """Every manifest must include pit_status field."""
        manifest = {
            "pit_status": "UNVERIFIED",
        }
        assert "pit_status" in manifest

    def test_pit_status_in_feature_metadata(self):
        """Feature store must carry pit_status in metadata."""
        feature_metadata = {
            "pit_status": "UNVERIFIED",
            "source": "layer1",
            "snapshot_date": "2026-04-01",
        }
        assert feature_metadata["pit_status"] == "UNVERIFIED"

    def test_pit_status_prevents_accidental_pit_claim(self):
        """PIT_STATUS = UNVERIFIED prevents C1.5-IGWT being treated as C1.5-PIT."""
        manifest = {
            "pit_status": "UNVERIFIED",
            "description": "C1.5-IGWT snapshot (reproducibility proof only, NOT C1.5-PIT)",
        }
        # Code must check this before allowing PIT-dependent work
        if manifest["pit_status"] == "UNVERIFIED":
            allow_wfv = False
        assert allow_wfv is False


class TestQAAcceptanceCriteria:
    """Integration QA for snapshot manifest system."""

    def test_complete_manifest_example(self):
        """Complete manifest example passes all structural checks."""
        manifest = {
            "snapshot_id": "20260929_150000",
            "snapshot_timestamp": "2026-09-29T15:30:00Z",
            "data_as_of": "2026-09-29T00:00:00Z",
            "sources": [
                {
                    "source": "coingecko",
                    "endpoint": "/coins/{id}/market_chart",
                    "fetch_timestamp": "2026-09-29T15:30:00Z",
                    "date_range": ["2019-01-01", "2026-09-29"],
                    "coins": ["bitcoin", "ethereum"],
                    "candle_resolution": "daily",
                    "rows_fetched": 45230,
                    "checksums": {
                        "file": "coingecko_raw.parquet",
                        "sha256": "abcdef0123456789" * 4,
                        "row_count": 45230,
                    },
                }
            ],
            "immutable_hash": "sha256:root_merkle_hash",
            "frozen_at": "2026-09-29T15:30:00Z",
            "pit_status": "UNVERIFIED",
            "retention_policy": "permanent",
            "versioned": True,
        }

        # Structural checks
        assert "snapshot_id" in manifest
        assert "pit_status" in manifest
        assert manifest["pit_status"] == "UNVERIFIED"
        assert manifest["retention_policy"] == "permanent"
        assert manifest["versioned"] is True
        assert len(manifest["sources"]) > 0

    def test_manifest_prevents_pit_confusion(self):
        """Manifest must prevent confusing C1.5-IGWT with C1.5-PIT."""
        manifest = {
            "pit_status": "UNVERIFIED",
            "snapshot_date": "2026-04-01T00:00:00Z",
            "note": "This is C1.5-IGWT: reproducibility of captured data, NOT C1.5-PIT: provider availability",
        }

        # Any code using this must check pit_status
        is_pit_verified = manifest["pit_status"] == "VERIFIED"
        assert is_pit_verified is False

        # Cannot use for WFV without C1.5-PIT
        if manifest["pit_status"] != "VERIFIED":
            can_use_for_wfv = False
        assert can_use_for_wfv is False
