"""Integration tests for Phase 6 RCM/RPM Engine.

Tests combined 5-component scoring and rotation confirmation.
"""

import pytest
from datetime import datetime

from src.layers.layer6_rcm import RCMEngine, RCMDecision


class TestRCMEngine:
    """Test RCM integration and decision matrix."""

    @pytest.fixture
    def engine(self):
        """Create RCM engine."""
        return RCMEngine()

    def test_strong_confirm_decision(self, engine):
        """CONFIRM when RCM ≥75 with Layer 5 rotation."""
        signal = engine.scan(
            asset="BTC",
            cf_score=80.0,
            rs_score=78.0,
            na_score=76.0,
            fund_score=74.0,
            deriv_score=72.0,
            layer5_narm=78.0,
        )

        assert signal.decision == RCMDecision.CONFIRM
        assert signal.confidence > 0.80
        assert signal.validation_status == "confirmed"
        assert signal.bullish_components >= 4

    def test_monitor_decision(self, engine):
        """MONITOR when 60 ≤ RCM < 75."""
        signal = engine.scan(
            asset="ETH",
            cf_score=65.0,
            rs_score=63.0,
            na_score=62.0,
            fund_score=61.0,
            deriv_score=60.0,
            layer5_narm=70.0,
        )

        assert signal.decision == RCMDecision.MONITOR
        assert 0.65 < signal.confidence < 0.75
        assert signal.validation_status == "pending"

    def test_neutral_decision(self, engine):
        """NEUTRAL when 45 ≤ RCM < 60."""
        signal = engine.scan(
            asset="SOL",
            cf_score=50.0,
            rs_score=48.0,
            na_score=46.0,
            fund_score=44.0,
            deriv_score=42.0,
        )

        assert signal.decision == RCMDecision.NEUTRAL
        assert 0.50 < signal.confidence < 0.60

    def test_reject_decision(self, engine):
        """REJECT when RCM < 45."""
        signal = engine.scan(
            asset="LINK",
            cf_score=35.0,
            rs_score=33.0,
            na_score=32.0,
            fund_score=31.0,
            deriv_score=30.0,
        )

        assert signal.decision == RCMDecision.REJECT

    def test_rcm_score_calculation(self, engine):
        """RCM score = 30% CF + 25% RS + 20% NA + 20% Fund + 5% Deriv."""
        signal = engine.scan(
            asset="TEST",
            cf_score=100.0,  # 30%
            rs_score=100.0,  # 25%
            na_score=100.0,  # 20%
            fund_score=100.0,  # 20%
            deriv_score=100.0,  # 5%
        )

        expected = (100 * 0.30 + 100 * 0.25 + 100 * 0.20 + 100 * 0.20 + 100 * 0.05)
        assert abs(signal.rcm_score - expected) < 0.1

    def test_component_score_storage(self, engine):
        """Component scores stored in signal."""
        signal = engine.scan(
            asset="TEST",
            cf_score=70.0,
            rs_score=75.0,
            na_score=80.0,
            fund_score=65.0,
            deriv_score=60.0,
        )

        assert signal.component_scores["capital_flow"] == 70.0
        assert signal.component_scores["relative_strength"] == 75.0
        assert signal.component_scores["narrative_acceleration"] == 80.0
        assert signal.component_scores["fundamentals"] == 65.0
        assert signal.component_scores["derivatives"] == 60.0

    def test_bullish_bearish_counting(self, engine):
        """Count bullish (>65) and bearish (<40) components."""
        signal = engine.scan(
            asset="TEST",
            cf_score=70.0,  # Bullish
            rs_score=75.0,  # Bullish
            na_score=35.0,  # Bearish
            fund_score=65.0,  # Borderline
            deriv_score=30.0,  # Bearish
        )

        assert signal.bullish_components == 2
        assert signal.bearish_components == 2

    def test_layer5_alignment_confirmed(self, engine):
        """RCM ≥75 + L5 ≥65 = confirmed."""
        signal = engine.scan(
            asset="TEST",
            cf_score=80.0,
            rs_score=78.0,
            na_score=76.0,
            fund_score=74.0,
            deriv_score=72.0,
            layer5_narm=75.0,
        )

        assert signal.validation_status == "confirmed"
        assert "confirms" in signal.integration_with_layer5.lower()

    def test_layer5_alignment_rejected(self, engine):
        """RCM <45 + L5 ≥65 = rejected (false positive)."""
        signal = engine.scan(
            asset="TEST",
            cf_score=35.0,
            rs_score=33.0,
            na_score=32.0,
            fund_score=31.0,
            deriv_score=30.0,
            layer5_narm=70.0,
        )

        assert signal.validation_status == "rejected"
        assert "rejects" in signal.integration_with_layer5.lower()

    def test_decision_caching(self, engine):
        """Latest decision cached per asset."""
        signal1 = engine.scan(
            asset="CACHE_TEST",
            cf_score=50.0,
            rs_score=50.0,
            na_score=50.0,
            fund_score=50.0,
            deriv_score=50.0,
        )

        signal2 = engine.scan(
            asset="CACHE_TEST",
            cf_score=80.0,
            rs_score=78.0,
            na_score=76.0,
            fund_score=74.0,
            deriv_score=72.0,
        )

        cached = engine.decision_cache["CACHE_TEST"]
        assert cached.rcm_score == pytest.approx(signal2.rcm_score, abs=0.1)
        assert cached.decision == signal2.decision

    def test_get_decision_summary(self, engine):
        """Retrieve cached decision summary."""
        engine.scan(
            asset="SUMMARY_TEST",
            cf_score=70.0,
            rs_score=75.0,
            na_score=72.0,
            fund_score=68.0,
            deriv_score=65.0,
            layer5_narm=72.0,
        )

        summary = engine.get_decision_summary("SUMMARY_TEST")
        assert summary is not None
        assert summary["asset"] == "SUMMARY_TEST"
        assert summary["decision"] in ["confirm", "monitor", "neutral", "reject"]
        assert 0 <= summary["confidence"] <= 1

    def test_rank_opportunities(self, engine):
        """Rank multiple assets by RCM score."""
        assets_data = [
            ("TOP", 80.0, 78.0, 76.0, 74.0, 72.0),
            ("MID", 70.0, 68.0, 66.0, 64.0, 62.0),
            ("LOW", 40.0, 38.0, 36.0, 34.0, 32.0),
        ]

        for asset, cf, rs, na, fund, deriv in assets_data:
            engine.scan(asset, cf, rs, na, fund, deriv)

        ranked = engine.rank_opportunities(["TOP", "MID", "LOW"], limit=3)

        assert len(ranked) == 3
        assert ranked[0]["asset"] == "TOP"
        assert ranked[0]["rcm_score"] > ranked[1]["rcm_score"]
        assert ranked[1]["rcm_score"] > ranked[2]["rcm_score"]

    def test_audit_rcm_decisions(self, engine):
        """Audit decision history."""
        for i, asset in enumerate(["BTC", "ETH", "SOL"]):
            engine.scan(
                asset,
                70.0 - i * 5,
                70.0 - i * 5,
                70.0 - i * 5,
                70.0 - i * 5,
                70.0 - i * 5,
            )

        audit = engine.audit_rcm_decisions()

        assert audit["total_decisions"] == 3
        assert audit["assets_analyzed"] == 3
        assert "confirm" in audit["decisions_by_type"] or "monitor" in audit["decisions_by_type"]
        assert audit["avg_rcm_score"] > 0

    def test_multiple_analyses_per_asset(self, engine):
        """Track history of multiple analyses per asset."""
        asset = "HISTORY_TEST"

        for i in range(3):
            engine.scan(
                asset,
                60.0 + i * 5,
                60.0 + i * 5,
                60.0 + i * 5,
                60.0 + i * 5,
                60.0 + i * 5,
            )

        history = engine.analysis_history[asset]
        assert len(history) == 3
        # Later analyses should have higher scores
        assert history[2].rcm_score > history[0].rcm_score

    def test_component_weights(self, engine):
        """Component weights affect overall score."""
        # High capital flow, low others
        high_cf = engine.scan(
            asset="HIGH_CF",
            cf_score=100.0,
            rs_score=0.0,
            na_score=0.0,
            fund_score=0.0,
            deriv_score=0.0,
        )

        # High relative strength, low others
        high_rs = engine.scan(
            asset="HIGH_RS",
            cf_score=0.0,
            rs_score=100.0,
            na_score=0.0,
            fund_score=0.0,
            deriv_score=0.0,
        )

        # CF weight 30% should make high_cf > high_rs
        assert high_cf.rcm_score > high_rs.rcm_score

    def test_no_layer5_signal(self, engine):
        """Handle missing Layer 5 signal gracefully."""
        signal = engine.scan(
            asset="NO_L5",
            cf_score=70.0,
            rs_score=70.0,
            na_score=70.0,
            fund_score=70.0,
            deriv_score=70.0,
            layer5_narm=None,
        )

        assert signal.layer5_narm_score is None
        assert signal.validation_status == "pending"
        assert "No Layer 5 signal" in signal.integration_with_layer5

    def test_extreme_component_scores(self, engine):
        """Handle extreme scores correctly."""
        signal = engine.scan(
            asset="EXTREME",
            cf_score=0.0,
            rs_score=100.0,
            na_score=50.0,
            fund_score=75.0,
            deriv_score=25.0,
        )

        assert 0 <= signal.rcm_score <= 100
        assert signal.decision in [RCMDecision.CONFIRM, RCMDecision.MONITOR,
                                   RCMDecision.NEUTRAL, RCMDecision.REJECT]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
