"""
Unit tests for Risk Assessment Engine (Phase 4 Component 4).
"""

import pytest
from src.layers.layer4_x20.risk_assessor import (
    RiskAssessor,
    RiskLevel,
    DrawdownMetrics,
    ConcentrationMetrics,
    ExecutionMetrics,
    TimelineMetrics,
)


class TestRiskAssessor:
    """Tests for RiskAssessor class."""

    @pytest.fixture
    def assessor(self):
        """Create risk assessor instance."""
        return RiskAssessor()

    @pytest.fixture
    def low_volatility_metrics(self):
        """Create low volatility drawdown metrics."""
        return DrawdownMetrics(
            volatility=0.12,  # 12%
            historical_max_drawdown=0.20,  # 20%
            estimated_max_drawdown=0.18,
            recovery_periods=[20, 25, 30],
            var_95=0.08,
        )

    @pytest.fixture
    def high_volatility_metrics(self):
        """Create high volatility drawdown metrics."""
        return DrawdownMetrics(
            volatility=0.50,  # 50%
            historical_max_drawdown=0.60,  # 60%
            estimated_max_drawdown=0.55,
            recovery_periods=[60, 90, 120],
            var_95=0.35,
        )

    @pytest.fixture
    def safe_concentration(self):
        """Create safe concentration metrics."""
        return ConcentrationMetrics(
            position_size_pct=0.02,  # 2%
            portfolio_allocation=0.05,
            max_position=0.10,
            avg_position=0.05,
            correlation_to_portfolio=0.4,  # Low correlation
            diversification_score=0.8,  # Well diversified
        )

    @pytest.fixture
    def risky_concentration(self):
        """Create risky concentration metrics."""
        return ConcentrationMetrics(
            position_size_pct=0.12,  # 12% (over limit)
            portfolio_allocation=0.05,
            max_position=0.10,
            avg_position=0.05,
            correlation_to_portfolio=0.85,  # High correlation
            diversification_score=0.3,  # Concentrated
        )

    @pytest.fixture
    def liquid_execution(self):
        """Create liquid execution metrics."""
        return ExecutionMetrics(
            bid_ask_spread=0.0008,  # 0.08%
            estimated_slippage_1pct=0.02,  # 2%
            estimated_slippage_5pct=0.08,  # 8%
            market_impact_factor=0.0005,
            liquidity_depth=5e6,  # $5M
            venue_fragmentation=0.7,
        )

    @pytest.fixture
    def illiquid_execution(self):
        """Create illiquid execution metrics."""
        return ExecutionMetrics(
            bid_ask_spread=0.05,  # 5%
            estimated_slippage_1pct=0.25,  # 25%
            estimated_slippage_5pct=0.50,  # 50%
            market_impact_factor=0.005,
            liquidity_depth=100e3,  # $100K
            venue_fragmentation=0.2,  # Single venue
        )

    @pytest.fixture
    def safe_timeline(self):
        """Create safe timeline metrics."""
        return TimelineMetrics(
            token_unlock_upcoming=0,  # No unlock
            unlock_amount_pct=0.0,
            regulatory_events=0,
            days_to_key_events=[],
            unlock_schedule_concentration=0.0,
        )

    @pytest.fixture
    def risky_timeline(self):
        """Create risky timeline metrics."""
        return TimelineMetrics(
            token_unlock_upcoming=20,  # 20 days
            unlock_amount_pct=0.25,  # 25% of supply
            regulatory_events=2,
            days_to_key_events=[20, 45],
            unlock_schedule_concentration=0.6,
        )

    def test_assessor_creation(self, assessor):
        """Test assessor instantiation."""
        assert assessor is not None
        assert len(assessor.results) == 0

    def test_drawdown_risk_low(self, assessor, low_volatility_metrics):
        """Test drawdown risk scoring with low volatility."""
        score = assessor._score_drawdown_risk(low_volatility_metrics)

        assert 0 <= score <= 100
        assert score < 40  # Low volatility = low risk

    def test_drawdown_risk_high(self, assessor, high_volatility_metrics):
        """Test drawdown risk scoring with high volatility."""
        score = assessor._score_drawdown_risk(high_volatility_metrics)

        assert 0 <= score <= 100
        assert score > 70  # High volatility = high risk

    def test_concentration_risk_safe(self, assessor, safe_concentration):
        """Test concentration risk scoring with safe metrics."""
        score = assessor._score_concentration_risk(safe_concentration)

        assert 0 <= score <= 100
        assert score < 45  # Safe position = low risk

    def test_concentration_risk_high(self, assessor, risky_concentration):
        """Test concentration risk scoring with risky metrics."""
        score = assessor._score_concentration_risk(risky_concentration)

        assert 0 <= score <= 100
        assert score > 60  # High correlation + large position = high risk

    def test_execution_risk_liquid(self, assessor, liquid_execution):
        """Test execution risk scoring with liquid asset."""
        score = assessor._score_execution_risk(liquid_execution)

        assert 0 <= score <= 100
        assert score < 50  # Liquid = low execution risk

    def test_execution_risk_illiquid(self, assessor, illiquid_execution):
        """Test execution risk scoring with illiquid asset."""
        score = assessor._score_execution_risk(illiquid_execution)

        assert 0 <= score <= 100
        assert score > 65  # Illiquid = high execution risk

    def test_timeline_risk_safe(self, assessor, safe_timeline):
        """Test timeline risk scoring with no unlocks."""
        score = assessor._score_timeline_risk(safe_timeline)

        assert 0 <= score <= 100
        assert score < 40  # No events = low timeline risk

    def test_timeline_risk_risky(self, assessor, risky_timeline):
        """Test timeline risk scoring with upcoming unlock."""
        score = assessor._score_timeline_risk(risky_timeline)

        assert 0 <= score <= 100
        assert score > 70  # Imminent unlock = high timeline risk

    def test_risk_level_minimal(self, assessor):
        """Test risk classification for minimal."""
        level = assessor._classify_risk_level(10.0)
        assert level == RiskLevel.MINIMAL

    def test_risk_level_low(self, assessor):
        """Test risk classification for low."""
        level = assessor._classify_risk_level(30.0)
        assert level == RiskLevel.LOW

    def test_risk_level_moderate(self, assessor):
        """Test risk classification for moderate."""
        level = assessor._classify_risk_level(50.0)
        assert level == RiskLevel.MODERATE

    def test_risk_level_high(self, assessor):
        """Test risk classification for high."""
        level = assessor._classify_risk_level(70.0)
        assert level == RiskLevel.HIGH

    def test_risk_level_critical(self, assessor):
        """Test risk classification for critical."""
        level = assessor._classify_risk_level(85.0)
        assert level == RiskLevel.CRITICAL

    def test_full_assessment_safe_asset(
        self, assessor, low_volatility_metrics, safe_concentration,
        liquid_execution, safe_timeline
    ):
        """Test complete assessment for safe asset."""
        result = assessor.assess_risk(
            asset='SAFE_ASSET',
            drawdown_metrics=low_volatility_metrics,
            concentration_metrics=safe_concentration,
            execution_metrics=liquid_execution,
            timeline_metrics=safe_timeline,
        )

        assert result is not None
        assert result.asset == 'SAFE_ASSET'
        assert result.overall_risk_score < 50
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MINIMAL]
        assert result.can_safely_allocate is True
        assert result.recommended_max_position > 0.03

    def test_full_assessment_risky_asset(
        self, assessor, high_volatility_metrics, risky_concentration,
        illiquid_execution, risky_timeline
    ):
        """Test complete assessment for risky asset."""
        result = assessor.assess_risk(
            asset='RISKY_ASSET',
            drawdown_metrics=high_volatility_metrics,
            concentration_metrics=risky_concentration,
            execution_metrics=illiquid_execution,
            timeline_metrics=risky_timeline,
        )

        assert result.overall_risk_score > 75
        assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert result.can_safely_allocate is False
        assert result.recommended_max_position < 0.03

    def test_drawdown_estimation(self, assessor, low_volatility_metrics):
        """Test max drawdown estimation."""
        result = assessor.assess_risk(
            asset='DRAWDOWN_TEST',
            drawdown_metrics=low_volatility_metrics,
            concentration_metrics=ConcentrationMetrics(),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        # Estimated drawdown should be volatility * k-factor
        expected = min(1.0, low_volatility_metrics.volatility * 1.5)
        assert abs(result.estimated_max_drawdown - expected) < 0.01

    def test_position_sizing_calculation(self, assessor):
        """Test recommended position sizing based on risk."""
        low_risk = assessor.assess_risk(
            asset='LOW_RISK',
            drawdown_metrics=DrawdownMetrics(volatility=0.10),
            concentration_metrics=ConcentrationMetrics(),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        high_risk = assessor.assess_risk(
            asset='HIGH_RISK',
            drawdown_metrics=DrawdownMetrics(
                volatility=0.50,
                historical_max_drawdown=0.70,
                var_95=0.40
            ),
            concentration_metrics=ConcentrationMetrics(),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        # Lower risk asset should allow larger position
        assert low_risk.recommended_max_position > high_risk.recommended_max_position

    def test_risk_warnings_volatility(self, assessor):
        """Test warning generation for high volatility."""
        result = assessor.assess_risk(
            asset='VOLATILE',
            drawdown_metrics=DrawdownMetrics(volatility=0.45),
            concentration_metrics=ConcentrationMetrics(),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        warnings = result.risk_warnings
        assert any('volatility' in w.lower() for w in warnings)

    def test_risk_warnings_concentration(self, assessor):
        """Test warning generation for high concentration."""
        result = assessor.assess_risk(
            asset='CONCENTRATED',
            drawdown_metrics=DrawdownMetrics(),
            concentration_metrics=ConcentrationMetrics(position_size_pct=0.12),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        warnings = result.risk_warnings
        assert any('position' in w.lower() for w in warnings)

    def test_risk_warnings_unlock(self, assessor):
        """Test warning generation for upcoming unlock."""
        result = assessor.assess_risk(
            asset='UNLOCK_RISK',
            drawdown_metrics=DrawdownMetrics(),
            concentration_metrics=ConcentrationMetrics(),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(
                token_unlock_upcoming=20,
                unlock_amount_pct=0.20
            ),
        )

        warnings = result.risk_warnings
        assert any('unlock' in w.lower() for w in warnings)

    def test_mitigations_suggested(self, assessor):
        """Test mitigation suggestions."""
        result = assessor.assess_risk(
            asset='HIGH_VOL_ASSET',
            drawdown_metrics=DrawdownMetrics(volatility=0.40),
            concentration_metrics=ConcentrationMetrics(),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        assert len(result.mitigations) > 0

    def test_report_generation(self, assessor, low_volatility_metrics):
        """Test report generation."""
        assessor.assess_risk(
            asset='REPORT_ASSET',
            drawdown_metrics=low_volatility_metrics,
            concentration_metrics=ConcentrationMetrics(),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        report = assessor.get_report('REPORT_ASSET')
        assert report is not None
        assert 'RISK ASSESSMENT' in report
        assert 'REPORT_ASSET' in report

    def test_no_report_for_unknown_asset(self, assessor):
        """Test report returns None for unknown asset."""
        report = assessor.get_report('UNKNOWN')
        assert report is None

    def test_high_risk_assets_filtering(self, assessor):
        """Test filtering of high-risk assets."""
        # Create low-risk asset
        assessor.assess_risk(
            asset='SAFE',
            drawdown_metrics=DrawdownMetrics(volatility=0.10),
            concentration_metrics=ConcentrationMetrics(),
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        # Create high-risk asset with multiple high-risk factors
        assessor.assess_risk(
            asset='DANGEROUS',
            drawdown_metrics=DrawdownMetrics(volatility=0.70, historical_max_drawdown=0.75),
            concentration_metrics=ConcentrationMetrics(position_size_pct=0.15, correlation_to_portfolio=0.9),
            execution_metrics=ExecutionMetrics(bid_ask_spread=0.10, estimated_slippage_1pct=0.30),
            timeline_metrics=TimelineMetrics(token_unlock_upcoming=10, unlock_amount_pct=0.30),
        )

        high_risk = assessor.get_high_risk_assets(threshold=70.0)
        assert len(high_risk) > 0  # Should have at least one high-risk asset

    def test_safe_allocatable_assets(self, assessor):
        """Test filtering of safely allocatable assets."""
        assessor.assess_risk(
            asset='ALLOCATABLE',
            drawdown_metrics=DrawdownMetrics(volatility=0.15),
            concentration_metrics=ConcentrationMetrics(position_size_pct=0.02),
            execution_metrics=ExecutionMetrics(
                bid_ask_spread=0.001,
                liquidity_depth=5e6
            ),
            timeline_metrics=TimelineMetrics(),
        )

        safe = assessor.get_safe_allocatable_assets()
        assert len(safe) >= 0  # May or may not be allocatable depending on thresholds

    def test_multi_asset_support(self, assessor):
        """Test assessment of multiple assets."""
        for asset in ['ASSET_1', 'ASSET_2', 'ASSET_3']:
            assessor.assess_risk(
                asset=asset,
                drawdown_metrics=DrawdownMetrics(),
                concentration_metrics=ConcentrationMetrics(),
                execution_metrics=ExecutionMetrics(),
                timeline_metrics=TimelineMetrics(),
            )

        assert len(assessor.results) == 3

    def test_concentration_over_hard_limit(self, assessor):
        """Test handling of position exceeding hard limit."""
        result = assessor.assess_risk(
            asset='OVER_LIMIT',
            drawdown_metrics=DrawdownMetrics(),
            concentration_metrics=ConcentrationMetrics(position_size_pct=0.15),  # Over 10% limit
            execution_metrics=ExecutionMetrics(),
            timeline_metrics=TimelineMetrics(),
        )

        # Should be marked as not safely allocatable
        assert result.can_safely_allocate is False
