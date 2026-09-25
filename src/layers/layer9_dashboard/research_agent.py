"""Autonomous Research Agent — Analyzes markets, detects signals, generates reports."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from src.core.models import OHLCV
from src.layers.layer9_dashboard.orchestrator import DecisionOrchestrator, DecisionSignal

logger = logging.getLogger(__name__)


@dataclass
class ResearchReport:
    """Autonomous agent research output."""

    timestamp: datetime
    assets_analyzed: List[str]
    signals_generated: int
    strong_signals: int  # high confidence
    weak_signals: int  # low confidence
    
    decisions: List[DecisionSignal] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    
    market_summary: str = ""
    top_opportunity: Optional[str] = None


class ResearchAgent:
    """
    Autonomous research assistant.

    Responsibilities:
    - Monitor multiple assets continuously
    - Detect entry/exit signals
    - Generate alert notifications
    - Analyze macro conditions
    - Produce daily research reports
    - Challenge hypotheses
    """

    def __init__(self):
        self.orchestrator = DecisionOrchestrator()
        self.analysis_history: Dict[str, List[DecisionSignal]] = {}
        
        logger.info("ResearchAgent initialized")

    def analyze_assets(
        self,
        assets_data: Dict[str, Dict[str, Any]],
        macro_context: Optional[Dict[str, Any]] = None,
    ) -> ResearchReport:
        """
        Analyze multiple assets and produce research report.

        Args:
            assets_data: {asset: {ohlcv, fundamental, narrative}}
            macro_context: Global market context

        Returns:
            ResearchReport with all findings
        """

        timestamp = datetime.utcnow()
        decisions = []
        findings = []
        alerts = []
        strong_signals = 0
        weak_signals = 0

        for asset, data in assets_data.items():
            ohlcv = data.get("ohlcv", [])
            fundamental = data.get("fundamental", {})
            narrative = data.get("narrative", {})

            if not ohlcv or len(ohlcv) < 20:
                findings.append(f"⊘ {asset}: Insufficient data (skipped)")
                continue

            # Orchestrate decision
            signal = self.orchestrator.analyze(
                asset, ohlcv, fundamental, narrative, macro_context or {}
            )

            decisions.append(signal)
            self.analysis_history.setdefault(asset, []).append(signal)

            # Count signals
            if signal.should_enter:
                if signal.confidence == "high":
                    strong_signals += 1
                    findings.append(f"✓ {asset}: HIGH CONFIDENCE SIGNAL")
                    alerts.append(f"🔔 {asset} entry signal (confidence: high, risk: {signal.risk_level})")
                else:
                    weak_signals += 1
                    findings.append(f"• {asset}: Medium confidence signal")
            else:
                findings.append(f"✗ {asset}: No entry signal")

        # Generate market summary
        market_summary = self._generate_market_summary(
            decisions, macro_context or {}
        )

        # Find top opportunity
        entering_assets = [d for d in decisions if d.should_enter]
        top_opportunity = None
        if entering_assets:
            best = sorted(
                entering_assets,
                key=lambda d: (
                    1 if d.confidence == "high" else 0,
                    d.x20_score,
                    d.rcm_score,
                ),
                reverse=True,
            )[0]
            top_opportunity = best.asset

        # Add strategic findings
        if not entering_assets:
            findings.append("⚠ Market caution: No high-conviction signals")
            alerts.append("⚠ Market analysis: No entry signals generated. Monitor for accumulation phases.")
        else:
            findings.append(f"✓ {len(entering_assets)} assets with entry signals")

        # Regime analysis
        regime_list = [d.market_regime for d in decisions]
        bullish_count = regime_list.count("bullish")
        bearish_count = regime_list.count("bearish")
        sideways_count = regime_list.count("sideways")

        if bullish_count > len(decisions) / 2:
            findings.append("✓ Overall market: Bullish regime dominant")
        elif bearish_count > len(decisions) / 2:
            findings.append("⚠ Overall market: Bearish regime dominant")
        else:
            findings.append("→ Overall market: Mixed/Sideways")

        return ResearchReport(
            timestamp=timestamp,
            assets_analyzed=list(assets_data.keys()),
            signals_generated=len([d for d in decisions if d.should_enter]),
            strong_signals=strong_signals,
            weak_signals=weak_signals,
            decisions=decisions,
            findings=findings,
            alerts=alerts,
            market_summary=market_summary,
            top_opportunity=top_opportunity,
        )

    def challenge_hypothesis(
        self, hypothesis: str, decisions: List[DecisionSignal]
    ) -> List[str]:
        """
        Challenge an investment hypothesis with data.

        Args:
            hypothesis: Claim to test (e.g., "Layer 1 tokens are in growth phase")
            decisions: Recent decision signals

        Returns:
            Evidence supporting or refuting hypothesis
        """

        challenges = []

        # Parse hypothesis type
        if "growth" in hypothesis.lower():
            narm_scores = [d.narm_score for d in decisions]
            if sum(narm_scores) / len(narm_scores) > 70:
                challenges.append(f"✓ Data supports: {hypothesis}")
            else:
                challenges.append(f"✗ Data contradicts: Average NARM score {sum(narm_scores)/len(narm_scores):.1f} < 70")

        elif "accumulation" in hypothesis.lower():
            bce_scores = [d.bce_score for d in decisions]
            bce_confirmed = sum(1 for s in bce_scores if s >= 5)
            if bce_confirmed / len(bce_scores) > 0.5:
                challenges.append(f"✓ Data supports: {hypothesis} ({bce_confirmed}/{len(bce_scores)} BCE confirmed)")
            else:
                challenges.append(f"✗ Data contradicts: Only {bce_confirmed}/{len(bce_scores)} show accumulation")

        elif "bear" in hypothesis.lower():
            regime_list = [d.market_regime for d in decisions]
            bearish = regime_list.count("bearish")
            if bearish / len(regime_list) > 0.5:
                challenges.append(f"✓ Data supports: {hypothesis} ({bearish}/{len(regime_list)} bearish)")
            else:
                challenges.append(f"✗ Data contradicts: {bearish}/{len(regime_list)} bearish regimes")

        else:
            challenges.append(f"⊘ Cannot parse hypothesis: {hypothesis}")

        return challenges

    def _generate_market_summary(
        self, decisions: List[DecisionSignal], macro: Dict[str, Any]
    ) -> str:
        """Generate executive summary of market conditions."""

        if not decisions:
            return "⊘ Insufficient data for market summary"

        lines = [
            f"Market Summary ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})",
        ]

        # Regime distribution
        regimes = [d.market_regime for d in decisions]
        bullish_pct = 100 * regimes.count("bullish") / len(regimes)
        bearish_pct = 100 * regimes.count("bearish") / len(regimes)

        lines.append(f"  Regime: {bullish_pct:.0f}% bullish, {bearish_pct:.0f}% bearish")

        # Signal distribution
        entering = [d for d in decisions if d.should_enter]
        high_conf = [d for d in entering if d.confidence == "high"]

        lines.append(f"  Signals: {len(entering)}/{len(decisions)} entry signals ({len(high_conf)} high confidence)")

        # Average opportunity scores
        avg_x20 = sum(d.x20_score for d in decisions) / len(decisions)
        avg_rcm = sum(d.rcm_score for d in decisions) / len(decisions)

        lines.append(f"  X20 Score: {avg_x20:.1f}/100 | RCM: {avg_rcm:.1f}/100")

        # Risk assessment
        high_risk = [d for d in decisions if d.risk_level == "high"]
        if high_risk:
            lines.append(f"  ⚠ High risk assets: {len(high_risk)}")

        return "\n".join(lines)

    def generate_report_text(self, report: ResearchReport) -> str:
        """Generate human-readable research report."""

        lines = [
            f"\n{'='*70}",
            f"AUTONOMOUS RESEARCH REPORT",
            f"{'='*70}",
            f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"",
            f"Summary:",
            f"  Assets analyzed: {len(report.assets_analyzed)}",
            f"  Entry signals: {report.signals_generated}",
            f"  High confidence: {report.strong_signals}",
            f"  Medium confidence: {report.weak_signals}",
            f"",
        ]

        if report.top_opportunity:
            lines.extend([
                f"Top Opportunity: {report.top_opportunity}",
                f"",
            ])

        lines.extend([
            f"Market Summary:",
        ])

        for line in report.market_summary.split("\n"):
            lines.append(f"  {line}")

        lines.extend([
            f"",
            f"Findings:",
        ])

        for finding in report.findings:
            lines.append(f"  {finding}")

        if report.alerts:
            lines.extend([
                f"",
                f"Alerts:",
            ])
            for alert in report.alerts:
                lines.append(f"  {alert}")

        lines.extend([
            f"",
            f"{'='*70}",
            f"",
        ])

        return "\n".join(lines)
