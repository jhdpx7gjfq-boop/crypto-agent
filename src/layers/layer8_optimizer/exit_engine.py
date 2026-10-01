"""Dynamic Exit Engine — Determines optimal exit conditions.

Risk management, profit taking, stop loss optimization.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class RiskMetrics:
    """Risk analysis for position."""

    entry_price: float
    current_price: float
    stop_loss_price: float
    risk_amount: float  # Entry - stop loss
    current_loss: float  # Current vs entry
    risk_reward_ratio: float
    position_risk_pct: float  # Risk as % of position
    score: float


@dataclass
class ProfitMetrics:
    """Profit target analysis."""

    entry_price: float
    current_price: float
    unrealized_gain: float  # % gain
    profit_target_1: float  # First TP
    profit_target_2: float  # Second TP
    profit_target_3: float  # Third TP
    current_gain_pct: float
    score: float


@dataclass
class ExitSignal:
    """Exit signal with reasoning."""

    exit_type: str  # "stop_loss", "take_profit", "exit", "hold"
    confidence: float  # 0-1
    exit_price: float
    reasoning: str
    risk_score: float  # 0-100 (higher = more risk)


@dataclass
class DynamicExitAnalysis:
    """Complete exit analysis."""

    asset: str
    timestamp: datetime
    entry_price: float
    current_price: float
    days_in_trade: int
    risk_metrics: RiskMetrics
    profit_metrics: ProfitMetrics
    exit_signal: ExitSignal
    regime_context: str  # bullish, bearish, ranging
    exit_score: float  # 0-100


class DynamicExitEngine:
    """Generates dynamic exit signals based on risk/reward."""

    def __init__(self, risk_limit_pct: float = 2.0):
        """Initialize exit engine."""
        self.risk_limit_pct = risk_limit_pct
        self.exit_history: Dict[str, list] = {}

    def analyze_exit(
        self,
        asset: str,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        profit_targets: Dict,
        days_in_trade: int,
        regime: str,
    ) -> DynamicExitAnalysis:
        """
        Analyze exit conditions for position.

        Args:
            asset: Asset symbol
            entry_price: Entry price
            current_price: Current market price
            stop_loss: Stop loss level
            profit_targets: {target_1, target_2, target_3}
            days_in_trade: Days position held
            regime: Market regime (bullish, bearish, ranging)

        Returns:
            DynamicExitAnalysis with exit signal
        """
        risk = self._analyze_risk(entry_price, current_price, stop_loss)
        profit = self._analyze_profit(
            entry_price,
            current_price,
            profit_targets.get("target_1", entry_price * 1.5),
            profit_targets.get("target_2", entry_price * 2.0),
            profit_targets.get("target_3", entry_price * 3.0),
        )

        exit_signal = self._generate_exit_signal(
            risk, profit, days_in_trade, regime
        )

        exit_score = self._calculate_exit_score(risk, profit, exit_signal)

        analysis = DynamicExitAnalysis(
            asset=asset,
            timestamp=datetime.utcnow(),
            entry_price=entry_price,
            current_price=current_price,
            days_in_trade=days_in_trade,
            risk_metrics=risk,
            profit_metrics=profit,
            exit_signal=exit_signal,
            regime_context=regime,
            exit_score=exit_score,
        )

        # Track history
        if asset not in self.exit_history:
            self.exit_history[asset] = []
        self.exit_history[asset].append(analysis)

        return analysis

    def _analyze_risk(
        self, entry: float, current: float, stop_loss: float
    ) -> RiskMetrics:
        """Analyze position risk."""
        risk_amount = entry - stop_loss
        current_loss = entry - current
        rr_ratio = abs((current - entry) / risk_amount) if risk_amount != 0 else 0
        position_risk_pct = (risk_amount / entry * 100) if entry > 0 else 0

        # Score based on risk metrics
        if position_risk_pct > self.risk_limit_pct * 2:
            score = max(0, 30 - (position_risk_pct - self.risk_limit_pct * 2) * 2)
        elif position_risk_pct > self.risk_limit_pct:
            score = 50 - (position_risk_pct - self.risk_limit_pct) * 5
        else:
            score = 80

        if current > entry:
            score = min(100, score + 10)

        return RiskMetrics(
            entry_price=entry,
            current_price=current,
            stop_loss_price=stop_loss,
            risk_amount=risk_amount,
            current_loss=current_loss,
            risk_reward_ratio=rr_ratio,
            position_risk_pct=position_risk_pct,
            score=score,
        )

    def _analyze_profit(
        self,
        entry: float,
        current: float,
        tp1: float,
        tp2: float,
        tp3: float,
    ) -> ProfitMetrics:
        """Analyze profit metrics."""
        unrealized = ((current - entry) / entry * 100) if entry > 0 else 0
        current_gain = unrealized

        # Score based on profit progression
        if current >= tp3:
            score = min(100, 90 + (current - tp3) / (entry * 0.1))
        elif current >= tp2:
            score = 75 + (current - tp2) / (tp3 - tp2) * 15
        elif current >= tp1:
            score = 60 + (current - tp1) / (tp2 - tp1) * 15
        elif current > entry:
            score = 50 + unrealized * 0.5
        else:
            score = max(0, 40 + unrealized * 0.3)

        return ProfitMetrics(
            entry_price=entry,
            current_price=current,
            unrealized_gain=unrealized,
            profit_target_1=tp1,
            profit_target_2=tp2,
            profit_target_3=tp3,
            current_gain_pct=current_gain,
            score=score,
        )

    def _generate_exit_signal(
        self, risk: RiskMetrics, profit: ProfitMetrics, days: int, regime: str
    ) -> ExitSignal:
        """Generate exit signal."""
        if risk.current_loss > risk.risk_amount:
            return ExitSignal(
                exit_type="stop_loss",
                confidence=0.95,
                exit_price=risk.stop_loss_price,
                reasoning="Stop loss hit",
                risk_score=95,
            )

        if profit.current_price >= profit.profit_target_3:
            return ExitSignal(
                exit_type="take_profit",
                confidence=0.9,
                exit_price=profit.profit_target_3,
                reasoning="TP3 reached",
                risk_score=10,
            )

        if profit.current_price >= profit.profit_target_2 and days > 45:
            return ExitSignal(
                exit_type="take_profit",
                confidence=0.8,
                exit_price=profit.profit_target_2,
                reasoning="TP2 + time exit",
                risk_score=20,
            )

        if regime == "bearish" and profit.current_price >= profit.profit_target_1:
            return ExitSignal(
                exit_type="exit",
                confidence=0.7,
                exit_price=profit.profit_target_1,
                reasoning="Regime bearish, take profits",
                risk_score=40,
            )

        if days > 90 and regime != "bullish":
            return ExitSignal(
                exit_type="exit",
                confidence=0.6,
                exit_price=profit.current_price,
                reasoning="Position aged, no strong regime",
                risk_score=50,
            )

        return ExitSignal(
            exit_type="hold",
            confidence=0.5,
            exit_price=profit.current_price,
            reasoning="Hold - targets not reached",
            risk_score=risk.score,
        )

    def _calculate_exit_score(
        self, risk: RiskMetrics, profit: ProfitMetrics, signal: ExitSignal
    ) -> float:
        """Calculate overall exit quality score."""
        return (risk.score * 0.4 + profit.score * 0.4 + (100 - signal.risk_score) * 0.2)

    def audit_exits(self, asset: str) -> Dict:
        """Audit exit history."""
        if asset not in self.exit_history:
            return {"asset": asset, "exits_analyzed": 0}

        history = self.exit_history[asset]
        exit_types = {}
        for analysis in history:
            t = analysis.exit_signal.exit_type
            exit_types[t] = exit_types.get(t, 0) + 1

        avg_exit_score = sum(a.exit_score for a in history) / len(history) if history else 0

        return {
            "asset": asset,
            "exits_analyzed": len(history),
            "exit_type_breakdown": exit_types,
            "avg_exit_score": round(avg_exit_score, 1),
        }
