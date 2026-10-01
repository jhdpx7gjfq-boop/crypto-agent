"""
Integration Layer - Layer 4 Component 6.
Combines Layer 3 BCE signals with Layer 4 X20 scoring.
Final decision layer for opportunity ranking.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import Enum


class IntegrationSignal(Enum):
    """Signal classification for integrated decision."""
    STRONG_BUY = "Strong Buy (BCE ≥5/6, X20 ≥75, aligned)"
    BUY = "Buy (BCE ≥5/6, X20 ≥65)"
    RESEARCH = "Research (BCE ≥5/6, X20 ≥55, needs diligence)"
    WATCH = "Watch (low BCE or X20 <55)"
    HOLD = "Hold (conditions not met)"
    REJECT = "Reject (multiple failures)"


@dataclass
class BCESignal:
    """Bottom Confirmation Engine signal."""
    asset: str
    bce_score: float          # 0-6 (sum of 6 components)
    wyckoff_structure: float  # 0-1
    volume_analysis: float    # 0-1
    selling_exhaustion: float # 0-1
    smart_money_acc: float    # 0-1
    market_structure: float   # 0-1
    momentum_confirmation: float  # 0-1
    valid: bool               # ≥5/6 threshold
    timestamp: Optional[float] = None


@dataclass
class X20Score:
    """X20 opportunity score from Component 5."""
    asset: str
    x20_opportunity_score: float  # 0-100
    fundamental_score: float      # 0-100
    narrative_score: float        # 0-100
    quantitative_score: float     # 0-100
    risk_score: float            # Inverted: 100 = low risk
    component_alignment: float    # 0-100
    risk_adjusted_score: float    # 0-100
    tier: str                     # Tier 1/2/3/Watch
    confidence: str               # High/Medium/Medium-Low/Watch


@dataclass
class FOPOMetrics:
    """FOMO circuit breaker metrics."""
    price_discovery_phase: bool    # Is price in discovery mode?
    euphoria_level: float         # 0-100 (sentiment/momentum)
    extension_factor: float       # How extended from base
    volume_surge: float           # Above normal volume %
    trending_intensity: float     # Social + on-chain activity


@dataclass
class IntegrationResult:
    """Integrated decision result."""
    asset: str

    # Input signals
    bce_signal: BCESignal
    x20_score: X20Score

    # Integration analysis
    bce_valid: bool              # True if BCE >= 5/6
    x20_sufficient: bool          # True if X20 >= 55
    components_aligned: bool      # True if alignment >= 60
    fomo_clear: bool             # True if no FOMO triggers

    # Final decision
    integration_signal: IntegrationSignal
    confidence_level: float      # 0-100 combined confidence
    action_recommendation: str   # What to do
    risk_rating: str            # Critical/High/Moderate/Low

    # Optional and default fields
    fomo_metrics: Optional[FOPOMetrics] = None
    validation_summary: List[str] = field(default_factory=list)
    warning_signals: List[str] = field(default_factory=list)
    entry_conditions: List[str] = field(default_factory=list)
    prev_integration_score: Optional[float] = None
    decision_momentum: float = 0.0


class IntegrationLayer:
    """Integrates BCE (Layer 3) with X20 (Layer 4) for final decisions."""

    # IGWT rules
    BCE_MINIMUM = 5.0 / 6.0  # 5/6 requirement
    X20_MINIMUM = 55.0        # Minimum X20 score
    ALIGNMENT_MINIMUM = 60.0  # Component alignment threshold

    # FOMO circuit breaker thresholds
    EUPHORIA_THRESHOLD = 80.0      # >80 = high euphoria
    EXTENSION_THRESHOLD = 2.0      # >2x extension = extended
    VOLUME_SURGE_THRESHOLD = 150.0 # >150% of normal
    TRENDING_INTENSITY_THRESHOLD = 80.0

    def __init__(self):
        """Initialize integration layer."""
        self.results: Dict[str, IntegrationResult] = {}
        self.history: Dict[str, List[float]] = {}

    def integrate_signals(
        self,
        bce_signal: BCESignal,
        x20_score: X20Score,
        fomo_metrics: Optional[FOPOMetrics] = None
    ) -> IntegrationResult:
        """
        Integrate BCE signal with X20 score.

        Rules:
        1. BCE must be >= 5/6 (IGWT requirement)
        2. X20 must be >= 55 (minimum opportunity score)
        3. Components should align (alignment >= 60)
        4. FOMO circuit breaker must not trigger

        Final signal classification:
        - STRONG_BUY: BCE ≥5/6, X20 ≥75, aligned, no FOMO
        - BUY: BCE ≥5/6, X20 ≥65
        - RESEARCH: BCE ≥5/6, X20 ≥55
        - WATCH: Low BCE or X20 <55
        - HOLD: Conditions not met
        - REJECT: Multiple failures
        """
        # Validate BCE
        bce_valid = bce_signal.bce_score >= self.BCE_MINIMUM

        # Validate X20
        x20_sufficient = x20_score.x20_opportunity_score >= self.X20_MINIMUM

        # Check component alignment
        components_aligned = x20_score.component_alignment >= self.ALIGNMENT_MINIMUM

        # Check FOMO circuit breaker
        fomo_clear = True
        if fomo_metrics is not None:
            fomo_clear = not self._fomo_triggered(fomo_metrics)

        # Generate validation summary
        validation_summary = self._generate_validation(
            bce_valid, x20_sufficient, components_aligned, fomo_clear
        )

        # Classify integration signal
        signal = self._classify_signal(
            bce_valid, x20_sufficient, components_aligned, fomo_clear,
            bce_signal.bce_score, x20_score.x20_opportunity_score
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            bce_signal, x20_score, components_aligned, fomo_clear
        )

        # Generate warning signals
        warning_signals = self._identify_warnings(
            bce_signal, x20_score, fomo_metrics
        )

        # Generate entry conditions
        entry_conditions = self._generate_entry_conditions(
            signal, bce_signal, x20_score
        )

        # Determine risk rating
        risk_rating = self._classify_risk(x20_score.risk_score)

        # Generate recommendation
        action_recommendation = self._generate_recommendation(
            signal, bce_valid, x20_sufficient, fomo_clear
        )

        # Calculate momentum
        prev_score = self.results.get(x20_score.asset).confidence_level \
            if x20_score.asset in self.results else None
        decision_momentum = (confidence - prev_score) if prev_score is not None else 0.0

        # Create result
        result = IntegrationResult(
            asset=x20_score.asset,
            bce_signal=bce_signal,
            x20_score=x20_score,
            fomo_metrics=fomo_metrics,
            bce_valid=bce_valid,
            x20_sufficient=x20_sufficient,
            components_aligned=components_aligned,
            fomo_clear=fomo_clear,
            integration_signal=signal,
            confidence_level=confidence,
            action_recommendation=action_recommendation,
            risk_rating=risk_rating,
            validation_summary=validation_summary,
            warning_signals=warning_signals,
            entry_conditions=entry_conditions,
            prev_integration_score=prev_score,
            decision_momentum=decision_momentum
        )

        # Store result
        self.results[x20_score.asset] = result

        # Track history
        if x20_score.asset not in self.history:
            self.history[x20_score.asset] = []
        self.history[x20_score.asset].append(confidence)

        return result

    def _fomo_triggered(self, fomo_metrics: FOPOMetrics) -> bool:
        """Check if FOMO circuit breaker is triggered."""
        triggers = 0

        if fomo_metrics.euphoria_level > self.EUPHORIA_THRESHOLD:
            triggers += 1

        if fomo_metrics.extension_factor > self.EXTENSION_THRESHOLD:
            triggers += 1

        if fomo_metrics.volume_surge > self.VOLUME_SURGE_THRESHOLD:
            triggers += 1

        if fomo_metrics.trending_intensity > self.TRENDING_INTENSITY_THRESHOLD:
            triggers += 1

        # FOMO triggered if ≥2 conditions met
        return triggers >= 2

    def _generate_validation(
        self,
        bce_valid: bool,
        x20_sufficient: bool,
        aligned: bool,
        fomo_clear: bool
    ) -> List[str]:
        """Generate validation summary."""
        summary = []

        if bce_valid:
            summary.append("✓ BCE ≥5/6 (IGWT requirement met)")
        else:
            summary.append("✗ BCE <5/6 (IGWT requirement failed)")

        if x20_sufficient:
            summary.append("✓ X20 ≥55 (minimum opportunity threshold)")
        else:
            summary.append("✗ X20 <55 (below minimum threshold)")

        if aligned:
            summary.append("✓ Components aligned (≥60% agreement)")
        else:
            summary.append("⚠ Components diverge (<60% alignment)")

        if fomo_clear:
            summary.append("✓ No FOMO circuit breaker triggers")
        else:
            summary.append("⚠ FOMO circuit breaker active (reduce size)")

        return summary

    def _classify_signal(
        self,
        bce_valid: bool,
        x20_sufficient: bool,
        aligned: bool,
        fomo_clear: bool,
        bce_score: float,
        x20_score: float
    ) -> IntegrationSignal:
        """Classify integration signal."""
        # Must have BCE >= 5/6
        if not bce_valid:
            return IntegrationSignal.HOLD

        # Classify by X20 score
        if x20_score >= 75 and aligned and fomo_clear:
            return IntegrationSignal.STRONG_BUY

        elif x20_score >= 65:
            return IntegrationSignal.BUY

        elif x20_score >= 55:
            return IntegrationSignal.RESEARCH

        elif x20_score < 55:
            return IntegrationSignal.WATCH

        else:
            return IntegrationSignal.REJECT

    def _calculate_confidence(
        self,
        bce_signal: BCESignal,
        x20_score: X20Score,
        aligned: bool,
        fomo_clear: bool
    ) -> float:
        """Calculate combined confidence (0-100)."""
        # Normalize BCE to 0-100
        bce_normalized = (bce_signal.bce_score / (6.0 / 6.0)) * 100.0
        bce_normalized = min(100.0, bce_normalized)

        # Average with X20 score
        base_confidence = (bce_normalized + x20_score.x20_opportunity_score) / 2.0

        # Apply alignment bonus
        if aligned:
            base_confidence = base_confidence * 1.1  # 10% bonus

        # Apply FOMO penalty
        if not fomo_clear:
            base_confidence = base_confidence * 0.8  # 20% penalty

        return min(100.0, base_confidence)

    def _identify_warnings(
        self,
        bce_signal: BCESignal,
        x20_score: X20Score,
        fomo_metrics: Optional[FOPOMetrics]
    ) -> List[str]:
        """Identify warning signals."""
        warnings = []

        # BCE warnings
        if bce_signal.bce_score < (5.0 / 6.0):
            warnings.append("BCE below 5/6 threshold - wait for confirmation")

        if bce_signal.selling_exhaustion < 0.7:
            warnings.append("Selling exhaustion not confirmed - entry risk")

        # X20 warnings
        if x20_score.x20_opportunity_score < 55:
            warnings.append("X20 score below 55 - weak opportunity")

        if x20_score.risk_score < 50:
            warnings.append("High risk profile - use smaller position size")

        # Component divergence
        if x20_score.component_alignment < 60:
            warnings.append("Components diverge - conflicting signals")

        # FOMO warnings
        if fomo_metrics is not None:
            if fomo_metrics.euphoria_level > 75:
                warnings.append("High euphoria detected - reduce position size")

            if fomo_metrics.extension_factor > 1.5:
                warnings.append("Price extended from base - wait for pullback")

        return warnings if warnings else ["No major warnings"]

    def _generate_entry_conditions(
        self,
        signal: IntegrationSignal,
        bce_signal: BCESignal,
        x20_score: X20Score
    ) -> List[str]:
        """Generate entry conditions for signal."""
        conditions = []

        if signal == IntegrationSignal.STRONG_BUY:
            conditions.append("Full entry size allowed (5% position per IGWT rules)")
            conditions.append("Limit orders recommended but not required")
            conditions.append("Immediate entry acceptable if BCE confirmed")

        elif signal == IntegrationSignal.BUY:
            conditions.append("75% of full size (3.75% position)")
            conditions.append("Use limit orders for better entry")
            conditions.append("Scale in over 2-3 orders if possible")

        elif signal == IntegrationSignal.RESEARCH:
            conditions.append("Deeper due diligence required before entry")
            conditions.append("Small probe position (1-2%) if proceeding")
            conditions.append("Wait for next BCE confirmation")

        elif signal == IntegrationSignal.WATCH:
            conditions.append("Monitor for improvement in BCE or X20 score")
            conditions.append("No entry at this time")
            conditions.append("Re-evaluate in 1-2 weeks")

        else:
            conditions.append("Do not enter at this time")
            conditions.append("Wait for fundamental improvement")

        return conditions

    def _classify_risk(self, risk_score: float) -> str:
        """Classify risk rating based on inverted risk score."""
        if risk_score >= 80:
            return "Low"
        elif risk_score >= 60:
            return "Moderate"
        elif risk_score >= 40:
            return "High"
        else:
            return "Critical"

    def _identify_warnings(
        self,
        bce_signal: BCESignal,
        x20_score: X20Score,
        fomo_metrics: Optional[FOPOMetrics]
    ) -> List[str]:
        """Identify warning signals."""
        warnings = []

        # BCE warnings
        if bce_signal.bce_score < (5.0 / 6.0):
            warnings.append("BCE below 5/6 threshold - wait for confirmation")

        if bce_signal.selling_exhaustion < 0.7:
            warnings.append("Selling exhaustion not confirmed - entry risk")

        # X20 warnings
        if x20_score.x20_opportunity_score < 55:
            warnings.append("X20 score below 55 - weak opportunity")

        if x20_score.risk_score < 50:
            warnings.append("High risk profile - use smaller position size")

        # Component divergence
        if x20_score.component_alignment < 60:
            warnings.append("Components diverge - conflicting signals")

        # FOMO warnings
        if fomo_metrics is not None:
            if fomo_metrics.euphoria_level > 75:
                warnings.append("High euphoria detected - reduce position size")

            if fomo_metrics.extension_factor > 1.5:
                warnings.append("Price extended from base - wait for pullback")

        return warnings if warnings else ["No major warnings"]

    def _generate_recommendation(
        self,
        signal: IntegrationSignal,
        bce_valid: bool,
        x20_sufficient: bool,
        fomo_clear: bool
    ) -> str:
        """Generate action recommendation."""
        if signal == IntegrationSignal.STRONG_BUY:
            return "BUY SIGNAL: All conditions met. Proceed with full entry per portfolio rules."

        elif signal == IntegrationSignal.BUY:
            return "BUY SIGNAL: Entry conditions favorable. Use limit orders for best execution."

        elif signal == IntegrationSignal.RESEARCH:
            return "RESEARCH: Opportunity exists but requires deeper analysis. Small probe position acceptable."

        elif signal == IntegrationSignal.WATCH:
            if not bce_valid:
                return "WATCH: Wait for BCE to reach ≥5/6. Re-evaluate next week."
            else:
                return "WATCH: X20 score insufficient. Monitor for improvement."

        elif signal == IntegrationSignal.HOLD:
            return "HOLD: Conditions not met. Do not enter at current time."

        else:
            return "REJECT: Multiple condition failures. Wait for fundamental improvement."

    def get_strong_buy_opportunities(self) -> List[Tuple[str, float]]:
        """Get STRONG_BUY opportunities only."""
        strong_buys = [
            (asset, result.confidence_level)
            for asset, result in self.results.items()
            if result.integration_signal == IntegrationSignal.STRONG_BUY
        ]
        return sorted(strong_buys, key=lambda x: x[1], reverse=True)

    def get_buy_opportunities(self) -> List[Tuple[str, float]]:
        """Get BUY opportunities (includes STRONG_BUY)."""
        buys = [
            (asset, result.confidence_level)
            for asset, result in self.results.items()
            if result.integration_signal in [
                IntegrationSignal.STRONG_BUY,
                IntegrationSignal.BUY
            ]
        ]
        return sorted(buys, key=lambda x: x[1], reverse=True)

    def get_research_candidates(self) -> List[Tuple[str, float]]:
        """Get RESEARCH candidates for deeper diligence."""
        research = [
            (asset, result.confidence_level)
            for asset, result in self.results.items()
            if result.integration_signal == IntegrationSignal.RESEARCH
        ]
        return sorted(research, key=lambda x: x[1], reverse=True)

    def get_watch_list(self) -> List[Tuple[str, float]]:
        """Get WATCH list items."""
        watch = [
            (asset, result.confidence_level)
            for asset, result in self.results.items()
            if result.integration_signal == IntegrationSignal.WATCH
        ]
        return sorted(watch, key=lambda x: x[1], reverse=True)

    def get_report(self, asset: str) -> Optional[str]:
        """Generate formatted integration report."""
        if asset not in self.results:
            return None

        result = self.results[asset]

        report = f"""
