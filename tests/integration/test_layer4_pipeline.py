"""
Integration tests for Layer 4 X20 Engine complete pipeline.
Tests end-to-end flow: Fundamental → Narrative → Quantitative → Risk → Ranker → Integration.
"""

import pytest
from src.layers.layer4_x20.fundamental_analyzer import (
    FundamentalAnalyzer,
    TeamMember,
)
from src.layers.layer4_x20.narrative_engine import (
    NarrativeEngine,
    NarrativeCategory,
    AdoptionMetrics,
    SocialSignals,
)
from src.layers.layer4_x20.quantitative_scorer import (
    QuantitativeScorer,
    MomentumMetrics,
    VolatilityMetrics,
    RelativeStrengthMetrics,
    LiquidityMetrics,
    VolumeClassification,
)
from src.layers.layer4_x20.risk_assessor import (
    RiskAssessor,
    DrawdownMetrics,
    ConcentrationMetrics,
    ExecutionMetrics,
    TimelineMetrics,
)
from src.layers.layer4_x20.opportunity_ranker import (
    OpportunityRanker,
    RankerInput,
    OpportunityConfidence,
    OpportunityTier,
)
from src.layers.layer4_x20.integration_layer import (
    IntegrationLayer,
    BCESignal,
    X20Score,
    FOPOMetrics,
    IntegrationSignal,
)


