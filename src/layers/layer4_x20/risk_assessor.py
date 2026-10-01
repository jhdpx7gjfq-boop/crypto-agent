"""
Risk Assessment Engine for Phase 4 Component 4.

Evaluates downside risk, concentration risk, execution risk, and timeline risk.
Scores 0-100 (lower = safer).

Components:
- Drawdown risk estimation (40%)
- Concentration risk (30%)
- Execution risk (20%)
- Timeline risk (10%)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np


class RiskLevel(Enum):
    """Risk classification."""
    MINIMAL = "Minimal"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass
class DrawdownMetrics:
    """Drawdown and volatility risk metrics."""
    volatility: float = 0.20  # Annual volatility
    historical_max_drawdown: float = 0.30  # Historical peak-to-trough
    estimated_max_drawdown: float = 0.25  # Model-based estimate
    recovery_periods: List[int] = field(default_factory=list)  # Days to recover
    var_95: float = 0.0  # Value at Risk 95%


@dataclass
class ConcentrationMetrics:
    """Position concentration risk metrics."""
    position_size_pct: float = 1.0  # % of portfolio
    portfolio_allocation: float = 0.05  # Recommended max: 5%
    max_position: float = 0.10  # Hard limit: 10%
    avg_position: float = 0.05  # Typical average
    correlation_to_portfolio: float = 0.6  # How correlated to holdings
    diversification_score: float = 0.7  # 0-1, higher = more diversified


@dataclass
class ExecutionMetrics:
    """Execution and slippage risk metrics."""
    bid_ask_spread: float = 0.01  # % spread
    estimated_slippage_1pct: float = 0.05  # 1% volume slippage
    estimated_slippage_5pct: float = 0.20  # 5% volume slippage
    market_impact_factor: float = 0.001  # Impact per 1% volume
    liquidity_depth: float = 1e6  # USD at 2% depth
    venue_fragmentation: float = 0.5  # 0-1, impact of split venues


@dataclass
class TimelineMetrics:
    """Timeline and event risk metrics."""
    token_unlock_upcoming: int = 0  # Days to next unlock
    unlock_amount_pct: float = 0.0  # % of supply unlocking
    regulatory_events: int = 0  # Number of upcoming regulatory events
    days_to_key_events: List[int] = field(default_factory=list)
    unlock_schedule_concentration: float = 0.0  # Concentration of unlocks


@dataclass
class RiskScore:
    """Complete risk assessment for an asset."""
    asset: str
    timestamp: str

    # Component scores (0-100)
    drawdown_risk_score: float
    concentration_risk_score: float
    execution_risk_score: float
    timeline_risk_score: float

    # Overall risk score (0-100, lower = safer)
    overall_risk_score: float

    # Risk classification
    risk_level: RiskLevel

    # Max drawdown estimates
    estimated_max_drawdown: float  # From volatility
    historical_max_drawdown: Optional[float] = None

    # Concentration metrics
    recommended_max_position: float = 0.05
    can_safely_allocate: bool = False

    # Recovery and warnings
    recovery_time_avg: int = 0  # Average days to recover
    risk_warnings: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)

    def format_report(self) -> str:
        """Format risk assessment as readable report."""
        return f"""
RISK ASSESSMENT: {self.asset}
Timestamp: {self.timestamp}

RISK SCORE COMPONENTS:
  Drawdown Risk:       {self.drawdown_risk_score:5.1f}%
  Concentration Risk:  {self.concentration_risk_score:5.1f}%
  Execution Risk:      {self.execution_risk_score:5.1f}%
  Timeline Risk:       {self.timeline_risk_score:5.1f}%

OVERALL RISK SCORE: {self.overall_risk_score:.1f}% ({self.risk_level.value})
Estimated Max Drawdown: {self.estimated_max_drawdown*100:.1f}%
Recommended Max Position: {self.recommended_max_position*100:.1f}%
Allocation Feasible: {'Yes ✓' if self.can_safely_allocate else 'No ✗'}

RISK WARNINGS:
{chr(10).join(f"  ⚠ {warning}" for warning in self.risk_warnings) if self.risk_warnings else "  None"}

