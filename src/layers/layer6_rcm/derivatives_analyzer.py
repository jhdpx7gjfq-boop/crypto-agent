"""Derivatives Analyzer for Phase 6 RCM/RPM.

Analyzes funding rates, open interest, and options flows.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class FundingRateMetrics:
    """Funding rate analysis."""

    current_funding: float  # % per 8h (can be negative)
    funding_7d_avg: float  # Average over 7 days
    funding_trend: str  # "rising", "stable", "falling"
    funding_volatility: float  # Std dev of funding rate
    historical_extremes: bool  # True if current is extreme
    score: float  # 0-100


@dataclass
class OpenInterestAnalysis:
    """Open interest metrics."""

    total_oi: float  # Total OI in notional USD
    oi_7d_change: float  # % change
    oi_concentration: float  # % held by top 10 addresses
    long_oi: float  # Long positions in notional
    short_oi: float  # Short positions in notional
    imbalance_ratio: float  # Long / Short
    score: float  # 0-100


@dataclass
class LiquidationRiskMetrics:
    """Liquidation cascade analysis."""

    liquidation_price_long: float  # Price at which longs liquidate
    liquidation_price_short: float  # Price at which shorts liquidate
    estimated_cascade_volume: float  # Estimated liquidation volume
    cascade_likelihood: float  # 0-1 probability
    distance_to_cascade_pct: float  # % distance from current price
    score: float  # 0-100


@dataclass
class DerivativesAnalysis:
    """Complete derivatives market analysis."""

    asset: str
    timestamp: datetime
    funding_rates: FundingRateMetrics
    open_interest: OpenInterestAnalysis
    liquidation_risk: LiquidationRiskMetrics
    derivatives_score: float  # Weighted 0-100
    market_structure: str  # "bullish", "bearish", "neutral"
    leverage_regime: str  # "extreme_long", "balanced", "extreme_short"


class DerivativesAnalyzer:
    """Analyzes derivatives market structure and risk."""

    def __init__(self):
        """Initialize analyzer."""
        self.analysis_history: Dict[str, list] = {}

    def analyze_derivatives(
        self,
        asset: str,
        funding_data: Dict,
        oi_data: Dict,
        liquidation_data: Dict,
    ) -> DerivativesAnalysis:
        """
        Analyze derivatives market structure.

        Args:
            asset: Asset symbol
            funding_data: {current_funding, avg_7d, trend, volatility}
            oi_data: {total_oi, oi_change_7d, concentration, long_oi, short_oi}
            liquidation_data: {liquidation_prices, estimated_volume, likelihood}

        Returns:
            DerivativesAnalysis with component scores
        """
        funding = self._analyze_funding_rates(funding_data)
        oi = self._analyze_open_interest(oi_data)
        liquidation = self._analyze_liquidation_risk(liquidation_data)

        # Calculate weighted score
        derivatives_score = (
            funding.score * 0.35 + oi.score * 0.35 + liquidation.score * 0.30
        )
        derivatives_score = min(100, max(0, derivatives_score))

        # Determine market structure
        market_struct = self._determine_market_structure(funding, oi)

        # Determine leverage regime
        leverage = self._determine_leverage_regime(oi, liquidation)

        analysis = DerivativesAnalysis(
            asset=asset,
            timestamp=datetime.utcnow(),
            funding_rates=funding,
            open_interest=oi,
            liquidation_risk=liquidation,
            derivatives_score=derivatives_score,
            market_structure=market_struct,
            leverage_regime=leverage,
        )

        # Track history
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append(analysis)

        return analysis

    def _analyze_funding_rates(self, funding_data: Dict) -> FundingRateMetrics:
        """Analyze funding rate levels and trends."""
        current = funding_data.get("current_funding", 0)
        avg_7d = funding_data.get("funding_7d_avg", 0)
        prev_funding = funding_data.get("previous_funding", current)
        volatility = funding_data.get("funding_volatility", 0.02)

        # Determine trend
        if current > prev_funding:
            trend = "rising"
        elif current < prev_funding:
            trend = "falling"
        else:
            trend = "stable"

        # Determine if extreme
        is_extreme = abs(current) > 0.15

        # Score based on funding level
        # Moderate positive funding (0.05-0.15) is healthy bullish
        if 0.05 <= current <= 0.15:
            score = 75  # Healthy bullish
        # Very high positive funding signals reversal risk
        elif current > 0.15:
            score = max(0, 70 - ((current - 0.15) * 100))
        # Neutral funding
        elif -0.05 <= current < 0.05:
            score = 50
        # Bearish funding
        elif -0.15 <= current < -0.05:
            score = 35
        # Extreme bearish
        else:
            score = max(0, 30 + (current * 100))

        # Adjust for volatility
        if volatility > 0.05:
            score = max(0, score - 10)

        return FundingRateMetrics(
            current_funding=current,
            funding_7d_avg=avg_7d,
            funding_trend=trend,
            funding_volatility=volatility,
            historical_extremes=is_extreme,
            score=max(0, min(100, score)),
        )

    def _analyze_open_interest(self, oi_data: Dict) -> OpenInterestAnalysis:
        """Analyze open interest structure."""
        total_oi = oi_data.get("total_oi", 0)
        oi_change = oi_data.get("oi_change_7d", 0)
        concentration = oi_data.get("concentration", 30)
        long_oi = oi_data.get("long_oi", 0)
        short_oi = oi_data.get("short_oi", 0)

        # Calculate imbalance
        if short_oi > 0:
            imbalance = long_oi / short_oi
        else:
            imbalance = 2.0 if long_oi > 0 else 1.0

        # Score based on OI change and structure
        # Growing OI is bullish
        if oi_change > 30:
            score = min(100, 75 + (oi_change - 30) * 0.5)
        elif oi_change > 15:
            score = 70 + (oi_change - 15)
        elif oi_change > 0:
            score = 60 + (oi_change * 2)
        # Declining OI suggests uncertainty
        elif oi_change > -15:
            score = 50 + (oi_change)
        else:
            score = max(0, 40 + (oi_change))

        # Imbalance affects score
        # Extreme long (>1.8) suggests reversal risk
        if imbalance > 1.8:
            score = max(0, score - 15)
        # Extreme short (<0.6) also suggests risk
        elif imbalance < 0.6:
            score = max(0, score - 10)
        # Balanced is good
        elif 0.9 <= imbalance <= 1.1:
            score = min(100, score + 10)

        # High concentration = risk
        if concentration > 50:
            score = max(0, score - 15)

        return OpenInterestAnalysis(
            total_oi=total_oi,
            oi_7d_change=oi_change,
            oi_concentration=concentration,
            long_oi=long_oi,
            short_oi=short_oi,
            imbalance_ratio=imbalance,
            score=max(0, min(100, score)),
        )

    def _analyze_liquidation_risk(
        self, liquidation_data: Dict
    ) -> LiquidationRiskMetrics:
        """Analyze liquidation cascade risk."""
        long_liq = liquidation_data.get("liquidation_price_long", 0)
        short_liq = liquidation_data.get("liquidation_price_short", 0)
        cascade_vol = liquidation_data.get("estimated_cascade_volume", 0)
        cascade_likelihood = liquidation_data.get("cascade_likelihood", 0.3)
        distance = liquidation_data.get("distance_to_cascade_pct", 10)

        # Score inversely to cascade risk
        # High likelihood of cascade = low score
        if cascade_likelihood > 0.7:
            score = max(0, 30 - (cascade_likelihood * 30))
        # Moderate risk
        elif cascade_likelihood > 0.4:
            score = max(0, 50 - (cascade_likelihood * 30))
        # Low risk
        else:
            score = min(100, 70 - (cascade_likelihood * 30))

        # Close distance to cascade = higher risk
        if distance < 3:
            score = max(0, score - 25)
        elif distance < 5:
            score = max(0, score - 15)
        elif distance > 20:
            score = min(100, score + 10)

        # Large cascade volume = more severe if it happens
        if cascade_vol > 500_000_000:
            score = max(0, score - 10)

        return LiquidationRiskMetrics(
            liquidation_price_long=long_liq,
            liquidation_price_short=short_liq,
            estimated_cascade_volume=cascade_vol,
            cascade_likelihood=cascade_likelihood,
            distance_to_cascade_pct=distance,
            score=max(0, min(100, score)),
        )

    def _determine_market_structure(
        self, funding: FundingRateMetrics, oi: OpenInterestAnalysis
    ) -> str:
        """Determine if market is bullish, bearish, or neutral."""
        funding_bullish = funding.current_funding > 0.05
        funding_bearish = funding.current_funding < -0.05
        oi_bullish = oi.imbalance_ratio > 1.2
        oi_bearish = oi.imbalance_ratio < 0.8

        bullish_signals = sum([funding_bullish, oi_bullish])
        bearish_signals = sum([funding_bearish, oi_bearish])

        if bullish_signals > bearish_signals:
            return "bullish"
        elif bearish_signals > bullish_signals:
            return "bearish"
        else:
            return "neutral"

    def _determine_leverage_regime(
        self, oi: OpenInterestAnalysis, liquidation: LiquidationRiskMetrics
    ) -> str:
        """Determine if market is over-leveraged long, short, or balanced."""
        imbalance = oi.imbalance_ratio

        if imbalance > 1.5:
            return "extreme_long"
        elif imbalance > 1.1:
            return "long_bias"
        elif imbalance < 0.7:
            return "extreme_short"
        elif imbalance < 0.9:
            return "short_bias"
        else:
            return "balanced"

    def audit_derivatives(self, asset: str) -> Dict:
        """Audit derivatives analysis history."""
        if asset not in self.analysis_history:
            return {
                "asset": asset,
                "analyses": 0,
                "avg_score": 0.0,
                "current_structure": "unknown",
            }

        history = self.analysis_history[asset]
        scores = [a.derivatives_score for a in history]

        return {
            "asset": asset,
            "analyses": len(history),
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "latest_score": scores[-1] if scores else 0.0,
            "current_structure": history[-1].market_structure if history else "unknown",
            "current_leverage": history[-1].leverage_regime if history else "unknown",
        }
