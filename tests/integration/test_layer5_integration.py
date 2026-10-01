"""
Integration tests for Phase 5: Layer 5 Integration Scorer.

Tests combined Layer 3 (BCE) + Layer 4 (X20) + Layer 5 (NARM) scoring.
"""

import pytest
from datetime import datetime

from src.layers.layer5_narm.layer5_integration import (
    Layer5IntegrationScorer,
    Layer5Decision,
)


class TestLayer5Integration:
    """Test Layer 5 integrated scoring."""

    @pytest.fixture
    def scorer(self):
        """Create Layer 5 integration scorer."""
        return Layer5IntegrationScorer()

    def test_strong_buy_decision(self, scorer):
        """STRONG_BUY when all conditions met."""
        signal = scorer.score_combined(
            asset="AI_STRONG",
            bce_signal={"bce_score": 5.5, "valid": True},
            x20_score={"x20_opportunity_score": 82.0},
            narm_signal={"narm_score": 78.0},
            capital_flow_validated=True,
        )

        assert signal.decision == Layer5Decision.STRONG_BUY
        assert signal.confidence_level > 85
        assert signal.capital_flow_confirmed is True
        assert signal.position_size_recommendation > 2.0

    def test_buy_rotation_decision(self, scorer):
        """BUY_ROTATION for narrative-driven without capital flow."""
        signal = scorer.score_combined(
            asset="DEFI_ROTATION",
            bce_signal={"bce_score": 5.2, "valid": True},
            x20_score={"x20_opportunity_score": 70.0},
            narm_signal={"narm_score": 72.0},
            capital_flow_validated=None,
        )

        assert signal.decision == Layer5Decision.BUY_ROTATION
        assert signal.confidence_level > 75
        assert signal.is_rotation_candidate is True

    def test_research_decision(self, scorer):
        """RESEARCH when opportunity strong but BCE invalid."""
        signal = scorer.score_combined(
            asset="EMERGING",
            bce_signal={"bce_score": 4.0, "valid": False},
            x20_score={"x20_opportunity_score": 68.0},
            narm_signal={"narm_score": 70.0},
            capital_flow_validated=None,
        )

        assert signal.decision == Layer5Decision.RESEARCH
        assert signal.confidence_level < 75
        assert signal.bce_valid is False

    def test_watchlist_decision(self, scorer):
        """WATCHLIST for rotation candidate with invalid BCE."""
        signal = scorer.score_combined(
            asset="MONITORING",
            bce_signal={"bce_score": 3.5, "valid": False},
            x20_score={"x20_opportunity_score": 45.0},
            narm_signal={"narm_score": 68.0},
            capital_flow_validated=None,
        )

        assert signal.decision == Layer5Decision.WATCHLIST
        assert signal.is_rotation_candidate is True
        assert signal.bce_valid is False
        assert signal.position_size_recommendation < 1.0

    def test_hold_decision(self, scorer):
        """HOLD when no rotation signal."""
        signal = scorer.score_combined(
            asset="NEUTRAL",
            bce_signal={"bce_score": 3.5, "valid": False},
            x20_score={"x20_opportunity_score": 48.0},
            narm_signal={"narm_score": 55.0},
            capital_flow_validated=None,
        )

        assert signal.decision == Layer5Decision.HOLD
        assert signal.is_rotation_candidate is False
        assert signal.position_size_recommendation == 0.0

    def test_reject_decision(self, scorer):
        """REJECT or HOLD for strong negative signals."""
        signal = scorer.score_combined(
            asset="POOR",
            bce_signal={"bce_score": 2.0, "valid": False},
            x20_score={"x20_opportunity_score": 30.0},
            narm_signal={"narm_score": 35.0},
            capital_flow_validated=None,
        )

        # With no rotation signal and weak X20, should be HOLD or REJECT
        assert signal.decision in [Layer5Decision.REJECT, Layer5Decision.HOLD]
        assert signal.confidence_level < 40

    def test_confidence_calculation(self, scorer):
        """Confidence reflects signal quality."""
        # High quality signal
        high_conf = scorer.score_combined(
            asset="HIGH_CONF",
            bce_signal={"bce_score": 5.5, "valid": True},
            x20_score={"x20_opportunity_score": 80.0},
            narm_signal={"narm_score": 80.0},
            capital_flow_validated=True,
        )

        # Low quality signal
        low_conf = scorer.score_combined(
            asset="LOW_CONF",
            bce_signal={"bce_score": 2.5, "valid": False},
            x20_score={"x20_opportunity_score": 35.0},
            narm_signal={"narm_score": 40.0},
            capital_flow_validated=False,
        )

        assert high_conf.confidence_level > low_conf.confidence_level

    def test_risk_assessment(self, scorer):
        """Risk level based on component scores."""
        # Low risk
        low_risk = scorer.score_combined(
            asset="LOW_RISK",
            bce_signal={"bce_score": 5.5, "valid": True},
            x20_score={"x20_opportunity_score": 80.0},
            narm_signal={"narm_score": 80.0},
        )

        assert low_risk.risk_level == "low"

        # High risk
        high_risk = scorer.score_combined(
            asset="HIGH_RISK",
            bce_signal={"bce_score": 2.0, "valid": False},
            x20_score={"x20_opportunity_score": 35.0},
            narm_signal={"narm_score": 40.0},
        )

        assert high_risk.risk_level == "high"

    def test_position_size_recommendation(self, scorer):
        """Position size based on decision + confidence + risk."""
        strong_buy = scorer.score_combined(
            asset="STRONG",
            bce_signal={"bce_score": 5.5, "valid": True},
            x20_score={"x20_opportunity_score": 82.0},
            narm_signal={"narm_score": 78.0},
        )

        watch = scorer.score_combined(
            asset="WATCH",
            bce_signal={"bce_score": 3.5, "valid": False},
            x20_score={"x20_opportunity_score": 45.0},
            narm_signal={"narm_score": 68.0},
        )

        # STRONG_BUY should have larger position than WATCHLIST
        assert strong_buy.position_size_recommendation > watch.position_size_recommendation
        # Max position size should be 5%
        assert strong_buy.position_size_recommendation <= 5.0

    def test_rotation_candidate_detection(self, scorer):
        """Identify rotation candidates (NARM ≥65)."""
        rotation = scorer.score_combined(
            asset="ROTATION",
            bce_signal={"bce_score": 5.0, "valid": True},
            x20_score={"x20_opportunity_score": 60.0},
            narm_signal={"narm_score": 72.0},
        )

        non_rotation = scorer.score_combined(
            asset="NON_ROTATION",
            bce_signal={"bce_score": 5.0, "valid": True},
            x20_score={"x20_opportunity_score": 70.0},
            narm_signal={"narm_score": 55.0},
        )

        assert rotation.is_rotation_candidate is True
        assert rotation.rotation_strength == 72.0
        assert non_rotation.is_rotation_candidate is False

    def test_decision_history_tracking(self, scorer):
        """Track decision history for audit."""
        scorer.score_combined(
            asset="BTC",
            bce_signal={"bce_score": 5.5, "valid": True},
            x20_score={"x20_opportunity_score": 75.0},
            narm_signal={"narm_score": 70.0},
        )

        scorer.score_combined(
            asset="ETH",
            bce_signal={"bce_score": 5.2, "valid": True},
            x20_score={"x20_opportunity_score": 70.0},
            narm_signal={"narm_score": 68.0},
        )

        audit = scorer.audit_layer5_decisions()

        assert audit["total_decisions"] == 2
        assert len(audit["decisions_by_type"]) > 0

    def test_opportunity_ranking(self, scorer):
        """Rank opportunities by decision signal."""
        # Generate multiple signals
        for i, (asset, narm) in enumerate(
            [("AI_TOP", 80.0), ("DEFI_MID", 70.0), ("RWA_LOW", 55.0)]
        ):
            scorer.score_combined(
                asset=asset,
                bce_signal={"bce_score": 5.0 - i * 0.3, "valid": i < 2},
                x20_score={"x20_opportunity_score": 75.0 - i * 10},
                narm_signal={"narm_score": narm},
            )

        ranked = scorer.rank_opportunities(limit=5)

        # Top should be highest confidence
        assert len(ranked) <= 3
        if ranked:
            assert ranked[0]["asset"] == "AI_TOP"
            assert ranked[0]["decision"] in [
                "strong_buy",
                "buy_rotation",
                "research",
            ]

    def test_decision_cache(self, scorer):
        """Cache latest decision per asset."""
        signal1 = scorer.score_combined(
            asset="CACHE_TEST",
            bce_signal={"bce_score": 4.0, "valid": False},
            x20_score={"x20_opportunity_score": 50.0},
            narm_signal={"narm_score": 60.0},
        )

        signal2 = scorer.score_combined(
            asset="CACHE_TEST",
            bce_signal={"bce_score": 5.5, "valid": True},
            x20_score={"x20_opportunity_score": 78.0},
            narm_signal={"narm_score": 75.0},
        )

        summary = scorer.get_decision_summary("CACHE_TEST")

        # Should return latest decision
        assert summary["decision"] == signal2.decision.value
        assert summary["confidence"] == pytest.approx(signal2.confidence_level, abs=1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
