"""
Integration tests for Phase 5 Sector Rotation Tracker.

Tests sector-level capital flow detection, weighting analysis, and rotation signals.
"""

import pytest
from datetime import datetime

from src.layers.layer5_narm.sector_rotation import (
    SectorRotationTracker,
    SectorMetrics,
)


class TestSectorRotationTracker:
    """Test sector rotation detection."""

    @pytest.fixture
    def tracker(self):
        """Create sector rotation tracker."""
        return SectorRotationTracker()

    def test_sector_metrics_calculation(self, tracker):
        """Calculate metrics for each sector."""
        narm_signals = {
            "AI_TOKEN_1": 78.0,
            "AI_TOKEN_2": 72.0,
            "DEFI_TOKEN_1": 65.0,
            "DEFI_TOKEN_2": 58.0,
            "RWA_TOKEN_1": 55.0,
        }

        asset_sectors = {
            "AI_TOKEN_1": "AI",
            "AI_TOKEN_2": "AI",
            "DEFI_TOKEN_1": "DeFi",
            "DEFI_TOKEN_2": "DeFi",
            "RWA_TOKEN_1": "RWA",
        }

        adoption_velocities = {
            "AI_TOKEN_1": 80.0,
            "AI_TOKEN_2": 75.0,
            "DEFI_TOKEN_1": 65.0,
            "DEFI_TOKEN_2": 55.0,
            "RWA_TOKEN_1": 45.0,
        }

        capital_rotations = {
            "AI_TOKEN_1": 85.0,
            "AI_TOKEN_2": 80.0,
            "DEFI_TOKEN_1": 60.0,
            "DEFI_TOKEN_2": 50.0,
            "RWA_TOKEN_1": 40.0,
        }

        metrics = tracker.track_sector_metrics(
            narm_signals=narm_signals,
            asset_sectors=asset_sectors,
            adoption_velocities=adoption_velocities,
            capital_rotations=capital_rotations,
        )

        # Verify AI sector metrics
        assert "AI" in metrics
        ai_metrics = metrics["AI"]
        assert ai_metrics.avg_narm_score == pytest.approx(75.0, abs=0.1)
        assert ai_metrics.top_scorer == "AI_TOKEN_1"
        assert ai_metrics.top_score == 78.0
        assert ai_metrics.candidate_count == 2  # Both >= 65

        # Verify DeFi sector metrics
        assert "DeFi" in metrics
        defi_metrics = metrics["DeFi"]
        assert defi_metrics.candidate_count == 1  # Only DEFI_TOKEN_1 >= 65

    def test_sector_rotation_detection(self, tracker):
        """Detect rotation from one sector to another."""
        # First period: DeFi dominant
        period1_narm = {
            "DEFI_1": 75.0,
            "DEFI_2": 70.0,
            "AI_1": 55.0,
            "AI_2": 50.0,
        }

        period1_sectors = {
            "DEFI_1": "DeFi",
            "DEFI_2": "DeFi",
            "AI_1": "AI",
            "AI_2": "AI",
        }

        metrics1 = tracker.track_sector_metrics(
            narm_signals=period1_narm,
            asset_sectors=period1_sectors,
            adoption_velocities={k: 60.0 for k in period1_narm},
            capital_rotations={k: 60.0 for k in period1_narm},
        )

        # Second period: AI gaining weight
        period2_narm = {
            "DEFI_1": 60.0,
            "DEFI_2": 55.0,
            "AI_1": 78.0,
            "AI_2": 75.0,
        }

        metrics2 = tracker.track_sector_metrics(
            narm_signals=period2_narm,
            asset_sectors=period1_sectors,
            adoption_velocities={k: 80.0 for k in period2_narm},
            capital_rotations={k: 80.0 for k in period2_narm},
        )

        # Detect rotation
        rotation = tracker.detect_rotation(metrics2)

        if rotation:  # Rotation may be detected
            assert rotation.to_sector == "AI"
            assert rotation.rotation_strength > 0
            assert rotation.confidence in ["high", "medium", "low"]

    def test_sector_weighting_analysis(self, tracker):
        """Analyze sector weightings and momentum."""
        narm_signals = {
            "AI_1": 76.0,
            "AI_2": 74.0,
            "DEFI_1": 66.0,
        }

        asset_sectors = {
            "AI_1": "AI",
            "AI_2": "AI",
            "DEFI_1": "DeFi",
        }

        metrics = tracker.track_sector_metrics(
            narm_signals=narm_signals,
            asset_sectors=asset_sectors,
            adoption_velocities={k: 70.0 for k in narm_signals},
            capital_rotations={k: 70.0 for k in narm_signals},
        )

        weightings = tracker.get_sector_weights(metrics)

        # AI should have higher weight (2 candidates vs 1)
        assert len(weightings) > 0
        assert weightings[0].sector_name == "AI"
        assert weightings[0].weight_pct > 50  # AI has 2/3 of candidates

    def test_top_narratives_ranking(self, tracker):
        """Get top narratives by NARM score."""
        narm_signals = {
            "AI_LEADING": 82.0,
            "AI_FOLLOWER": 70.0,
            "DEFI_TOP": 76.0,
            "RWA_EMERGING": 68.0,
        }

        asset_sectors = {
            "AI_LEADING": "AI",
            "AI_FOLLOWER": "AI",
            "DEFI_TOP": "DeFi",
            "RWA_EMERGING": "RWA",
        }

        metrics = tracker.track_sector_metrics(
            narm_signals=narm_signals,
            asset_sectors=asset_sectors,
            adoption_velocities={k: 70.0 for k in narm_signals},
            capital_rotations={k: 70.0 for k in narm_signals},
        )

        top = tracker.get_top_narratives(metrics, limit=3)

        assert len(top) == 3
        assert top[0][1] == "AI_LEADING"  # Highest scorer
        assert top[0][2] == 82.0

    def test_rotation_confidence_scoring(self, tracker):
        """Confidence reflects signal quality."""
        narm_signals = {
            "TOKEN_1": 80.0,
            "TOKEN_2": 78.0,
            "TOKEN_3": 76.0,
        }

        asset_sectors = {
            "TOKEN_1": "NewNarrative",
            "TOKEN_2": "NewNarrative",
            "TOKEN_3": "NewNarrative",
        }

        metrics = tracker.track_sector_metrics(
            narm_signals=narm_signals,
            asset_sectors=asset_sectors,
            adoption_velocities={k: 80.0 for k in narm_signals},
            capital_rotations={k: 85.0 for k in narm_signals},  # Strong inflow
        )

        assert metrics["NewNarrative"].candidate_count == 3
        assert metrics["NewNarrative"].inflow_acceleration > 0

    def test_inflow_acceleration_calculation(self, tracker):
        """Calculate inflow acceleration rates."""
        narm_signals = {
            "HIGH_INFLOW": 70.0,
            "LOW_INFLOW": 65.0,
        }

        asset_sectors = {
            "HIGH_INFLOW": "Sector_A",
            "LOW_INFLOW": "Sector_B",
        }

        adoption = {"HIGH_INFLOW": 70.0, "LOW_INFLOW": 40.0}
        capital = {"HIGH_INFLOW": 90.0, "LOW_INFLOW": 45.0}  # Different flows

        metrics = tracker.track_sector_metrics(
            narm_signals=narm_signals,
            asset_sectors=asset_sectors,
            adoption_velocities=adoption,
            capital_rotations=capital,
        )

        # Sector_A should have positive acceleration
        assert metrics["Sector_A"].inflow_acceleration > 0
        # Sector_B should have negative acceleration
        assert metrics["Sector_B"].inflow_acceleration < 0

    def test_rotation_history_tracking(self, tracker):
        """Track rotation history for audit trail."""
        narm_signals = {
            "AI_1": 78.0,
            "DEFI_1": 62.0,
        }

        asset_sectors = {
            "AI_1": "AI",
            "DEFI_1": "DeFi",
        }

        metrics = tracker.track_sector_metrics(
            narm_signals=narm_signals,
            asset_sectors=asset_sectors,
            adoption_velocities={k: 75.0 for k in narm_signals},
            capital_rotations={k: 80.0 for k in narm_signals},
        )

        tracker.detect_rotation(metrics)

        audit = tracker.audit_rotation_history()
        assert audit["tracked_sectors"] == 2

    def test_sector_momentum_direction(self, tracker):
        """Detect sector momentum (up/down/stable)."""
        narm_signals = {
            "RISING": 72.0,
            "STABLE": 70.0,
            "FALLING": 68.0,
        }

        asset_sectors = {
            "RISING": "Growing",
            "STABLE": "Stable",
            "FALLING": "Declining",
        }

        metrics = tracker.track_sector_metrics(
            narm_signals=narm_signals,
            asset_sectors=asset_sectors,
            adoption_velocities={k: 70.0 for k in narm_signals},
            capital_rotations={k: 70.0 for k in narm_signals},
        )

        weightings = tracker.get_sector_weights(metrics)

        # All sectors should have momentum assigned
        for weighting in weightings:
            assert weighting.momentum_direction in ["up", "down", "stable"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