class TestLayer4Pipeline:
    """Integration tests for complete Layer 4 pipeline."""

    @pytest.fixture
    def fundamental_analyzer(self):
        """Create fundamental analyzer."""
        return FundamentalAnalyzer()

    @pytest.fixture
    def narrative_engine(self):
        """Create narrative engine."""
        return NarrativeEngine()

    @pytest.fixture
    def quantitative_scorer(self):
        """Create quantitative scorer."""
        return QuantitativeScorer()

    @pytest.fixture
    def risk_assessor(self):
        """Create risk assessor."""
        return RiskAssessor()

    @pytest.fixture
    def opportunity_ranker(self):
        """Create opportunity ranker."""
        return OpportunityRanker()

    @pytest.fixture
    def integration_layer(self):
        """Create integration layer."""
        return IntegrationLayer()

    # ========== SCENARIO 1: STRONG OPPORTUNITY (Should be STRONG_BUY) ==========

    def test_strong_ai_token_pipeline(
        self,
        fundamental_analyzer,
        narrative_engine,
        quantitative_scorer,
        risk_assessor,
        opportunity_ranker,
        integration_layer,
    ):
        """Test full pipeline for strong AI token (STRONG_BUY scenario)."""
        asset = 'AI_TOKEN_STRONG'

        # Component 1: Fundamental Analysis
        team_members = [
            TeamMember(
                name='Alice CEO',
                role='CEO',
                prior_experience='Stripe, OpenAI',
                github_activity=500,
                expertise_relevance=0.95,
                is_founder=True,
            ),
            TeamMember(
                name='Bob CTO',
                role='CTO',
                prior_experience='Google, Facebook',
                github_activity=400,
                expertise_relevance=0.90,
                is_founder=False,
            ),
        ]

        tokenomics = {
            'total_supply': 1000000000,
            'circulating': 300000000,
            'vesting_schedule': {
                'cliff_months': 12,
                'monthly_unlock_pct': 1.0,
            },
            'distribution': {
                'founders': 0.15,
                'investors': 0.30,
                'community': 0.55,
            },
        }

        adoption_metrics_dict = {
            'users': 1500000,
            'growth_rate': 0.40,
            'tvl': 350000000,
            'transaction_volume': 30000000,
            'developer_activity': 150,
        }

        competitive_context = {
            'market_position': 0.50,  # Top 3 in category
            'differentiation': 0.85,  # 0-1 score
            'has_technology_moat': True,
        }

        fundamental_score = fundamental_analyzer.analyze_asset(
            asset=asset,
            team_members=team_members,
            vc_backers=['Sequoia', 'a16z', 'Paradigm', 'Polychain'],
            tokenomics=tokenomics,
            adoption_metrics=adoption_metrics_dict,
            competitive_context=competitive_context,
        )

        assert fundamental_score.overall_fundamental_score > 70

        # Component 2: Narrative Analysis
        adoption = AdoptionMetrics(
            users=1500000,
            growth_rate=0.40,
            tvl=350000000,
            transaction_volume=30000000,
            developer_activity=150,
            active_addresses=120000,
        )

        social = SocialSignals(
            mention_volume=12000,
            sentiment_score=0.80,
            twitter_volume=4000,
            reddit_activity=1500,
            discord_growth=0.35,
            social_trend=0.75,
        )

        market = {
            'market_cap': 35e9,
            'volume_24h': 3.5e9,
            'price_change_24h': 0.15,
            'volume_to_mcap_ratio': 0.10,
            'inflow_indicator': 0.70,
        }

        narrative_score = narrative_engine.analyze_narrative(
            asset=asset,
            category=NarrativeCategory.AI,
            adoption_metrics=adoption,
            social_signals=social,
            market_metrics=market,
        )

        assert narrative_score.overall_narrative_score > 75

        # Component 3: Quantitative Analysis
        momentum = MomentumMetrics(
            rsi_14=68.0,
            rsi_strength=12.0,
            macd_value=0.04,
            macd_positive=True,
            price_position=0.75,
            price_above_ma_20=True,
            price_above_ma_50=True,
            price_above_ma_200=True,
            breakout_readiness=0.80,
            strength_bars=4,
        )

        volatility = VolatilityMetrics(
            volatility_recent=0.35,
            volatility_historical=0.28,
            volatility_ratio=1.25,
            average_true_range=0.12,
            beta=1.2,
            sharpe_ratio=1.3,
        )

        relative_strength = RelativeStrengthMetrics(
            outperformance_vs_top10=0.28,
            rs_line_trend=0.72,
            sector_percentile=0.82,
            correlation_to_btc=0.45,
            alpha=0.18,
        )

        liquidity = LiquidityMetrics(
            volume_24h=80e6,
            bid_ask_spread=0.0010,
            volume_classification=VolumeClassification.HIGH,
            order_book_depth=8e6,
            exchange_diversity=4,
            slippage_estimate_1pct=0.002,
        )

        quantitative_score = quantitative_scorer.analyze_asset(
            asset=asset,
            momentum_metrics=momentum,
            volatility_metrics=volatility,
            relative_strength=relative_strength,
            liquidity_metrics=liquidity,
        )

        assert quantitative_score.overall_quantitative_score > 75

        # Component 4: Risk Assessment
        drawdown = DrawdownMetrics(
            volatility=0.35,
            historical_max_drawdown=0.42,
            estimated_max_drawdown=0.40,
            recovery_periods=[30, 45, 60],
            var_95=0.22,
        )

        concentration = ConcentrationMetrics(
            position_size_pct=0.03,
            portfolio_allocation=0.05,
            max_position=0.10,
            avg_position=0.05,
            correlation_to_portfolio=0.35,
            diversification_score=0.85,
        )

        execution = ExecutionMetrics(
            bid_ask_spread=0.0010,
            estimated_slippage_1pct=0.002,
            estimated_slippage_5pct=0.010,
            market_impact_factor=0.0005,
            liquidity_depth=8e6,
            venue_fragmentation=0.8,
        )

        timeline = TimelineMetrics(
            token_unlock_upcoming=0,
            unlock_amount_pct=0.0,
            regulatory_events=0,
            days_to_key_events=[],
            unlock_schedule_concentration=0.0,
        )

        risk_score = risk_assessor.assess_risk(
            asset=asset,
            drawdown_metrics=drawdown,
            concentration_metrics=concentration,
            execution_metrics=execution,
            timeline_metrics=timeline,
        )

        # Risk score is inverted: 100 = low risk, 0 = high risk
        # So we need to convert to get a "risk adjusted" version
        risk_inverted = 100.0 - (risk_score.overall_risk_score * 0.5)
        assert risk_inverted > 70

        # Component 5: Opportunity Ranking
        ranker_input = RankerInput(
            asset=asset,
            fundamental_score=fundamental_score.overall_fundamental_score,
            narrative_score=narrative_score.overall_narrative_score,
            quantitative_score=quantitative_score.overall_quantitative_score,
            risk_score=risk_inverted,  # Pass inverted score
        )

        x20_result = opportunity_ranker.rank_opportunity(ranker_input)

        assert x20_result.x20_opportunity_score > 75
        assert x20_result.confidence == OpportunityConfidence.HIGH
        assert x20_result.tier == OpportunityTier.TIER_1

        # Component 6: Integration with BCE
        bce_signal = BCESignal(
            asset=asset,
            bce_score=5.5 / 6,
            wyckoff_structure=0.92,
            volume_analysis=0.90,
            selling_exhaustion=0.88,
            smart_money_acc=0.95,
            market_structure=0.90,
            momentum_confirmation=0.92,
            valid=True,
        )

        x20_score_obj = X20Score(
            asset=asset,
            x20_opportunity_score=x20_result.x20_opportunity_score,
            fundamental_score=fundamental_score.overall_fundamental_score,
            narrative_score=narrative_score.overall_narrative_score,
            quantitative_score=quantitative_score.overall_quantitative_score,
            risk_score=risk_inverted,
            component_alignment=x20_result.component_alignment,
            risk_adjusted_score=x20_result.risk_adjusted_score,
            tier=x20_result.tier.value,
            confidence=x20_result.confidence.value,
        )

        integration_result = integration_layer.integrate_signals(
            bce_signal, x20_score_obj
        )

        # Should result in STRONG_BUY
        assert integration_result.integration_signal == IntegrationSignal.STRONG_BUY
        assert integration_result.confidence_level > 80
        assert integration_result.bce_valid is True
        assert integration_result.x20_sufficient is True

    # ========== SCENARIO 2: MEDIUM OPPORTUNITY (Should be BUY) ==========

    def test_medium_defi_token_pipeline(
        self,
        fundamental_analyzer,
        narrative_engine,
        quantitative_scorer,
        risk_assessor,
        opportunity_ranker,
        integration_layer,
    ):
        """Test full pipeline for medium DeFi token (BUY scenario)."""
        asset = 'DEFI_TOKEN_MEDIUM'

        # Fundamental: Medium quality
        fundamental_score = fundamental_analyzer.analyze_asset(
            asset=asset,
            team_members=[
                TeamMember(
                    name='Dave Dev',
                    role='CEO',
                    prior_experience='DeFi Protocol Labs, Curve',
                    github_activity=400,
                    expertise_relevance=0.85,
                    is_founder=True,
                ),
                TeamMember(
                    name='Eve Engineer',
                    role='CTO',
                    prior_experience='Aave, Compound',
                    github_activity=350,
                    expertise_relevance=0.80,
                    is_founder=False,
                ),
                TeamMember(
                    name='Frank Finance',
                    role='CFO',
                    prior_experience='JPMorgan',
                    github_activity=100,
                    expertise_relevance=0.75,
                    is_founder=False,
                )
            ],
            vc_backers=['Sequoia', 'a16z Crypto', 'Pantera'],
            tokenomics={
                'total_supply': 100000000,
                'circulating': 30000000,
                'vesting_schedule': {'cliff_months': 6, 'monthly_unlock_pct': 2.0},
                'distribution': {'founders': 0.25, 'investors': 0.35, 'community': 0.40},
            },
            adoption_metrics={
                'users': 300000,
                'growth_rate': 0.20,
                'tvl': 50000000,
                'transaction_volume': 5000000,
                'developer_activity': 40,
            },
            competitive_context={
                'market_position': 0.50,  # Top 5 in category
                'differentiation': 0.65,
                'has_technology_moat': True,
            },
        )

        assert 60 < fundamental_score.overall_fundamental_score < 75

        # Narrative: Growing but not hot
        adoption = AdoptionMetrics(
            users=200000,  # Lower user base
            growth_rate=0.08,  # Lower growth rate
            tvl=30000000,  # Lower TVL
            transaction_volume=3000000,  # Lower volume
            developer_activity=25,  # Reduced activity
            active_addresses=15000,  # Fewer addresses
        )

        social = SocialSignals(
            mention_volume=1500,  # Moderate mentions
            sentiment_score=0.55,  # Neutral-positive
            twitter_volume=500,  # Lower Twitter activity
            reddit_activity=200,
            discord_growth=0.08,  # Slower growth
            social_trend=0.40,  # Moderate trend
        )

        market = {
            'market_cap': 5e9,
            'volume_24h': 400e6,  # Slightly lower
            'price_change_24h': 0.04,  # Moderate daily move
            'volume_to_mcap_ratio': 0.08,
            'inflow_indicator': 0.35,  # Moderate inflow
        }

        narrative_score = narrative_engine.analyze_narrative(
            asset=asset,
            category=NarrativeCategory.DEFI,
            adoption_metrics=adoption,
            social_signals=social,
            market_metrics=market,
        )

        assert 60 < narrative_score.overall_narrative_score < 75

        # Quantitative: Solid but not explosive
        momentum = MomentumMetrics(
            rsi_14=58.0,
            rsi_strength=5.0,
            macd_value=0.02,
            macd_positive=True,
            price_position=0.55,
            price_above_ma_20=True,
            price_above_ma_50=True,
            price_above_ma_200=False,
            breakout_readiness=0.60,
            strength_bars=2,
        )

        volatility = VolatilityMetrics(
            volatility_recent=0.25,
            volatility_historical=0.22,
            volatility_ratio=1.14,
            average_true_range=0.08,
            beta=0.95,
            sharpe_ratio=0.9,
        )

        relative_strength = RelativeStrengthMetrics(
            outperformance_vs_top10=0.12,
            rs_line_trend=0.55,
            sector_percentile=0.65,
            correlation_to_btc=0.60,
            alpha=0.08,
        )

        liquidity = LiquidityMetrics(
            volume_24h=20e6,
            bid_ask_spread=0.0015,
            volume_classification=VolumeClassification.MODERATE,
            order_book_depth=2e6,
            exchange_diversity=2,
            slippage_estimate_1pct=0.005,
        )

        quantitative_score = quantitative_scorer.analyze_asset(
            asset=asset,
            momentum_metrics=momentum,
            volatility_metrics=volatility,
            relative_strength=relative_strength,
            liquidity_metrics=liquidity,
        )

        assert 60 < quantitative_score.overall_quantitative_score < 75

        # Risk: Moderate
        drawdown = DrawdownMetrics(
            volatility=0.25,
            historical_max_drawdown=0.55,
            estimated_max_drawdown=0.50,
            recovery_periods=[40, 60, 90],
            var_95=0.18,
        )

        concentration = ConcentrationMetrics(
            position_size_pct=0.05,
            portfolio_allocation=0.05,
            max_position=0.10,
            avg_position=0.05,
            correlation_to_portfolio=0.50,
            diversification_score=0.70,
        )

        execution = ExecutionMetrics(
            bid_ask_spread=0.0015,
            estimated_slippage_1pct=0.005,
            estimated_slippage_5pct=0.025,
            market_impact_factor=0.001,
            liquidity_depth=2e6,
            venue_fragmentation=0.6,
        )

        timeline = TimelineMetrics(
            token_unlock_upcoming=45,
            unlock_amount_pct=0.10,
            regulatory_events=0,
            days_to_key_events=[45],
            unlock_schedule_concentration=0.3,
        )

        risk_score = risk_assessor.assess_risk(
            asset=asset,
            drawdown_metrics=drawdown,
            concentration_metrics=concentration,
            execution_metrics=execution,
            timeline_metrics=timeline,
        )

        risk_inverted = 100.0 - (risk_score.overall_risk_score * 0.5)
        assert 50 < risk_inverted < 80  # Moderate risk

        # Ranking
        ranker_input = RankerInput(
            asset=asset,
            fundamental_score=fundamental_score.overall_fundamental_score,
            narrative_score=narrative_score.overall_narrative_score,
            quantitative_score=quantitative_score.overall_quantitative_score,
            risk_score=risk_inverted,
        )

        x20_result = opportunity_ranker.rank_opportunity(ranker_input)

        assert 65 < x20_result.x20_opportunity_score < 75
        assert x20_result.confidence == OpportunityConfidence.MEDIUM
        assert x20_result.tier == OpportunityTier.TIER_2

        # Integration
        bce_signal = BCESignal(
            asset=asset,
            bce_score=5.2 / 6,
            wyckoff_structure=0.88,
            volume_analysis=0.85,
            selling_exhaustion=0.82,
            smart_money_acc=0.90,
            market_structure=0.86,
            momentum_confirmation=0.88,
            valid=True,
        )

        x20_score_obj = X20Score(
            asset=asset,
            x20_opportunity_score=x20_result.x20_opportunity_score,
            fundamental_score=fundamental_score.overall_fundamental_score,
            narrative_score=narrative_score.overall_narrative_score,
            quantitative_score=quantitative_score.overall_quantitative_score,
            risk_score=risk_inverted,
            component_alignment=x20_result.component_alignment,
            risk_adjusted_score=x20_result.risk_adjusted_score,
            tier=x20_result.tier.value,
            confidence=x20_result.confidence.value,
        )

        integration_result = integration_layer.integrate_signals(
            bce_signal, x20_score_obj
        )

        # Should result in BUY
        assert integration_result.integration_signal == IntegrationSignal.BUY
        assert 75 < integration_result.confidence_level < 92  # BUY confidence with good alignment

    # ========== SCENARIO 3: WEAK OPPORTUNITY (Should be WATCH/HOLD) ==========

    def test_weak_token_pipeline_rejected(
        self,
        fundamental_analyzer,
        narrative_engine,
        quantitative_scorer,
        risk_assessor,
        opportunity_ranker,
        integration_layer,
    ):
        """Test full pipeline for weak token (WATCH/HOLD scenario)."""
        asset = 'WEAK_TOKEN'

        # Fundamental: Poor quality
        fundamental_score = fundamental_analyzer.analyze_asset(
            asset=asset,
            team_members=[],
            vc_backers=[],
            tokenomics={
                'total_supply': 1000000000,
                'circulating': 500000000,
                'vesting_schedule': {'cliff_months': 0, 'monthly_unlock_pct': 5.0},
                'distribution': {'founders': 0.50, 'investors': 0.30, 'community': 0.20},
            },
            adoption_metrics={
                'users': 10000,
                'growth_rate': -0.15,
                'tvl': 500000,
                'transaction_volume': 50000,
                'developer_activity': 5,
            },
            competitive_context={
                'market_position': 0.02,  # Far outside top 10
                'differentiation': 0.20,
                'has_technology_moat': False,
            },
        )

        assert fundamental_score.overall_fundamental_score < 50

        # Narrative: Declining
        adoption = AdoptionMetrics(
            users=10000,
            growth_rate=-0.15,
            tvl=500000,
            transaction_volume=50000,
            developer_activity=5,
            active_addresses=2000,
        )

        social = SocialSignals(
            mention_volume=100,
            sentiment_score=0.35,
            twitter_volume=50,
            reddit_activity=20,
            discord_growth=-0.10,
            social_trend=-0.60,
        )

        market = {
            'market_cap': 50e6,
            'volume_24h': 5e6,
            'price_change_24h': -0.12,
            'volume_to_mcap_ratio': 0.10,
            'inflow_indicator': -0.50,
        }

        narrative_score = narrative_engine.analyze_narrative(
            asset=asset,
            category=NarrativeCategory.OTHER,
            adoption_metrics=adoption,
            social_signals=social,
            market_metrics=market,
        )

        assert narrative_score.overall_narrative_score < 50

        # Quantitative: Weak
        momentum = MomentumMetrics(
            rsi_14=25.0,
            rsi_strength=-20.0,
            macd_value=-0.03,
            macd_positive=False,
            price_position=0.15,
            price_above_ma_20=False,
            price_above_ma_50=False,
            price_above_ma_200=False,
            breakout_readiness=0.10,
            strength_bars=-3,
        )

        volatility = VolatilityMetrics(
            volatility_recent=0.60,
            volatility_historical=0.40,
            volatility_ratio=1.50,
            average_true_range=0.25,
            beta=2.0,
            sharpe_ratio=-0.5,
        )

        relative_strength = RelativeStrengthMetrics(
            outperformance_vs_top10=-0.40,
            rs_line_trend=-0.85,
            sector_percentile=0.10,
            correlation_to_btc=0.90,
            alpha=-0.30,
        )

        liquidity = LiquidityMetrics(
            volume_24h=100e3,
            bid_ask_spread=0.05,
            volume_classification=VolumeClassification.LOW,
            order_book_depth=100e3,
            exchange_diversity=1,
            slippage_estimate_1pct=0.10,
        )

        quantitative_score = quantitative_scorer.analyze_asset(
            asset=asset,
            momentum_metrics=momentum,
            volatility_metrics=volatility,
            relative_strength=relative_strength,
            liquidity_metrics=liquidity,
        )

        assert quantitative_score.overall_quantitative_score < 40

        # Risk: High
        drawdown = DrawdownMetrics(
            volatility=0.60,
            historical_max_drawdown=0.75,
            estimated_max_drawdown=0.70,
            recovery_periods=[120, 180, 240],
            var_95=0.50,
        )

        concentration = ConcentrationMetrics(
            position_size_pct=0.15,
            portfolio_allocation=0.05,
            max_position=0.10,
            avg_position=0.05,
            correlation_to_portfolio=0.85,
            diversification_score=0.15,
        )

        execution = ExecutionMetrics(
            bid_ask_spread=0.05,
            estimated_slippage_1pct=0.10,
            estimated_slippage_5pct=0.40,
            market_impact_factor=0.01,
            liquidity_depth=100e3,
            venue_fragmentation=0.1,
        )

        timeline = TimelineMetrics(
            token_unlock_upcoming=10,
            unlock_amount_pct=0.30,
            regulatory_events=2,
            days_to_key_events=[10, 60],
            unlock_schedule_concentration=0.8,
        )

        risk_score = risk_assessor.assess_risk(
            asset=asset,
            drawdown_metrics=drawdown,
            concentration_metrics=concentration,
            execution_metrics=execution,
            timeline_metrics=timeline,
        )

        risk_inverted = 100.0 - (risk_score.overall_risk_score * 0.5)
        assert 40 < risk_inverted < 70  # Moderate-to-high risk profile

        # Ranking
        ranker_input = RankerInput(
            asset=asset,
            fundamental_score=fundamental_score.overall_fundamental_score,
            narrative_score=narrative_score.overall_narrative_score,
            quantitative_score=quantitative_score.overall_quantitative_score,
            risk_score=risk_inverted,
        )

        x20_result = opportunity_ranker.rank_opportunity(ranker_input)

        assert x20_result.x20_opportunity_score < 55
        assert x20_result.tier == OpportunityTier.WATCH

        # Integration: Invalid BCE
        bce_signal = BCESignal(
            asset=asset,
            bce_score=3.5 / 6,
            wyckoff_structure=0.50,
            volume_analysis=0.45,
            selling_exhaustion=0.40,
            smart_money_acc=0.55,
            market_structure=0.50,
            momentum_confirmation=0.45,
            valid=False,
        )

        x20_score_obj = X20Score(
            asset=asset,
            x20_opportunity_score=x20_result.x20_opportunity_score,
            fundamental_score=fundamental_score.overall_fundamental_score,
            narrative_score=narrative_score.overall_narrative_score,
            quantitative_score=quantitative_score.overall_quantitative_score,
            risk_score=risk_inverted,
            component_alignment=x20_result.component_alignment,
            risk_adjusted_score=x20_result.risk_adjusted_score,
            tier=x20_result.tier.value,
            confidence=x20_result.confidence.value,
        )

        integration_result = integration_layer.integrate_signals(
            bce_signal, x20_score_obj
        )

        # Should result in WATCH or HOLD
        assert integration_result.integration_signal in [
            IntegrationSignal.WATCH,
            IntegrationSignal.HOLD,
        ]
        assert integration_result.bce_valid is False

    # ========== SCENARIO 4: FOMO SCENARIO (Price extended, euphoria high) ==========

    def test_fomo_circuit_breaker_activation(
        self,
        fundamental_analyzer,
        narrative_engine,
        quantitative_scorer,
        risk_assessor,
        opportunity_ranker,
        integration_layer,
    ):
        """Test FOMO circuit breaker prevents STRONG_BUY despite good fundamentals."""
        asset = 'HYPED_TOKEN'

        # Good fundamentals
        fundamental_score = fundamental_analyzer.analyze_asset(
            asset=asset,
            team_members=[
                TeamMember(
                    name='CEO', role='CEO', prior_experience='OpenAI, DeepMind',
                    github_activity=300, expertise_relevance=0.90, is_founder=True,
                )
            ],
            vc_backers=['Sequoia', 'a16z', 'Paradigm'],
            tokenomics={
                'total_supply': 1000000000,
                'circulating': 200000000,
                'vesting_schedule': {'cliff_months': 12, 'monthly_unlock_pct': 1.0},
                'distribution': {'founders': 0.15, 'investors': 0.40, 'community': 0.45},
            },
            adoption_metrics={
                'users': 500000,
                'growth_rate': 0.50,
                'tvl': 100000000,
                'transaction_volume': 10000000,
                'developer_activity': 80,
            },
            competitive_context={
                'market_position': 0.40,  # Top 3 in category
                'differentiation': 0.75,
                'has_technology_moat': True,
            },
        )

        # Strong narrative (hot)
        adoption = AdoptionMetrics(
            users=500000, growth_rate=0.50, tvl=100000000,
            transaction_volume=10000000, developer_activity=80, active_addresses=40000,
        )

        social = SocialSignals(
            mention_volume=20000, sentiment_score=0.85,
            twitter_volume=8000, reddit_activity=3000,
            discord_growth=0.60, social_trend=0.90,
        )

        market = {
            'market_cap': 15e9, 'volume_24h': 2e9,
            'price_change_24h': 0.45,
            'volume_to_mcap_ratio': 0.133,
            'inflow_indicator': 0.85,
        }

        narrative_score = narrative_engine.analyze_narrative(
            asset=asset, category=NarrativeCategory.AI,
            adoption_metrics=adoption, social_signals=social,
            market_metrics=market,
        )

        # Strong quantitative
        momentum = MomentumMetrics(
            rsi_14=75.0, rsi_strength=18.0, macd_value=0.08,
            macd_positive=True, price_position=0.95,
            price_above_ma_20=True, price_above_ma_50=True,
            price_above_ma_200=True, breakout_readiness=0.95,
            strength_bars=6,
        )

        volatility = VolatilityMetrics(
            volatility_recent=0.55, volatility_historical=0.30,
            volatility_ratio=1.83, average_true_range=0.20,
            beta=1.8, sharpe_ratio=1.5,
        )

        relative_strength = RelativeStrengthMetrics(
            outperformance_vs_top10=0.50, rs_line_trend=0.90,
            sector_percentile=0.95, correlation_to_btc=0.30,
            alpha=0.40,
        )

        liquidity = LiquidityMetrics(
            volume_24h=150e6, bid_ask_spread=0.001,
            volume_classification=VolumeClassification.VERY_HIGH,
            order_book_depth=15e6, exchange_diversity=5,
            slippage_estimate_1pct=0.001,
        )

        quantitative_score = quantitative_scorer.analyze_asset(
            asset=asset, momentum_metrics=momentum,
            volatility_metrics=volatility, relative_strength=relative_strength,
            liquidity_metrics=liquidity,
        )

        # Good risk profile despite high volatility
        risk_score = risk_assessor.assess_risk(
            asset=asset,
            drawdown_metrics=DrawdownMetrics(volatility=0.55, historical_max_drawdown=0.45),
            concentration_metrics=ConcentrationMetrics(position_size_pct=0.02),
            execution_metrics=ExecutionMetrics(bid_ask_spread=0.001, liquidity_depth=15e6),
            timeline_metrics=TimelineMetrics(),
        )

        risk_inverted = 100.0 - (risk_score.overall_risk_score * 0.5)

        # Component 5: Get high X20 score
        ranker_input = RankerInput(
            asset=asset,
            fundamental_score=fundamental_score.overall_fundamental_score,
            narrative_score=narrative_score.overall_narrative_score,
            quantitative_score=quantitative_score.overall_quantitative_score,
            risk_score=risk_inverted,
        )

        x20_result = opportunity_ranker.rank_opportunity(ranker_input)
        assert x20_result.x20_opportunity_score > 75

        # Component 6: With valid BCE but FOMO triggered
        bce_signal = BCESignal(
            asset=asset, bce_score=5.5 / 6,
            wyckoff_structure=0.90, volume_analysis=0.88,
            selling_exhaustion=0.85, smart_money_acc=0.92,
            market_structure=0.88, momentum_confirmation=0.90,
            valid=True,
        )

        x20_score_obj = X20Score(
            asset=asset,
            x20_opportunity_score=x20_result.x20_opportunity_score,
            fundamental_score=fundamental_score.overall_fundamental_score,
            narrative_score=narrative_score.overall_narrative_score,
            quantitative_score=quantitative_score.overall_quantitative_score,
            risk_score=risk_inverted,
            component_alignment=x20_result.component_alignment,
            risk_adjusted_score=x20_result.risk_adjusted_score,
            tier=x20_result.tier.value,
            confidence=x20_result.confidence.value,
        )

        # FOMO metrics: Multiple triggers
        fomo_metrics = FOPOMetrics(
            price_discovery_phase=True,
            euphoria_level=85.0,  # >80 trigger
            extension_factor=2.2,  # >2x trigger
            volume_surge=200.0,  # >150% trigger
            trending_intensity=90.0,  # >80 trigger
        )

        integration_result = integration_layer.integrate_signals(
            bce_signal, x20_score_obj, fomo_metrics
        )

        # FOMO breaker should trigger and reduce confidence
        assert integration_result.fomo_clear is False
        # Even with good scores, FOMO should prevent STRONG_BUY
        assert integration_result.integration_signal != IntegrationSignal.STRONG_BUY
        # Should still allow BUY or downgrade to RESEARCH
        assert integration_result.integration_signal in [
            IntegrationSignal.BUY,
            IntegrationSignal.RESEARCH,
        ]

    # ========== SCENARIO 5: MULTI-ASSET ANALYSIS ==========

    def test_multi_asset_ranking_comparison(
        self,
        opportunity_ranker,
        integration_layer,
    ):
        """Test ranking and filtering across multiple assets."""
        assets_data = [
            {
                'name': 'STRONG_ASSET',
                'fundamental': 82.0,
                'narrative': 80.0,
                'quantitative': 85.0,
                'risk': 82.0,
            },
            {
                'name': 'MEDIUM_ASSET',
                'fundamental': 70.0,
                'narrative': 68.0,
                'quantitative': 72.0,
                'risk': 70.0,
            },
            {
                'name': 'WEAK_ASSET',
                'fundamental': 40.0,
                'narrative': 38.0,
                'quantitative': 42.0,
                'risk': 35.0,
            },
        ]

        # Rank all assets
        for asset_data in assets_data:
            ranker_input = RankerInput(
                asset=asset_data['name'],
                fundamental_score=asset_data['fundamental'],
                narrative_score=asset_data['narrative'],
                quantitative_score=asset_data['quantitative'],
                risk_score=asset_data['risk'],
            )

            x20_result = opportunity_ranker.rank_opportunity(ranker_input)

            # Create integration signals
            if asset_data == assets_data[0]:  # STRONG
                bce_score = 5.5 / 6
            elif asset_data == assets_data[1]:  # MEDIUM
                bce_score = 5.2 / 6
            else:  # WEAK
                bce_score = 3.5 / 6

            bce_signal = BCESignal(
                asset=asset_data['name'],
                bce_score=bce_score,
                wyckoff_structure=0.80,
                volume_analysis=0.80,
                selling_exhaustion=0.80,
                smart_money_acc=0.80,
                market_structure=0.80,
                momentum_confirmation=0.80,
                valid=bce_score >= 5.0 / 6,
            )

            x20_score_obj = X20Score(
                asset=asset_data['name'],
                x20_opportunity_score=x20_result.x20_opportunity_score,
                fundamental_score=asset_data['fundamental'],
                narrative_score=asset_data['narrative'],
                quantitative_score=asset_data['quantitative'],
                risk_score=asset_data['risk'],
                component_alignment=x20_result.component_alignment,
                risk_adjusted_score=x20_result.risk_adjusted_score,
                tier=x20_result.tier.value,
                confidence=x20_result.confidence.value,
            )

            integration_layer.integrate_signals(bce_signal, x20_score_obj)

        # Verify filtering
        strong_buys = integration_layer.get_strong_buy_opportunities()
        buys = integration_layer.get_buy_opportunities()
        watch = integration_layer.get_watch_list()

        # Strong asset should be in at least buys
        strong_assets = [asset[0] for asset in buys]
        assert 'STRONG_ASSET' in strong_assets

        # Check ranking order
        all_results = list(integration_layer.results.items())
        scores = [r[1].confidence_level for r in all_results]
        assert scores[0] >= scores[1] >= scores[2]
