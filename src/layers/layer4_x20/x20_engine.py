"""X20 Opportunity Scanner (Layer 4)."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from src.core.models import OHLCV, X20Opportunity
from src.core.config import Config
from src.utils.feature_store import FeatureStore

logger = logging.getLogger(__name__)


@dataclass
class X20AnalysisReport:
    """Comprehensive X20 analysis report."""

    asset: str
    combined_score: float  # 0-100
    is_opportunity: bool  # >= 70
    fundamental_score: float
    narrative_score: float
    quantitative_score: float
    fundamental_factors: Dict[str, float]
    narrative_factors: Dict[str, float]
    quantitative_factors: Dict[str, float]
    risk_assessment: str  # low/medium/high
    asymmetric_ratio: float  # potential return / risk
    reasoning: List[str]


class X20Scanner:
    """Identifies asymmetric opportunities with X10-X20 potential."""

    def __init__(self):
        self.config = Config
        self.feature_store = FeatureStore()

    def scan(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        fundamental_data: Optional[Dict[str, Any]] = None,
        narrative_data: Optional[Dict[str, Any]] = None,
    ) -> X20Opportunity:
        """Quick scan returning opportunity score (0-100)."""

        if not ohlcv_data or len(ohlcv_data) < 20:
            return X20Opportunity(
                timestamp=datetime.utcnow(),
                asset=asset,
                ticker=asset.upper(),
                fundamental_score=0.0,
                narrative_score=0.0,
                quantitative_score=0.0,
                combined_score=0.0,
                team_quality="unknown",
                investors=[],
            )

        fund_score = self._score_fundamental(fundamental_data or {})
        narrative_score = self._score_narrative(narrative_data or {})
        quant_score = self._score_quantitative(ohlcv_data)

        # Weighted average: 40% fundamental, 35% narrative, 25% quantitative
        combined = (
            fund_score * 0.40 + narrative_score * 0.35 + quant_score * 0.25
        )

        return X20Opportunity(
            timestamp=datetime.utcnow(),
            asset=asset,
            ticker=asset.upper(),
            fundamental_score=fund_score,
            narrative_score=narrative_score,
            quantitative_score=quant_score,
            combined_score=min(100.0, combined),
            team_quality=fundamental_data.get("team_quality", "unknown") if fundamental_data else "unknown",
            investors=fundamental_data.get("investors", []) if fundamental_data else [],
        )

    def analyze(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        fundamental_data: Optional[Dict[str, Any]] = None,
        narrative_data: Optional[Dict[str, Any]] = None,
    ) -> X20AnalysisReport:
        """Comprehensive X20 analysis with reasoning."""

        reasoning = []

        if not ohlcv_data or len(ohlcv_data) < 20:
            reasoning.append("Insufficient OHLCV data for analysis")
            return self._create_invalid_report(asset, reasoning)

        # Score all three dimensions
        fund_score, fund_factors = self._score_fundamental_detailed(
            fundamental_data or {}
        )
        narrative_score, narrative_factors = self._score_narrative_detailed(
            narrative_data or {}
        )
        quant_score, quant_factors = self._score_quantitative_detailed(ohlcv_data)

        # Weighted combined score
        combined = (
            fund_score * 0.40 + narrative_score * 0.35 + quant_score * 0.25
        )
        combined = min(100.0, combined)

        is_opportunity = combined >= 70.0

        # Add reasoning
        reasoning.append(f"Fundamental: {fund_score:.1f}/100 ({', '.join([f'{k}: {v:.0f}' for k, v in fund_factors.items()])})")
        reasoning.append(f"Narrative: {narrative_score:.1f}/100 ({', '.join([f'{k}: {v:.0f}' for k, v in narrative_factors.items()])})")
        reasoning.append(f"Quantitative: {quant_score:.1f}/100 ({', '.join([f'{k}: {v:.0f}' for k, v in quant_factors.items()])})")

        # Risk assessment
        risk = self._assess_risk(ohlcv_data, combined)
        reasoning.append(f"Risk Rating: {risk}")

        # Asymmetric ratio
        asymmetric = self._compute_asymmetric_ratio(
            combined, quant_factors.get("volatility", 50)
        )
        reasoning.append(f"Asymmetric Ratio: {asymmetric:.2f}x")

        if is_opportunity:
            reasoning.append("✓ X20 OPPORTUNITY DETECTED")
        else:
            reasoning.append("✗ Does not meet X20 threshold (70+)")

        return X20AnalysisReport(
            asset=asset,
            combined_score=combined,
            is_opportunity=is_opportunity,
            fundamental_score=fund_score,
            narrative_score=narrative_score,
            quantitative_score=quant_score,
            fundamental_factors=fund_factors,
            narrative_factors=narrative_factors,
            quantitative_factors=quant_factors,
            risk_assessment=risk,
            asymmetric_ratio=asymmetric,
            reasoning=reasoning,
        )

    def _score_fundamental(self, data: Dict[str, Any]) -> float:
        """Quick fundamental score (0-100)."""
        _, factors = self._score_fundamental_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_fundamental_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed fundamental analysis."""
        factors = {}

        # Team quality: 0-25
        team_quality = data.get("team_quality", "unknown")
        if team_quality == "elite":
            factors["team"] = 25.0
        elif team_quality == "strong":
            factors["team"] = 20.0
        elif team_quality == "adequate":
            factors["team"] = 15.0
        else:
            factors["team"] = 10.0

        # Investors quality: 0-25
        investors = data.get("investors", [])
        investor_score = min(25.0, len(investors) * 5.0)
        factors["investors"] = investor_score

        # Tokenomics: 0-25
        tokenomics = data.get("tokenomics_score", 50)
        factors["tokenomics"] = min(25.0, tokenomics / 2)

        # Adoption metrics: 0-25
        adoption = data.get("adoption_score", 50)
        factors["adoption"] = min(25.0, adoption / 2)

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_narrative(self, data: Dict[str, Any]) -> float:
        """Quick narrative score (0-100)."""
        _, factors = self._score_narrative_detailed(data)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_narrative_detailed(
        self, data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed narrative analysis."""
        factors = {}

        # Sector momentum: 0-30
        sector = data.get("sector", "")
        sector_growth = data.get("sector_growth", 50)
        factors["sector_momentum"] = min(30.0, sector_growth / 100 * 30)

        # Media attention: 0-25
        media_score = data.get("media_attention", 50)
        factors["media_attention"] = min(25.0, media_score / 100 * 25)

        # Capital flow: 0-25
        capital_flow = data.get("capital_inflow_score", 50)
        factors["capital_flow"] = min(25.0, capital_flow / 100 * 25)

        # Competitive advantage: 0-20
        competitive = data.get("competitive_advantage", 50)
        factors["competitive_edge"] = min(20.0, competitive / 100 * 20)

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _score_quantitative(self, ohlcv: List[OHLCV]) -> float:
        """Quick quantitative score (0-100)."""
        _, factors = self._score_quantitative_detailed(ohlcv)
        if not factors:
            return 50.0
        return sum(factors.values()) / len(factors)

    def _score_quantitative_detailed(
        self, ohlcv: List[OHLCV]
    ) -> Tuple[float, Dict[str, float]]:
        """Detailed quantitative analysis."""
        factors = {}

        if len(ohlcv) < 20:
            return 50.0, {"insufficient_data": 50.0}

        # Momentum: 0-25 (% change last 20 periods)
        price_change = (ohlcv[-1].close - ohlcv[-20].close) / ohlcv[-20].close
        momentum_score = min(25.0, max(0.0, (price_change + 1) * 12.5))
        factors["momentum"] = momentum_score

        # Volatility: 0-25 (lower vol = better stability, higher = opportunity)
        closes = [c.close for c in ohlcv[-20:]]
        avg_close = sum(closes) / len(closes)
        variance = sum((c - avg_close) ** 2 for c in closes) / len(closes)
        volatility = (variance ** 0.5) / avg_close * 100
        # Sweet spot: 15-40% volatility
        vol_score = 25.0 - abs(volatility - 25.0) / 4
        factors["volatility"] = max(0.0, min(25.0, vol_score))

        # Relative Strength (vs. reference price): 0-25
        # Use distance from 20-period average
        avg_price_20 = avg_close
        current_price = ohlcv[-1].close
        distance_pct = (current_price - avg_price_20) / avg_price_20 * 100
        rs_score = max(0.0, min(25.0, 12.5 + distance_pct / 4))
        factors["relative_strength"] = rs_score

        # Liquidity proxy (volume trend): 0-25
        volumes = [c.volume for c in ohlcv[-20:]]
        avg_vol = sum(volumes) / len(volumes)
        recent_vol = sum(volumes[-5:]) / 5
        vol_trend = (recent_vol / avg_vol) * 25 if avg_vol > 0 else 12.5
        factors["liquidity"] = max(0.0, min(25.0, vol_trend))

        avg_score = sum(factors.values()) / len(factors) if factors else 50.0
        return avg_score, factors

    def _assess_risk(self, ohlcv: List[OHLCV], opportunity_score: float) -> str:
        """Assess risk level."""
        if len(ohlcv) < 20:
            return "high"

        closes = [c.close for c in ohlcv[-20:]]
        avg_close = sum(closes) / len(closes)
        volatility = (sum((c - avg_close) ** 2 for c in closes) / len(closes)) ** 0.5 / avg_close * 100

        # High volatility + low score = high risk
        if volatility > 30 and opportunity_score < 60:
            return "high"
        elif volatility > 20 or opportunity_score < 50:
            return "medium"
        else:
            return "low"

    def _compute_asymmetric_ratio(
        self, opportunity_score: float, volatility: float
    ) -> float:
        """Compute asymmetric return/risk ratio."""
        # Higher score = higher potential return
        # Higher volatility = higher risk
        potential_return = opportunity_score / 100 * 20  # Max 20x potential
        risk_factor = max(0.5, volatility / 20)
        asymmetric = potential_return / risk_factor
        return asymmetric

    def _create_invalid_report(
        self, asset: str, reasoning: List[str]
    ) -> X20AnalysisReport:
        """Create invalid report."""
        return X20AnalysisReport(
            asset=asset,
            combined_score=0.0,
            is_opportunity=False,
            fundamental_score=0.0,
            narrative_score=0.0,
            quantitative_score=0.0,
            fundamental_factors={},
            narrative_factors={},
            quantitative_factors={},
            risk_assessment="high",
            asymmetric_ratio=0.0,
            reasoning=reasoning,
        )

    def generate_report_text(self, report: X20AnalysisReport) -> str:
        """Generate human-readable report."""
        lines = [
            f"\n{'='*60}",
            f"X20 OPPORTUNITY ANALYSIS — {report.asset.upper()}",
            f"{'='*60}",
            f"",
            f"Combined Score: {report.combined_score:.1f}/100 {'✓ OPPORTUNITY' if report.is_opportunity else '✗ NOT QUALIFIED'}",
            f"Risk Assessment: {report.risk_assessment.upper()}",
            f"Asymmetric Ratio: {report.asymmetric_ratio:.2f}x",
            f"",
            f"Dimension Scores:",
            f"  Fundamental:    {report.fundamental_score:.1f}/100",
            f"  Narrative:      {report.narrative_score:.1f}/100",
            f"  Quantitative:   {report.quantitative_score:.1f}/100",
            f"",
            f"Analysis:",
        ]

        for reason in report.reasoning:
            lines.append(f"  • {reason}")

        lines.extend([
            f"",
            f"{'='*60}",
            f"",
        ])

        return "\n".join(lines)
