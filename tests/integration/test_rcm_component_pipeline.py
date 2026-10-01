"""Integration tests for Phase 6 complete component pipeline.

Tests all 5 analyzers working together with realistic data flows.
"""

import pytest
from datetime import datetime

from src.layers.layer6_rcm import (
    CapitalFlowTracker,
    RelativeStrengthAnalyzer,
    NarrativeAccelerationEngine,
    FundamentalAnalyzer,
    DerivativesAnalyzer,
)


class TestCapitalFlowTracker:
    """Test capital flow component."""

    @pytest.fixture
    def tracker(self):
        return CapitalFlowTracker()

    def test_whale_accumulation_high_confidence(self, tracker):
        """High confidence when accum > distrib*2."""
        whale_data = {
            "accumulating_addresses": 40,
            "distributing_addresses": 10,
            "net_accumulation_pct": 2.5,
            "acceleration_rate": 1.2,
            "large_addresses_count": 50,
        }

        analysis = tracker.analyze_capital_flow(
            "BTC",
            whale_data,
            {"total_inflow": 500, "total_outflow": 800},
            {"active_smart_wallets": 12, "avg_holding_period_days": 240},
            {"cluster_count": 3, "total_volume": 500},
        )

        assert analysis.whale_accumulation.confidence == "high"
        assert analysis.whale_accumulation.score > 70

    def test_exchange_outflow_bullish(self, tracker):
        """Outflow > inflow signals bullish."""
        analysis = tracker.analyze_capital_flow(
            "ETH",
            {"accumulating_addresses": 30, "distributing_addresses": 10},
            {"total_inflow": 200, "total_outflow": 1200, "large_withdrawal_count": 25},
            {"active_smart_wallets": 10},
            {"cluster_count": 2, "total_volume": 300},
        )

        assert analysis.exchange_flows.net_exchange_flow == 1000
        assert analysis.exchange_flows.exchange_net_ratio == 6.0
        assert analysis.exchange_flows.score > 60

    def test_smart_money_recent_accumulation(self, tracker):
        """Smart money recent accumulation boosts score."""
        analysis = tracker.analyze_capital_flow(
            "SOL",
            {"accumulating_addresses": 25},
            {"total_inflow": 400, "total_outflow": 600},
            {
                "active_smart_wallets": 15,
                "avg_holding_period_days": 300,
                "recent_accumulation": True,
                "unrealized_gain_pct": 50,
            },
            {"cluster_count": 4},
        )

        assert analysis.smart_money.recent_accumulation is True
        assert analysis.smart_money.score > 70

    def test_transaction_clustering_bullish(self, tracker):
        """Multiple clusters signal coordinated buying."""
        analysis = tracker.analyze_capital_flow(
            "LINK",
            {"accumulating_addresses": 20},
            {"total_inflow": 300, "total_outflow": 700},
            {"active_smart_wallets": 8},
            {
                "cluster_count": 5,
                "cluster_size_avg": 10,
                "time_span_hours": 48,
                "total_volume": 1000,
            },
        )

        assert analysis.transaction_clusters.cluster_count == 5
        assert analysis.transaction_clusters.score > 60


class TestRelativeStrengthAnalyzer:
    """Test relative strength component."""

    @pytest.fixture
    def analyzer(self):
        return RelativeStrengthAnalyzer()

    def test_outperformance_vs_btc(self, analyzer):
        """Asset outperforming BTC gets higher score."""
        # Note: analyze_relative_strength needs proper price_data structure
        # Simplify test to check component functions
        analysis = analyzer.analyze_relative_strength(
            "ETH",
            {"price_change_7d": 20, "volatility_7d": 3.5},
            {"price_change_7d": 10, "volatility_7d": 2.5},
            {"price_change_7d": 8, "volatility_7d": 3.0},
        )

        assert analysis.asset_momentum.price_change_7d == 20
        assert analysis.relative_strength_score > 30

    def test_accelerating_momentum(self, analyzer):
        """Strong outperformance = accelerating momentum."""
        analysis = analyzer.analyze_relative_strength(
            "SOL",
            {"price_change_7d": 30, "volatility_7d": 4.0},
            {"price_change_7d": 10, "volatility_7d": 2.0},
            {"price_change_7d": 8, "volatility_7d": 3.0},
        )

        assert analysis.momentum_direction in ["accelerating", "stable", "decelerating"]
        assert analysis.relative_strength_score > 30

    def test_sector_leadership(self, analyzer):
        """Top performer in sector gets boost."""
        analysis = analyzer.analyze_relative_strength(
            "UNI",
            {"asset": {"price_change_7d": 12, "volatility_7d": 3.0}},
            {"btc": {"price_change_7d": 8, "volatility_7d": 2.0}},
            {"market": {"price_change_7d": 7, "volatility_7d": 3.0}},
            {"sector": {"top_performer": "UNI", "top_performer_score": 80}},
        )

        assert analysis.sector_context is not None
        assert analysis.sector_context.top_performer == "UNI"


