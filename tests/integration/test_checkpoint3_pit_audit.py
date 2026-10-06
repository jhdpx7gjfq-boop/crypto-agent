"""Tests for DATA-SRC-COINDESK-001 Checkpoint 3: Point-in-Time Semantics Audit."""

import pytest
import os
from datetime import datetime

from src.layers.layer1_data.coindesk_checkpoint3_pit_validator import (
    Checkpoint3PitValidator,
    PitSnapshot,
    PitRevision,
)


class TestCheckpoint3PitAudit:
    """Test PIT semantics audit framework."""

    def test_validator_init(self):
        """Test validator initialization."""
        validator = Checkpoint3PitValidator(api_key="test_key")
        assert validator.api_key == "test_key"
        assert len(validator.snapshots) == 0
        assert len(validator.revisions) == 0

    def test_no_api_key_returns_unverified(self):
        """Test that missing API key returns UNVERIFIED."""
        validator = Checkpoint3PitValidator(api_key=None)
        result = validator.audit_pit_semantics(asset="bitcoin")

        assert result["status"] == "SKIPPED"
        assert result["verdict"] == "UNVERIFIED"
        assert "No API key" in result["error"]

    def test_pit_snapshot_structure(self):
        """Test PitSnapshot dataclass structure."""
        snapshot = PitSnapshot(
            asset="bitcoin",
            fetch_date="2026-10-01",
            data_date="2026-09-30",
            volume_aggregate=100.0,
            volume_top_tier=50.0,
            volume_direct=30.0,
            fetch_timestamp="2026-10-01T00:00:00Z",
        )

        assert snapshot.asset == "bitcoin"
        assert snapshot.volume_aggregate == 100.0
        assert snapshot.volume_top_tier == 50.0

    def test_pit_revision_structure(self):
        """Test PitRevision dataclass structure."""
        revision = PitRevision(
            asset="bitcoin",
            data_date="2026-09-30",
            fetch_t0="2026-10-01T00:00:00Z",
            fetch_t1="2026-10-08T00:00:00Z",
            fetch_t2="2026-10-31T00:00:00Z",
            value_t0=100.0,
            value_t1=101.0,
            value_t2=100.5,
            revision_t0_t1=1.0,
            revision_t1_t2=-0.5,
            is_revised=True,
            magnitude=1.0,
        )

        assert revision.asset == "bitcoin"
        assert revision.is_revised is True
        assert revision.magnitude == 1.0

    def test_compare_stable_snapshots(self):
        """Test comparison of snapshots with no revision."""
        validator = Checkpoint3PitValidator(api_key="test_key")

        snapshot_t0 = PitSnapshot(
            asset="bitcoin",
            fetch_date="2026-10-01",
            data_date="2026-09-30",
            volume_aggregate=100.0,
            volume_top_tier=50.0,
            volume_direct=30.0,
            fetch_timestamp="2026-10-01T00:00:00Z",
        )

        snapshot_t1 = PitSnapshot(
            asset="bitcoin",
            fetch_date="2026-10-08",
            data_date="2026-09-30",
            volume_aggregate=100.0,
            volume_top_tier=50.0,
            volume_direct=30.0,
            fetch_timestamp="2026-10-08T00:00:00Z",
        )

        snapshot_t2 = PitSnapshot(
            asset="bitcoin",
            fetch_date="2026-10-31",
            data_date="2026-09-30",
            volume_aggregate=100.0,
            volume_top_tier=50.0,
            volume_direct=30.0,
            fetch_timestamp="2026-10-31T00:00:00Z",
        )

        revision = validator.compare_snapshots(snapshot_t0, snapshot_t1, snapshot_t2)

        assert revision.is_revised is False
        assert revision.magnitude == 0.0
        assert revision.revision_t0_t1 == 0.0
        assert revision.revision_t1_t2 == 0.0

    def test_compare_revised_snapshots(self):
        """Test comparison of snapshots with revision."""
        validator = Checkpoint3PitValidator(api_key="test_key")

        snapshot_t0 = PitSnapshot(
            asset="bitcoin",
            fetch_date="2026-10-01",
            data_date="2026-09-30",
            volume_aggregate=100.0,
            volume_top_tier=50.0,
            volume_direct=30.0,
            fetch_timestamp="2026-10-01T00:00:00Z",
        )

        snapshot_t1 = PitSnapshot(
            asset="bitcoin",
            fetch_date="2026-10-08",
            data_date="2026-09-30",
            volume_aggregate=105.0,
            volume_top_tier=52.5,
            volume_direct=31.5,
            fetch_timestamp="2026-10-08T00:00:00Z",
        )

        snapshot_t2 = PitSnapshot(
            asset="bitcoin",
            fetch_date="2026-10-31",
            data_date="2026-09-30",
            volume_aggregate=105.0,
            volume_top_tier=52.5,
            volume_direct=31.5,
            fetch_timestamp="2026-10-31T00:00:00Z",
        )

        revision = validator.compare_snapshots(snapshot_t0, snapshot_t1, snapshot_t2)

        assert revision.is_revised is True
        assert revision.magnitude > 0.0
        assert abs(revision.revision_t0_t1 - 5.0) < 0.01  # 5% revision

    def test_audit_pit_semantics_research_mode(self):
        """Test audit in research mode (no API key)."""
        validator = Checkpoint3PitValidator(api_key=None)
        result = validator.audit_pit_semantics(asset="bitcoin")

        assert result["status"] == "SKIPPED"
        assert result["checkpoint"] == "C3_PIT_SEMANTICS"
        assert result["verdict"] == "UNVERIFIED"

    def test_audit_multiple_dates_research_mode(self):
        """Test multi-date audit in research mode."""
        validator = Checkpoint3PitValidator(api_key=None)
        result = validator.audit_multiple_dates(asset="bitcoin", days=30)

        assert "revision_summary" in result
        assert result["status"] == "RESEARCH_READY"

    def test_generate_report_structure(self):
        """Test report generation."""
        validator = Checkpoint3PitValidator(api_key=None)
        report = validator.generate_report()

        assert "checkpoint" in report
        assert "status" in report
        assert "summary" in report
        assert report["checkpoint"] == "C3_PIT_SEMANTICS"


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("COINDESK_API_KEY"),
    reason="Requires COINDESK_API_KEY environment variable",
)
class TestCheckpoint3PitLive:
    """Live API tests for C3 (requires COINDESK_API_KEY)."""

    def test_pit_audit_single_date(self):
        """Test PIT audit on single date with real API."""
        api_key = os.environ.get("COINDESK_API_KEY")
        validator = Checkpoint3PitValidator(api_key=api_key)

        result = validator.audit_pit_semantics(
            asset="bitcoin",
            data_date="2026-09-30",
        )

        assert result["checkpoint"] == "C3_PIT_SEMANTICS"
        assert "verdict" in result
        assert "revisions_detected" in result

    def test_pit_audit_multiple_dates(self):
        """Test PIT audit across multiple dates."""
        api_key = os.environ.get("COINDESK_API_KEY")
        validator = Checkpoint3PitValidator(api_key=api_key)

        result = validator.audit_multiple_dates(
            asset="bitcoin",
            days=30,
        )

        assert result["checkpoint"] == "C3_PIT_SEMANTICS"
        assert "revision_summary" in result


def test_checkpoint_3_can_run():
    """Test that C3 validation can be executed."""
    from src.layers.layer1_data.coindesk_checkpoint3_pit_validator import (
        checkpoint_3_status,
    )

    report = checkpoint_3_status()

    assert report is not None
    assert report["checkpoint"] == "C3_PIT_SEMANTICS"
    assert "status" in report
