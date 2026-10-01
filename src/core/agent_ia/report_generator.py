"""Report generation engine for Agent IA."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


@dataclass
class MarketReport:
    """Daily market summary report."""

    date: str
    regime: Dict[str, Any]  # type, confidence, expected_duration
    top_bce_signals: List[Dict]  # Top 3 BCE >= 5
    top_x20_opportunities: List[Dict]  # Top 5 asymmetric plays
    rrp_revival_candidates: List[Dict]  # Top 3 by stage
    rcm_rotations: List[Dict]  # Key capital rotations
    risk_summary: Dict[str, Any]
    key_insights: List[str]
    recommendations: str
    generated_at: str


@dataclass
class AssetReport:
    """Deep dive on single asset."""

    asset: str
    timestamp: str
    price: float
    bce_analysis: Dict
    x20_analysis: Dict
    price_structure: Dict
    risk_reward: Dict
    recommendation: str  # entry|hold|avoid|research
    reasoning: List[str]
    next_catalysts: List[str]


@dataclass
class ScenarioReport:
    """Scenario analysis."""

    asset: str
    scenarios: Dict[str, Dict]  # bullish|base|bearish
    most_likely: str
    confidence: float
    key_assumptions: List[str]
    trigger_events: List[str]
    generated_at: str


class ReportGenerator:
    """Generates market analysis reports."""

    def __init__(self):
        """Initialize generator."""
        self.report_history: Dict[str, List] = {}

    async def daily_summary(
        self,
        regime_data: Dict,
        bce_signals: Dict,
        x20_scores: Dict,
        rrp_candidates: Dict,
        rcm_rotations: Dict,
    ) -> MarketReport:
        """
        Generate daily market summary.

        Args:
            regime_data: Current market regime
            bce_signals: Top BCE signals
            x20_scores: Opportunity scores
            rrp_candidates: Revival radar candidates
            rcm_rotations: Capital rotation signals

        Returns:
            Comprehensive daily report
        """
        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")

        # Extract top signals
        top_bce = sorted(
            [
                {"asset": a, "score": d.get("score"), "confidence": d.get("confidence")}
                for a, d in bce_signals.items()
                if d.get("score", 0) >= 5
            ],
            key=lambda x: x["score"],
            reverse=True,
        )[:3]

        top_x20 = sorted(
            [
                {
                    "asset": a,
                    "score": d.get("score"),
                    "asymmetric_potential": d.get("asymmetric_potential"),
                }
                for a, d in x20_scores.items()
            ],
            key=lambda x: x["score"],
            reverse=True,
        )[:5]

        rrp_early = [
            {"asset": a, "stage": d.get("stage"), "score": d.get("score")}
            for a, d in rrp_candidates.items()
            if d.get("stage") in ["emerging", "confirmed"]
        ][:3]

        rcm_active = [
            {
                "asset": a,
                "rotation": d.get("rotation_type"),
                "strength": d.get("capital_flow_strength"),
            }
            for a, d in rcm_rotations.items()
            if abs(d.get("capital_flow_strength", 0)) > 0.5
        ][:2]

        # Risk summary
        risk_high = len([s for s in top_bce if s["score"] < 3])
        risk_summary = {
            "high_risk_assets": risk_high,
            "volatility_regime": regime_data.get("regime_type") == "volatile",
            "market_confidence": regime_data.get("confidence", 0.5),
        }

        # Key insights
        insights = self._generate_insights(
            regime_data, top_bce, top_x20, rrp_early, rcm_active
        )

        # Recommendations
        recommendation = self._generate_recommendation(
            regime_data, top_bce, top_x20, insights
        )

        report = MarketReport(
            date=date_str,
            regime={
                "type": regime_data.get("regime_type", "ranging"),
                "confidence": regime_data.get("confidence", 0.5),
                "expected_duration_days": regime_data.get("expected_duration_days", 14),
            },
            top_bce_signals=top_bce,
            top_x20_opportunities=top_x20,
            rrp_revival_candidates=rrp_early,
            rcm_rotations=rcm_active,
            risk_summary=risk_summary,
            key_insights=insights,
            recommendations=recommendation,
            generated_at=now.isoformat(),
        )

        # Store in history
        if date_str not in self.report_history:
            self.report_history[date_str] = []
        self.report_history[date_str].append(report)

        return report

    async def asset_deep_dive(
        self, asset: str, bce_data: Dict, x20_data: Dict, price_data: Dict
    ) -> AssetReport:
        """
        Generate deep analysis of single asset.

        Args:
            asset: Asset symbol
            bce_data: BCE analysis
            x20_data: X20 scoring
            price_data: Price structure data

        Returns:
            Comprehensive asset report
        """
        now = datetime.utcnow()

        bce_score = bce_data.get("score", 0)
        x20_score = x20_data.get("score", 0)

        # Risk/reward
        entry_price = price_data.get("current_price", 0)
        tp1 = entry_price * 1.5
        tp2 = entry_price * 2.5
        tp3 = entry_price * 5.0
        sl = entry_price * 0.97

        risk_reward = {
            "entry": entry_price,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "risk_reward_ratio": (tp3 - entry_price) / (entry_price - sl) if entry_price > sl else 0,
        }

        # Recommendation logic
        if bce_score >= 5.5 and x20_score >= 75:
            recommendation = "entry"
            confidence_score = min(bce_score / 6, 1.0) * min(x20_score / 100, 1.0)
        elif bce_score >= 4.5 and x20_score >= 60:
            recommendation = "research"
            confidence_score = 0.6
        else:
            recommendation = "hold"
            confidence_score = 0.4

        # Reasoning
        reasoning = self._generate_asset_reasoning(asset, bce_data, x20_data, price_data)

        # Next catalysts
        catalysts = self._identify_catalysts(asset, bce_data, x20_data)

        report = AssetReport(
            asset=asset,
            timestamp=now.isoformat(),
            price=entry_price,
            bce_analysis={"score": bce_score, "stage": bce_data.get("stage")},
            x20_analysis={"score": x20_score, "asymmetric_potential": x20_data.get("asymmetric_potential")},
            price_structure={
                "current": entry_price,
                "support": price_data.get("support", 0),
                "resistance": price_data.get("resistance", 0),
            },
            risk_reward=risk_reward,
            recommendation=recommendation,
            reasoning=reasoning,
            next_catalysts=catalysts,
        )

        return report

    async def scenario_analysis(
        self, asset: str, current_price: float, scenarios: Dict[str, Dict]
    ) -> ScenarioReport:
        """
        Compare bullish/base/bearish scenarios.

        Args:
            asset: Asset symbol
            current_price: Entry price
            scenarios: {scenario_name: {probability, target, reasoning}}

        Returns:
            Scenario comparison
        """
        now = datetime.utcnow()

        # Default scenarios if not provided
        if not scenarios:
            scenarios = {
                "bullish": {
                    "probability": 0.3,
                    "target": current_price * 3,
                    "reasoning": "Breakout above resistance",
                },
                "base": {
                    "probability": 0.5,
                    "target": current_price * 1.5,
                    "reasoning": "Gradual accumulation",
                },
                "bearish": {
                    "probability": 0.2,
                    "target": current_price * 0.8,
                    "reasoning": "Failure to break resistance",
                },
            }

        # Find most likely
        most_likely = max(scenarios.items(), key=lambda x: x[1].get("probability", 0))[0]
        confidence = scenarios[most_likely].get("probability", 0.5)

        # Extract assumptions and triggers
        assumptions = self._extract_assumptions(scenarios)
        triggers = self._extract_triggers(scenarios)

        report = ScenarioReport(
            asset=asset,
            scenarios=scenarios,
            most_likely=most_likely,
            confidence=confidence,
            key_assumptions=assumptions,
            trigger_events=triggers,
            generated_at=now.isoformat(),
        )

        return report

    def _generate_insights(
        self, regime: Dict, bce: List, x20: List, rrp: List, rcm: List
    ) -> List[str]:
        """Generate key market insights."""
        insights = []

        if regime.get("regime_type") == "bullish":
            insights.append("Market in bullish regime - bias towards long entries")
        elif regime.get("regime_type") == "bearish":
            insights.append("Bearish pressure - raise entry requirements")

        if len(bce) >= 2:
            insights.append(f"Multiple BCE signals active ({len(bce)} assets)")

        if len(x20) >= 3:
            insights.append(f"Strong asymmetric opportunities available ({len(x20)} assets)")

        if len(rrp) > 0:
            insights.append(f"Revival radar detecting {len(rrp)} candidates")

        if len(rcm) > 0:
            insights.append("Capital rotation signals active - watch flows")

        return insights

    def _generate_recommendation(
        self, regime: Dict, bce: List, x20: List, insights: List
    ) -> str:
        """Generate overall recommendation."""
        signal_strength = len(bce) + len(x20) / 5

        if regime.get("confidence", 0) > 0.7 and signal_strength >= 3:
            return "Market conditions favorable. Multiple high-confidence signals. Focus on BCE ≥5 entries. Monitor regime daily."
        elif signal_strength >= 2:
            return "Selective entry conditions. Increase due diligence. Require higher BBC threshold (≥5.5). Watch for regime confirmation."
        else:
            return "Wait for better entry conditions. Low signal environment. Accumulate watchlist. Monitor for mean reversion."

    def _generate_asset_reasoning(self, asset: str, bce: Dict, x20: Dict, price: Dict) -> List[str]:
        """Generate reasoning for asset recommendation."""
        reasoning = []

        if bce.get("score", 0) >= 5:
            reasoning.append(f"Strong BCE signal: {bce.get('stage', 'mixed')} pattern confirmed")

        if x20.get("score", 0) >= 75:
            reasoning.append(f"High asymmetric potential: {x20.get('asymmetric_potential', 1):.1f}x upside")

        if price.get("volume_surge"):
            reasoning.append("Volume acceleration supports price move")

        return reasoning or ["Standard accumulation pattern"]

    def _identify_catalysts(self, asset: str, bce: Dict, x20: Dict) -> List[str]:
        """Identify next catalysts."""
        catalysts = []

        if bce.get("stage") == "accumulation":
            catalysts.append("Watch for breakout above resistance")

        catalysts.append("Monitor on-chain metrics for smart money activity")

        if x20.get("narrative_score", 0) > 70:
            catalysts.append("Narrative rotation could accelerate movement")

        return catalysts

    def _extract_assumptions(self, scenarios: Dict) -> List[str]:
        """Extract key assumptions from scenarios."""
        assumptions = []

        for scenario_name, data in scenarios.items():
            if "reasoning" in data:
                assumptions.append(f"{scenario_name.title()}: {data['reasoning']}")

        return assumptions[:3]

    def _extract_triggers(self, scenarios: Dict) -> List[str]:
        """Extract trigger events from scenarios."""
        triggers = []

        for scenario_name, data in scenarios.items():
            if scenario_name == "bullish":
                triggers.append("Breakout above resistance + volume spike")
            elif scenario_name == "bearish":
                triggers.append("Break below support + capitulation volume")
            else:
                triggers.append("Continued consolidation without breakout")

        return triggers[:3]
