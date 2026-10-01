"""
Unit tests for Quantitative Scorer (Phase 4 Component 3).
"""

import pytest
from src.layers.layer4_x20.quantitative_scorer import (
    QuantitativeScorer,
    MomentumMetrics,
    VolatilityMetrics,
    RelativeStrengthMetrics,
    LiquidityMetrics,
    VolumeClassification,
    VolatilityProfile,
)


class TestQuantitativeScorer:
    """Tests for QuantitativeScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create quantitative scorer instance."""
        return QuantitativeScorer()

    @pytest.fixture
    def strong_momentum(self):
        """Create strong momentum metrics."""
        return MomentumMetrics(
            rsi_14=65.0,  # Above midpoint
            rsi_strength=15.0,
            macd_value=0.05,
            macd_positive=True,
            price_position=0.80,  # Near highs
            price_above_ma_20=True,
            price_above_ma_50=True,
            price_above_ma_200=True,  # All MAs
            breakout_readiness=0.85,
            strength_bars=5,
        )

    @pytest.fixture
    def weak_momentum(self):
        """Create weak momentum metrics."""
        return MomentumMetrics(
            rsi_14=25.0,  # Oversold
            rsi_strength=-25.0,
            macd_value=-0.05,
            macd_positive=False,
            price_position=0.20,  # Near lows
            price_above_ma_20=False,
            price_above_ma_50=False,
            price_above_ma_200=False,  # Below all MAs
            breakout_readiness=0.10,
            strength_bars=-5,
        )

    @pytest.fixture
    def high_volatility(self):
        """Create high volatility metrics."""
        return VolatilityMetrics(
            volatility_recent=0.45,  # 45%
            volatility_historical=0.30,
            volatility_ratio=1.50,  # Recent > Historical
            average_true_range=0.15,
            beta=1.3,
            sharpe_ratio=1.2,
        )

    @pytest.fixture
    def low_volatility(self):
        """Create low volatility metrics."""
        return VolatilityMetrics(
            volatility_recent=0.08,  # 8%
            volatility_historical=0.10,
            volatility_ratio=0.80,  # Recent < Historical
            average_true_range=0.03,
            beta=0.7,
            sharpe_ratio=0.5,
        )

    @pytest.fixture
    def strong_relative_strength(self):
        """Create strong relative strength metrics."""
        return RelativeStrengthMetrics(
            outperformance_vs_top10=0.35,  # 35% outperformance
            rs_line_trend=0.75,  # Strong uptrend
            sector_percentile=0.85,  # Top 15%
            correlation_to_btc=0.5,
            alpha=0.20,  # 20% alpha
        )

    @pytest.fixture
    def weak_relative_strength(self):
        """Create weak relative strength metrics."""
        return RelativeStrengthMetrics(
            outperformance_vs_top10=-0.25,  # -25% underperformance
            rs_line_trend=-0.75,  # Strong downtrend
            sector_percentile=0.15,  # Bottom 15%
            correlation_to_btc=0.8,
            alpha=-0.15,  # -15% alpha
        )

    @pytest.fixture
    def high_liquidity(self):
        """Create high liquidity metrics."""
        return LiquidityMetrics(
            volume_24h=100e6,  # $100M daily
            bid_ask_spread=0.0008,  # 0.08%
            volume_classification=VolumeClassification.VERY_HIGH,
            order_book_depth=10e6,  # $10M on each side
            exchange_diversity=5,
            slippage_estimate_1pct=0.001,
        )

    @pytest.fixture
    def low_liquidity(self):
        """Create low liquidity metrics."""
        return LiquidityMetrics(
            volume_24h=100e3,  # $100K daily
            bid_ask_spread=0.05,  # 5%
            volume_classification=VolumeClassification.LOW,
            order_book_depth=50e3,  # $50K on each side
            exchange_diversity=1,
            slippage_estimate_1pct=0.05,
        )

    def test_scorer_creation(self, scorer):
        """Test scorer instantiation."""
        assert scorer is not None
        assert len(scorer.results) == 0

    def test_momentum_scoring_strong(self, scorer, strong_momentum):
        """Test momentum scoring with strong metrics."""
        score = scorer._score_momentum(strong_momentum)

        assert 0 <= score <= 100
        assert score > 70  # Strong momentum

    def test_momentum_scoring_weak(self, scorer, weak_momentum):
        """Test momentum scoring with weak metrics."""
        score = scorer._score_momentum(weak_momentum)

        assert 0 <= score <= 100
        assert score < 40  # Weak momentum

    def test_momentum_rsi_oversold(self, scorer):
        """Test momentum scoring with oversold RSI."""
        metrics = MomentumMetrics(rsi_14=20.0)  # Oversold
        score = scorer._score_momentum(metrics)

        assert score < 50  # Below midpoint

    def test_momentum_rsi_overbought(self, scorer):
        """Test momentum scoring with overbought RSI."""
        metrics = MomentumMetrics(rsi_14=80.0)  # Overbought
        score = scorer._score_momentum(metrics)

        assert score > 70  # Still positive but risky

    def test_volatility_scoring_high(self, scorer, high_volatility):
        """Test volatility scoring with high volatility."""
        score = scorer._score_volatility(high_volatility)

        assert 0 <= score <= 100
        assert score > 60  # High volatility = opportunity

    def test_volatility_scoring_low(self, scorer, low_volatility):
        """Test volatility scoring with low volatility."""
        score = scorer._score_volatility(low_volatility)

        assert 0 <= score <= 100
        assert score <= 60  # Low volatility = lower opportunity but not extreme

    def test_relative_strength_scoring_strong(self, scorer, strong_relative_strength):
        """Test relative strength scoring with strong metrics."""
        score = scorer._score_relative_strength(strong_relative_strength)

        assert 0 <= score <= 100
        assert score > 70  # Strong outperformance

    def test_relative_strength_scoring_weak(self, scorer, weak_relative_strength):
        """Test relative strength scoring with weak metrics."""
        score = scorer._score_relative_strength(weak_relative_strength)

        assert 0 <= score <= 100
        assert score < 40  # Weak underperformance

    def test_liquidity_scoring_high(self, scorer, high_liquidity):
        """Test liquidity scoring with high liquidity."""
        score = scorer._score_liquidity(high_liquidity)

        assert 0 <= score <= 100
        assert score > 75  # High liquidity

    def test_liquidity_scoring_low(self, scorer, low_liquidity):
        """Test liquidity scoring with low liquidity."""
        score = scorer._score_liquidity(low_liquidity)

        assert 0 <= score <= 100
        assert score < 40  # Low liquidity

    def test_liquidity_scoring_wide_spread(self, scorer):
        """Test liquidity scoring with wide bid-ask spread."""
        metrics = LiquidityMetrics(
            volume_24h=5e6,
            bid_ask_spread=0.10,  # 10% spread
            volume_classification=VolumeClassification.MODERATE,
            order_book_depth=1e6,
            exchange_diversity=1,
        )
        score = scorer._score_liquidity(metrics)

        assert score < 50  # Reduced by spread

    def test_full_analysis_strong_asset(
        self, scorer, strong_momentum, high_volatility,
        strong_relative_strength, high_liquidity
    ):
        """Test complete analysis for strong asset."""
        result = scorer.analyze_asset(
            asset='STRONG_ASSET',
            momentum_metrics=strong_momentum,
            volatility_metrics=high_volatility,
            relative_strength=strong_relative_strength,
            liquidity_metrics=high_liquidity,
        )

        assert result is not None
        assert result.asset == 'STRONG_ASSET'
        assert result.overall_quantitative_score > 70
        assert result.passes_liquidity_test is True
        assert result.reward_potential in ["High", "Moderate"]
        assert len(result.bullish_signals) > 0

    def test_full_analysis_weak_asset(
        self, scorer, weak_momentum, low_volatility,
        weak_relative_strength, low_liquidity
    ):
        """Test complete analysis for weak asset."""
        result = scorer.analyze_asset(
            asset='WEAK_ASSET',
            momentum_metrics=weak_momentum,
            volatility_metrics=low_volatility,
            relative_strength=weak_relative_strength,
            liquidity_metrics=low_liquidity,
        )

        assert result.overall_quantitative_score < 40
        assert result.passes_liquidity_test is False
        assert result.risk_rating in ["Moderate", "Low"]
        assert len(result.bearish_signals) > 0

    def test_volatility_classification_explosive(self, scorer):
        """Test volatility classification for explosive."""
        metrics = VolatilityMetrics(volatility_recent=0.60)
        profile = scorer._classify_volatility(metrics.volatility_recent)

        assert profile == VolatilityProfile.EXPLOSIVE

    def test_volatility_classification_high(self, scorer):
        """Test volatility classification for high."""
        metrics = VolatilityMetrics(volatility_recent=0.30)
        profile = scorer._classify_volatility(metrics.volatility_recent)

        assert profile == VolatilityProfile.HIGH

    def test_volatility_classification_normal(self, scorer):
        """Test volatility classification for normal."""
        metrics = VolatilityMetrics(volatility_recent=0.15)
        profile = scorer._classify_volatility(metrics.volatility_recent)

        assert profile == VolatilityProfile.NORMAL

    def test_volatility_classification_low(self, scorer):
        """Test volatility classification for low."""
        metrics = VolatilityMetrics(volatility_recent=0.05)
        profile = scorer._classify_volatility(metrics.volatility_recent)

        assert profile == VolatilityProfile.LOW

    def test_risk_classification(self, scorer):
        """Test risk classification."""
        assert scorer._classify_risk(0.50) == "Very High"
        assert scorer._classify_risk(0.30) == "High"
        assert scorer._classify_risk(0.18) == "Moderate"
        assert scorer._classify_risk(0.08) == "Low"

    def test_reward_classification(self, scorer):
        """Test reward potential classification."""
        assert scorer._classify_reward(75.0, 75.0) == "High"
        assert scorer._classify_reward(60.0, 60.0) == "Moderate"  # Clearly moderate
        assert scorer._classify_reward(30.0, 30.0) == "Low"

    def test_risk_reward_ratio(self, scorer):
        """Test risk/reward ratio calculation."""
        ratio = scorer._calculate_risk_reward_ratio("Low", "High")
        assert ratio > 2.0

        ratio = scorer._calculate_risk_reward_ratio("Very High", "Low")
        assert ratio < 1.0

    def test_liquidity_requirement(
        self, scorer, strong_momentum, high_volatility,
        strong_relative_strength
    ):
        """Test liquidity requirement enforcement."""
        # High liquidity - should pass
        high_liq = LiquidityMetrics(
            volume_24h=10e6,  # $10M daily
            bid_ask_spread=0.01,
            volume_classification=VolumeClassification.HIGH,
            order_book_depth=2e6,
            exchange_diversity=3,
        )

        result = scorer.analyze_asset(
            asset='HIGH_LIQ',
            momentum_metrics=strong_momentum,
            volatility_metrics=high_volatility,
            relative_strength=strong_relative_strength,
            liquidity_metrics=high_liq,
        )

        assert result.passes_liquidity_test is True

        # Low liquidity - should fail
        low_liq = LiquidityMetrics(
            volume_24h=100e3,  # $100K daily (below $1M requirement)
            bid_ask_spread=0.05,
            volume_classification=VolumeClassification.LOW,
            order_book_depth=50e3,
            exchange_diversity=1,
        )

        result = scorer.analyze_asset(
            asset='LOW_LIQ',
            momentum_metrics=strong_momentum,
            volatility_metrics=high_volatility,
            relative_strength=strong_relative_strength,
            liquidity_metrics=low_liq,
        )

        assert result.passes_liquidity_test is False

    def test_bullish_signals(self, scorer, strong_momentum):
        """Test bullish signal identification."""
        volatility = VolatilityMetrics(volatility_recent=0.40, volatility_ratio=1.5)
        rs = RelativeStrengthMetrics(
            outperformance_vs_top10=0.25, rs_line_trend=0.7
        )

        signals = scorer._identify_bullish_signals(strong_momentum, volatility, rs)

        assert len(signals) > 0
        # Check for expected signals
        signal_text = ' '.join(signals).lower()
        assert 'above' in signal_text or 'outperform' in signal_text

    def test_bearish_signals(self, scorer, weak_momentum):
        """Test bearish signal identification."""
        volatility = VolatilityMetrics(volatility_recent=0.30, beta=1.6)
        rs = RelativeStrengthMetrics(
            outperformance_vs_top10=-0.30, rs_line_trend=-0.8
        )

        signals = scorer._identify_bearish_signals(weak_momentum, volatility, rs)

        assert len(signals) > 0

    def test_neutral_signals(self, scorer):
        """Test neutral signal identification."""
        liquidity = LiquidityMetrics(
            volume_24h=100e3,  # Low volume
            bid_ask_spread=0.03,
            volume_classification=VolumeClassification.LOW,
            order_book_depth=100e3,
            exchange_diversity=1,
        )
        volatility = VolatilityMetrics(volatility_recent=0.08)  # Low vol

        signals = scorer._identify_neutral_signals(liquidity, volatility)

        assert len(signals) > 0
        signal_text = ' '.join(signals).lower()
        assert 'volume' in signal_text or 'volatility' in signal_text

    def test_report_generation(
        self, scorer, strong_momentum, high_volatility,
        strong_relative_strength, high_liquidity
    ):
        """Test report generation."""
        scorer.analyze_asset(
            asset='REPORT_ASSET',
            momentum_metrics=strong_momentum,
            volatility_metrics=high_volatility,
            relative_strength=strong_relative_strength,
            liquidity_metrics=high_liquidity,
        )

        report = scorer.get_report('REPORT_ASSET')
        assert report is not None
        assert 'QUANTITATIVE ANALYSIS' in report
        assert 'REPORT_ASSET' in report
        assert 'COMPONENT SCORES' in report

    def test_no_report_for_unknown_asset(self, scorer):
        """Test report returns None for unknown asset."""
        report = scorer.get_report('UNKNOWN')
        assert report is None

    def test_liquid_assets_filtering(
        self, scorer, strong_momentum, high_volatility,
        strong_relative_strength
    ):
        """Test filtering of liquid assets."""
        high_liq = LiquidityMetrics(
            volume_24h=10e6, volume_classification=VolumeClassification.HIGH
        )
        low_liq = LiquidityMetrics(
            volume_24h=100e3, volume_classification=VolumeClassification.LOW
        )

        scorer.analyze_asset(
            asset='LIQUID_1',
            momentum_metrics=strong_momentum,
            volatility_metrics=high_volatility,
            relative_strength=strong_relative_strength,
            liquidity_metrics=high_liq,
        )

        scorer.analyze_asset(
            asset='ILLIQUID_1',
            momentum_metrics=strong_momentum,
            volatility_metrics=high_volatility,
            relative_strength=strong_relative_strength,
            liquidity_metrics=low_liq,
        )

        liquid = scorer.get_liquid_assets()
        assert len(liquid) >= 1
        assert any(asset == 'LIQUID_1' for asset, _ in liquid)

    def test_high_momentum_filtering(
        self, scorer, high_volatility,
        strong_relative_strength, high_liquidity
    ):
        """Test filtering of high momentum assets."""
        strong_mom = MomentumMetrics(
            rsi_14=75.0, macd_positive=True, price_above_ma_50=True
        )
        weak_mom = MomentumMetrics(
            rsi_14=30.0, macd_positive=False, price_above_ma_50=False
        )

        scorer.analyze_asset(
            asset='HIGH_MOM',
            momentum_metrics=strong_mom,
            volatility_metrics=high_volatility,
            relative_strength=strong_relative_strength,
            liquidity_metrics=high_liquidity,
        )

        scorer.analyze_asset(
            asset='LOW_MOM',
            momentum_metrics=weak_mom,
            volatility_metrics=high_volatility,
            relative_strength=strong_relative_strength,
            liquidity_metrics=high_liquidity,
        )

        high_mom = scorer.get_high_momentum_assets(threshold=70)
        assert len(high_mom) >= 1
        assert any(asset == 'HIGH_MOM' for asset, _ in high_mom)

    def test_multi_asset_support(
        self, scorer, strong_momentum, high_volatility,
        strong_relative_strength, high_liquidity
    ):
        """Test analysis of multiple assets."""
        for asset in ['ASSET_1', 'ASSET_2', 'ASSET_3']:
            scorer.analyze_asset(
                asset=asset,
                momentum_metrics=strong_momentum,
                volatility_metrics=high_volatility,
                relative_strength=strong_relative_strength,
                liquidity_metrics=high_liquidity,
            )

        assert len(scorer.results) == 3
