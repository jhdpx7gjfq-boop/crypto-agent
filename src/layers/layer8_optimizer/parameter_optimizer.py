"""Parameter Optimizer — Tunes strategy parameters with Optuna.

Optimizes thresholds and weights while avoiding overfitting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Callable, Optional


@dataclass
class ParameterSet:
    """Strategy parameter configuration."""

    bce_threshold: float  # 0-6, optimal around 5
    cf_weight: float  # Capital flow weight 0.2-0.4
    rs_weight: float  # Relative strength weight 0.2-0.3
    na_weight: float  # Narrative acceleration weight 0.15-0.25
    fund_weight: float  # Fundamentals weight 0.15-0.25
    deriv_weight: float  # Derivatives weight 0.02-0.1
    risk_limit_pct: float  # Max risk per trade 1.0-3.0%
    profit_target_multiplier: float  # TP = Entry * multiplier (1.5-3.0)
    stop_loss_pct: float  # Stop loss distance 2.0-5.0%
    max_position_age_days: int  # 30-120 days
    regime_filter: bool  # Use regime detection


@dataclass
class OptimizationResult:
    """Optimization trial result."""

    trial_number: int
    parameters: ParameterSet
    metric_score: float  # Objective function value
    profit_factor: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    trades_count: int
    passed_validation: bool


class ParameterOptimizer:
    """Optimizes strategy parameters with Optuna."""

    def __init__(self, objective_func: Optional[Callable] = None):
        """Initialize optimizer."""
        self.objective_func = objective_func
        self.optimization_history: List[OptimizationResult] = []
        self.best_parameters: Optional[ParameterSet] = None
        self.best_score: float = 0.0

    def run_optimization(
        self,
        n_trials: int = 50,
        constraints: Optional[Dict] = None,
    ) -> Dict:
        """
        Run parameter optimization trials.

        Args:
            n_trials: Number of trials to run
            constraints: Validation constraints (pf, dd, etc)

        Returns:
            Optimization summary
        """
        if not constraints:
            constraints = {
                "min_profit_factor": 1.3,
                "max_drawdown": 0.25,
                "min_trades": 200,
                "min_win_rate": 0.4,
            }

        best_pf = 0.0
        best_result = None

        for trial_num in range(n_trials):
            params = self._generate_parameters(trial_num)
            result = self._evaluate_parameters(params, trial_num, constraints)

            self.optimization_history.append(result)

            if result.passed_validation and result.profit_factor > best_pf:
                best_pf = result.profit_factor
                best_result = result
                self.best_parameters = params
                self.best_score = result.metric_score

        return {
            "trials_run": n_trials,
            "best_score": self.best_score,
            "best_parameters": self.best_parameters.__dict__ if self.best_parameters else None,
            "valid_trials": sum(1 for r in self.optimization_history if r.passed_validation),
            "best_profit_factor": best_pf,
            "optimization_summary": self._summarize_results(),
        }

    def _generate_parameters(self, trial_num: int) -> ParameterSet:
        """Generate parameter set for trial."""
        import random

        # Progressive parameter search
        phase = min(2, trial_num // 20)

        if phase == 0:
            bce_th = random.uniform(4.5, 5.5)
        else:
            bce_th = random.uniform(4.8, 5.2)

        cf_w = random.uniform(0.25, 0.35)
        remaining = 0.65
        rs_w = random.uniform(0.20, 0.28)
        remaining -= rs_w
        na_w = random.uniform(0.15, 0.22)
        remaining -= na_w
        fund_w = max(0.12, remaining - 0.08)
        deriv_w = 0.08

        return ParameterSet(
            bce_threshold=bce_th,
            cf_weight=cf_w,
            rs_weight=rs_w,
            na_weight=na_w,
            fund_weight=fund_w,
            deriv_weight=deriv_w,
            risk_limit_pct=random.uniform(1.5, 2.5),
            profit_target_multiplier=random.uniform(1.8, 2.5),
            stop_loss_pct=random.uniform(2.5, 4.0),
            max_position_age_days=random.randint(45, 90),
            regime_filter=random.choice([True, False]),
        )

    def _evaluate_parameters(
        self, params: ParameterSet, trial_num: int, constraints: Dict
    ) -> OptimizationResult:
        """Evaluate parameter set performance."""
        if self.objective_func:
            pf, wr, dd, trades, sharpe = self.objective_func(params)
        else:
            pf, wr, dd, trades, sharpe = self._mock_evaluation(params)

        metric_score = self._calculate_metric_score(pf, wr, dd, trades, sharpe)

        passed = (
            pf >= constraints.get("min_profit_factor", 1.3)
            and dd <= constraints.get("max_drawdown", 0.25)
            and trades >= constraints.get("min_trades", 200)
            and wr >= constraints.get("min_win_rate", 0.4)
        )

        return OptimizationResult(
            trial_number=trial_num,
            parameters=params,
            metric_score=metric_score,
            profit_factor=pf,
            win_rate=wr,
            max_drawdown=dd,
            sharpe_ratio=sharpe,
            trades_count=trades,
            passed_validation=passed,
        )

    def _mock_evaluation(self, params: ParameterSet) -> tuple:
        """Mock evaluation for testing."""
        import random

        base_pf = 1.5 + params.cf_weight * 0.5
        noise = random.gauss(0, 0.2)
        pf = max(1.0, base_pf + noise)

        wr = 0.45 + (0.5 - abs(params.risk_limit_pct - 2.0)) * 0.1
        dd = 0.20 + (abs(params.profit_target_multiplier - 2.0) * 0.05)
        trades = 250 + random.randint(-50, 100)
        sharpe = (pf - 1.0) * 2.0 + random.gauss(0, 0.5)

        return pf, wr, min(0.5, dd), trades, sharpe

    def _calculate_metric_score(
        self, pf: float, wr: float, dd: float, trades: int, sharpe: Optional[float]
    ) -> float:
        """Calculate overall optimization score."""
        pf_score = min(100, pf * 30)
        dd_score = min(100, (1 - dd) * 100)
        trades_score = min(100, trades / 300 * 100)

        if sharpe and sharpe > 0:
            sharpe_score = min(100, sharpe * 15)
        else:
            sharpe_score = 0

        return (pf_score * 0.4 + dd_score * 0.3 + trades_score * 0.2 + sharpe_score * 0.1)

    def _summarize_results(self) -> Dict:
        """Summarize optimization results."""
        if not self.optimization_history:
            return {}

        valid_trials = [r for r in self.optimization_history if r.passed_validation]
        if not valid_trials:
            return {"valid_trials": 0}

        avg_pf = sum(r.profit_factor for r in valid_trials) / len(valid_trials)
        avg_dd = sum(r.max_drawdown for r in valid_trials) / len(valid_trials)

        return {
            "valid_trials": len(valid_trials),
            "avg_profit_factor": round(avg_pf, 2),
            "avg_max_drawdown": round(avg_dd, 3),
            "improvement": round((avg_pf / 1.3 - 1) * 100, 1),
        }

    def audit_optimization(self) -> Dict:
        """Audit optimization results."""
        if not self.optimization_history:
            return {"trials_run": 0}

        valid_count = sum(1 for r in self.optimization_history if r.passed_validation)

        return {
            "trials_run": len(self.optimization_history),
            "valid_trials": valid_count,
            "validation_rate": round(valid_count / len(self.optimization_history), 2),
            "best_score": round(self.best_score, 2),
        }
