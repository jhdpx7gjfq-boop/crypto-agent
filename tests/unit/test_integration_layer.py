"""
Unit tests for Integration Layer (Phase 4 Component 6).
"""

import pytest
from src.layers.layer4_x20.integration_layer import (
    IntegrationLayer,
    IntegrationSignal,
    BCESignal,
    X20Score,
    FOPOMetrics,
)


class TestIntegrationLayer:
    """Tests for IntegrationLayer class."""

    @pytest.fixture
    def integration_layer(self):
        """Create integration layer instance."""
        return IntegrationLayer()

    @pytest.fixture
    def valid_bce_signal(self):
        """Create valid BCE signal (≥5/6)."""
        return BCESignal(
            asset='TEST_ASSET',
            bce_score=5.5/6,  # Above 5/6 threshold
            wyckoff_structure=0.95,
            volume_analysis=0.90,
            selling_exhaustion=0.85,
            smart_money_acc=0.92,
            market_structure=0.88,
            momentum_confirmation=0.90,
            valid=True,
        )

    @pytest.fixture
    def invalid_bce_signal(self):
        """Create invalid BCE signal (<5/6)."""
        return BCESignal(
            asset='INVALID_ASSET',
            bce_score=4.0/6,  # Below 5/6 threshold
            wyckoff_structure=0.60,
            volume_analysis=0.50,
            selling_exhaustion=0.40,
            smart_money_acc=0.50,
            market_structure=0.60,
            momentum_confirmation=0.50,
            valid=False,
        )

    @pytest.fixture
    def strong_x20_score(self):
        """Create strong X20 opportunity score."""
        return X20Score(
            asset='TEST_ASSET',
            x20_opportunity_score=80.0,
            fundamental_score=82.0,
            narrative_score=78.0,
            quantitative_score=80.0,
            risk_score=85.0,  # Low risk
            component_alignment=90.0,
            risk_adjusted_score=75.0,
            tier='Tier 1 (★★★★★)',
            confidence='High',
        )

    @pytest.fixture
    def weak_x20_score(self):
        """Create weak X20 opportunity score."""
        return X20Score(
            asset='WEAK_ASSET',
            x20_opportunity_score=40.0,
            fundamental_score=38.0,
            narrative_score=42.0,
            quantitative_score=40.0,
            risk_score=35.0,  # High risk
            component_alignment=40.0,
            risk_adjusted_score=20.0,
            tier='Watch List',
            confidence='Watch',
        )

    @pytest.fixture
    def medium_x20_score(self):
        """Create medium X20 opportunity score."""
        return X20Score(
            asset='MEDIUM_ASSET',
            x20_opportunity_score=68.0,
            fundamental_score=70.0,
            narrative_score=65.0,
            quantitative_score=70.0,
            risk_score=70.0,
            component_alignment=75.0,
            risk_adjusted_score=62.0,
            tier='Tier 2 (★★★★)',
            confidence='Medium',
        )

    @pytest.fixture
    def clear_fomo_metrics(self):
        """Create FOMO metrics with no triggers."""
        return FOPOMetrics(
            price_discovery_phase=False,
            euphoria_level=30.0,
            extension_factor=0.8,
            volume_surge=50.0,
            trending_intensity=20.0,
        )

    @pytest.fixture
    def triggered_fomo_metrics(self):
        """Create FOMO metrics with triggers."""
        return FOPOMetrics(
            price_discovery_phase=True,
            euphoria_level=85.0,
            extension_factor=2.5,
            volume_surge=200.0,
            trending_intensity=90.0,
        )

    def test_integration_layer_creation(self, integration_layer):
        """Test integration layer instantiation."""
        assert integration_layer is not None
        assert len(integration_layer.results) == 0
        assert len(integration_layer.history) == 0

    def test_strong_buy_signal(
        self, integration_layer, valid_bce_signal, strong_x20_score,
        clear_fomo_metrics
    ):
        """Test STRONG_BUY signal generation."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score, clear_fomo_metrics
        )

        assert result.integration_signal == IntegrationSignal.STRONG_BUY
        assert result.bce_valid is True
        assert result.x20_sufficient is True
        assert result.components_aligned is True
        assert result.fomo_clear is True

    def test_buy_signal(
        self, integration_layer, valid_bce_signal, medium_x20_score,
        clear_fomo_metrics
    ):
        """Test BUY signal generation."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, medium_x20_score, clear_fomo_metrics
        )

        assert result.integration_signal == IntegrationSignal.BUY
        assert result.bce_valid is True
        assert result.x20_sufficient is True

    def test_research_signal(
        self, integration_layer, valid_bce_signal
    ):
        """Test RESEARCH signal for mid-range X20 score."""
        x20_research = X20Score(
            asset='RESEARCH_ASSET',
            x20_opportunity_score=58.0,
            fundamental_score=60.0,
            narrative_score=55.0,
            quantitative_score=60.0,
            risk_score=65.0,
            component_alignment=70.0,
            risk_adjusted_score=55.0,
            tier='Tier 3 (★★★)',
            confidence='Medium-Low',
        )

        result = integration_layer.integrate_signals(
            valid_bce_signal, x20_research
        )

        assert result.integration_signal == IntegrationSignal.RESEARCH

    def test_watch_signal_invalid_bce(
        self, integration_layer, invalid_bce_signal, strong_x20_score
    ):
        """Test WATCH signal when BCE is invalid."""
        result = integration_layer.integrate_signals(
            invalid_bce_signal, strong_x20_score
        )

        assert result.bce_valid is False
        assert result.integration_signal in [
            IntegrationSignal.WATCH, IntegrationSignal.HOLD
        ]

    def test_watch_signal_weak_x20(
        self, integration_layer, valid_bce_signal, weak_x20_score
    ):
        """Test WATCH signal when X20 is weak."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, weak_x20_score
        )

        assert result.x20_sufficient is False
        assert result.integration_signal == IntegrationSignal.WATCH

    def test_fomo_circuit_breaker_not_triggered(
        self, integration_layer, valid_bce_signal, strong_x20_score,
        clear_fomo_metrics
    ):
        """Test FOMO circuit breaker with no triggers."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score, clear_fomo_metrics
        )

        assert result.fomo_clear is True
        assert result.integration_signal == IntegrationSignal.STRONG_BUY

    def test_fomo_circuit_breaker_triggered(
        self, integration_layer, valid_bce_signal, strong_x20_score,
        triggered_fomo_metrics
    ):
        """Test FOMO circuit breaker triggers."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score, triggered_fomo_metrics
        )

        assert result.fomo_clear is False
        # Signal should be downgraded due to FOMO
        assert result.confidence_level < 90

    def test_component_alignment_scoring(
        self, integration_layer, valid_bce_signal
    ):
        """Test component alignment affects classification."""
        aligned_x20 = X20Score(
            asset='ALIGNED',
            x20_opportunity_score=75.0,
            fundamental_score=75.0,
            narrative_score=74.0,
            quantitative_score=76.0,
            risk_score=75.0,
            component_alignment=95.0,  # Well aligned
            risk_adjusted_score=70.0,
            tier='Tier 1 (★★★★★)',
            confidence='High',
        )

        misaligned_x20 = X20Score(
            asset='MISALIGNED',
            x20_opportunity_score=75.0,
            fundamental_score=85.0,
            narrative_score=40.0,
            quantitative_score=85.0,
            risk_score=70.0,
            component_alignment=40.0,  # Poorly aligned
            risk_adjusted_score=60.0,
            tier='Tier 2 (★★★★)',
            confidence='Medium',
        )

        result_aligned = integration_layer.integrate_signals(
            valid_bce_signal, aligned_x20
        )
        result_misaligned = integration_layer.integrate_signals(
            valid_bce_signal, misaligned_x20
        )

        # Aligned should have higher confidence
        assert result_aligned.confidence_level > result_misaligned.confidence_level

    def test_confidence_calculation_high(
        self, integration_layer, valid_bce_signal, strong_x20_score,
        clear_fomo_metrics
    ):
        """Test confidence calculation for strong signal."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score, clear_fomo_metrics
        )

        # Should have high confidence
        assert result.confidence_level > 80

    def test_confidence_calculation_low(
        self, integration_layer, invalid_bce_signal, weak_x20_score
    ):
        """Test confidence calculation for weak signal."""
        result = integration_layer.integrate_signals(
            invalid_bce_signal, weak_x20_score
        )

        # Should have low confidence (much lower than high confidence test)
        assert result.confidence_level < 60

    def test_risk_rating_classification(self, integration_layer, valid_bce_signal):
        """Test risk rating classification."""
        low_risk_x20 = X20Score(
            asset='LOW_RISK',
            x20_opportunity_score=70.0,
            fundamental_score=70.0,
            narrative_score=70.0,
            quantitative_score=70.0,
            risk_score=85.0,  # Low risk
            component_alignment=80.0,
            risk_adjusted_score=65.0,
            tier='Tier 2 (★★★★)',
            confidence='Medium',
        )

        high_risk_x20 = X20Score(
            asset='HIGH_RISK',
            x20_opportunity_score=70.0,
            fundamental_score=70.0,
            narrative_score=70.0,
            quantitative_score=70.0,
            risk_score=30.0,  # High risk
            component_alignment=80.0,
            risk_adjusted_score=20.0,
            tier='Tier 2 (★★★★)',
            confidence='Medium',
        )

        result_low = integration_layer.integrate_signals(
            valid_bce_signal, low_risk_x20
        )
        result_high = integration_layer.integrate_signals(
            valid_bce_signal, high_risk_x20
        )

        assert result_low.risk_rating == 'Low'
        assert result_high.risk_rating == 'Critical' or result_high.risk_rating == 'High'

    def test_validation_summary_generation(
        self, integration_layer, valid_bce_signal, strong_x20_score
    ):
        """Test validation summary generation."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score
        )

        assert len(result.validation_summary) > 0
        summary_text = ' '.join(result.validation_summary).lower()
        assert 'bce' in summary_text or '5/6' in summary_text

    def test_warning_signals_generation(
        self, integration_layer, valid_bce_signal, weak_x20_score
    ):
        """Test warning signal identification."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, weak_x20_score
        )

        # Weak X20 should generate warnings
        assert len(result.warning_signals) > 0
        warnings_text = ' '.join(result.warning_signals).lower()
        assert 'risk' in warnings_text or 'weak' in warnings_text

    def test_entry_conditions_generation(
        self, integration_layer, valid_bce_signal, strong_x20_score,
        clear_fomo_metrics
    ):
        """Test entry condition generation."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score, clear_fomo_metrics
        )

        assert len(result.entry_conditions) > 0
        # STRONG_BUY should allow full entry
        conditions_text = ' '.join(result.entry_conditions).lower()
        assert 'entry' in conditions_text or 'position' in conditions_text

    def test_action_recommendation_generation(
        self, integration_layer, valid_bce_signal, strong_x20_score,
        clear_fomo_metrics
    ):
        """Test action recommendation generation."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score, clear_fomo_metrics
        )

        assert len(result.action_recommendation) > 0
        assert 'BUY' in result.action_recommendation or 'buy' in result.action_recommendation.lower()

    def test_decision_momentum_first_analysis(
        self, integration_layer, valid_bce_signal, strong_x20_score
    ):
        """Test that first analysis has zero momentum."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score
        )

        assert result.decision_momentum == 0.0
        assert result.prev_integration_score is None

    def test_decision_momentum_tracking(self, integration_layer, valid_bce_signal):
        """Test momentum tracking between analyses."""
        asset = 'MOMENTUM_TEST'

        # First analysis
        strong_x20 = X20Score(
            asset=asset,
            x20_opportunity_score=75.0,
            fundamental_score=75.0,
            narrative_score=75.0,
            quantitative_score=75.0,
            risk_score=75.0,
            component_alignment=80.0,
            risk_adjusted_score=70.0,
            tier='Tier 1 (★★★★★)',
            confidence='High',
        )

        result1 = integration_layer.integrate_signals(
            valid_bce_signal, strong_x20
        )
        initial_confidence = result1.confidence_level

        # Second analysis: weaker
        weak_x20 = X20Score(
            asset=asset,
            x20_opportunity_score=60.0,
            fundamental_score=60.0,
            narrative_score=60.0,
            quantitative_score=60.0,
            risk_score=60.0,
            component_alignment=70.0,
            risk_adjusted_score=55.0,
            tier='Tier 2 (★★★★)',
            confidence='Medium',
        )

        result2 = integration_layer.integrate_signals(
            valid_bce_signal, weak_x20
        )

        # Momentum should be negative
        assert result2.decision_momentum < 0
        assert result2.prev_integration_score == initial_confidence

    def test_report_generation(
        self, integration_layer, valid_bce_signal, strong_x20_score,
        clear_fomo_metrics
    ):
        """Test report generation."""
        integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score, clear_fomo_metrics
        )

        report = integration_layer.get_report(strong_x20_score.asset)
        assert report is not None
        assert 'INTEGRATION DECISION' in report
        assert strong_x20_score.asset in report
        assert 'BCE' in report
        assert 'X20' in report

    def test_no_report_for_unknown_asset(self, integration_layer):
        """Test report returns None for unknown asset."""
        report = integration_layer.get_report('UNKNOWN')
        assert report is None

    def test_strong_buy_filtering(
        self, integration_layer, valid_bce_signal, strong_x20_score,
        clear_fomo_metrics
    ):
        """Test STRONG_BUY opportunities filtering."""
        integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score, clear_fomo_metrics
        )

        strong_buys = integration_layer.get_strong_buy_opportunities()
        assert len(strong_buys) == 1
        assert strong_buys[0][0] == strong_x20_score.asset

    def test_buy_filtering(
        self, integration_layer, valid_bce_signal, medium_x20_score,
        clear_fomo_metrics
    ):
        """Test BUY opportunities filtering."""
        integration_layer.integrate_signals(
            valid_bce_signal, medium_x20_score, clear_fomo_metrics
        )

        buys = integration_layer.get_buy_opportunities()
        assert len(buys) >= 1
        assert any(asset == medium_x20_score.asset for asset, _ in buys)

    def test_research_candidates_filtering(
        self, integration_layer, valid_bce_signal
    ):
        """Test RESEARCH candidates filtering."""
        research_x20 = X20Score(
            asset='RESEARCH_CANDIDATE',
            x20_opportunity_score=58.0,
            fundamental_score=60.0,
            narrative_score=55.0,
            quantitative_score=60.0,
            risk_score=65.0,
            component_alignment=70.0,
            risk_adjusted_score=55.0,
            tier='Tier 3 (★★★)',
            confidence='Medium-Low',
        )

        integration_layer.integrate_signals(
            valid_bce_signal, research_x20
        )

        research = integration_layer.get_research_candidates()
        assert len(research) >= 1
        assert any(asset == 'RESEARCH_CANDIDATE' for asset, _ in research)

    def test_watch_list_filtering(
        self, integration_layer, valid_bce_signal, weak_x20_score
    ):
        """Test WATCH list filtering."""
        integration_layer.integrate_signals(
            valid_bce_signal, weak_x20_score
        )

        watch = integration_layer.get_watch_list()
        assert len(watch) >= 1

    def test_multi_asset_support(
        self, integration_layer, valid_bce_signal
    ):
        """Test integration of multiple assets."""
        for i in range(3):
            x20_score = X20Score(
                asset=f'ASSET_{i}',
                x20_opportunity_score=60.0 + i * 5,
                fundamental_score=60.0 + i * 5,
                narrative_score=60.0 + i * 5,
                quantitative_score=60.0 + i * 5,
                risk_score=70.0,
                component_alignment=80.0,
                risk_adjusted_score=60.0,
                tier='Tier 2 (★★★★)',
                confidence='Medium',
            )

            integration_layer.integrate_signals(
                valid_bce_signal, x20_score
            )

        assert len(integration_layer.results) == 3

    def test_history_tracking(
        self, integration_layer, valid_bce_signal
    ):
        """Test historical confidence tracking."""
        asset = 'HISTORY_TEST'

        # Multiple analyses
        for score_val in [50.0, 60.0, 70.0]:
            x20_score = X20Score(
                asset=asset,
                x20_opportunity_score=score_val,
                fundamental_score=score_val,
                narrative_score=score_val,
                quantitative_score=score_val,
                risk_score=70.0,
                component_alignment=80.0,
                risk_adjusted_score=score_val,
                tier='Tier 2 (★★★★)',
                confidence='Medium',
            )

            integration_layer.integrate_signals(
                valid_bce_signal, x20_score
            )

        assert asset in integration_layer.history
        assert len(integration_layer.history[asset]) == 3

    def test_bce_requirement_enforced(
        self, integration_layer, invalid_bce_signal, strong_x20_score
    ):
        """Test that BCE ≥5/6 requirement is enforced."""
        result = integration_layer.integrate_signals(
            invalid_bce_signal, strong_x20_score
        )

        # Even with strong X20, signal should not be BUY if BCE invalid
        assert result.bce_valid is False
        assert result.integration_signal != IntegrationSignal.STRONG_BUY
        assert result.integration_signal != IntegrationSignal.BUY

    def test_x20_minimum_enforced(
        self, integration_layer, valid_bce_signal, weak_x20_score
    ):
        """Test that X20 ≥55 minimum is enforced."""
        result = integration_layer.integrate_signals(
            valid_bce_signal, weak_x20_score
        )

        # Even with valid BCE, signal should not exceed WATCH if X20 weak
        assert result.x20_sufficient is False
        assert result.integration_signal == IntegrationSignal.WATCH

    def test_igwt_compliance_summary(
        self, integration_layer, valid_bce_signal, strong_x20_score
    ):
        """Test IGWT compliance is documented in report."""
        integration_layer.integrate_signals(
            valid_bce_signal, strong_x20_score
        )

        report = integration_layer.get_report(strong_x20_score.asset)
        assert 'IGWT' in report
        assert 'BCE' in report or '5/6' in report
        assert 'execution' in report.lower()
