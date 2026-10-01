"""
Opportunity Ranker - Layer 4 Component 5.
Aggregates component scores into unified X20 opportunity ranking.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


class OpportunityConfidence(Enum):
    """Confidence classification for opportunity score."""
    HIGH = "High"          # ≥75
    MEDIUM = "Medium"      # 65-75
    MEDIUM_LOW = "Medium-Low"  # 55-65
    WATCH_LIST = "Watch"   # <55


class OpportunityTier(Enum):
    """Opportunity tier for easy filtering."""
    TIER_1 = "Tier 1 (★★★★★)"  # ≥75: High conviction X10-X20 potential
    TIER_2 = "Tier 2 (★★★★)"    # 65-75: Strong conviction, ready for detailed analysis
    TIER_3 = "Tier 3 (★★★)"     # 55-65: Interesting but requires deeper diligence
    WATCH = "Watch List"        # <55: Monitor for future opportunities


@dataclass
class RankerInput:
    """Input scores from all 4 components."""
    fundamental_score: float       # 0-100
    narrative_score: float         # 0-100
    quantitative_score: float      # 0-100
    risk_score: float             # 0-100 (inverted: 100 = low risk)

    # Metadata
    asset: str = ""
    timestamp: Optional[float] = None


@dataclass
class OpportunityScore:
    """Unified opportunity ranking."""
    asset: str

    # Component scores (for transparency)
    fundamental_score: float
    narrative_score: float
    quantitative_score: float
    risk_score: float              # Inverted (100 = low risk)

    # Aggregated score
    x20_opportunity_score: float    # 0-100
    confidence: OpportunityConfidence
    tier: OpportunityTier

    # Signal strength
    component_alignment: float      # 0-100, how aligned are components
    risk_adjusted_score: float      # x20 score penalized by drawdown risk

    # Key signals
    key_opportunities: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    recommendation: str = ""

    # Historical tracking
    prev_score: Optional[float] = None
    score_momentum: float = 0.0      # Change from previous analysis


@dataclass
class OpportunityReport:
    """Formatted report for a ranked asset."""
    asset: str
    x20_score: float
    tier: str
    confidence: str
    analysis: str


class OpportunityRanker:
    """Aggregates component scores into unified X20 opportunity ranking."""

    # Component weights (must sum to 1.0)
    WEIGHT_FUNDAMENTAL = 0.35
    WEIGHT_NARRATIVE = 0.25
    WEIGHT_QUANTITATIVE = 0.25
    WEIGHT_RISK = 0.15

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 75.0
    MEDIUM_CONFIDENCE_THRESHOLD = 65.0
    MEDIUM_LOW_CONFIDENCE_THRESHOLD = 55.0

    def __init__(self):
        """Initialize ranker."""
        self.results: Dict[str, OpportunityScore] = {}
        self.history: Dict[str, List[float]] = {}

    def rank_opportunity(self, ranker_input: RankerInput) -> OpportunityScore:
        """
        Rank asset based on aggregated component scores.

        Weights:
        - Fundamental: 35% (team, investors, tokenomics, adoption, competition)
        - Narrative: 25% (sector, adoption trend, social, capital rotation)
        - Quantitative: 25% (momentum, volatility, relative strength, liquidity)
        - Risk: 15% (drawdown, concentration, execution, timeline)

        Note: Risk score should be inverted (100 = low risk, 0 = high risk)
        before passing to ranker.
        """
        # Calculate weighted X20 score
        x20_score = (
            ranker_input.fundamental_score * self.WEIGHT_FUNDAMENTAL +
            ranker_input.narrative_score * self.WEIGHT_NARRATIVE +
            ranker_input.quantitative_score * self.WEIGHT_QUANTITATIVE +
            ranker_input.risk_score * self.WEIGHT_RISK
        )

        # Ensure score is in valid range
        x20_score = max(0.0, min(100.0, x20_score))

        # Classify confidence
        confidence = self._classify_confidence(x20_score)

        # Classify tier
        tier = self._classify_tier(x20_score)

        # Calculate component alignment (how similar are scores)
        component_alignment = self._calculate_alignment(
            ranker_input.fundamental_score,
            ranker_input.narrative_score,
            ranker_input.quantitative_score,
            ranker_input.risk_score
        )

        # Risk-adjusted score: Apply penalty based on risk
        risk_adjustment = ranker_input.risk_score / 100.0
        risk_adjusted_score = x20_score * risk_adjustment

        # Generate signals
        key_opportunities = self._identify_opportunities(ranker_input)
        key_risks = self._identify_risks(ranker_input)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            x20_score, confidence, component_alignment, ranker_input
        )

        # Calculate momentum from history
        prev_score = self.results.get(ranker_input.asset).x20_opportunity_score \
            if ranker_input.asset in self.results else None
        score_momentum = (x20_score - prev_score) if prev_score is not None else 0.0

        # Create result
        result = OpportunityScore(
            asset=ranker_input.asset,
            fundamental_score=ranker_input.fundamental_score,
            narrative_score=ranker_input.narrative_score,
            quantitative_score=ranker_input.quantitative_score,
            risk_score=ranker_input.risk_score,
            x20_opportunity_score=x20_score,
            confidence=confidence,
            tier=tier,
            component_alignment=component_alignment,
            risk_adjusted_score=risk_adjusted_score,
            key_opportunities=key_opportunities,
            key_risks=key_risks,
            recommendation=recommendation,
            prev_score=prev_score,
            score_momentum=score_momentum
        )

        # Store result
        self.results[ranker_input.asset] = result

        # Track history
        if ranker_input.asset not in self.history:
            self.history[ranker_input.asset] = []
        self.history[ranker_input.asset].append(x20_score)

        return result

    def _classify_confidence(self, score: float) -> OpportunityConfidence:
        """Classify confidence level based on score."""
        if score >= self.HIGH_CONFIDENCE_THRESHOLD:
            return OpportunityConfidence.HIGH
        elif score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return OpportunityConfidence.MEDIUM
        elif score >= self.MEDIUM_LOW_CONFIDENCE_THRESHOLD:
            return OpportunityConfidence.MEDIUM_LOW
        else:
            return OpportunityConfidence.WATCH_LIST

    def _classify_tier(self, score: float) -> OpportunityTier:
        """Classify opportunity tier."""
        if score >= self.HIGH_CONFIDENCE_THRESHOLD:
            return OpportunityTier.TIER_1
        elif score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return OpportunityTier.TIER_2
        elif score >= self.MEDIUM_LOW_CONFIDENCE_THRESHOLD:
            return OpportunityTier.TIER_3
        else:
            return OpportunityTier.WATCH

    def _calculate_alignment(
        self,
        fundamental: float,
        narrative: float,
        quantitative: float,
        risk: float
    ) -> float:
        """
        Calculate component alignment (0-100).
        Higher = components agree on opportunity quality.
        """
        scores = [fundamental, narrative, quantitative, risk]
        mean = sum(scores) / len(scores)

        # Calculate standard deviation
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        # Convert std_dev to alignment (high std_dev = low alignment)
        # Max std_dev ~50, so alignment = 100 * (1 - std_dev/50)
        alignment = max(0.0, 100.0 * (1.0 - (std_dev / 50.0)))
        return min(100.0, alignment)

    def _identify_opportunities(self, inp: RankerInput) -> List[str]:
        """Identify key opportunity signals."""
        signals = []

        if inp.fundamental_score >= 75:
            signals.append("Strong fundamental foundation (team/investors/tokenomics)")

        if inp.narrative_score >= 75:
            signals.append("Hot narrative with adoption acceleration")

        if inp.quantitative_score >= 75:
            signals.append("Strong technical momentum and liquidity")

        if inp.fundamental_score >= 70 and inp.narrative_score >= 70:
            signals.append("Fundamentals + narrative aligned (defensible story)")

        if inp.quantitative_score >= 70 and inp.risk_score >= 70:
            signals.append("Good risk/reward setup (high liquidity, limited drawdown)")

        if inp.risk_score < 40:
            signals.append("HIGH RISK: Consider smaller position size")

        return signals if signals else ["Monitor for better entry"]

    def _identify_risks(self, inp: RankerInput) -> List[str]:
        """Identify key risk factors."""
        risks = []

        if inp.risk_score < 40:
            risks.append("Critical risk exposure - wait for improvement")

        if inp.risk_score < 60:
            risks.append("Elevated risk (high volatility or concentration)")

        if inp.fundamental_score < 50:
            risks.append("Weak fundamentals (team/investors/tokenomics concerns)")

        if inp.narrative_score < 50:
            risks.append("Narrative weakness or declining adoption")

        if inp.quantitative_score < 50:
            risks.append("Poor technicals (weak momentum or low liquidity)")

        if (inp.fundamental_score < 60 and inp.narrative_score < 60 and
            inp.quantitative_score < 60):
            risks.append("REJECT: Multiple component weaknesses")

        return risks if risks else ["Low risk profile"]

    def _generate_recommendation(
        self,
        x20_score: float,
        confidence: OpportunityConfidence,
        alignment: float,
        inp: RankerInput
    ) -> str:
        """Generate actionable recommendation."""
        if x20_score >= 75 and alignment >= 70:
            if inp.risk_score >= 70:
                return "BUY SIGNAL: High conviction, good risk/reward. Size per portfolio rules."
            else:
                return "BUY SIGNAL: High conviction but elevated risk. Use smaller size."

        elif x20_score >= 65 and alignment >= 60:
            return "RESEARCH: Strong candidate. Recommend deeper diligence before entry."

        elif x20_score >= 55:
            return "WATCH: Interesting but requires monitoring. Re-evaluate in 1-2 weeks."

        elif alignment < 50:
            return "INCONCLUSIVE: Components diverge. Wait for clearer signal."

        else:
            return "HOLD: Does not meet minimum opportunity threshold at this time."

    def get_report(self, asset: str) -> Optional[str]:
        """Generate formatted report for asset."""
        if asset not in self.results:
            return None

        score = self.results[asset]

        report = f"""