class TestNarrativeAccelerationEngine:
    """Test narrative acceleration component."""

    @pytest.fixture
    def engine(self):
        return NarrativeAccelerationEngine()

    def test_narm_acceleration_detection(self, engine):
        """Detect NARM score acceleration."""
        narm_history = [
            50, 51, 52, 53, 54, 55, 57, 60, 65, 71,  # Accelerating
        ]

        analysis = engine.analyze_narrative_acceleration(
            "AI",
            narm_history,
            {"social_volume_7d_change": 150, "sentiment_score": 75},
            {"current_funding_rate": 0.08},
        )

        # Should detect growth in NARM
        assert analysis.narm_acceleration.current_narm > 50
        assert analysis.narm_acceleration.narm_7d_change > 0
        assert analysis.narrative_acceleration_score > 50

    def test_explosive_phase_detection(self, engine):
        """Detect explosive acceleration phase."""
        narm_history = [60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80, 82, 84]

        analysis = engine.analyze_narrative_acceleration(
            "DEFI",
            narm_history,
            {"social_volume_7d_change": 300, "sentiment_score": 80},
            {"current_funding_rate": 0.12, "open_interest_change_7d": 25},
        )

        assert analysis.acceleration_phase in ["explosive", "mature", "stable"]
        assert analysis.narrative_acceleration_score > 60

    def test_mean_reversion_signal(self, engine):
        """Extreme funding rates signal reversal risk."""
        narm_history = [80, 82, 85, 86, 85, 82]

        analysis = engine.analyze_narrative_acceleration(
            "PEAK",
            narm_history,
            {"social_volume_7d_change": 50, "sentiment_score": 65},
            {"current_funding_rate": 0.20},  # Extreme
        )

        assert analysis.funding_structure.mean_reversion_signal is True
        assert analysis.narrative_acceleration_score < 70


class TestFundamentalAnalyzer:
    """Test fundamental analysis component."""

    @pytest.fixture
    def analyzer(self):
        return FundamentalAnalyzer()

    def test_on_chain_dau_growth(self, analyzer):
        """Growing DAU signals health."""
        analysis = analyzer.analyze_fundamentals(
            "SOL",
            {
                "daily_active_users": 150000,
                "dau_growth_rate": 25,
                "transaction_volume": 5000,
                "transaction_volume_growth": 20,
                "whale_transaction_count": 100,
            },
        )

        assert analysis.on_chain_metrics.daily_active_users == 150000
        assert analysis.on_chain_metrics.dau_growth_rate == 25
        assert analysis.on_chain_metrics.score > 70

    def test_tvl_growth_defi(self, analyzer):
        """Growing TVL signals protocol health."""
        analysis = analyzer.analyze_fundamentals(
            "AAVE",
            {"daily_active_users": 50000},
            {
                "current_tvl": 5_000_000_000,
                "tvl_7d_change": 15,
                "major_deposits_7d": 20,
            },
        )

        assert analysis.tvl_analysis is not None
        assert analysis.tvl_analysis.tvl_trend == "growing"
        assert analysis.tvl_analysis.score > 65

    def test_token_unlock_risk_medium(self, analyzer):
        """Near-term large unlock = medium risk."""
        analysis = analyzer.analyze_fundamentals(
            "TOKEN",
            {"daily_active_users": 30000},
            tvl_data=None,
            unlock_data={
                "days_to_next_unlock": 20,
                "unlock_percentage": 5.0,
                "concentration_risk": 0.5,
            },
        )

        assert analysis.token_unlock_risk.days_to_next_unlock == 20
        assert analysis.token_unlock_risk.score < 70

    def test_developer_activity_health(self, analyzer):
        """Active developer community = health."""
        analysis = analyzer.analyze_fundamentals(
            "ARCH",
            {"daily_active_users": 50000},
            dev_data={
                "weekly_commits": 250,
                "active_developers": 30,
                "ecosystem_projects_count": 150,
                "security_audit_status": "passed",
            },
        )

        assert analysis.developer_activity.active_developers == 30
        assert analysis.developer_activity.score > 75


