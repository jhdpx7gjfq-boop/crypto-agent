"""Relative Strength Analyzer for Phase 6 RCM/RPM Engine.

Measures sector momentum vs. BTC/market and identifies outperformance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import statistics


@dataclass
class MomentumMetrics:
    """Asset momentum metrics."""

    asset: str
    price_change_7d: float  # % change over 7 days
    price_change_30d: float  # % change over 30 days
    volatility_7d: float  # Standard deviation
    trend_direction: str  # "up", "down", "neutral"
    momentum_score: float  # 0-100


@dataclass
class OutperformanceAnalysis:
    """Outperformance vs. benchmark."""

    asset: str
    benchmark: str  # Usually "BTC"
    outperformance_ratio: float  # Asset gain / BTC gain
    outperformance_pct: float  # (Asset - BTC) / BTC * 100
    relative_volatility: float  # Asset volatility / BTC volatility
    win_streak: int  # Consecutive days outperforming
    consistency_score: float  # 0-100 (how consistent the outperformance)


@dataclass
class SectorMomentum:
    """Sector-level momentum analysis."""

    sector: str
    top_performer: str  # Best performing asset in sector
    top_performer_score: float  # 0-100
    avg_sector_performance: float  # % change
    sector_participation_rate: float  # % of assets in sector outperforming
    sector_momentum_score: float  # 0-100


@dataclass
class RelativeStrengthAnalysis:
    """Complete relative strength analysis."""

    asset: str
    timestamp: datetime
    asset_momentum: MomentumMetrics
    vs_btc: OutperformanceAnalysis
    vs_market: OutperformanceAnalysis
    sector_context: Optional[SectorMomentum]
    relative_strength_score: float  # 0-100 (weighted)
    momentum_direction: str  # "accelerating", "stable", "decelerating"
    composite_rank: int  # Rank among analyzed assets (1=best)


class RelativeStrengthAnalyzer:
    """Analyzes momentum and outperformance vs. benchmarks."""

    def __init__(self):
        """Initialize analyzer."""
        self.analysis_history: Dict[str, List[RelativeStrengthAnalysis]] = {}
        self.asset_rankings: Dict[str, int] = {}

    def analyze_relative_strength(
        self,
        asset: str,
        price_data: Dict,
        benchmark_btc: Dict,
        market_avg: Dict,
        sector_data: Optional[Dict] = None,
    ) -> RelativeStrengthAnalysis:
        """
        Analyze asset momentum vs. benchmarks.

        Args:
            asset: Asset symbol
            price_data: {price_change_7d, price_change_30d, volatility_7d}
            benchmark_btc: BTC price and momentum data
            market_avg: Market average metrics
            sector_data: Optional sector context

        Returns:
            RelativeStrengthAnalysis with component scores
        """
        # Analyze asset momentum
        asset_mom = self._analyze_momentum(asset, price_data)

        # Analyze vs. BTC
        btc_mom = self._analyze_momentum("BTC", benchmark_btc)
        vs_btc = self._analyze_outperformance(
            asset, asset_mom, "BTC", btc_mom
        )

        # Analyze vs. market
        market_mom = self._analyze_momentum("MARKET", market_avg)
        vs_market = self._analyze_outperformance(
            asset, asset_mom, "MARKET", market_mom
        )

        # Sector context
        sector = None
        if sector_data:
            sector = self._analyze_sector_momentum(
                asset, sector_data, asset_mom
            )

        # Calculate weighted score
        rs_score = (
            asset_mom.momentum_score * 0.30
            + vs_btc.consistency_score * 0.35
            + vs_market.consistency_score * 0.25
            + (
                sector.sector_momentum_score * 0.10
                if sector
                else 50 * 0.10
            )
        )
        rs_score = min(100, max(0, rs_score))

        # Determine momentum direction
        momentum_dir = self._determine_momentum_direction(
            asset_mom, vs_btc, vs_market
        )

        analysis = RelativeStrengthAnalysis(
            asset=asset,
            timestamp=datetime.utcnow(),
            asset_momentum=asset_mom,
            vs_btc=vs_btc,
            vs_market=vs_market,
            sector_context=sector,
            relative_strength_score=rs_score,
            momentum_direction=momentum_dir,
            composite_rank=1,  # Will be set by ranking function
        )

        # Track history
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append(analysis)

        return analysis

    def _analyze_momentum(self, asset: str, price_data: Dict) -> MomentumMetrics:
        """Analyze price momentum metrics."""
        change_7d = price_data.get("price_change_7d", 0)
        change_30d = price_data.get("price_change_30d", 0)
        volatility = price_data.get("volatility_7d", 0)

        # Determine trend direction
        if change_7d > 5:
            trend = "up"
        elif change_7d < -5:
            trend = "down"
        else:
            trend = "neutral"

        # Calculate momentum score
        if change_7d > 20:
            score = min(100, 80 + (change_7d - 20) * 0.5)
        elif change_7d > 10:
            score = min(100, 70 + (change_7d - 10) * 1.0)
        elif change_7d > 0:
            score = 50 + (change_7d * 2)
        elif change_7d > -10:
            score = 40 + (change_7d)
        else:
            score = max(0, 30 + (change_7d * 0.5))

        # Adjust for volatility (higher volatility = higher risk/reward)
        if volatility > 5:
            score = min(100, score + (volatility * 2))

        return MomentumMetrics(
            asset=asset,
            price_change_7d=change_7d,
            price_change_30d=change_30d,
            volatility_7d=volatility,
            trend_direction=trend,
            momentum_score=max(0, min(100, score)),
        )

    def _analyze_outperformance(
        self,
        asset: str,
        asset_mom: MomentumMetrics,
        benchmark: str,
        benchmark_mom: MomentumMetrics,
    ) -> OutperformanceAnalysis:
        """Analyze outperformance vs. benchmark."""
        asset_7d = asset_mom.price_change_7d
        bench_7d = benchmark_mom.price_change_7d

        # Calculate outperformance
        if bench_7d != 0:
            ratio = asset_7d / bench_7d if asset_7d != 0 else 0
            outperf_pct = ((asset_7d - bench_7d) / abs(bench_7d)) * 100
        else:
            ratio = 1.0 if asset_7d == 0 else (2.0 if asset_7d > 0 else 0)
            outperf_pct = asset_7d

        # Relative volatility
        if benchmark_mom.volatility_7d > 0:
            rel_vol = (
                asset_mom.volatility_7d / benchmark_mom.volatility_7d
            )
        else:
            rel_vol = 1.0

        # Count win streak (simplified)
        win_streak = 7 if asset_7d > bench_7d else 0

        # Consistency score
        if asset_7d > bench_7d * 1.2:
            consistency = min(100, 75 + (outperf_pct * 0.5))
        elif asset_7d > bench_7d:
            consistency = min(100, 60 + (outperf_pct))
        elif asset_7d > 0:
            consistency = 40
        else:
            consistency = max(0, 30 + (asset_7d * 2))

        return OutperformanceAnalysis(
            asset=asset,
            benchmark=benchmark,
            outperformance_ratio=max(0, min(3.0, ratio)),
            outperformance_pct=outperf_pct,
            relative_volatility=rel_vol,
            win_streak=win_streak,
            consistency_score=max(0, min(100, consistency)),
        )

    def _analyze_sector_momentum(
        self,
        asset: str,
        sector_data: Dict,
        asset_mom: MomentumMetrics,
    ) -> SectorMomentum:
        """Analyze sector context and leadership."""
        sector_name = sector_data.get("sector", "Unknown")
        top_perf = sector_data.get("top_performer", asset)
        top_score = sector_data.get("top_performer_score", 50)
        avg_perf = sector_data.get("avg_sector_performance", 0)
        participation = sector_data.get("sector_participation_rate", 50)

        # Asset leadership score
        if asset == top_perf:
            sector_score = 80
        elif asset_mom.momentum_score > (avg_perf + 20):
            sector_score = 70
        elif asset_mom.momentum_score > avg_perf:
            sector_score = 60
        else:
            sector_score = 40

        return SectorMomentum(
            sector=sector_name,
            top_performer=top_perf,
            top_performer_score=top_score,
            avg_sector_performance=avg_perf,
            sector_participation_rate=participation,
            sector_momentum_score=sector_score,
        )

    def _determine_momentum_direction(
        self,
        asset_mom: MomentumMetrics,
        vs_btc: OutperformanceAnalysis,
        vs_market: OutperformanceAnalysis,
    ) -> str:
        """Determine if momentum is accelerating, stable, or decelerating."""
        outperf_btc = vs_btc.outperformance_pct
        outperf_market = vs_market.outperformance_pct

        # If both outperforming and momentum is strong
        if outperf_btc > 10 and outperf_market > 10:
            return "accelerating"
        # If moderately outperforming
        elif outperf_btc > 0 or outperf_market > 0:
            return "stable"
        # If underperforming
        else:
            return "decelerating"

    def rank_assets(
        self, analyses: List[RelativeStrengthAnalysis]
    ) -> List[RelativeStrengthAnalysis]:
        """Rank assets by relative strength score."""
        ranked = sorted(
            analyses, key=lambda x: x.relative_strength_score, reverse=True
        )

        for i, analysis in enumerate(ranked, 1):
            analysis.composite_rank = i
            self.asset_rankings[analysis.asset] = i

        return ranked

    def compare_assets(
        self, assets: List[str]
    ) -> Dict[str, RelativeStrengthAnalysis]:
        """Get latest analysis for multiple assets."""
        result = {}
        for asset in assets:
            if asset in self.analysis_history:
                latest = self.analysis_history[asset][-1]
                result[asset] = latest

        return result

    def audit_relative_strength(self, asset: str) -> Dict:
        """Audit momentum history."""
        if asset not in self.analysis_history:
            return {
                "asset": asset,
                "analyses": 0,
                "avg_score": 0.0,
                "trend": "unknown",
            }

        history = self.analysis_history[asset]
        scores = [a.relative_strength_score for a in history]

        if len(scores) >= 2:
            trend = "up" if scores[-1] > scores[-2] else "down"
        else:
            trend = "unknown"

        return {
            "asset": asset,
            "analyses": len(history),
            "avg_score": statistics.mean(scores) if scores else 0.0,
            "latest_score": scores[-1] if scores else 0.0,
            "trend": trend,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "current_rank": self.asset_rankings.get(asset, 0),
        }
