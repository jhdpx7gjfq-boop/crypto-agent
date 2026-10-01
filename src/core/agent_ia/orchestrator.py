"""Agent IA Orchestrator — Main agent loop and coordination."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio


class SignalType(str, Enum):
    """Signal types."""
    ENTRY = "entry"
    REGIME_SHIFT = "regime_shift"
    BREAKOUT = "breakout"
    ANOMALY = "anomaly"
    DIVERGENCE = "divergence"


@dataclass
class Signal:
    """Market signal."""
    signal_type: SignalType
    asset: str
    score: float
    confidence: float
    reasoning: str
    timestamp: datetime


@dataclass
class AgentDecision:
    """Agent decision output."""
    timestamp: datetime
    decision_type: str  # "research"|"monitor"|"alert_user"|"hypothesis_test"
    assets: List[str]
    reasoning: str
    recommended_action: str
    priority: int  # 1-5, 1=critical


@dataclass
class MarketContext:
    """Current market context for agent memory."""
    regime: str
    regime_confidence: float
    key_assets: List[str]
    active_signals: List[Signal]
    last_update: datetime


class AgentOrchestrator:
    """Main agent coordination and decision engine."""

    def __init__(self):
        """Initialize orchestrator."""
        self.context: MarketContext = MarketContext(
            regime="ranging",
            regime_confidence=0.5,
            key_assets=[],
            active_signals=[],
            last_update=datetime.utcnow(),
        )
        self.decision_history: List[AgentDecision] = []
        self.running = False

    async def run_continuous(self, interval_seconds: int = 60):
        """
        Main agent loop.

        Args:
            interval_seconds: Update interval
        """
        self.running = True
        while self.running:
            try:
                await self._update_cycle()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                print(f"Agent error: {e}")
                await asyncio.sleep(interval_seconds)

    async def _update_cycle(self):
        """Single update cycle."""
        self.context.last_update = datetime.utcnow()

        # 1. Scan signals from all layers
        signals = await self._scan_signals()
        self.context.active_signals = signals

        # 2. Detect anomalies
        anomalies = await self._detect_anomalies()
        if anomalies:
            signals.extend(anomalies)

        # 3. Prioritize signals
        priority_signals = self._prioritize_signals(signals)

        # 4. Generate decision
        if priority_signals:
            decision = await self._make_decision(priority_signals)
            self.decision_history.append(decision)
            await self._execute_decision(decision)

    async def _scan_signals(self) -> List[Signal]:
        """Scan all layers for new signals."""
        signals = []

        # This would connect to layers 1-8
        # For now, return empty (will be populated by real layer data)

        return signals

    async def _detect_anomalies(self) -> List[Signal]:
        """Detect market anomalies."""
        anomalies = []

        # Volume spikes without price move
        # Funding rate extremes
        # Whale accumulation
        # Exchange flow reversals
        # Sentiment divergence

        return anomalies

    def _prioritize_signals(self, signals: List[Signal]) -> List[Signal]:
        """Sort signals by priority."""
        return sorted(signals, key=lambda s: (-s.score, -s.confidence))

    async def _make_decision(self, signals: List[Signal]) -> AgentDecision:
        """Generate decision from signals."""
        if not signals:
            return AgentDecision(
                timestamp=datetime.utcnow(),
                decision_type="monitor",
                assets=[],
                reasoning="No actionable signals",
                recommended_action="Continue monitoring",
                priority=1,
            )

        top_signal = signals[0]

        # Determine action based on signal
        if top_signal.score >= 80 and top_signal.confidence >= 0.7:
            decision_type = "alert_user"
            priority = 5
            action = f"High-confidence signal: {top_signal.reasoning}"
        elif top_signal.score >= 60:
            decision_type = "research"
            priority = 3
            action = f"Research opportunity: {top_signal.asset}"
        else:
            decision_type = "monitor"
            priority = 2
            action = "Continue monitoring"

        return AgentDecision(
            timestamp=datetime.utcnow(),
            decision_type=decision_type,
            assets=[s.asset for s in signals[:3]],
            reasoning=f"Top signal: {top_signal.reasoning}",
            recommended_action=action,
            priority=priority,
        )

    async def _execute_decision(self, decision: AgentDecision):
        """Execute decision (logging, alerts, etc.)."""
        if decision.priority >= 4:
            # Would send email/webhook alert
            print(f"[ALERT] {decision.recommended_action}")
        elif decision.priority >= 3:
            # Would log to report
            print(f"[RESEARCH] {decision.recommended_action}")

    async def on_signal(self, signal: Signal) -> AgentDecision:
        """
        Event-driven trigger on new signal.

        Args:
            signal: New market signal

        Returns:
            Agent decision
        """
        self.context.active_signals.append(signal)

        # If high-confidence signal, trigger deep analysis
        if signal.confidence >= 0.75:
            return await self._deep_analysis(signal)
        else:
            decision = await self._make_decision([signal])
            return decision

    async def _deep_analysis(self, signal: Signal) -> AgentDecision:
        """Perform deep analysis on high-confidence signal."""
        # Would call:
        # - Asset deep dive
        # - Scenario analysis
        # - Hypothesis validation

        return AgentDecision(
            timestamp=datetime.utcnow(),
            decision_type="research",
            assets=[signal.asset],
            reasoning=f"Deep dive: {signal.reasoning}",
            recommended_action=f"Generate detailed report on {signal.asset}",
            priority=4,
        )

    async def challenge_hypothesis(self, hypothesis: str, asset: str) -> Dict[str, Any]:
        """
        Devil's advocate: counter-argument to thesis.

        Args:
            hypothesis: Investment thesis (e.g., "accumulation", "breakout")
            asset: Asset to test

        Returns:
            Rebuttal with counter-evidence
        """
        rebuttal = {
            "thesis": hypothesis,
            "asset": asset,
            "counter_arguments": [],
            "risk_score": 0.5,
            "verdict": "neutral",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Would analyze layer data to find contradicting signals
        if hypothesis == "accumulation":
            rebuttal["counter_arguments"].append(
                "Volume declining while price consolidating suggests lack of participation"
            )
            rebuttal["counter_arguments"].append("Whale outflows recent - confidence weakening")

        elif hypothesis == "breakout":
            rebuttal["counter_arguments"].append(
                "Resistance level remains intact on multiple timeframes"
            )
            rebuttal["counter_arguments"].append("Momentum indicators diverging from price")

        rebuttal["verdict"] = (
            "risky" if len(rebuttal["counter_arguments"]) >= 2 else "viable"
        )

        return rebuttal

    def stop(self):
        """Stop agent loop."""
        self.running = False

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "running": self.running,
            "current_regime": self.context.regime,
            "regime_confidence": self.context.regime_confidence,
            "active_signals": len(self.context.active_signals),
            "decisions_made": len(self.decision_history),
            "last_update": self.context.last_update.isoformat(),
        }