╔════════════════════════════════════════════════════════════════════╗
║                     X20 OPPORTUNITY RANKING                        ║
╚════════════════════════════════════════════════════════════════════╝

Asset: {score.asset}
X20 Score: {score.x20_opportunity_score:.1f}/100
Tier: {score.tier.value}
Confidence: {score.confidence.value}

━━━ COMPONENT SCORES ━━━
Fundamental:     {score.fundamental_score:6.1f}/100 (35% weight)
Narrative:       {score.narrative_score:6.1f}/100 (25% weight)
Quantitative:    {score.quantitative_score:6.1f}/100 (25% weight)
Risk (Inv):      {score.risk_score:6.1f}/100 (15% weight) [100=low risk]

━━━ ANALYSIS METRICS ━━━
Component Alignment:  {score.component_alignment:.1f}% (consensus strength)
Risk-Adjusted Score:  {score.risk_adjusted_score:.1f}/100
Score Momentum:       {score.score_momentum:+.1f}

━━━ KEY OPPORTUNITIES ━━━
{chr(10).join(f"✓ {opp}" for opp in score.key_opportunities)}

━━━ KEY RISKS ━━━
{chr(10).join(f"⚠ {risk}" for risk in score.key_risks)}

━━━ RECOMMENDATION ━━━
{score.recommendation}

