"""
Narrative Detection Engine for Phase 4 Component 2.

Detects narrative trends, sector rotations, and adoption acceleration
to identify emerging investment themes.

Components:
- Sector/theme detection (AI, RWA, DeFi, Gaming, L2, Infrastructure, etc.)
- Narrative strength scoring from multiple signals
- Adoption acceleration detection (week-over-week growth)
- Capital rotation tracking
- Composite narrative score 0-100
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np


class NarrativeCategory(Enum):
    """Supported crypto narratives."""
    AI = "AI"
    RWA = "RWA"  # Real World Assets
    DEFI = "DeFi"
    GAMING = "Gaming"
    L2 = "Layer 2"
    INFRASTRUCTURE = "Infrastructure"
    PRIVACY = "Privacy"
    PAYMENTS = "Payments"
    ENERGY = "Energy"
    OTHER = "Other"


@dataclass
class AdoptionMetrics:
    """Adoption and growth metrics."""
    users: int = 0
    growth_rate: float = 0.0  # MoM or WoW percentage
    tvl: float = 0.0  # USD
    transaction_volume: float = 0.0  # Daily USD
    developer_activity: int = 0  # GitHub commits/activity
    active_addresses: int = 0


@dataclass
class SocialSignals:
    """Social media and mention metrics."""
    mention_volume: int = 0  # Total mentions in period
    sentiment_score: float = 0.5  # 0-1 scale
    twitter_volume: int = 0  # Tweets
    reddit_activity: int = 0  # Posts/comments
    discord_growth: float = 0.0  # Growth rate
    social_trend: float = 0.0  # -1 to +1 trend


@dataclass
class NarrativeSignal:
    """Individual narrative signal."""
    category: NarrativeCategory
    timestamp: str  # ISO format
    sector_strength: float  # 0-100
    adoption_trend: float  # 0-100
    social_momentum: float  # 0-100
    capital_rotation: float  # 0-100
    narrative_score: float  # 0-100 composite


@dataclass
class NarrativeScore:
    """Complete narrative analysis for an asset."""
    asset: str
    timestamp: str
    category: NarrativeCategory

    # Component scores (0-100)
    sector_strength: float
    adoption_trend: float
    social_momentum: float
    capital_rotation: float

    # Composite score
    overall_narrative_score: float

    # Signals and trends
    is_accelerating: bool  # WoW growth > threshold
    trend_direction: str  # "rising", "stable", "declining"
    key_signals: List[str] = field(default_factory=list)

    # Historical data
    prev_score: Optional[float] = None
    score_momentum: float = 0.0  # Change from previous

    def is_hot_narrative(self) -> bool:
        """Check if narrative is actively trending."""
        return self.overall_narrative_score >= 70 and self.is_accelerating

    def format_report(self) -> str:
        """Format narrative analysis as readable report."""
        return f"""
NARRATIVE ANALYSIS: {self.asset}
Category: {self.category.value}
Timestamp: {self.timestamp}

COMPONENT SCORES:
  Sector Strength:      {self.sector_strength:5.1f}%
  Adoption Trend:       {self.adoption_trend:5.1f}%
  Social Momentum:      {self.social_momentum:5.1f}%
  Capital Rotation:     {self.capital_rotation:5.1f}%

COMPOSITE NARRATIVE SCORE: {self.overall_narrative_score:.1f}%
Trend: {self.trend_direction.upper()}
Accelerating: {'Yes ↑' if self.is_accelerating else 'No'}
Momentum: {self.score_momentum:+.1f}%