╔════════════════════════════════════════════════════════════════════╗
║               LAYER 4 INTEGRATION DECISION REPORT                  ║
╚════════════════════════════════════════════════════════════════════╝

Asset: {result.asset}
Decision: {result.integration_signal.value}
Confidence: {result.confidence_level:.1f}%
Risk Rating: {result.risk_rating}

━━━ VALIDATION STATUS ━━━
{chr(10).join(result.validation_summary)}

━━━ BCE SIGNAL (Layer 3) ━━━
BCE Score: {result.bce_signal.bce_score:.2f}/6.0 {("✓ VALID" if result.bce_valid else "✗ INVALID")}
  Wyckoff Structure: {result.bce_signal.wyckoff_structure:.2f}
  Volume Analysis: {result.bce_signal.volume_analysis:.2f}
  Selling Exhaustion: {result.bce_signal.selling_exhaustion:.2f}
  Smart Money Acc: {result.bce_signal.smart_money_acc:.2f}
  Market Structure: {result.bce_signal.market_structure:.2f}
  Momentum Confirm: {result.bce_signal.momentum_confirmation:.2f}

━━━ X20 OPPORTUNITY (Layer 4 Components 1-5) ━━━
X20 Score: {result.x20_score.x20_opportunity_score:.1f}/100 {("✓ SUFFICIENT" if result.x20_sufficient else "✗ INSUFFICIENT")}
Tier: {result.x20_score.tier}
Component Alignment: {result.x20_score.component_alignment:.1f}% {("✓ ALIGNED" if result.components_aligned else "⚠ DIVERGED")}

Component Scores:
  Fundamental: {result.x20_score.fundamental_score:.1f}/100
  Narrative: {result.x20_score.narrative_score:.1f}/100
  Quantitative: {result.x20_score.quantitative_score:.1f}/100
  Risk (Inv): {result.x20_score.risk_score:.1f}/100

━━━ KEY WARNINGS ━━━
{chr(10).join(f"⚠ {w}" for w in result.warning_signals)}

━━━ ENTRY CONDITIONS ━━━
{chr(10).join(f"• {c}" for c in result.entry_conditions)}

━━━ RECOMMENDATION ━━━
{result.action_recommendation}

━━━ IGWT COMPLIANCE ━━━
✓ BCE ≥5/6 requirement enforced
✓ X20 ≥55 minimum enforced
✓ Component alignment validated
✓ FOMO circuit breaker active
✓ Position sizing per portfolio rules
✓ All decisions require human execution
"""

        return report
