"""Overfit Detector — Identifies signs of curve-fitting.

Detects parameter optimization that doesn't generalize.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class OverfitMetrics:
    """Overfitting indicators."""

    parameter_sensitivity: float  # 0-100 (higher = more fragile)
    is_curve_fitted: bool
    in_sample_out_sample_ratio: float  # IS Sharpe / OOS Sharpe
    optimal_vs_baseline_improvement: float  # % improvement over baseline
    robustness_score: float  # 0-100 (how robust to parameter changes)
    recommendations: List[str]


class OverfitDetector:
    """Detects overfitting in optimization results."""

    def __init__(self):
        """Initialize detector."""
        self.analysis_history: Dict[str, list] = {}

    def detect_overfit(
        self,
        asset: str,
        in_sample_metrics: Dict,
        out_sample_metrics: Dict,
        parameter_set: Dict,
        baseline_metrics: Optional[Dict] = None,
    ) -> OverfitMetrics:
        """
        Detect overfitting in strategy.

        Args:
            asset: Asset symbol
            in_sample_metrics: IS backtest results {pf, dd, sharpe, trades}
            out_sample_metrics: OOS backtest results {pf, dd, sharpe, trades}
            parameter_set: Optimized parameters
            baseline_metrics: Baseline strategy metrics for comparison

        Returns:
            OverfitMetrics with overfitting indicators
        """
        is_pf = in_sample_metrics.get("profit_factor", 1.0)
        oos_pf = out_sample_metrics.get("profit_factor", 1.0)

        is_dd = in_sample_metrics.get("max_drawdown", 0.3)
        oos_dd = out_sample_metrics.get("max_drawdown", 0.3)

        is_sharpe = in_sample_metrics.get("sharpe_ratio", 1.0)
        oos_sharpe = out_sample_metrics.get("sharpe_ratio", 1.0)

        # Calculate overfitting signals
        pf_degradation = 1.0 - (oos_pf / is_pf) if is_pf > 0 else 0
        dd_increase = (oos_dd / is_dd - 1.0) if is_dd > 0 else 0
        sharpe_ratio = is_sharpe / oos_sharpe if oos_sharpe > 0 else 10.0

        is_curve_fitted = (
            pf_degradation > 0.4 or dd_increase > 0.3 or sharpe_ratio > 3.0
        )

        param_sensitivity = self._estimate_parameter_sensitivity(parameter_set)
        robustness = self._calculate_robustness_score(
            pf_degradation, dd_increase, sharpe_ratio, param_sensitivity
        )

        improvement = 0.0
        if baseline_metrics:
            baseline_pf = baseline_metrics.get("profit_factor", 1.3)
            improvement = ((is_pf / baseline_pf) - 1) * 100

        recommendations = self._generate_recommendations(
            is_curve_fitted,
            pf_degradation,
            dd_increase,
            param_sensitivity,
            robustness,
        )

        metrics = OverfitMetrics(
            parameter_sensitivity=param_sensitivity,
            is_curve_fitted=is_curve_fitted,
            in_sample_out_sample_ratio=sharpe_ratio,
            optimal_vs_baseline_improvement=improvement,
            robustness_score=robustness,
            recommendations=recommendations,
        )

        # Track history
        if asset not in self.analysis_history:
            self.analysis_history[asset] = []
        self.analysis_history[asset].append((datetime.utcnow(), metrics))

        return metrics

    def _estimate_parameter_sensitivity(self, parameters: Dict) -> float:
        """Estimate how sensitive strategy is to parameter changes."""
        if not parameters:
            return 50.0

        # Count parameters near boundaries
        sensitivity = 0.0
        boundary_sensitivity = 0

        for key, value in parameters.items():
            if key == "bce_threshold":
                if value < 4.7 or value > 5.3:
                    boundary_sensitivity += 1
            elif key in ["cf_weight", "rs_weight", "na_weight"]:
                if value < 0.22 or value > 0.32:
                    boundary_sensitivity += 1
            elif key == "stop_loss_pct":
                if value < 2.2 or value > 4.5:
                    boundary_sensitivity += 1

        sensitivity = (boundary_sensitivity / max(1, len(parameters))) * 100
        return min(100.0, sensitivity)

    def _calculate_robustness_score(
        self,
        pf_degradation: float,
        dd_increase: float,
        sharpe_ratio: float,
        param_sensitivity: float,
    ) -> float:
        """Calculate overall robustness score."""
        pf_score = max(0, 100 - pf_degradation * 100)
        dd_score = max(0, 100 - dd_increase * 100)
        sharpe_score = max(0, 100 - (sharpe_ratio - 1.0) * 20)
        param_score = 100 - param_sensitivity

        robustness = (pf_score * 0.3 + dd_score * 0.3 + sharpe_score * 0.2 + param_score * 0.2)
        return max(0.0, min(100.0, robustness))

    def _generate_recommendations(
        self,
        is_curve_fitted: bool,
        pf_degradation: float,
        dd_increase: float,
        param_sensitivity: float,
        robustness: float,
    ) -> List[str]:
        """Generate recommendations for improving robustness."""
        recommendations = []

        if is_curve_fitted:
            recommendations.append("Strategy shows signs of overfitting - consider wider parameter ranges")

        if pf_degradation > 0.4:
            recommendations.append("Large profit factor degradation OOS - reduce optimization strictness")

        if dd_increase > 0.3:
            recommendations.append("Drawdown increased significantly OOS - adjust risk limits")

        if param_sensitivity > 70:
            recommendations.append("Parameters are near boundaries - consider re-optimizing with wider ranges")

        if robustness < 50:
            recommendations.append("Strategy lacks robustness - increase out-of-sample data or simplify parameters")

        if not recommendations:
            recommendations.append("Strategy appears robust - safe to deploy")

        return recommendations

    def audit_overfit(self, asset: str) -> Dict:
        """Audit overfitting analysis."""
        if asset not in self.analysis_history:
            return {"asset": asset, "analyses_run": 0}

        history = self.analysis_history[asset]
        if not history:
            return {"asset": asset, "analyses_run": 0}

        overfitted_count = sum(1 for _, m in history if m.is_curve_fitted)
        latest = history[-1][1]

        return {
            "asset": asset,
            "analyses_run": len(history),
            "overfitted_cases": overfitted_count,
            "latest_robustness": round(latest.robustness_score, 1),
            "latest_is_oos_ratio": round(latest.in_sample_out_sample_ratio, 2),
        }
