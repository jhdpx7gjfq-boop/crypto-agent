"""Tests for DATA-SRC-COINDESK-001 Checkpoint 4: Reference Dataset."""

import pytest
import os
from pathlib import Path

from src.layers.layer1_data.coindesk_checkpoint4_reference_dataset import (
    Checkpoint4ReferenceDataset,
)


class TestCheckpoint4ReferenceDataset:
    """Test reference dataset framework."""

    def test_validator_init(self):
        """Test validator initialization."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        assert validator.api_key == "test_key"
        assert validator.data_dir == Path("data/coindesk")

    def test_directories_created(self):
        """Test that required directories are created."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        assert validator.data_dir.exists()
        assert validator.metadata_dir.exists()

    def test_assets_defined(self):
        """Test asset definitions."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        assert "BTC" in validator.ASSETS
        assert "ETH" in validator.ASSETS
        assert "SOL" in validator.ASSETS
        assert validator.ASSETS["BTC"] == "bitcoin"

    def test_no_api_key_returns_skipped(self):
        """Test that missing API key returns SKIPPED."""
        validator = Checkpoint4ReferenceDataset(api_key=None)
        result = validator.fetch_volume_metrics(asset="bitcoin")

        assert result["status"] == "SKIPPED"
        assert result["verdict"] == "UNVERIFIED"
        assert "No API key" in result["error"]

    def test_fetch_volume_metrics_research_mode(self):
        """Test volume metrics fetch in research mode."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        result = validator.fetch_volume_metrics(
            asset="bitcoin",
            days=365,
            volume_type="aggregate"
        )

        assert result["checkpoint"] == "C4_REFERENCE_DATASET"
        assert result["status"] == "RESEARCH_READY"
        assert result["days_requested"] == 365

    def test_validate_dataset_quality(self):
        """Test quality validation framework."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        report = validator.validate_dataset_quality(asset="bitcoin")

        assert report["asset"] == "bitcoin"
        assert "quality_checks" in report
        assert "completeness" in report["quality_checks"]
        assert "no_gaps" in report["quality_checks"]

    def test_estimate_dataset_size(self):
        """Test storage estimation."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        estimate = validator.estimate_dataset_size()

        assert "estimated_size" in estimate
        assert "total_bytes" in estimate["estimated_size"]
        assert "total_mb" in estimate["estimated_size"]
        assert len(estimate["files"]) == 3

    def test_storage_plan(self):
        """Test storage plan structure."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        estimate = validator.estimate_dataset_size()

        assert estimate["storage_plan"]["format"] == "Parquet (columnar, compressed)"
        assert estimate["storage_plan"]["assets"] == ["BTC", "ETH", "SOL"]
        assert estimate["storage_plan"]["duration"] == "12 months (365 days)"

    def test_generate_report_structure(self):
        """Test report generation."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        report = validator.generate_report()

        assert report["checkpoint"] == "C4_REFERENCE_DATASET"
        assert report["status"] == "RESEARCH_MODE"
        assert "summary" in report
        assert "collection_plan" in report
        assert "quality_gates" in report

    def test_quality_gates_defined(self):
        """Test that quality gates are clearly defined."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        report = validator.generate_report()

        gates = report["quality_gates"]
        assert len(gates) >= 5
        assert any("95%" in gate for gate in gates)
        assert any("gaps" in gate.lower() for gate in gates)
        assert any("duplicate" in gate.lower() for gate in gates)

    def test_gate_dependencies(self):
        """Test that gate dependencies are documented."""
        validator = Checkpoint4ReferenceDataset(api_key="test_key")
        report = validator.generate_report()

        deps = report["dependencies"]
        assert len(deps) >= 2
        assert any("C2" in dep for dep in deps)
        assert any("C3" in dep for dep in deps)


def test_checkpoint_4_can_run():
    """Test that C4 validation can be executed."""
    from src.layers.layer1_data.coindesk_checkpoint4_reference_dataset import (
        checkpoint_4_status,
    )

    report = checkpoint_4_status()

    assert report is not None
    assert report["checkpoint"] == "C4_REFERENCE_DATASET"
    assert "summary" in report