━━━ NOTES ━━━
• Weights are transparent and fixed across all assets
• Risk score is inverted (100 = low risk, 0 = high risk)
• This score is an aggregator, not an alpha predictor
• Always validate with additional due diligence before trading
• All analysis must satisfy IGWT garde-fous (BCE ≥5/6, no FOMO)
"""
        return report

    def get_tier_1_opportunities(self) -> List[tuple]:
        """Get Tier 1 opportunities (≥75 score, high conviction)."""
        tier_1 = [
            (asset, score.x20_opportunity_score)
            for asset, score in self.results.items()
            if score.tier == OpportunityTier.TIER_1
        ]
        return sorted(tier_1, key=lambda x: x[1], reverse=True)

    def get_tier_2_opportunities(self) -> List[tuple]:
        """Get Tier 2 opportunities (65-75, ready for diligence)."""
        tier_2 = [
            (asset, score.x20_opportunity_score)
            for asset, score in self.results.items()
            if score.tier == OpportunityTier.TIER_2
        ]
        return sorted(tier_2, key=lambda x: x[1], reverse=True)

    def get_watch_list(self) -> List[tuple]:
        """Get watch list items (<55, monitor for improvement)."""
        watch = [
            (asset, score.x20_opportunity_score)
            for asset, score in self.results.items()
            if score.tier == OpportunityTier.WATCH
        ]
        return sorted(watch, key=lambda x: x[1], reverse=True)

    def get_aligned_opportunities(self, threshold: float = 70.0) -> List[tuple]:
        """Get opportunities with high component alignment."""
        aligned = [
            (asset, score.x20_opportunity_score, score.component_alignment)
            for asset, score in self.results.items()
            if score.component_alignment >= threshold
        ]
        return sorted(aligned, key=lambda x: x[1], reverse=True)

    def get_risk_adjusted_ranking(self) -> List[tuple]:
        """Get ranking by risk-adjusted score."""
        ranking = [
            (asset, score.risk_adjusted_score, score.risk_score)
            for asset, score in self.results.items()
        ]
        return sorted(ranking, key=lambda x: x[1], reverse=True)
