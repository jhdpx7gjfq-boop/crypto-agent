"""Decision Orchestrator — Combines all 8 layers into unified intelligence."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from src.core.models import OHLCV
from src.layers.layer1_data.collector import DataCollector
from src.layers.layer2_regime.regime_engine import MarketRegimeDetector
from src.layers.layer3_wyckoff.bce_analyzer import BCEAnalyzer
from src.layers.layer4_x20.x20_engine import X20Scanner
from src.layers.layer5_narm.narm_engine import NARMEngine
from src.layers.layer6_rcm.rcm_engine import RCMEngine
from src.layers.layer7_rrp.rrp_engine import RRPEngine
from src.layers.layer8_optimizer.optimizer_engine import OptimizerEngine

logger = logging.getLogger(__name__)


@dataclass
class DecisionSignal:
    """Final decision signal from orchestrator."""

    asset: str
    timestamp: datetime
    
    # Layer outputs
    market_regime: str  # bullish/bearish/sideways
    bce_score: float  # 0-6
    bce_confirmed: bool  # >= 5?
    x20_score: float  # 0-100
    narm_score: float  # 0-100
    rcm_score: float  # 0-100
    rrp_probability: float  # 0-100
    
    # Composite decision
    should_enter: bool
    confidence: str  # high/medium/low
    risk_level: str  # low/medium/high
    
    # Audit trail
    reasoning: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.reasoning:
            self.reasoning = []
        if not self.warnings:
            self.warnings = []


@dataclass
class OrchestrationReport:
    """Complete decision report across all layers."""

    asset: str
    timestamp: datetime
    decision_signal: DecisionSignal
    
    # Layer-specific reports
    bce_report: Optional[str] = None
    x20_report: Optional[str] = None
    narm_report: Optional[str] = None
    rcm_report: Optional[str] = None
    rrp_signal: Optional[str] = None
    
    summary: List[str] = field(default_factory=list)


class DecisionOrchestrator:
    """
    Unified decision intelligence across all 8 layers.

    Flow:
    1. Collect market data
    2. Analyze market regime
    3. Score entry opportunity (BCE, X20, NARM)
    4. Validate rotation (RCM)
    5. Detect revival signals (RRP)
    6. Generate unified decision
    """

    def __init__(self):
        self.collector = DataCollector()
        self.regime_engine = MarketRegimeDetector()
        self.bce_analyzer = BCEAnalyzer()
        self.x20_scanner = X20Scanner()
        self.narm_engine = NARMEngine()
        self.rcm_engine = RCMEngine()
        self.rrp_engine = RRPEngine()
        
        logger.info("DecisionOrchestrator initialized (all 8 layers)")

    def analyze(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        fundamental_data: Optional[Dict[str, Any]] = None,
        narrative_data: Optional[Dict[str, Any]] = None,
        macro_data: Optional[Dict[str, Any]] = None,
    ) -> DecisionSignal:
        """
        Orchestrate all layers and produce unified decision.

        Args:
            asset: Asset identifier
            ohlcv_data: Historical OHLCV candles
            fundamental_data: Fundamentals (team, investors, tokenomics)
            narrative_data: Narrative analysis (media, adoption, rotation)
            macro_data: Macro context (DXY, rates, BTC dominance)

        Returns:
            DecisionSignal with unified intelligence
        """

        timestamp = datetime.utcnow()
        reasoning = []
        warnings = []

        # Layer 2: Market Regime
        btc_price = ohlcv_data[-1].close if ohlcv_data else None
        funding_rate = macro_data.get("funding_rate") if macro_data else None
        oi_change = macro_data.get("oi_change") if macro_data else None
        btc_dom = macro_data.get("btc_dominance") if macro_data else None

        regime_signal = self.regime_engine.detect_regime(
            btc_price=btc_price,
            funding_rate=funding_rate,
            open_interest_change=oi_change,
            btc_dominance=btc_dom,
        )
        market_regime = regime_signal.regime
        reasoning.append(f"Market Regime: {market_regime.value}")

        if market_regime.value == "bear":
            warnings.append("⚠ Bearish regime detected — elevated risk")

        # Layer 3: BCE (Bottom Confirmation)
        bce_report = self.bce_analyzer.analyze(asset, ohlcv_data)
        bce_score = bce_report.bce_score
        bce_confirmed = bce_report.is_valid
        reasoning.append(f"BCE Score: {bce_score:.1f}/6 {'✓ CONFIRMED' if bce_confirmed else '✗ Below threshold'}")

        if not bce_confirmed:
            warnings.append(f"⚠ BCE not confirmed (score: {bce_score:.1f} < 5.0)")

        # Layer 4: X20 (Asymmetric Opportunity)
        x20_report = self.x20_scanner.scan(
            asset, ohlcv_data, fundamental_data or {}, narrative_data or {}
        )
        x20_score = x20_report.combined_score
        x20_risk = "low" if x20_score >= 70 else "medium" if x20_score >= 50 else "high"
        reasoning.append(f"X20 Opportunity Score: {x20_score:.1f}/100 ({x20_risk} risk)")

        if x20_score < 70:
            warnings.append(f"⚠ Low asymmetric opportunity (X20: {x20_score:.1f} < 70)")

        # Layer 5: NARM-P+ (Narrative Adoption Rotation)
        narm_signal = self.narm_engine.scan(
            asset, ohlcv_data, narrative_data or {}
        )
        narm_score = narm_signal.narm_score if hasattr(narm_signal, 'narm_score') else 50.0
        reasoning.append(f"NARM Score: {narm_score:.1f}/100 (timing: {narm_signal.timing_assessment if hasattr(narm_signal, 'timing_assessment') else 'unknown'})")

        # Layer 6: RCM (Rotation Confirmation)
        rcm_signal = self.rcm_engine.scan(
            asset, ohlcv_data, narrative_data or {}, fundamental_data or {}
        )
        rcm_score = rcm_signal.combined_score
        rcm_confirmed = rcm_score >= 70.0
        reasoning.append(f"RCM Confirmation: {rcm_score:.1f}/100 {'✓' if rcm_confirmed else '✗'}")

        if not rcm_confirmed:
            warnings.append(f"⚠ Rotation not confirmed (RCM: {rcm_score:.1f} < 70)")

        # Layer 7: RRP (Revival Radar)
        rrp_signal = self.rrp_engine.scan(asset, ohlcv_data, {}, {})
        rrp_probability = rrp_signal.revival_probability
        reasoning.append(f"RRP Stage: {rrp_signal.stage} (probability: {rrp_probability:.1f}%)")

        if rrp_signal.stage == "dead":
            warnings.append("⚠ Asset in 'dead' stage — avoid entry")

        # Composite Decision Logic
        # Rules:
        # 1. BCE >= 5/6 is mandatory (no entry without it)
        # 2. X20 >= 70 is strongly preferred
        # 3. RCM >= 70 validates rotation
        # 4. NARM timing matters (early/mid stage preferred)
        # 5. RRP "dead" stage blocks entry
        # 6. Market regime context matters

        should_enter = False
        confidence = "low"
        risk_level = "high"

        # Hard gate: BCE must pass
        if not bce_confirmed:
            reasoning.append("✗ BLOCKED: BCE not confirmed (mandatory)")
        elif rrp_signal.stage == "dead":
            reasoning.append("✗ BLOCKED: Asset in dead stage (RRP)")
        else:
            # Soft scoring for entry probability
            entry_score = 0.0

            # BCE confirmation: 0-30 points
            if bce_confirmed:
                entry_score += 30

            # X20 opportunity: 0-30 points
            if x20_score >= 70:
                entry_score += 30
            elif x20_score >= 60:
                entry_score += 15

            # RCM validation: 0-25 points
            if rcm_confirmed:
                entry_score += 25
            elif rcm_score >= 60:
                entry_score += 12

            # NARM early stage: 0-15 points
            if hasattr(narm_signal, 'timing') and narm_signal.timing == "early":
                entry_score += 15
            elif hasattr(narm_signal, 'timing') and narm_signal.timing == "mid":
                entry_score += 7

            # Market regime: 0-10 points
            if market_regime.value == "bull":
                entry_score += 10
            elif market_regime.value == "sideways":
                entry_score += 5

            # Determine entry decision and confidence
            if entry_score >= 80:
                should_enter = True
                confidence = "high"
                risk_level = "low"
                reasoning.append("✓ ENTRY SIGNAL (high confidence)")
            elif entry_score >= 60:
                should_enter = True
                confidence = "medium"
                risk_level = "medium"
                reasoning.append("✓ ENTRY SIGNAL (medium confidence)")
            elif entry_score >= 40:
                should_enter = False
                confidence = "low"
                risk_level = "medium"
                reasoning.append("✗ Insufficient confirmation (low score)")
            else:
                should_enter = False
                confidence = "low"
                risk_level = "high"
                reasoning.append("✗ Below minimum threshold")

        # FOMO circuit breaker
        if should_enter and market_regime.value == "bear" and bce_score < 5.5:
            should_enter = False
            confidence = "low"
            warnings.append("⚠ FOMO circuit breaker: Bearish regime + weak BCE")
            reasoning.append("⚠ FOMO circuit breaker triggered")

        return DecisionSignal(
            asset=asset,
            timestamp=timestamp,
            market_regime=market_regime.value,
            bce_score=bce_score,
            bce_confirmed=bce_confirmed,
            x20_score=x20_score,
            narm_score=narm_score,
            rcm_score=rcm_score,
            rrp_probability=rrp_probability,
            should_enter=should_enter,
            confidence=confidence,
            risk_level=risk_level,
            reasoning=reasoning,
            warnings=warnings,
        )

    def generate_report_text(self, signal: DecisionSignal) -> str:
        """Generate human-readable decision report."""

        lines = [
            f"\n{'='*70}",
            f"DECISION ORCHESTRATION — {signal.asset.upper()}",
            f"{'='*70}",
            f"",
            f"Decision: {'✓ ENTER' if signal.should_enter else '✗ WAIT'}",
            f"Confidence: {signal.confidence.upper()}",
            f"Risk Level: {signal.risk_level.upper()}",
            f"",
            f"Layer Signals:",
            f"  Market Regime: {signal.market_regime}",
            f"  BCE Score: {signal.bce_score:.1f}/6 {'✓' if signal.bce_confirmed else '✗'}",
            f"  X20 Opportunity: {signal.x20_score:.1f}/100",
            f"  NARM Adoption: {signal.narm_score:.1f}/100",
            f"  RCM Confirmation: {signal.rcm_score:.1f}/100",
            f"  RRP Revival: {signal.rrp_probability:.1f}%",
            f"",
            f"Reasoning:",
        ]

        for reason in signal.reasoning:
            lines.append(f"  • {reason}")

        if signal.warnings:
            lines.extend([
                f"",
                f"Warnings:",
            ])
            for warning in signal.warnings:
                lines.append(f"  {warning}")

        lines.extend([
            f"",
            f"{'='*70}",
            f"",
        ])

        return "\n".join(lines)
