"""Tests for DATA-SRC-COINDESK-001 Checkpoint 2: Historical Access & Timestamps."""

import pytest
import os
from datetime import datetime

from src.layers.layer1_data.coindesk_checkpoint2_validator import (
    Checkpoint2HistoricalValidator
)


class TestCheckpoint2HistoricalAccess:
    """Test historical data access validation."""

    def test_validator_init(self):
        """Test validator initialization."""
        validator = Checkpoint2HistoricalValidator(api_key="test_key")
        assert validator.api_key == "test_key"
        assert validator.BASE_URL == "https://api.coindesk.com/v1"
        assert "BTC" in validator.ASSETS

    def test_no_api_key_returns_unverified(self):
        """Test that missing API key returns UNVERIFIED."""
        validator = Checkpoint2HistoricalValidator(api_key=None)
        result = validator.validate_historical_access(asset="bitcoin")

        assert result["status"] == "SKIPPED"
        assert result["verdict"] == "UNVERIFIED"
        assert "No API key" in result["error"]

    def test_report_structure(self):
        """Test report structure with missing API key."""
        validator = Checkpoint2HistoricalValidator(api_key=None)
        report = validator.generate_report()

        assert "checkpoint" in report
        assert "summary" in report
        assert "results" in report
        assert "key_findings" in report
        assert report["checkpoint"] == "C2_HISTORICAL_ACCESS"

    def test_report_has_all_assets(self):
        """Test that report includes all tracked assets."""
        validator = Checkpoint2HistoricalValidator(api_key=None)
        report = validator.generate_report()

        assert "BTC" in report["results"]
        assert "ETH" in report["results"]
        assert "SOL" in report["results"]

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.environ.get("COINDESK_API_KEY"),
        reason="Requires COINDESK_API_KEY environment variable"
    )
    def test_historical_access_with_real_key(self):
        """Test actual API call with real API key (requires Pro/Enterprise tier)."""
        api_key = os.environ.get("COINDESK_API_KEY")
        validator = Checkpoint2HistoricalValidator(api_key=api_key)

        result = validator.validate_historical_access(asset="bitcoin", days=365)

        # Check result structure
        assert "status" in result
        assert "verdict" in result
        assert "data_points" in result
        assert "timestamp_first" in result
        assert "timestamp_last" in result

        # If successful, check data quality
        if result["verdict"] == "PASS":
            assert result["is_monotonic"] is True
            assert len(result["timestamp_gaps"]) == 0
            assert result["completeness"] >= 0.95

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.environ.get("COINDESK_API_KEY"),
        reason="Requires COINDESK_API_KEY environment variable"
    )
    def test_all_assets_validation_with_real_key(self):
        """Test validation of all assets (BTC, ETH, SOL) with real API key."""
        api_key = os.environ.get("COINDESK_API_KEY")
        validator = Checkpoint2HistoricalValidator(api_key=api_key)

        results = validator.validate_all_assets()

        assert len(results) == 3
        for ticker, result in results.items():
            assert ticker in ["BTC", "ETH", "SOL"]
            assert "verdict" in result
            assert "data_points" in result


# Checkpoint 2 status command
def test_checkpoint2_can_run(capsys):
    """Test that C2 validation can be executed."""
    from src.layers.layer1_data.coindesk_checkpoint2_validator import (
        checkpoint_2_status
    )

    report = checkpoint_2_status()

    assert report is not None
    assert report["checkpoint"] == "C2_HISTORICAL_ACCESS"
    assert "summary" in report