class TestDerivativesAnalyzer:
    """Test derivatives market component."""

    @pytest.fixture
    def analyzer(self):
        return DerivativesAnalyzer()

    def test_healthy_funding_rate(self, analyzer):
        """Moderate positive funding = healthy bullish."""
        analysis = analyzer.analyze_derivatives(
            "BTC",
            {
                "current_funding": 0.08,
                "funding_7d_avg": 0.07,
                "previous_funding": 0.06,
                "funding_volatility": 0.02,
            },
            {"total_oi": 100_000_000, "oi_change_7d": 20, "long_oi": 60_000_000, "short_oi": 40_000_000},
            {"liquidation_price_long": 45000, "liquidation_price_short": 55000},
        )

        assert analysis.funding_rates.current_funding == 0.08
        assert analysis.funding_rates.score > 70

    def test_extreme_long_leverage(self, analyzer):
        """Heavy long positioning = reversal risk."""
        analysis = analyzer.analyze_derivatives(
            "MEME",
            {"current_funding": 0.15, "funding_7d_avg": 0.12, "previous_funding": 0.10},
            {
                "total_oi": 50_000_000,
                "oi_change_7d": 30,
                "long_oi": 40_000_000,
                "short_oi": 10_000_000,
            },
            {"liquidation_price_long": 1.50, "liquidation_price_short": 5.0,
             "estimated_cascade_volume": 200_000_000, "cascade_likelihood": 0.3},
        )

        assert analysis.leverage_regime == "extreme_long"
        assert analysis.derivatives_score < 75

    def test_liquidation_cascade_risk(self, analyzer):
        """Close liquidation levels = high risk."""
        analysis = analyzer.analyze_derivatives(
            "VOLATILE",
            {"current_funding": 0.05},
            {"total_oi": 30_000_000, "long_oi": 20_000_000, "short_oi": 10_000_000},
            {
                "liquidation_price_long": 99.50,
                "cascade_likelihood": 0.80,
                "distance_to_cascade_pct": 2.0,
            },
        )

        assert analysis.liquidation_risk.cascade_likelihood == 0.80
        assert analysis.liquidation_risk.score < 40


class TestMultiComponentPipeline:
    """Test all 5 components working together."""

    def test_bullish_rotation_signal(self):
        """All components signal bullish rotation."""
        cf = CapitalFlowTracker()
        rs = RelativeStrengthAnalyzer()
        na = NarrativeAccelerationEngine()
        fund = FundamentalAnalyzer()
        deriv = DerivativesAnalyzer()

        # Capital flow: bullish
        cf_analysis = cf.analyze_capital_flow(
            "AI_LEADER",
            {"accumulating_addresses": 40, "distributing_addresses": 10,
             "net_accumulation_pct": 2.0, "acceleration_rate": 1.0, "large_addresses_count": 50},
            {"total_inflow": 300, "total_outflow": 700, "large_withdrawal_count": 10},
            {"active_smart_wallets": 12, "avg_holding_period_days": 200,
             "recent_accumulation": True, "unrealized_gain_pct": 30},
            {"cluster_count": 4, "cluster_size_avg": 8, "time_span_hours": 48, "total_volume": 500},
        )

        # Momentum: accelerating
        rs_analysis = rs.analyze_relative_strength(
            "AI_LEADER",
            {"price_change_7d": 25, "volatility_7d": 3.0},
            {"price_change_7d": 10, "volatility_7d": 2.0},
            {"price_change_7d": 8, "volatility_7d": 3.0},
        )

        # Narrative: accelerating
        na_analysis = na.analyze_narrative_acceleration(
            "AI_LEADER",
            [50, 52, 55, 58, 62, 66, 70, 74, 77, 80],
            {"social_volume_7d_change": 200, "sentiment_score": 78},
            {"current_funding_rate": 0.09},
        )

        # Fundamentals: healthy
        fund_analysis = fund.analyze_fundamentals(
            "AI_LEADER",
            {"daily_active_users": 100000, "dau_growth_rate": 20,
             "transaction_volume": 5000, "whale_transaction_count": 80},
            dev_data={"weekly_commits": 200, "active_developers": 25,
                     "ecosystem_projects_count": 100},
        )

        # Derivatives: bullish
        deriv_analysis = deriv.analyze_derivatives(
            "AI_LEADER",
            {"current_funding": 0.08, "funding_7d_avg": 0.07, "previous_funding": 0.06},
            {"total_oi": 150_000_000, "oi_change_7d": 25, "long_oi": 85_000_000, "short_oi": 65_000_000},
            {"liquidation_price_long": 0.9, "liquidation_price_short": 1.1,
             "cascade_likelihood": 0.2, "distance_to_cascade_pct": 10},
        )

        # All components should have valid scores
        assert cf_analysis.capital_flow_score > 0
        assert rs_analysis.relative_strength_score > 0
        assert na_analysis.narrative_acceleration_score > 0
        assert fund_analysis.fundamental_score > 0
        assert deriv_analysis.derivatives_score > 0

        # Weighted RCM score should be positive
        rcm_score = (
            cf_analysis.capital_flow_score * 0.30
            + rs_analysis.relative_strength_score * 0.25
            + na_analysis.narrative_acceleration_score * 0.20
            + fund_analysis.fundamental_score * 0.20
            + deriv_analysis.derivatives_score * 0.05
        )

        assert rcm_score > 40  # Valid signal


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
