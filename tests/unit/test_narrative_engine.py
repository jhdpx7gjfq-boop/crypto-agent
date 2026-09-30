"""
Unit tests for Narrative Detection Engine (Phase 4 Component 2).
"""

import pytest
from src.layers.layer4_x20.narrative_engine import (
    NarrativeEngine,
    NarrativeCategory,
    AdoptionMetrics,
    SocialSignals,
    NarrativeScore,
)


class TestNarrativeEngine:
    """Tests for NarrativeEngine class."""

    @pytest.fixture
    def engine(self):
        """Create narrative engine instance."""
        return NarrativeEngine()

    @pytest.fixture
    def strong_adoption(self):
        """Create strong adoption metrics."""
        return AdoptionMetrics(
            users=2000000,
            growth_rate=0.50,  # 50% WoW
            tvl=500000000,  # $500M
            transaction_volume=50000000,  # $50M daily
            developer_activity=200,
            active_addresses=150000,
        )

    @pytest.fixture
    def weak_adoption(self):
        """Create weak adoption metrics."""
        return AdoptionMetrics(
            users=50000,
            growth_rate=-0.10,  # Negative growth
            tvl=5000000,  # $5M
            transaction_volume=500000,  # $500K daily
            developer_activity=10,
            active_addresses=5000,
        )

    @pytest.fixture
    def strong_social(self):
        """Create strong social signals."""
        return SocialSignals(
            mention_volume=15000,
            sentiment_score=0.75,  # Positive
            twitter_volume=5000,
            reddit_activity=2000,
            discord_growth=0.40,  # 40% growth
            social_trend=0.8,  # Strong positive trend
        )

    @pytest.fixture
    def weak_social(self):
        """Create weak social signals."""
        return SocialSignals(
            mention_volume=500,
            sentiment_score=0.45,  # Negative
            twitter_volume=100,
            reddit_activity=50,
            discord_growth=-0.10,  # Negative growth
            social_trend=-0.5,  # Declining
        )

    @pytest.fixture
    def hot_market(self):
        """Create hot market metrics."""
        return {
            'market_cap': 50e9,  # $50B
            'volume_24h': 5e9,  # $5B
            'price_change_24h': 0.25,  # +25%
            'volume_to_mcap_ratio': 0.10,  # 10% daily volume
            'inflow_indicator': 0.75,  # Strong inflow
        }

    @pytest.fixture
    def cold_market(self):
        """Create cold market metrics."""
        return {
            'market_cap': 100e6,  # $100M
            'volume_24h': 10e6,  # $10M
            'price_change_24h': -0.15,  # -15%
            'volume_to_mcap_ratio': 0.01,  # 1% daily volume
            'inflow_indicator': -0.4,  # Outflow
        }

    def test_engine_creation(self, engine):
        """Test engine instantiation."""
        assert engine is not None
        assert len(engine.results) == 0
        assert len(engine.history) == 0

    def test_sector_strength_scoring_hot(self, engine, hot_market):
        """Test sector strength scoring for hot market."""
        score = engine._score_sector_strength(
            NarrativeCategory.AI, hot_market
        )

        assert 0 <= score <= 100
        assert score > 80  # Hot market should score high

    def test_sector_strength_scoring_cold(self, engine, cold_market):
        """Test sector strength scoring for cold market."""
        score = engine._score_sector_strength(
            NarrativeCategory.OTHER, cold_market
        )

        assert 0 <= score <= 100
        assert score < 40  # Cold market should score low

    def test_adoption_trend_scoring_strong(self, engine, strong_adoption):
        """Test adoption trend scoring with strong metrics."""
        score = engine._score_adoption_trend(strong_adoption)

        assert 0 <= score <= 100
        assert score > 75  # Strong adoption should score high

    def test_adoption_trend_scoring_weak(self, engine, weak_adoption):
        """Test adoption trend scoring with weak metrics."""
        score = engine._score_adoption_trend(weak_adoption)

        assert 0 <= score <= 100
        assert score < 50  # Weak adoption should score low

    def test_adoption_trend_no_users(self, engine):
        """Test adoption scoring with no users."""
        metrics = AdoptionMetrics(users=0, growth_rate=0.0)
        score = engine._score_adoption_trend(metrics)

        assert score >= 0  # Should not be negative
        assert score < 60

    def test_social_momentum_scoring_strong(self, engine, strong_social):
        """Test social momentum scoring with strong signals."""
        score = engine._score_social_momentum(strong_social)

        assert 0 <= score <= 100
        assert score > 70  # Strong social should score high

    def test_social_momentum_scoring_weak(self, engine, weak_social):
        """Test social momentum scoring with weak signals."""
        score = engine._score_social_momentum(weak_social)

        assert 0 <= score <= 100
        assert score < 50  # Weak social should score low

    def test_capital_rotation_scoring_inflow(self, engine, hot_market):
        """Test capital rotation with strong inflow."""
        score = engine._score_capital_rotation(hot_market)

        assert 0 <= score <= 100
        assert score > 70  # Strong inflow should score high

    def test_capital_rotation_scoring_outflow(self, engine, cold_market):
        """Test capital rotation with outflow."""
        score = engine._score_capital_rotation(cold_market)

        assert 0 <= score <= 100
        assert score < 50  # Outflow should score low

    def test_trend_classification_rising(self, engine):
        """Test trend classification for rising."""
        trend = engine._classify_trend(0.20)  # 20% growth
        assert trend == "rising"

    def test_trend_classification_stable(self, engine):
        """Test trend classification for stable."""
        trend = engine._classify_trend(0.05)  # 5% growth
        assert trend == "stable"

    def test_trend_classification_declining(self, engine):
        """Test trend classification for declining."""
        trend = engine._classify_trend(-0.10)  # -10% growth
        assert trend == "declining"

    def test_full_analysis_ai_narrative(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test complete narrative analysis for AI sector."""
        result = engine.analyze_narrative(
            asset='AI_TOKEN',
            category=NarrativeCategory.AI,
            adoption_metrics=strong_adoption,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        assert result is not None
        assert result.asset == 'AI_TOKEN'
        assert result.category == NarrativeCategory.AI
        assert 0 <= result.overall_narrative_score <= 100
        assert result.overall_narrative_score > 70  # Should be hot
        assert result.is_accelerating is True
        assert result.trend_direction == "rising"
        assert len(result.key_signals) > 0

    def test_full_analysis_rwa_narrative(
        self, engine, weak_adoption, weak_social, cold_market
    ):
        """Test complete narrative analysis for weak RWA."""
        result = engine.analyze_narrative(
            asset='RWA_TOKEN',
            category=NarrativeCategory.RWA,
            adoption_metrics=weak_adoption,
            social_signals=weak_social,
            market_metrics=cold_market,
        )

        assert result.overall_narrative_score < 60
        assert result.is_accelerating is False
        assert result.trend_direction == "declining"

    def test_hot_narrative_detection(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test hot narrative detection."""
        engine.analyze_narrative(
            asset='HOT_AI',
            category=NarrativeCategory.AI,
            adoption_metrics=strong_adoption,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        hot = engine.get_hot_narratives(threshold=70)
        assert len(hot) > 0
        assert any(asset == 'HOT_AI' for asset, _ in hot)

    def test_narrative_by_category(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test filtering narratives by category."""
        engine.analyze_narrative(
            asset='AI_1',
            category=NarrativeCategory.AI,
            adoption_metrics=strong_adoption,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        engine.analyze_narrative(
            asset='DEFI_1',
            category=NarrativeCategory.DEFI,
            adoption_metrics=strong_adoption,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        ai_assets = engine.get_narrative_by_category(NarrativeCategory.AI)
        assert len(ai_assets) == 1
        assert ai_assets[0][0] == 'AI_1'

    def test_report_generation(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test report generation."""
        engine.analyze_narrative(
            asset='REPORT_AI',
            category=NarrativeCategory.AI,
            adoption_metrics=strong_adoption,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        report = engine.get_report('REPORT_AI')
        assert report is not None
        assert 'NARRATIVE ANALYSIS' in report
        assert 'REPORT_AI' in report
        assert 'AI' in report

    def test_no_report_for_unknown_asset(self, engine):
        """Test that report returns None for unknown asset."""
        report = engine.get_report('UNKNOWN_ASSET')
        assert report is None

    def test_narrative_momentum_tracking(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test momentum calculation between analyses."""
        # First analysis
        score1 = engine.analyze_narrative(
            asset='MOMENTUM_TEST',
            category=NarrativeCategory.DEFI,
            adoption_metrics=strong_adoption,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        initial_score = score1.overall_narrative_score

        # Second analysis with significantly weaker metrics
        weak_adoption2 = AdoptionMetrics(
            users=100000,  # Much lower
            growth_rate=-0.10,  # Negative growth
            tvl=10000000,  # Much lower TVL
            transaction_volume=500000,  # Much lower volume
            developer_activity=5,  # Much lower activity
        )

        weak_social2 = SocialSignals(
            mention_volume=500,  # Much lower
            sentiment_score=0.3,  # Negative
            twitter_volume=50,
            reddit_activity=10,
            discord_growth=-0.20,
            social_trend=-0.6,
        )

        score2 = engine.analyze_narrative(
            asset='MOMENTUM_TEST',
            category=NarrativeCategory.DEFI,
            adoption_metrics=weak_adoption2,
            social_signals=weak_social2,
            market_metrics=hot_market,
        )

        assert score2.prev_score == initial_score
        assert score2.score_momentum < 0  # Score should decrease significantly

    def test_multi_asset_support(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test analysis of multiple assets."""
        for asset in ['ASSET_1', 'ASSET_2', 'ASSET_3']:
            engine.analyze_narrative(
                asset=asset,
                category=NarrativeCategory.L2,
                adoption_metrics=strong_adoption,
                social_signals=strong_social,
                market_metrics=hot_market,
            )

        assert len(engine.results) == 3
        assert 'ASSET_1' in engine.results
        assert 'ASSET_2' in engine.results
        assert 'ASSET_3' in engine.results

    def test_history_tracking(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test historical score tracking."""
        asset = 'HISTORY_TEST'

        # Analyze multiple times
        for i in range(3):
            engine.analyze_narrative(
                asset=asset,
                category=NarrativeCategory.AI,
                adoption_metrics=strong_adoption,
                social_signals=strong_social,
                market_metrics=hot_market,
            )

        assert asset in engine.history
        assert len(engine.history[asset]) == 3

    def test_is_hot_narrative(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test is_hot_narrative method."""
        score = engine.analyze_narrative(
            asset='HOT_CHECK',
            category=NarrativeCategory.AI,
            adoption_metrics=strong_adoption,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        assert score.is_hot_narrative() is True

    def test_not_hot_narrative(
        self, engine, weak_adoption, weak_social, cold_market
    ):
        """Test is_hot_narrative returns False for weak narrative."""
        score = engine.analyze_narrative(
            asset='COLD_CHECK',
            category=NarrativeCategory.OTHER,
            adoption_metrics=weak_adoption,
            social_signals=weak_social,
            market_metrics=cold_market,
        )

        assert score.is_hot_narrative() is False

    def test_zero_adoption_metrics(self, engine, strong_social, hot_market):
        """Test with zero adoption metrics."""
        metrics = AdoptionMetrics()  # All zeros
        score = engine.analyze_narrative(
            asset='ZERO_ADOPTION',
            category=NarrativeCategory.GAMING,
            adoption_metrics=metrics,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        assert 0 <= score.adoption_trend <= 100

    def test_narrative_signals_generation(
        self, engine, strong_adoption, strong_social, hot_market
    ):
        """Test key signal identification."""
        score = engine.analyze_narrative(
            asset='SIGNALS_TEST',
            category=NarrativeCategory.DEFI,
            adoption_metrics=strong_adoption,
            social_signals=strong_social,
            market_metrics=hot_market,
        )

        # Should identify key signals
        assert len(score.key_signals) > 0
        # Check for expected signal patterns
        signal_text = ' '.join(score.key_signals).lower()
        assert 'adoption' in signal_text or 'capital' in signal_text or 'social' in signal_text
