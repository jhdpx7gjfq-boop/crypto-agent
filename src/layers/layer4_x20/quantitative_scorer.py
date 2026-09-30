"""
Quantitative Scorer for Phase 4 Component 3.

Analyzes technical metrics: momentum, volatility, relative strength, and liquidity.
Scores 0-100 based on multiple quantitative dimensions.

Components:
- Momentum metrics (RSI, price structure, breakout readiness)
- Volatility analysis (recent vs historical)
- Relative strength (vs sector/top 10)
- Liquidity assessment (volume, bid-ask spread)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np


class VolumeClassification(Enum):
    """Volume classification."""
    VERY_HIGH = "Very High"  # >$100M daily
    HIGH = "High"  # >$10M daily
    MODERATE = "Moderate"  # >$1M daily
    LOW = "Low"  # <$1M daily


class VolatilityProfile(Enum):
    """Asset volatility profile."""
    EXPLOSIVE = "Explosive"  # >50% recent volatility
    HIGH = "High"  # 20-50%
    NORMAL = "Normal"  # 10-20%
    LOW = "Low"  # <10%


@dataclass
class MomentumMetrics:
    """Momentum and price action metrics."""
    rsi_14: float = 50.0  # RSI 14-period (0-100)
    rsi_strength: float = 0.0  # RSI distance from 50
    macd_value: float = 0.0  # MACD histogram
    macd_positive: bool = True  # MACD above signal
    price_position: float = 0.5  # Position in 52w range (0-1)
    price_above_ma_20: bool = True  # Price vs 20-day MA
    price_above_ma_50: bool = True  # Price vs 50-day MA
    price_above_ma_200: bool = False  # Price vs 200-day MA
    breakout_readiness: float = 0.5  # 0-1, proximity to breakout
    strength_bars: int = 0  # Consecutive up/down bars


@dataclass
class VolatilityMetrics:
    """Volatility assessment metrics."""
    volatility_recent: float = 0.20  # Last 30 days
    volatility_historical: float = 0.25  # Last 1 year
    volatility_ratio: float = 0.80  # Recent / Historical
    average_true_range: float = 0.0  # ATR
    beta: float = 1.0  # Relative to BTC
    sharpe_ratio: float = 0.0  # Risk-adjusted return


@dataclass
class RelativeStrengthMetrics:
    """Relative strength vs peer assets."""
    outperformance_vs_top10: float = 0.0  # % outperformance
    rs_line_trend: float = 0.0  # -1 to +1 RS trend
    sector_percentile: float = 0.5  # Rank in sector (0-1)
    correlation_to_btc: float = 0.7  # BTC correlation
    alpha: float = 0.0  # Excess return vs sector


@dataclass
class LiquidityMetrics:
    """Liquidity assessment."""
    volume_24h: float = 0.0  # USD volume
    bid_ask_spread: float = 0.01  # Spread %
    volume_classification: VolumeClassification = VolumeClassification.LOW
    order_book_depth: float = 0.0  # Orders at 2% (both sides)
    exchange_diversity: int = 1  # Number of exchanges
    slippage_estimate_1pct: float = 0.0  # Slippage for 1% volume


@dataclass
class QuantitativeScore:
    """Complete quantitative analysis for an asset."""
    asset: str
    timestamp: str

    # Component scores (0-100)
    momentum_score: float
    volatility_score: float
    relative_strength_score: float
    liquidity_score: float

    # Composite score
    overall_quantitative_score: float

    # Profiles
    volatility_profile: VolatilityProfile
    volume_classification: VolumeClassification

    # Risk/reward indicators
    risk_rating: str  # "Very High", "High", "Moderate", "Low"
    reward_potential: str  # "High", "Moderate", "Low"
    risk_reward_ratio: float  # Reward / Risk

    # Technical signals
    bullish_signals: List[str] = field(default_factory=list)
    bearish_signals: List[str] = field(default_factory=list)
    neutral_signals: List[str] = field(default_factory=list)

    # Liquidity checks
    passes_liquidity_test: bool = True

    def format_report(self) -> str:
        """Format quantitative analysis as readable report."""
        return f"""
QUANTITATIVE ANALYSIS: {self.asset}
Timestamp: {self.timestamp}