MITIGATIONS:
{chr(10).join(f"  → {mit}" for mit in self.mitigations) if self.mitigations else "  Standard position sizing"}
"""


class RiskAssessor:
    """
    Comprehensive risk assessment framework.

    Scores risk 0-100 (lower = safer) across 4 dimensions:
    - Drawdown Risk (40%): Max loss estimation from volatility
    - Concentration (30%): Position size vs portfolio
    - Execution Risk (20%): Slippage and market impact
    - Timeline Risk (10%): Unlock schedules and events
    """

    # Position sizing parameters
    MAX_POSITION_HARD_LIMIT = 0.10  # 10% max
    RECOMMENDED_MAX_POSITION = 0.05  # 5% recommended
    TYPICAL_PORTFOLIO_SIZE = 0.05  # 5% typical

    # Volatility-based drawdown estimation (historical rule of thumb)
    # Max Drawdown ~ Volatility * k-factor (typically 1.5-2.0)
    DRAWDOWN_K_FACTOR = 1.5

    def __init__(self):
        """Initialize risk assessor."""
        self.results: Dict[str, RiskScore] = {}

    def assess_risk(
        self,
        asset: str,
        drawdown_metrics: DrawdownMetrics,
        concentration_metrics: ConcentrationMetrics,
        execution_metrics: ExecutionMetrics,
        timeline_metrics: TimelineMetrics,
        timestamp: str = "2026-09-30",
    ) -> RiskScore:
        """
        Assess overall risk for an asset.

        Args:
            asset: Asset symbol
            drawdown_metrics: Volatility and drawdown data
            concentration_metrics: Position sizing risk
            execution_metrics: Slippage and market impact
            timeline_metrics: Unlock schedules and events
            timestamp: Analysis timestamp

        Returns:
            RiskScore with component breakdown
        """
        # Calculate component scores (0-100, higher = more risky)
        drawdown_risk = self._score_drawdown_risk(drawdown_metrics)
        concentration_risk = self._score_concentration_risk(concentration_metrics)
        execution_risk = self._score_execution_risk(execution_metrics)
        timeline_risk = self._score_timeline_risk(timeline_metrics)

        # Composite risk score (weighted average)
        overall_score = (
            drawdown_risk * 0.40 +
            concentration_risk * 0.30 +
            execution_risk * 0.20 +
            timeline_risk * 0.10
        )

        # Classify risk level
        risk_level = self._classify_risk_level(overall_score)

        # Estimate max drawdown
        estimated_drawdown = min(
            1.0,
            drawdown_metrics.volatility * self.DRAWDOWN_K_FACTOR
        )

        # Calculate recommended position size (inverse of risk)
        risk_adjustment = max(0.01, 1.0 - (overall_score / 100))
        recommended_max = self.RECOMMENDED_MAX_POSITION * risk_adjustment

        # Check if allocation is feasible
        can_allocate = (
            concentration_metrics.position_size_pct <= recommended_max
            and overall_score < 75
        )

        # Calculate average recovery time
        recovery_avg = int(np.mean(drawdown_metrics.recovery_periods)) if drawdown_metrics.recovery_periods else 30

        # Identify risk warnings
        warnings = self._identify_risk_warnings(
            drawdown_metrics,
            concentration_metrics,
            execution_metrics,
            timeline_metrics,
            overall_score,
        )

        # Identify mitigations
        mitigations = self._identify_mitigations(
            drawdown_metrics,
            concentration_metrics,
            execution_metrics,
            timeline_metrics,
        )

        score = RiskScore(
            asset=asset,
            timestamp=timestamp,
            drawdown_risk_score=drawdown_risk,
            concentration_risk_score=concentration_risk,
            execution_risk_score=execution_risk,
            timeline_risk_score=timeline_risk,
            overall_risk_score=overall_score,
            risk_level=risk_level,
            estimated_max_drawdown=estimated_drawdown,
            historical_max_drawdown=drawdown_metrics.historical_max_drawdown,
            recovery_time_avg=recovery_avg,
            recommended_max_position=recommended_max,
            can_safely_allocate=can_allocate,
            risk_warnings=warnings,
            mitigations=mitigations,
        )

        self.results[asset] = score
        return score

    def _score_drawdown_risk(self, metrics: DrawdownMetrics) -> float:
        """Score drawdown risk (0-100, higher = more risk)."""
        score = 50.0  # Baseline

        # Volatility component (40%)
        if metrics.volatility < 0.10:  # <10%
            vol_score = 20.0
        elif metrics.volatility < 0.15:  # 10-15%
            vol_score = 35.0
        elif metrics.volatility < 0.25:  # 15-25%
            vol_score = 50.0
        elif metrics.volatility < 0.40:  # 25-40%
            vol_score = 70.0
        else:  # >40%
            vol_score = 90.0

        score += (vol_score - 50) * 0.40

        # Historical drawdown component (40%)
        if metrics.historical_max_drawdown < 0.15:  # <15%
            hist_score = 20.0
        elif metrics.historical_max_drawdown < 0.30:  # 15-30%
            hist_score = 40.0
        elif metrics.historical_max_drawdown < 0.50:  # 30-50%
            hist_score = 60.0
        elif metrics.historical_max_drawdown < 0.70:  # 50-70%
            hist_score = 75.0
        else:  # >70%
            hist_score = 90.0

        score += (hist_score - 50) * 0.40

        # Value at Risk component (20%)
        if metrics.var_95 > 0:
            var_score = min(90, metrics.var_95 * 100)
        else:
            var_score = 50.0

        score += (var_score - 50) * 0.20

        return min(100, max(0, score))

    def _score_concentration_risk(self, metrics: ConcentrationMetrics) -> float:
        """Score concentration risk (0-100, higher = more risk)."""
        score = 50.0  # Baseline

        # Position size vs recommended (50%)
        if metrics.position_size_pct < 0.01:  # <1%
            position_score = 10.0  # Very low risk
        elif metrics.position_size_pct < 0.03:  # 1-3%
            position_score = 25.0
        elif metrics.position_size_pct < 0.05:  # 3-5%
            position_score = 40.0
        elif metrics.position_size_pct < 0.08:  # 5-8%
            position_score = 65.0
        elif metrics.position_size_pct < 0.10:  # 8-10%
            position_score = 80.0
        else:  # >10%
            position_score = 95.0

        score += (position_score - 50) * 0.50

        # Correlation to portfolio (30%)
        if metrics.correlation_to_portfolio < 0.3:  # Low correlation
            corr_score = 20.0
        elif metrics.correlation_to_portfolio < 0.6:  # Moderate
            corr_score = 45.0
        elif metrics.correlation_to_portfolio < 0.8:  # High
            corr_score = 70.0
        else:  # Very high
            corr_score = 85.0

        score += (corr_score - 50) * 0.30

        # Diversification (20%)
        if metrics.diversification_score > 0.8:  # Well diversified
            div_score = 20.0
        elif metrics.diversification_score > 0.6:  # Moderate
            div_score = 40.0
        elif metrics.diversification_score > 0.4:  # Low
            div_score = 65.0
        else:  # Concentrated
            div_score = 85.0

        score += (div_score - 50) * 0.20

        return min(100, max(0, score))

    def _score_execution_risk(self, metrics: ExecutionMetrics) -> float:
        """Score execution risk (0-100, higher = more risk)."""
        score = 50.0  # Baseline

        # Bid-ask spread (35%)
        if metrics.bid_ask_spread < 0.001:  # <0.1%
            spread_score = 10.0
        elif metrics.bid_ask_spread < 0.005:  # <0.5%
            spread_score = 25.0
        elif metrics.bid_ask_spread < 0.01:  # <1%
            spread_score = 40.0
        elif metrics.bid_ask_spread < 0.05:  # <5%
            spread_score = 65.0
        else:  # >5%
            spread_score = 90.0

        score += (spread_score - 50) * 0.35

        # Slippage for 1% volume (35%)
        if metrics.estimated_slippage_1pct < 0.01:  # <1%
            slip_score = 15.0
        elif metrics.estimated_slippage_1pct < 0.05:  # <5%
            slip_score = 35.0
        elif metrics.estimated_slippage_1pct < 0.10:  # <10%
            slip_score = 50.0
        elif metrics.estimated_slippage_1pct < 0.20:  # <20%
            slip_score = 70.0
        else:  # >20%
            slip_score = 85.0

        score += (slip_score - 50) * 0.35

        # Liquidity depth (20%)
        if metrics.liquidity_depth > 10e6:  # >$10M
            liq_score = 20.0
        elif metrics.liquidity_depth > 1e6:  # >$1M
            liq_score = 40.0
        elif metrics.liquidity_depth > 100e3:  # >$100K
            liq_score = 65.0
        else:  # <$100K
            liq_score = 85.0

        score += (liq_score - 50) * 0.20

        # Venue fragmentation (10%)
        if metrics.venue_fragmentation < 0.3:  # Concentrated on 1 venue
            frag_score = 70.0
        elif metrics.venue_fragmentation < 0.6:  # 2-3 venues
            frag_score = 45.0
        else:  # Well distributed
            frag_score = 20.0

        score += (frag_score - 50) * 0.10

        return min(100, max(0, score))

    def _score_timeline_risk(self, metrics: TimelineMetrics) -> float:
        """Score timeline risk (0-100, higher = more risk)."""
        score = 50.0  # Baseline

        # Unlock timing (50%)
        if metrics.token_unlock_upcoming == 0:  # No upcoming unlock
            unlock_score = 20.0
        elif metrics.token_unlock_upcoming > 180:  # >6 months
            unlock_score = 30.0
        elif metrics.token_unlock_upcoming > 90:  # >3 months
            unlock_score = 45.0
        elif metrics.token_unlock_upcoming > 30:  # >1 month
            unlock_score = 65.0
        else:  # <1 month
            unlock_score = 85.0

        score += (unlock_score - 50) * 0.50

        # Unlock amount (30%)
        if metrics.unlock_amount_pct == 0:
            amount_score = 20.0
        elif metrics.unlock_amount_pct < 0.05:  # <5%
            amount_score = 35.0
        elif metrics.unlock_amount_pct < 0.10:  # <10%
            amount_score = 50.0
        elif metrics.unlock_amount_pct < 0.20:  # <20%
            amount_score = 70.0
        else:  # >20%
            amount_score = 85.0

        score += (amount_score - 50) * 0.30

        # Regulatory events (20%)
        if metrics.regulatory_events == 0:
            reg_score = 30.0
        elif metrics.regulatory_events == 1:
            reg_score = 50.0
        elif metrics.regulatory_events == 2:
            reg_score = 70.0
        else:  # 3+
            reg_score = 85.0

        score += (reg_score - 50) * 0.20

        return min(100, max(0, score))

    def _classify_risk_level(self, score: float) -> RiskLevel:
        """Classify overall risk level."""
        if score < 20:
            return RiskLevel.MINIMAL
        elif score < 40:
            return RiskLevel.LOW
        elif score < 60:
            return RiskLevel.MODERATE
        elif score < 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _identify_risk_warnings(
        self,
        drawdown: DrawdownMetrics,
        concentration: ConcentrationMetrics,
        execution: ExecutionMetrics,
        timeline: TimelineMetrics,
        overall_score: float,
    ) -> List[str]:
        """Identify key risk warnings."""
        warnings = []

        if drawdown.volatility > 0.30:
            warnings.append(f"High volatility: {drawdown.volatility*100:.0f}%")

        if drawdown.historical_max_drawdown > 0.50:
            warnings.append(f"Historical drawdown: {drawdown.historical_max_drawdown*100:.0f}%")

        if concentration.position_size_pct > 0.08:
            warnings.append(f"Large position: {concentration.position_size_pct*100:.1f}% of portfolio")

        if concentration.correlation_to_portfolio > 0.75:
            warnings.append("High correlation to existing holdings")

        if execution.bid_ask_spread > 0.02:
            warnings.append(f"Wide spread: {execution.bid_ask_spread*100:.2f}%")

        if execution.estimated_slippage_1pct > 0.10:
            warnings.append(f"High slippage: {execution.estimated_slippage_1pct*100:.1f}% for 1% volume")

        if timeline.token_unlock_upcoming < 30 and timeline.unlock_amount_pct > 0.05:
            warnings.append(f"Unlock in {timeline.token_unlock_upcoming} days: {timeline.unlock_amount_pct*100:.1f}% of supply")

        if timeline.regulatory_events > 0:
            warnings.append(f"{timeline.regulatory_events} regulatory event(s) upcoming")

        if overall_score > 75:
            warnings.append("CRITICAL: Multiple high-risk factors")

        return warnings

    def _identify_mitigations(
        self,
        drawdown: DrawdownMetrics,
        concentration: ConcentrationMetrics,
        execution: ExecutionMetrics,
        timeline: TimelineMetrics,
    ) -> List[str]:
        """Suggest risk mitigations."""
        mitigations = []

        if drawdown.volatility > 0.25:
            mitigations.append("Use limit orders to reduce slippage")

        if concentration.position_size_pct > 0.07:
            mitigations.append("Reduce position size to lower concentration risk")

        if concentration.correlation_to_portfolio > 0.7:
            mitigations.append("Consider alternatives with lower correlation")

        if execution.bid_ask_spread > 0.015:
            mitigations.append("Trade during peak liquidity hours")

        if timeline.token_unlock_upcoming < 60 and timeline.unlock_amount_pct > 0.05:
            mitigations.append("Delay entry until post-unlock stabilization")

        if not mitigations:
            mitigations.append("Risk profile acceptable - standard position sizing recommended")

        return mitigations

    def get_report(self, asset: str) -> Optional[str]:
        """Get formatted risk report for asset."""
        if asset not in self.results:
            return None

        return self.results[asset].format_report()

    def get_high_risk_assets(self, threshold: float = 75.0) -> List[Tuple[str, float]]:
        """Get assets with high risk scores."""
        high_risk = [
            (asset, score.overall_risk_score)
            for asset, score in self.results.items()
            if score.overall_risk_score >= threshold
        ]
        return sorted(high_risk, key=lambda x: x[1], reverse=True)

    def get_safe_allocatable_assets(self) -> List[Tuple[str, float, float]]:
        """Get assets that can be safely allocated to."""
        safe = [
            (asset, score.overall_risk_score, score.recommended_max_position)
            for asset, score in self.results.items()
            if score.can_safely_allocate
        ]
        return sorted(safe, key=lambda x: x[1])  # Sort by risk