KEY SIGNALS:
{chr(10).join(f"  • {sig}" for sig in self.key_signals)}
"""


class NarrativeEngine:
    """
    Detects narrative trends and emerging themes in crypto.

    Scores narratives 0-100 across 4 dimensions:
    - Sector Strength (35%): How hot is this narrative?
    - Adoption Trend (30%): Is adoption accelerating?
    - Social Momentum (20%): Mention volume and sentiment
    - Capital Rotation (15%): Capital inflows to narrative
    """

    # Narrative category definitions
    CATEGORY_KEYWORDS = {
        NarrativeCategory.AI: ['AI', 'artificial intelligence', 'GPT', 'LLM', 'neural'],
        NarrativeCategory.RWA: ['RWA', 'real world assets', 'tokenized', 'real estate', 'commodities'],
        NarrativeCategory.DEFI: ['DeFi', 'decentralized finance', 'lending', 'DEX', 'yield'],
        NarrativeCategory.GAMING: ['gaming', 'game', 'metaverse', 'NFT', 'play-to-earn'],
        NarrativeCategory.L2: ['Layer 2', 'L2', 'scaling', 'Arbitrum', 'Optimism', 'Polygon'],
        NarrativeCategory.INFRASTRUCTURE: ['infrastructure', 'blockchain', 'consensus', 'validator'],
        NarrativeCategory.PRIVACY: ['privacy', 'anonymous', 'confidential', 'zero-knowledge'],
        NarrativeCategory.PAYMENTS: ['payments', 'remittance', 'stablecoin', 'settlement'],
        NarrativeCategory.ENERGY: ['energy', 'sustainable', 'green', 'mining'],
    }

    # Thresholds for classification
    ACCELERATION_THRESHOLD = 0.15  # 15% WoW growth
    MOMENTUM_THRESHOLD = 10.0  # Score change threshold

    def __init__(self):
        """Initialize narrative engine."""
        self.results: Dict[str, NarrativeScore] = {}
        self.history: Dict[str, List[NarrativeScore]] = {}

    def analyze_narrative(
        self,
        asset: str,
        category: NarrativeCategory,
        adoption_metrics: AdoptionMetrics,
        social_signals: SocialSignals,
        market_metrics: Dict[str, float],
        timestamp: str = "2026-09-30",
    ) -> NarrativeScore:
        """
        Analyze narrative strength for an asset.

        Args:
            asset: Asset symbol
            category: Primary narrative category
            adoption_metrics: User, TVL, volume metrics
            social_signals: Social media signals
            market_metrics: Market data (market_cap, 24h_volume, price_change)
            timestamp: Analysis timestamp

        Returns:
            NarrativeScore with component breakdown
        """
        # Calculate component scores
        sector_strength = self._score_sector_strength(
            category, market_metrics
        )
        adoption_trend = self._score_adoption_trend(adoption_metrics)
        social_momentum = self._score_social_momentum(social_signals)
        capital_rotation = self._score_capital_rotation(market_metrics)

        # Composite score
        overall_score = (
            sector_strength * 0.35 +
            adoption_trend * 0.30 +
            social_momentum * 0.20 +
            capital_rotation * 0.15
        )

        # Detect acceleration
        is_accelerating = adoption_metrics.growth_rate >= self.ACCELERATION_THRESHOLD

        # Determine trend direction
        trend_direction = self._classify_trend(adoption_metrics.growth_rate)

        # Identify key signals
        key_signals = self._identify_narrative_signals(
            sector_strength,
            adoption_trend,
            social_momentum,
            capital_rotation,
            adoption_metrics,
        )

        # Calculate momentum from previous score
        prev_score = None
        score_momentum = 0.0
        if asset in self.results:
            prev_score = self.results[asset].overall_narrative_score
            score_momentum = overall_score - prev_score

        score = NarrativeScore(
            asset=asset,
            timestamp=timestamp,
            category=category,
            sector_strength=sector_strength,
            adoption_trend=adoption_trend,
            social_momentum=social_momentum,
            capital_rotation=capital_rotation,
            overall_narrative_score=overall_score,
            is_accelerating=is_accelerating,
            trend_direction=trend_direction,
            key_signals=key_signals,
            prev_score=prev_score,
            score_momentum=score_momentum,
        )

        # Store results
        self.results[asset] = score
        if asset not in self.history:
            self.history[asset] = []
        self.history[asset].append(score)

        return score

    def _score_sector_strength(
        self,
        category: NarrativeCategory,
        market_metrics: Dict[str, float],
    ) -> float:
        """Score how hot this narrative/sector is (0-100)."""
        # Base score from market cap
        market_cap = market_metrics.get('market_cap', 0)
        volume_24h = market_metrics.get('volume_24h', 0)

        # Market cap tier scoring
        if market_cap > 50e9:  # >$50B
            market_score = 85.0
        elif market_cap > 10e9:  # >$10B
            market_score = 70.0
        elif market_cap > 1e9:  # >$1B
            market_score = 55.0
        elif market_cap > 100e6:  # >$100M
            market_score = 40.0
        else:
            market_score = 20.0

        # Volume/liquidity bonus
        if volume_24h > 0:
            volume_score = min(30, (volume_24h / market_cap) * 100)
        else:
            volume_score = 0

        # Category relevance bonus (established narratives score higher)
        category_bonus = {
            NarrativeCategory.DEFI: 10,
            NarrativeCategory.L2: 10,
            NarrativeCategory.AI: 15,
            NarrativeCategory.RWA: 12,
            NarrativeCategory.INFRASTRUCTURE: 8,
            NarrativeCategory.GAMING: 5,
            NarrativeCategory.PRIVACY: 5,
            NarrativeCategory.PAYMENTS: 5,
            NarrativeCategory.ENERGY: 5,
            NarrativeCategory.OTHER: 0,
        }

        total_score = market_score + (volume_score * 0.3) + category_bonus.get(category, 0)
        return min(100, total_score)

    def _score_adoption_trend(self, metrics: AdoptionMetrics) -> float:
        """Score adoption acceleration (0-100)."""
        score = 50.0  # Baseline

        # Growth rate impact (30% of score)
        if metrics.growth_rate >= 0.50:  # 50%+ growth
            score += 30
        elif metrics.growth_rate >= 0.30:  # 30%+ growth
            score += 20
        elif metrics.growth_rate >= 0.10:  # 10%+ growth
            score += 10
        elif metrics.growth_rate < 0:  # Negative growth
            score -= 15

        # User growth impact (20%)
        if metrics.users > 5e6:  # 5M+ users
            score += 20
        elif metrics.users > 1e6:  # 1M+ users
            score += 15
        elif metrics.users > 100e3:  # 100K+ users
            score += 10

        # TVL impact (20%)
        if metrics.tvl > 1e9:  # >$1B TVL
            score += 20
        elif metrics.tvl > 100e6:  # >$100M TVL
            score += 15
        elif metrics.tvl > 10e6:  # >$10M TVL
            score += 10

        # Transaction volume impact (15%)
        if metrics.transaction_volume > 100e6:  # >$100M daily
            score += 15
        elif metrics.transaction_volume > 10e6:  # >$10M daily
            score += 10
        elif metrics.transaction_volume > 1e6:  # >$1M daily
            score += 5

        # Developer activity (15%)
        if metrics.developer_activity > 500:
            score += 15
        elif metrics.developer_activity > 100:
            score += 10
        elif metrics.developer_activity > 10:
            score += 5

        return min(100, max(0, score))

    def _score_social_momentum(self, signals: SocialSignals) -> float:
        """Score social media momentum (0-100)."""
        score = 50.0  # Baseline

        # Mention volume (40%)
        if signals.mention_volume > 10000:
            score += 40
        elif signals.mention_volume > 5000:
            score += 30
        elif signals.mention_volume > 1000:
            score += 20
        elif signals.mention_volume > 100:
            score += 10

        # Sentiment (30%)
        sentiment_component = (signals.sentiment_score - 0.5) * 2 * 30
        score += sentiment_component

        # Social trend (20%)
        trend_component = signals.social_trend * 20
        score += trend_component

        # Discord/community growth (10%)
        if signals.discord_growth > 0.30:  # 30%+ growth
            score += 10
        elif signals.discord_growth > 0.10:  # 10%+ growth
            score += 5

        return min(100, max(0, score))

    def _score_capital_rotation(self, market_metrics: Dict[str, float]) -> float:
        """Score capital flow into narrative (0-100)."""
        score = 50.0  # Baseline

        # Price momentum (40%)
        price_change = market_metrics.get('price_change_24h', 0)
        if price_change > 0.15:  # +15% in 24h
            score += 30
        elif price_change > 0.05:  # +5% in 24h
            score += 15
        elif price_change < -0.10:  # -10% in 24h
            score -= 20

        # Volume surge (30%)
        volume_ratio = market_metrics.get('volume_to_mcap_ratio', 0)
        if volume_ratio > 0.5:  # 50%+ daily volume
            score += 30
        elif volume_ratio > 0.2:  # 20%+ daily volume
            score += 15
        elif volume_ratio > 0.1:  # 10%+ daily volume
            score += 5

        # Inflow indicator (30%)
        inflow_indicator = market_metrics.get('inflow_indicator', 0)
        if inflow_indicator > 0.6:  # Strong inflow
            score += 25
        elif inflow_indicator > 0.3:  # Moderate inflow
            score += 12
        elif inflow_indicator < -0.3:  # Strong outflow
            score -= 20

        return min(100, max(0, score))

    def _classify_trend(self, growth_rate: float) -> str:
        """Classify trend direction."""
        if growth_rate >= 0.15:  # 15%+ growth
            return "rising"
        elif growth_rate >= -0.05:  # -5% to +15%
            return "stable"
        else:
            return "declining"

    def _identify_narrative_signals(
        self,
        sector: float,
        adoption: float,
        social: float,
        capital: float,
        metrics: AdoptionMetrics,
    ) -> List[str]:
        """Identify key narrative signals."""
        signals = []

        if sector >= 75:
            signals.append("Sector narrative at peak strength")
        elif sector >= 60:
            signals.append("Sector narrative gaining traction")

        if adoption >= 75:
            signals.append("Adoption accelerating strongly")
        elif adoption >= 60:
            signals.append("Adoption metrics improving")

        if social >= 75:
            signals.append("Social momentum building")
        elif social >= 60:
            signals.append("Social activity elevated")

        if capital >= 75:
            signals.append("Strong capital rotation into narrative")
        elif capital >= 60:
            signals.append("Capital flowing into sector")

        if metrics.growth_rate >= 0.50:
            signals.append(f"Explosive growth: {metrics.growth_rate*100:.0f}% WoW")

        if metrics.users > 1e6:
            signals.append(f"Large user base: {metrics.users/1e6:.1f}M users")

        if metrics.tvl > 100e6:
            signals.append(f"Significant TVL: ${metrics.tvl/1e9:.2f}B")

        return signals if signals else ["Narrative metrics within normal range"]

    def get_report(self, asset: str) -> Optional[str]:
        """Get formatted narrative report for asset."""
        if asset not in self.results:
            return None

        return self.results[asset].format_report()

    def get_hot_narratives(self, threshold: float = 70.0) -> List[Tuple[str, float]]:
        """Get narratives scoring above threshold."""
        hot = [
            (asset, score.overall_narrative_score)
            for asset, score in self.results.items()
            if score.is_hot_narrative()
        ]
        return sorted(hot, key=lambda x: x[1], reverse=True)

    def get_narrative_by_category(
        self, category: NarrativeCategory
    ) -> List[Tuple[str, float]]:
        """Get all assets in a narrative category."""
        assets = [
            (asset, score.overall_narrative_score)
            for asset, score in self.results.items()
            if score.category == category
        ]
        return sorted(assets, key=lambda x: x[1], reverse=True)
