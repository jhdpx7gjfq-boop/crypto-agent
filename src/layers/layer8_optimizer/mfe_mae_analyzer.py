"""MFE/MAE Analyzer — Maximum Favorable/Adverse Excursion analysis.

Analyzes price movement extremes during trade lifetime.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class TradeExcursion:
    """Maximum price extremes during trade."""

    entry_price: float
    highest_price: float  # Peak during trade
    lowest_price: float  # Trough during trade
    mfe: float  # Maximum Favorable Excursion (% gain from entry)
    mae: float  # Maximum Adverse Excursion (% loss from entry)
    exit_price: float
    final_profit_loss: float  # % actual P&L
    mfe_ratio: float  # How much of MFE was captured
    mae_managed: float  # % of MAE avoided


@dataclass
class MFEMAEAnalysis:
    """Complete MFE/MAE analysis."""

    asset: str
    timestamp: datetime
    entry_price: float
    exit_price: float
    excursion: TradeExcursion
    trade_quality: str  # "ideal", "good", "ok", "poor"
    exit_efficiency: float  # 0-1 (how close to optimal exit)
    risk_management_score: float  # 0-100


class MFEMAEAnalyzer:
    """Analyzes trade excursions for quality metrics."""

    def __init__(self):
        """Initialize analyzer."""
        self.analysis_history: Dict[str, list] = {}

    def analyze_trade(
        self,
        asset: str,
        entry_price: float,
        exit_price: float,
        high_price: float,
        low_price: float,
        stop_loss: float,
    ) -> MFEMAEAnalysis:
        """
        Analyze trade excursion metrics.

        Args:
            asset: Asset symbol
            entry_price: Entry price
            exit_price: Exit price (realized P&L)
            high_price: Highest price during trade
            low_price: Lowest price during trade
            stop_loss: Stop loss level

        Returns:
            MFEMAEAnalysis with excursion metrics
        """
        mfe = ((high_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        mae = ((entry_price - low_price) / entry_price * 100) if entry_price > 0 else 0
        final_pl = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0

        # How much of favorable excursion was captured
        if mfe > 0:
            mfe_ratio = final_pl / mfe if final_pl > 0 else 0
        else:
            mfe_ratio = 1.0

        # How well was MAE managed
        max_allowed_loss = ((entry_price - stop_loss) / entry_price * 100) if entry_price > 0 else 0
        if max_allowed_loss > 0:
            mae_managed = 1.0 - (mae / max_allowed_loss) if mae > 0 else 1.0
        else:
            mae_managed = 1.0

        excursion = TradeExcursion(
            entry_price=entry_price,
            highest_price=high_price,
            lowest_price=low_price,
            mfe=mfe,
            mae=mae,
            exit_price=exit_price,
            final_profit_loss=final_pl,
            mfe_ratio=mfe_ratio,
            mae_managed=mae_managed,
        )

        trade_quality = self._classify_trade_quality(mfe, mae, final_pl, mfe_ratio)
        exit_efficiency = self._calculate_exit_efficiency(mfe, final_pl)
        risk_score = self._calculate_risk_management(mae, mae_managed, max_allowed_loss)

        analysis = MFEMAEAnalysis(
            asset=asset,
            timestamp=datetime.utcnow(),
            entry_price=entry_price,
            exit_price=exit_price,
            excursion=excursion,
            trade_quality=trade_quality,
            exit_efficiency=exit_efficiency,
            risk_management_score=risk_score,
        )

        # Track history
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append(analysis)

        return analysis

    def _classify_trade_quality(
        self, mfe: float, mae: float, final_pl: float, mfe_ratio: float
    ) -> str:
        """Classify trade quality."""
        if mfe > 30 and final_pl > 20 and mfe_ratio > 0.5:
            return "ideal"
        elif mfe > 15 and final_pl > 10 and mfe_ratio > 0.4:
            return "good"
        elif final_pl > 0 or mae < 10:
            return "ok"
        else:
            return "poor"

    def _calculate_exit_efficiency(self, mfe: float, final_pl: float) -> float:
        """Calculate how well exit was timed relative to MFE."""
        if mfe <= 0:
            return 1.0 if final_pl <= 0 else 0.5
        return min(1.0, final_pl / mfe) if final_pl > 0 else 0.0

    def _calculate_risk_management(
        self, mae: float, mae_managed: float, max_loss: float
    ) -> float:
        """Calculate risk management score."""
        if mae > max_loss:
            return 0.0
        if mae_managed >= 0.8:
            return 90 + mae_managed * 10
        elif mae_managed >= 0.5:
            return 70 + mae_managed * 20
        elif mae_managed >= 0.2:
            return 50 + mae_managed * 20
        else:
            return 30

    def audit_mfe_mae(self, asset: str) -> Dict:
        """Audit MFE/MAE analysis."""
        if asset not in self.analysis_history:
            return {"asset": asset, "trades_analyzed": 0}

        history = self.analysis_history[asset]
        if not history:
            return {"asset": asset, "trades_analyzed": 0}

        ideal_trades = sum(1 for a in history if a.trade_quality == "ideal")
        good_trades = sum(1 for a in history if a.trade_quality == "good")
        poor_trades = sum(1 for a in history if a.trade_quality == "poor")

        avg_exit_efficiency = sum(a.exit_efficiency for a in history) / len(history)
        avg_risk_score = sum(a.risk_management_score for a in history) / len(history)

        return {
            "asset": asset,
            "trades_analyzed": len(history),
            "ideal_trades": ideal_trades,
            "good_trades": good_trades,
            "poor_trades": poor_trades,
            "avg_exit_efficiency": round(avg_exit_efficiency, 2),
            "avg_risk_management_score": round(avg_risk_score, 1),
        }
