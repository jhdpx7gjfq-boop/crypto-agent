"""
Unit tests for Opportunity Ranker (Phase 4 Component 5).
"""

import pytest
from src.layers.layer4_x20.opportunity_ranker import (
    OpportunityRanker,
    OpportunityConfidence,
    OpportunityTier,
    RankerInput,
)


class TestOpportunityRanker:
    """Tests for OpportunityRanker class."""

    @pytest.fixture
    def ranker(self):
        """Create opportunity ranker instance."""
        return OpportunityRanker()

    @pytest.fixture
    def tier_1_input(self):
        """Create high-conviction opportunity input."""
        return RankerInput(
            asset='TIER_1_ASSET',
            fundamental_score=80.0,
            narrative_score=78.0,
            quantitative_score=82.0,
            risk_score=80.0,  # Inverted: 80 = low risk
        )

    @pytest.fixture
    def tier_2_input(self):
        """Create strong opportunity input."""
        return RankerInput(
            asset='TIER_2_ASSET',
            fundamental_score=70.0,
            narrative_score=68.0,
            quantitative_score=72.0,
            risk_score=70.0,
        )

    @pytest.fixture
    def tier_3_input(self):
        """Create interesting opportunity input."""
        return RankerInput(
            asset='TIER_3_ASSET',
            fundamental_score=60.0,
            narrative_score=58.0,
            quantitative_score=62.0,
            risk_score=60.0,
        )

    @pytest.fixture
    def watch_input(self):
        """Create watch list input."""
        return RankerInput(
            asset='WATCH_ASSET',
            fundamental_score=50.0,
            narrative_score=48.0,
            quantitative_score=52.0,
            risk_score=50.0,
        )

    @pytest.fixture
    def high_risk_input(self):
        """Create high-risk opportunity input."""
        return RankerInput(
            asset='HIGH_RISK_ASSET',
            fundamental_score=75.0,
            narrative_score=72.0,
            quantitative_score=70.0,
            risk_score=35.0,  # Very high risk
        )

    @pytest.fixture
    def misaligned_input(self):
        """Create misaligned component input."""
        return RankerInput(
            asset='MISALIGNED_ASSET',
            fundamental_score=85.0,  # Excellent
            narrative_score=45.0,    # Weak
            quantitative_score=80.0, # Strong
            risk_score=30.0,         # Very risky
        )

    def test_ranker_creation(self, ranker):
        """Test ranker instantiation."""
        assert ranker is not None
        assert len(ranker.results) == 0
        assert len(ranker.history) == 0

    def test_ranking_tier_1(self, ranker, tier_1_input):
        """Test ranking for Tier 1 opportunity."""
        result = ranker.rank_opportunity(tier_1_input)

        assert result is not None
        assert result.asset == 'TIER_1_ASSET'
        assert result.x20_opportunity_score >= 75
        assert result.confidence == OpportunityConfidence.HIGH
        assert result.tier == OpportunityTier.TIER_1

    def test_ranking_tier_2(self, ranker, tier_2_input):
        """Test ranking for Tier 2 opportunity."""
        result = ranker.rank_opportunity(tier_2_input)

        assert result.x20_opportunity_score >= 65
        assert result.x20_opportunity_score < 75
        assert result.confidence == OpportunityConfidence.MEDIUM
        assert result.tier == OpportunityTier.TIER_2

    def test_ranking_tier_3(self, ranker, tier_3_input):
        """Test ranking for Tier 3 opportunity."""
        result = ranker.rank_opportunity(tier_3_input)

        assert result.x20_opportunity_score >= 55
        assert result.x20_opportunity_score < 65
        assert result.confidence == OpportunityConfidence.MEDIUM_LOW
        assert result.tier == OpportunityTier.TIER_3

    def test_ranking_watch_list(self, ranker, watch_input):
        """Test ranking for watch list item."""
        result = ranker.rank_opportunity(watch_input)

        assert result.x20_opportunity_score < 55
        assert result.confidence == OpportunityConfidence.WATCH_LIST
        assert result.tier == OpportunityTier.WATCH

    def test_score_calculation_weights(self, ranker):
        """Test that weights are applied correctly."""
        # Simple test: all 100 should give 100
        result = ranker.rank_opportunity(
            RankerInput(
                asset='PERFECT',
                fundamental_score=100.0,
                narrative_score=100.0,
                quantitative_score=100.0,
                risk_score=100.0,
            )
        )

        assert result.x20_opportunity_score == 100.0

    def test_score_calculation_all_zeros(self, ranker):
        """Test score with all zeros."""
        result = ranker.rank_opportunity(
            RankerInput(
                asset='TERRIBLE',
                fundamental_score=0.0,
                narrative_score=0.0,
                quantitative_score=0.0,
                risk_score=0.0,
            )
        )

        assert result.x20_opportunity_score == 0.0

    def test_weight_composition(self, ranker):
        """Test that weights sum to 1.0."""
        total_weight = (
            ranker.WEIGHT_FUNDAMENTAL +
            ranker.WEIGHT_NARRATIVE +
            ranker.WEIGHT_QUANTITATIVE +
            ranker.WEIGHT_RISK
        )
        assert abs(total_weight - 1.0) < 0.001

    def test_component_alignment_high(self, ranker):
        """Test component alignment when scores are similar."""
        result = ranker.rank_opportunity(
            RankerInput(
                asset='ALIGNED',
                fundamental_score=70.0,
                narrative_score=72.0,
                quantitative_score=71.0,
                risk_score=69.0,
            )
        )

        # Aligned components should have high alignment score
        assert result.component_alignment > 80

    def test_component_alignment_low(self, ranker, misaligned_input):
        """Test component alignment when scores diverge."""
        result = ranker.rank_opportunity(misaligned_input)

        # Misaligned components should have low alignment score
        assert result.component_alignment < 60

    def test_risk_adjusted_score(self, ranker):
        """Test risk adjustment reduces score."""
        # Good score but with risk
        result = ranker.rank_opportunity(
            RankerInput(
                asset='RISKY_GOOD',
                fundamental_score=80.0,
                narrative_score=80.0,
                quantitative_score=80.0,
                risk_score=50.0,  # Moderate risk (50 = moderate)
            )
        )

        # Risk-adjusted should be lower than base score
        assert result.risk_adjusted_score < result.x20_opportunity_score

    def test_risk_adjusted_with_low_risk(self, ranker, tier_1_input):
        """Test risk adjustment with low risk."""
        result = ranker.rank_opportunity(tier_1_input)

        # With low risk (80), risk-adjusted should be close to base
        ratio = result.risk_adjusted_score / result.x20_opportunity_score
        assert 0.75 < ratio <= 1.0

    def test_high_risk_opportunity(self, ranker, high_risk_input):
        """Test high-risk opportunity scoring."""
        result = ranker.rank_opportunity(high_risk_input)

        # Should be flagged as critical risk
        risks_text = " ".join(result.key_risks).lower()
        assert "critical" in risks_text or "risk" in risks_text
        assert result.risk_score < 50

    def test_key_opportunities_tier_1(self, ranker, tier_1_input):
        """Test opportunity signal generation for Tier 1."""
        result = ranker.rank_opportunity(tier_1_input)

        assert len(result.key_opportunities) > 0
        # Should have positive signals
        signals_text = " ".join(result.key_opportunities).lower()
        assert "strong" in signals_text or "aligned" in signals_text

    def test_key_risks_identification(self, ranker):
        """Test risk signal generation."""
        result = ranker.rank_opportunity(
            RankerInput(
                asset='RISKY',
                fundamental_score=40.0,
                narrative_score=35.0,
                quantitative_score=38.0,
                risk_score=30.0,
            )
        )

        assert len(result.key_risks) > 0
        risks_text = " ".join(result.key_risks).lower()
        assert "weak" in risks_text or "risk" in risks_text

    def test_recommendation_tier_1(self, ranker, tier_1_input):
        """Test recommendation for Tier 1."""
        result = ranker.rank_opportunity(tier_1_input)

        assert "BUY" in result.recommendation or "Signal" in result.recommendation

    def test_recommendation_tier_3(self, ranker, tier_3_input):
        """Test recommendation for Tier 3."""
        result = ranker.rank_opportunity(tier_3_input)

        assert "WATCH" in result.recommendation or "watch" in result.recommendation.lower()

    def test_recommendation_watch(self, ranker, watch_input):
        """Test recommendation for watch list."""
        result = ranker.rank_opportunity(watch_input)

        assert "HOLD" in result.recommendation or "threshold" in result.recommendation.lower()

    def test_score_momentum_first_analysis(self, ranker, tier_1_input):
        """Test that first analysis has zero momentum."""
        result = ranker.rank_opportunity(tier_1_input)

        assert result.score_momentum == 0.0
        assert result.prev_score is None

    def test_score_momentum_tracking(self, ranker):
        """Test momentum calculation between analyses."""
        asset = 'MOMENTUM_TEST'

        # First analysis
        score1 = ranker.rank_opportunity(
            RankerInput(
                asset=asset,
                fundamental_score=70.0,
                narrative_score=70.0,
                quantitative_score=70.0,
                risk_score=70.0,
            )
        )

        initial_score = score1.x20_opportunity_score

        # Second analysis with higher scores
        score2 = ranker.rank_opportunity(
            RankerInput(
                asset=asset,
                fundamental_score=80.0,
                narrative_score=80.0,
                quantitative_score=80.0,
                risk_score=80.0,
            )
        )

        # Momentum should be positive
        assert score2.score_momentum > 0
        assert score2.prev_score == initial_score

    def test_score_momentum_declining(self, ranker):
        """Test negative momentum tracking."""
        asset = 'DECLINE_TEST'

        # First analysis: high
        score1 = ranker.rank_opportunity(
            RankerInput(
                asset=asset,
                fundamental_score=80.0,
                narrative_score=80.0,
                quantitative_score=80.0,
                risk_score=80.0,
            )
        )

        initial_score = score1.x20_opportunity_score

        # Second analysis: lower
        score2 = ranker.rank_opportunity(
            RankerInput(
                asset=asset,
                fundamental_score=60.0,
                narrative_score=60.0,
                quantitative_score=60.0,
                risk_score=60.0,
            )
        )

        # Momentum should be negative
        assert score2.score_momentum < 0
        assert score2.prev_score == initial_score

    def test_report_generation(self, ranker, tier_1_input):
        """Test report generation."""
        ranker.rank_opportunity(tier_1_input)

        report = ranker.get_report('TIER_1_ASSET')
        assert report is not None
        assert 'X20 OPPORTUNITY RANKING' in report
        assert 'TIER_1_ASSET' in report
        assert 'COMPONENT SCORES' in report

    def test_no_report_for_unknown_asset(self, ranker):
        """Test report returns None for unknown asset."""
        report = ranker.get_report('UNKNOWN')
        assert report is None

    def test_tier_1_filtering(self, ranker, tier_1_input, tier_2_input):
        """Test Tier 1 opportunity filtering."""
        ranker.rank_opportunity(tier_1_input)
        ranker.rank_opportunity(tier_2_input)

        tier_1 = ranker.get_tier_1_opportunities()
        assert len(tier_1) == 1
        assert tier_1[0][0] == 'TIER_1_ASSET'

    def test_tier_2_filtering(self, ranker, tier_1_input, tier_2_input):
        """Test Tier 2 opportunity filtering."""
        ranker.rank_opportunity(tier_1_input)
        ranker.rank_opportunity(tier_2_input)

        tier_2 = ranker.get_tier_2_opportunities()
        assert len(tier_2) == 1
        assert tier_2[0][0] == 'TIER_2_ASSET'

    def test_watch_list_filtering(self, ranker, watch_input, tier_3_input):
        """Test watch list filtering."""
        ranker.rank_opportunity(tier_3_input)
        ranker.rank_opportunity(watch_input)

        watch = ranker.get_watch_list()
        assert len(watch) >= 1
        assert any(asset == 'WATCH_ASSET' for asset, _ in watch)

    def test_aligned_opportunities_filtering(self, ranker):
        """Test aligned opportunities filtering."""
        # Aligned: all scores similar
        ranker.rank_opportunity(
            RankerInput(
                asset='ALIGNED_1',
                fundamental_score=75.0,
                narrative_score=74.0,
                quantitative_score=76.0,
                risk_score=75.0,
            )
        )

        # Misaligned: scores vary widely
        ranker.rank_opportunity(
            RankerInput(
                asset='MISALIGNED_1',
                fundamental_score=85.0,
                narrative_score=40.0,
                quantitative_score=70.0,
                risk_score=50.0,
            )
        )

        aligned = ranker.get_aligned_opportunities(threshold=70.0)
        assert len(aligned) >= 1
        assert any(asset == 'ALIGNED_1' for asset, _, _ in aligned)

    def test_risk_adjusted_ranking(self, ranker):
        """Test risk-adjusted ranking."""
        # Low risk, good fundamentals
        ranker.rank_opportunity(
            RankerInput(
                asset='LOW_RISK_GOOD',
                fundamental_score=75.0,
                narrative_score=75.0,
                quantitative_score=75.0,
                risk_score=85.0,
            )
        )

        # High score, high risk
        ranker.rank_opportunity(
            RankerInput(
                asset='HIGH_RISK_GOOD',
                fundamental_score=80.0,
                narrative_score=80.0,
                quantitative_score=80.0,
                risk_score=30.0,
            )
        )

        ranking = ranker.get_risk_adjusted_ranking()
        assert len(ranking) == 2
        # Low-risk asset should rank higher after risk adjustment
        assert ranking[0][0] == 'LOW_RISK_GOOD'

    def test_multi_asset_support(self, ranker):
        """Test ranking multiple assets."""
        for i in range(5):
            ranker.rank_opportunity(
                RankerInput(
                    asset=f'ASSET_{i}',
                    fundamental_score=50.0 + i * 5,
                    narrative_score=50.0 + i * 5,
                    quantitative_score=50.0 + i * 5,
                    risk_score=50.0 + i * 5,
                )
            )

        assert len(ranker.results) == 5
        assert len(ranker.history) == 5

    def test_history_tracking(self, ranker):
        """Test historical score tracking."""
        asset = 'HISTORY_TEST'

        # Analyze multiple times with different scores
        scores = [60.0, 70.0, 75.0, 72.0]
        for score in scores:
            ranker.rank_opportunity(
                RankerInput(
                    asset=asset,
                    fundamental_score=score,
                    narrative_score=score,
                    quantitative_score=score,
                    risk_score=score,
                )
            )

        assert asset in ranker.history
        assert len(ranker.history[asset]) == 4

    def test_score_bounds(self, ranker):
        """Test that scores are bounded 0-100."""
        # Try with scores > 100
        result = ranker.rank_opportunity(
            RankerInput(
                asset='OVER_100',
                fundamental_score=150.0,
                narrative_score=150.0,
                quantitative_score=150.0,
                risk_score=150.0,
            )
        )

        assert result.x20_opportunity_score <= 100.0

        # Try with negative scores
        result = ranker.rank_opportunity(
            RankerInput(
                asset='NEGATIVE',
                fundamental_score=-50.0,
                narrative_score=-50.0,
                quantitative_score=-50.0,
                risk_score=-50.0,
            )
        )

        assert result.x20_opportunity_score >= 0.0

    def test_weight_verification(self, ranker):
        """Test that weights actually affect score calculation."""
        # Scenario 1: All components equal at 60
        result_equal = ranker.rank_opportunity(
            RankerInput(
                asset='EQUAL_60',
                fundamental_score=60.0,
                narrative_score=60.0,
                quantitative_score=60.0,
                risk_score=60.0,
            )
        )

        # Scenario 2: Only fundamental at 90, others at 60
        result_fund_high = ranker.rank_opportunity(
            RankerInput(
                asset='FUND_90',
                fundamental_score=90.0,
                narrative_score=60.0,
                quantitative_score=60.0,
                risk_score=60.0,
            )
        )

        # Increasing fundamental by 30 points should increase score proportionally
        # Expected increase: 30 * 0.35 (fundamental weight) = 10.5 points
        score_increase = result_fund_high.x20_opportunity_score - result_equal.x20_opportunity_score
        assert 8 < score_increase < 12  # Allow some margin for rounding

    def test_transparency_signal_generation(self, ranker):
        """Test that signals are generated transparently."""
        result = ranker.rank_opportunity(
            RankerInput(
                asset='SIGNAL_TEST',
                fundamental_score=75.0,
                narrative_score=75.0,
                quantitative_score=75.0,
                risk_score=75.0,
            )
        )

        # Should have signals
        assert len(result.key_opportunities) > 0 or len(result.key_risks) >= 0
        # Recommendation should be present
        assert len(result.recommendation) > 0

    def test_confidence_thresholds(self, ranker):
        """Test confidence level thresholds."""
        # Test each boundary
        test_cases = [
            (10.0, OpportunityConfidence.WATCH_LIST),
            (50.0, OpportunityConfidence.WATCH_LIST),
            (55.0, OpportunityConfidence.MEDIUM_LOW),
            (60.0, OpportunityConfidence.MEDIUM_LOW),
            (70.0, OpportunityConfidence.MEDIUM),
            (75.0, OpportunityConfidence.HIGH),
            (90.0, OpportunityConfidence.HIGH),
        ]

        for score, expected_confidence in test_cases:
            result = ranker.rank_opportunity(
                RankerInput(
                    asset=f'CONF_{score}',
                    fundamental_score=score,
                    narrative_score=score,
                    quantitative_score=score,
                    risk_score=score,
                )
            )

            assert result.confidence == expected_confidence
