"""
Statistical Validators for Backtest Results
Version: 1.0.0

Implements Phase 2 validation constraints:
- Profit Factor: total_gains / abs(total_losses)
- Maximum Drawdown: peak-to-trough loss percentage
- Sharpe Ratio: return per unit volatility
- Win Rate: percentage of winning trades
- Walk-Forward Validation: in-sample vs out-of-sample comparison
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

VERSION = "1.0.0"

# Phase 2 Validation Gates
VALIDATION_CONSTRAINTS = {
    "min_trades": 200,
    "profit_factor_min": 1.3,
    "max_drawdown_max": 0.25,  # 25%
    "sharpe_ratio_min": 0.5,  # Optional, for information
    "wfv_mandatory": True,  # Walk-forward validation required
}


@dataclass
class StatisticalValidation:
    """Result of statistical validation."""

    is_valid: bool
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    messages: List[str]


class StatisticalValidator:
    """
    Validates backtest results against Phase 2 constraints.

    All metrics must pass for final approval:
    - ✅ Min 200 trades
    - ✅ Profit factor > 1.3
    - ✅ Max drawdown < 25%
    - ✅ Walk-forward validation PASS
    """

    @staticmethod
    def validate_profit_factor(
        winning_pnl: float,
        losing_pnl: float,
    ) -> Tuple[float, bool]:
        """
        Calculate profit factor: total_gains / abs(total_losses).

        Returns: (profit_factor, passes_threshold)
        """
        if losing_pnl == 0:
            # No losses: either all winners or no trades
            pf = float("inf") if winning_pnl > 0 else 0.0
        else:
            pf = winning_pnl / abs(losing_pnl)

        threshold = VALIDATION_CONSTRAINTS["profit_factor_min"]
        passes = pf >= threshold

        logger.debug(f"Profit Factor: {pf:.3f} (threshold: {threshold}, pass: {passes})")
        return pf, passes

    @staticmethod
    def validate_max_drawdown(equity_curve: List[float]) -> Tuple[float, bool]:
        """
        Calculate maximum drawdown as percentage from peak.

        Returns: (max_drawdown_pct, passes_threshold)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0, True

        max_dd = 0.0
        peak = equity_curve[0]

        for equity in equity_curve:
            if equity > peak:
                peak = equity

            if peak > 0:
                dd = (peak - equity) / peak
                max_dd = max(max_dd, dd)

        threshold = VALIDATION_CONSTRAINTS["max_drawdown_max"]
        passes = max_dd <= threshold

        logger.debug(f"Max Drawdown: {max_dd*100:.2f}% (threshold: {threshold*100:.2f}%, pass: {passes})")
        return max_dd, passes

    @staticmethod
    def validate_win_rate(winning_trades: int, total_trades: int) -> Tuple[float, bool]:
        """
        Calculate win rate as percentage.

        Returns: (win_rate_pct, is_valid)
        """
        if total_trades == 0:
            return 0.0, False

        win_rate = (winning_trades / total_trades) * 100
        # Win rate is informational, not a hard constraint
        is_valid = True

        logger.debug(f"Win Rate: {win_rate:.2f}%")
        return win_rate, is_valid

    @staticmethod
    def validate_trade_count(total_trades: int) -> Tuple[bool]:
        """Validate minimum trade count."""
        min_trades = VALIDATION_CONSTRAINTS["min_trades"]
        passes = total_trades >= min_trades

        logger.debug(f"Trade Count: {total_trades} (minimum: {min_trades}, pass: {passes})")
        return passes

    @staticmethod
    def validate_sharpe_ratio(
        returns_pct: List[float],
        risk_free_rate: float = 0.02,
    ) -> Tuple[Optional[float], bool]:
        """
        Calculate Sharpe ratio (annualized).

        Returns: (sharpe_ratio, passes_threshold)
        """
        if not returns_pct or len(returns_pct) < 2:
            return None, True  # Can't compute, not a blocker

        mean_return = sum(returns_pct) / len(returns_pct)
        variance = sum((r - mean_return) ** 2 for r in returns_pct) / len(returns_pct)
        std_dev = variance ** 0.5

        if std_dev == 0:
            sharpe = 0.0 if mean_return == 0 else float("inf")
        else:
            sharpe = ((mean_return - risk_free_rate) / std_dev) * (250 ** 0.5)

        threshold = VALIDATION_CONSTRAINTS.get("sharpe_ratio_min", 0.5)
        passes = sharpe >= threshold if sharpe is not None else True

        logger.debug(f"Sharpe Ratio: {sharpe:.3f} (threshold: {threshold}, pass: {passes})")
        return sharpe, passes

    @staticmethod
    def validate_walk_forward(
        in_sample_pf: float,
        out_of_sample_pf: float,
        max_degradation: float = 0.3,  # Allow 30% degradation
    ) -> Tuple[bool, float]:
        """
        Validate walk-forward results.

        Out-of-sample performance must not degrade excessively from in-sample.

        Returns: (passes_wfv, degradation_pct)
        """
        if in_sample_pf == 0:
            return False, 100.0

        degradation = (in_sample_pf - out_of_sample_pf) / in_sample_pf
        passes = degradation <= max_degradation and out_of_sample_pf > 1.0

        logger.debug(
            f"Walk-Forward: IS_PF={in_sample_pf:.3f}, OOS_PF={out_of_sample_pf:.3f}, "
            f"degradation={degradation*100:.2f}% (threshold: {max_degradation*100:.2f}%, pass: {passes})"
        )
        return passes, degradation

    @classmethod
    def validate_backtest(
        cls,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        winning_pnl: float,
        losing_pnl: float,
        equity_curve: List[float],
        returns_pct: List[float],
        wfv_pass: bool = False,
        walk_forward_details: Optional[Dict] = None,
    ) -> StatisticalValidation:
        """
        Comprehensive backtest validation.

        Returns StatisticalValidation with all metrics and pass/fail status.
        """
        messages = []

        # 1. Trade count
        trades_pass = cls.validate_trade_count(total_trades)
        if not trades_pass:
            messages.append(f"❌ Trade count {total_trades} < {VALIDATION_CONSTRAINTS['min_trades']}")
        else:
            messages.append(f"✅ Trade count: {total_trades}")

        # 2. Profit factor
        pf, pf_pass = cls.validate_profit_factor(winning_pnl, losing_pnl)
        if not pf_pass:
            messages.append(f"❌ Profit factor {pf:.3f} < {VALIDATION_CONSTRAINTS['profit_factor_min']}")
        else:
            messages.append(f"✅ Profit factor: {pf:.3f}")

        # 3. Max drawdown
        max_dd, dd_pass = cls.validate_max_drawdown(equity_curve)
        if not dd_pass:
            messages.append(f"❌ Max drawdown {max_dd*100:.2f}% > {VALIDATION_CONSTRAINTS['max_drawdown_max']*100:.2f}%")
        else:
            messages.append(f"✅ Max drawdown: {max_dd*100:.2f}%")

        # 4. Win rate (informational)
        win_rate, _ = cls.validate_win_rate(winning_trades, total_trades)
        messages.append(f"ℹ️  Win rate: {win_rate:.2f}% ({winning_trades}/{total_trades})")

        # 5. Sharpe ratio (informational)
        sharpe, _ = cls.validate_sharpe_ratio(returns_pct)
        if sharpe is not None:
            messages.append(f"ℹ️  Sharpe ratio: {sharpe:.3f}")

        # 6. Walk-forward validation
        if VALIDATION_CONSTRAINTS["wfv_mandatory"]:
            if not wfv_pass:
                messages.append("❌ Walk-forward validation: FAILED")
            else:
                messages.append("✅ Walk-forward validation: PASSED")

        # Aggregate result
        is_valid = (
            trades_pass
            and pf_pass
            and dd_pass
            and (wfv_pass if VALIDATION_CONSTRAINTS["wfv_mandatory"] else True)
        )

        return StatisticalValidation(
            is_valid=is_valid,
            profit_factor=pf,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            messages=messages,
        )

    @staticmethod
    def format_validation_report(validation: StatisticalValidation) -> str:
        """Format validation result as readable report."""
        header = "=" * 60
        status = "✅ PASS" if validation.is_valid else "❌ FAIL"

        report = f"""{header}
BACKTEST VALIDATION REPORT
{header}

Status: {status}

Metrics:
{chr(10).join(f'  {msg}' for msg in validation.messages)}

{header}"""

        return report