COMPONENT SCORES:
  Momentum:           {self.momentum_score:5.1f}%
  Volatility:         {self.volatility_score:5.1f}%
  Relative Strength:  {self.relative_strength_score:5.1f}%
  Liquidity:          {self.liquidity_score:5.1f}%

COMPOSITE QUANTITATIVE SCORE: {self.overall_quantitative_score:.1f}%

PROFILE:
  Volatility:       {self.volatility_profile.value}
  Volume:           {self.volume_classification.value}
  Risk Rating:      {self.risk_rating}
  Reward Potential: {self.reward_potential}
  Risk/Reward:      {self.risk_reward_ratio:.2f}x

TECHNICAL SIGNALS:
Bullish ({len(self.bullish_signals)}):
{chr(10).join(f"  ✓ {sig}" for sig in self.bullish_signals) if self.bullish_signals else "  None"}

Bearish ({len(self.bearish_signals)}):
{chr(10).join(f"  ✗ {sig}" for sig in self.bearish_signals) if self.bearish_signals else "  None"}

Neutral ({len(self.neutral_signals)}):
{chr(10).join(f"  ~ {sig}" for sig in self.neutral_signals) if self.neutral_signals else "  None"}

Liquidity Check: {'PASS ✓' if self.passes_liquidity_test else 'FAIL ✗'}
"""


class QuantitativeScorer:
    """
    Scores assets on quantitative metrics.

    Components:
    - Momentum (40%): RSI, MACD, price structure, breakout readiness
    - Volatility (25%): Recent vs historical, ATR, beta
    - Relative Strength (20%): Outperformance vs sector/top 10
    - Liquidity (15%): Trading volume, bid-ask spread, order book depth
    """

    # Minimum liquidity requirement ($1M daily volume)
    MIN_VOLUME_REQUIREMENT = 1e6

    # Momentum thresholds
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70

    # Volatility classification thresholds
    VOLATILITY_EXPLOSIVE = 0.50
    VOLATILITY_HIGH = 0.20
    VOLATILITY_NORMAL = 0.10

    def __init__(self):
        """Initialize quantitative scorer."""
        self.results: Dict[str, QuantitativeScore] = {}

    def analyze_asset(
        self,
        asset: str,
        momentum_metrics: MomentumMetrics,
        volatility_metrics: VolatilityMetrics,
        relative_strength: RelativeStrengthMetrics,
        liquidity_metrics: LiquidityMetrics,
        timestamp: str = "2026-09-30",
    ) -> QuantitativeScore:
        """
        Analyze quantitative metrics for an asset.

        Args:
            asset: Asset symbol
            momentum_metrics: Price momentum and RSI/MACD
            volatility_metrics: Volatility analysis
            relative_strength: Performance vs peers
            liquidity_metrics: Volume and bid-ask metrics
            timestamp: Analysis timestamp

        Returns:
            QuantitativeScore with component breakdown
        """
        # Calculate component scores
        momentum_score = self._score_momentum(momentum_metrics)
        volatility_score = self._score_volatility(volatility_metrics)
        relative_strength_score = self._score_relative_strength(relative_strength)
        liquidity_score = self._score_liquidity(liquidity_metrics)

        # Composite score
        overall_score = (
            momentum_score * 0.40 +
            volatility_score * 0.25 +
            relative_strength_score * 0.20 +
            liquidity_score * 0.15
        )

        # Classify volatility profile
        volatility_profile = self._classify_volatility(volatility_metrics.volatility_recent)

        # Classify volume
        volume_classification = liquidity_metrics.volume_classification

        # Risk/reward assessment
        risk_rating = self._classify_risk(volatility_metrics.volatility_recent)
        reward_potential = self._classify_reward(momentum_score, relative_strength_score)
        risk_reward_ratio = self._calculate_risk_reward_ratio(
            risk_rating, reward_potential
        )

        # Identify signals
        bullish_signals = self._identify_bullish_signals(
            momentum_metrics, volatility_metrics, relative_strength
        )
        bearish_signals = self._identify_bearish_signals(
            momentum_metrics, volatility_metrics, relative_strength
        )
        neutral_signals = self._identify_neutral_signals(
            liquidity_metrics, volatility_metrics
        )

        # Check liquidity requirement
        passes_liquidity_test = (
            liquidity_metrics.volume_24h >= self.MIN_VOLUME_REQUIREMENT
        )

        score = QuantitativeScore(
            asset=asset,
            timestamp=timestamp,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            relative_strength_score=relative_strength_score,
            liquidity_score=liquidity_score,
            overall_quantitative_score=overall_score,
            volatility_profile=volatility_profile,
            volume_classification=volume_classification,
            risk_rating=risk_rating,
            reward_potential=reward_potential,
            risk_reward_ratio=risk_reward_ratio,
            bullish_signals=bullish_signals,
            bearish_signals=bearish_signals,
            neutral_signals=neutral_signals,
            passes_liquidity_test=passes_liquidity_test,
        )

        self.results[asset] = score
        return score

    def _score_momentum(self, metrics: MomentumMetrics) -> float:
        """Score momentum (0-100)."""
        score = 50.0  # Baseline

        # RSI component (40%)
        if metrics.rsi_14 < self.RSI_OVERSOLD:  # <30
            rsi_score = 20.0  # Oversold
        elif metrics.rsi_14 < 40:
            rsi_score = 30.0
        elif metrics.rsi_14 < 50:
            rsi_score = 45.0
        elif metrics.rsi_14 < 60:
            rsi_score = 55.0
        elif metrics.rsi_14 < 70:
            rsi_score = 70.0
        else:  # >70
            rsi_score = 85.0  # Overbought but strong

        # MACD component (30%)
        macd_score = 50.0
        if metrics.macd_positive:
            macd_score = 60.0
            if metrics.macd_value > 0:
                macd_score = min(85, 60 + abs(metrics.macd_value) * 100)
        else:
            macd_score = 40.0
            if metrics.macd_value < 0:
                macd_score = max(15, 40 - abs(metrics.macd_value) * 100)

        # Price structure component (30%)
        structure_score = 50.0
        ma_count = sum([
            metrics.price_above_ma_20,
            metrics.price_above_ma_50,
            metrics.price_above_ma_200,
        ])

        if ma_count == 3:  # Above all MAs
            structure_score = 85.0
        elif ma_count == 2:  # Above 2 of 3
            structure_score = 70.0
        elif ma_count == 1:  # Above 1 of 3
            structure_score = 50.0
        else:  # Below all MAs
            structure_score = 25.0

        # Position in range bonus
        if metrics.price_position > 0.75:
            structure_score += 10  # Near highs
        elif metrics.price_position < 0.25:
            structure_score -= 10  # Near lows

        # Breakout readiness bonus
        if metrics.breakout_readiness > 0.75:
            structure_score += 5

        momentum_score = (rsi_score * 0.40) + (macd_score * 0.30) + (structure_score * 0.30)
        return min(100, max(0, momentum_score))

    def _score_volatility(self, metrics: VolatilityMetrics) -> float:
        """Score volatility assessment (0-100)."""
        score = 50.0  # Baseline

        # Volatility ratio (40%) - recent vs historical
        if metrics.volatility_ratio > 1.5:  # Recent >> Historical
            score += 25  # High opportunity
        elif metrics.volatility_ratio > 1.2:
            score += 15
        elif metrics.volatility_ratio > 0.9:
            score += 5  # Slightly elevated
        elif metrics.volatility_ratio < 0.7:
            score -= 15  # Low opportunity

        # Recent volatility level (35%)
        if metrics.volatility_recent > self.VOLATILITY_EXPLOSIVE:
            score += 20  # Explosive moves
        elif metrics.volatility_recent > self.VOLATILITY_HIGH:
            score += 12  # High opportunity
        elif metrics.volatility_recent > self.VOLATILITY_NORMAL:
            score += 0  # Normal range
        else:
            score -= 10  # Low volatility

        # Beta component (15%) - risk relative to BTC
        if metrics.beta < 0.8:
            score += 10  # Lower risk
        elif metrics.beta < 1.2:
            score += 5  # Reasonable
        elif metrics.beta < 1.5:
            score -= 5  # Higher risk
        else:
            score -= 15  # Highly volatile

        # Sharpe ratio (10%) - risk-adjusted return
        if metrics.sharpe_ratio > 1.0:
            score += 10
        elif metrics.sharpe_ratio > 0:
            score += 5
        elif metrics.sharpe_ratio < -1.0:
            score -= 10

        return min(100, max(0, score))

    def _score_relative_strength(self, metrics: RelativeStrengthMetrics) -> float:
        """Score relative strength vs sector (0-100)."""
        score = 50.0  # Baseline

        # Outperformance vs top 10 (35%)
        if metrics.outperformance_vs_top10 > 0.30:  # 30%+ outperformance
            score += 30
        elif metrics.outperformance_vs_top10 > 0.10:  # 10%+ outperformance
            score += 15
        elif metrics.outperformance_vs_top10 < -0.20:  # 20%+ underperformance
            score -= 20

        # RS line trend (25%)
        if metrics.rs_line_trend > 0.5:  # Strong uptrend
            score += 20
        elif metrics.rs_line_trend > 0:  # Uptrend
            score += 10
        elif metrics.rs_line_trend < -0.5:  # Strong downtrend
            score -= 20
        elif metrics.rs_line_trend < 0:  # Downtrend
            score -= 10

        # Sector percentile (25%)
        if metrics.sector_percentile > 0.75:  # Top 25%
            score += 20
        elif metrics.sector_percentile > 0.50:  # Top 50%
            score += 10
        elif metrics.sector_percentile < 0.25:  # Bottom 25%
            score -= 15

        # Alpha (15%) - excess return
        if metrics.alpha > 0.15:  # 15%+ alpha
            score += 12
        elif metrics.alpha < -0.15:  # -15% alpha
            score -= 10

        return min(100, max(0, score))

    def _score_liquidity(self, metrics: LiquidityMetrics) -> float:
        """Score liquidity (0-100)."""
        score = 50.0  # Baseline

        # Volume classification (40%)
        volume_scores = {
            VolumeClassification.VERY_HIGH: 85,
            VolumeClassification.HIGH: 70,
            VolumeClassification.MODERATE: 50,
            VolumeClassification.LOW: 20,
        }
        score += (volume_scores[metrics.volume_classification] - 50) * 0.40

        # Bid-ask spread (30%)
        if metrics.bid_ask_spread < 0.001:  # <0.1%
            spread_score = 85
        elif metrics.bid_ask_spread < 0.005:  # <0.5%
            spread_score = 70
        elif metrics.bid_ask_spread < 0.01:  # <1%
            spread_score = 50
        elif metrics.bid_ask_spread < 0.05:  # <5%
            spread_score = 30
        else:
            spread_score = 10

        score += (spread_score - 50) * 0.30

        # Order book depth (20%)
        if metrics.order_book_depth > 5e6:  # >$5M on each side
            depth_score = 85
        elif metrics.order_book_depth > 1e6:
            depth_score = 70
        elif metrics.order_book_depth > 100e3:
            depth_score = 50
        else:
            depth_score = 20

        score += (depth_score - 50) * 0.20

        # Exchange diversity (10%)
        if metrics.exchange_diversity >= 5:
            score += 8
        elif metrics.exchange_diversity >= 3:
            score += 4
        elif metrics.exchange_diversity < 2:
            score -= 5

        return min(100, max(0, score))

    def _classify_volatility(self, volatility: float) -> VolatilityProfile:
        """Classify volatility profile."""
        if volatility > self.VOLATILITY_EXPLOSIVE:
            return VolatilityProfile.EXPLOSIVE
        elif volatility > self.VOLATILITY_HIGH:
            return VolatilityProfile.HIGH
        elif volatility > self.VOLATILITY_NORMAL:
            return VolatilityProfile.NORMAL
        else:
            return VolatilityProfile.LOW

    def _classify_risk(self, volatility: float) -> str:
        """Classify risk level."""
        if volatility > 0.40:
            return "Very High"
        elif volatility > 0.25:
            return "High"
        elif volatility > 0.15:
            return "Moderate"
        else:
            return "Low"

    def _classify_reward(self, momentum: float, rs: float) -> str:
        """Classify reward potential."""
        avg = (momentum + rs) / 2
        if avg > 70:
            return "High"
        elif avg > 50:
            return "Moderate"
        else:
            return "Low"

    def _calculate_risk_reward_ratio(self, risk: str, reward: str) -> float:
        """Calculate risk/reward ratio."""
        risk_vals = {
            "Very High": 4.0,
            "High": 3.0,
            "Moderate": 2.0,
            "Low": 1.0,
        }
        reward_vals = {
            "High": 3.0,
            "Moderate": 2.0,
            "Low": 1.0,
        }

        return reward_vals[reward] / risk_vals[risk]

    def _identify_bullish_signals(
        self,
        momentum: MomentumMetrics,
        volatility: VolatilityMetrics,
        rs: RelativeStrengthMetrics,
    ) -> List[str]:
        """Identify bullish technical signals."""
        signals = []

        if momentum.rsi_14 < self.RSI_OVERSOLD:
            signals.append("RSI oversold (<30)")
        elif momentum.rsi_14 > 50:
            signals.append("RSI above midpoint")

        if momentum.macd_positive and momentum.macd_value > 0:
            signals.append("MACD positive and rising")

        if momentum.price_above_ma_20 and momentum.price_above_ma_50:
            signals.append("Price above 20 and 50 day MAs")

        if momentum.price_above_ma_200:
            signals.append("Price above 200 day MA (long-term uptrend)")

        if momentum.price_position > 0.75:
            signals.append("Price near 52-week highs")

        if momentum.breakout_readiness > 0.75:
            signals.append("Breakout conditions forming")

        if rs.outperformance_vs_top10 > 0.20:
            signals.append("Outperforming sector by 20%+")

        if rs.rs_line_trend > 0.5:
            signals.append("Relative strength in strong uptrend")

        if volatility.volatility_ratio > 1.3:
            signals.append("Volatility elevated vs historical")

        return signals

    def _identify_bearish_signals(
        self,
        momentum: MomentumMetrics,
        volatility: VolatilityMetrics,
        rs: RelativeStrengthMetrics,
    ) -> List[str]:
        """Identify bearish technical signals."""
        signals = []

        if momentum.rsi_14 > self.RSI_OVERBOUGHT:
            signals.append("RSI overbought (>70)")
        elif momentum.rsi_14 < 50:
            signals.append("RSI below midpoint")

        if not momentum.macd_positive or momentum.macd_value < 0:
            signals.append("MACD negative")

        if not momentum.price_above_ma_50:
            signals.append("Price below 50 day MA")

        if not momentum.price_above_ma_200:
            signals.append("Price below 200 day MA (long-term downtrend)")

        if momentum.price_position < 0.25:
            signals.append("Price near 52-week lows")

        if rs.outperformance_vs_top10 < -0.20:
            signals.append("Underperforming sector by 20%+")

        if rs.rs_line_trend < -0.5:
            signals.append("Relative strength in strong downtrend")

        if volatility.beta > 1.5:
            signals.append("High beta - more volatile than BTC")

        return signals

    def _identify_neutral_signals(
        self,
        liquidity: LiquidityMetrics,
        volatility: VolatilityMetrics,
    ) -> List[str]:
        """Identify neutral signals."""
        signals = []

        if liquidity.volume_classification == VolumeClassification.LOW:
            signals.append("Low trading volume")

        if liquidity.bid_ask_spread > 0.02:
            signals.append("Wide bid-ask spread (>2%)")

        if volatility.volatility_recent < 0.10:
            signals.append("Low volatility environment")

        if liquidity.exchange_diversity == 1:
            signals.append("Trading on single exchange only")

        return signals

    def get_report(self, asset: str) -> Optional[str]:
        """Get formatted quantitative report for asset."""
        if asset not in self.results:
            return None

        return self.results[asset].format_report()

    def get_liquid_assets(self) -> List[Tuple[str, float]]:
        """Get assets passing liquidity requirements."""
        liquid = [
            (asset, score.overall_quantitative_score)
            for asset, score in self.results.items()
            if score.passes_liquidity_test
        ]
        return sorted(liquid, key=lambda x: x[1], reverse=True)

    def get_high_momentum_assets(self, threshold: float = 70.0) -> List[Tuple[str, float]]:
        """Get assets with high momentum scores."""
        high = [
            (asset, score.momentum_score)
            for asset, score in self.results.items()
            if score.momentum_score >= threshold
        ]
        return sorted(high, key=lambda x: x[1], reverse=True)
