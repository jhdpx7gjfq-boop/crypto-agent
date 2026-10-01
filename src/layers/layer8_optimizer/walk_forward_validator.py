"""Walk Forward Validator — Validates optimization on out-of-sample data.

Prevents overfitting through rolling window validation.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class WalkForwardWindow:
    """Single walk-forward test window."""

    window_id: int
    in_sample_start: datetime
    in_sample_end: datetime
    out_sample_start: datetime
    out_sample_end: datetime
    is_training: bool  # True = in-sample, False = out-sample


@dataclass
class WindowResults:
    """Results for a single window."""

    window_id: int
    profit_factor: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    trades_count: int
    passed: bool


@dataclass
class WalkForwardResults:
    """Complete walk-forward validation results."""

    asset: str
    timestamp: datetime
    total_windows: int
    in_sample_results: List[WindowResults]
    out_sample_results: List[WindowResults]
    validation_status: str  # "passed", "failed", "marginal"
    degradation_ratio: float  # Out/In performance
    consistency_score: float  # 0-100 (higher = more consistent)


class WalkForwardValidator:
    """Validates strategies with walk-forward analysis."""

    def __init__(self, window_size_days: int = 60, step_size_days: int = 20):
        """Initialize validator."""
        self.window_size_days = window_size_days
        self.step_size_days = step_size_days
        self.validation_history: Dict[str, list] = {}

    def create_windows(self, start_date: datetime, end_date: datetime) -> List[WalkForwardWindow]:
        """Create walk-forward windows."""
        windows = []
        window_id = 0
        current = start_date

        while current < end_date:
            in_start = current
            in_end = self._add_days(current, self.window_size_days)

            if in_end > end_date:
                break

            out_start = in_end
            out_end = self._add_days(in_end, self.window_size_days)

            if out_end > end_date:
                out_end = end_date

            windows.append(
                WalkForwardWindow(
                    window_id=window_id,
                    in_sample_start=in_start,
                    in_sample_end=in_end,
                    out_sample_start=out_start,
                    out_sample_end=out_end,
                    is_training=True,
                )
            )

            window_id += 1
            current = self._add_days(current, self.step_size_days)

        return windows

    def validate(
        self,
        asset: str,
        windows: List[WalkForwardWindow],
        in_sample_results: List[WindowResults],
        out_sample_results: List[WindowResults],
    ) -> WalkForwardResults:
        """
        Validate strategy across windows.

        Args:
            asset: Asset symbol
            windows: Walk-forward windows
            in_sample_results: Training window results
            out_sample_results: Test window results

        Returns:
            WalkForwardResults with validation status
        """
        passed_out = sum(1 for r in out_sample_results if r.passed)
        total_out = len(out_sample_results)

        degradation = self._calculate_degradation(in_sample_results, out_sample_results)
        consistency = self._calculate_consistency(out_sample_results)

        if passed_out >= total_out * 0.75 and degradation < 0.4:
            status = "passed"
        elif passed_out >= total_out * 0.50 and degradation < 0.6:
            status = "marginal"
        else:
            status = "failed"

        results = WalkForwardResults(
            asset=asset,
            timestamp=datetime.utcnow(),
            total_windows=len(windows),
            in_sample_results=in_sample_results,
            out_sample_results=out_sample_results,
            validation_status=status,
            degradation_ratio=degradation,
            consistency_score=consistency,
        )

        # Track history
        if asset not in self.validation_history:
            self.validation_history[asset] = []
        self.validation_history[asset].append(results)

        return results

    def _calculate_degradation(
        self, in_sample: List[WindowResults], out_sample: List[WindowResults]
    ) -> float:
        """Calculate performance degradation from IS to OOS."""
        if not in_sample or not out_sample:
            return 1.0

        avg_in_pf = sum(r.profit_factor for r in in_sample) / len(in_sample)
        avg_out_pf = sum(r.profit_factor for r in out_sample) / len(out_sample)

        if avg_in_pf == 0:
            return 1.0

        degradation = 1.0 - (avg_out_pf / avg_in_pf)
        return max(0.0, min(1.0, degradation))

    def _calculate_consistency(self, results: List[WindowResults]) -> float:
        """Calculate consistency across windows."""
        if not results:
            return 0.0

        passed = sum(1 for r in results if r.passed)
        consistency_pct = (passed / len(results)) * 100 if results else 0

        # Bonus for tight variation
        pfs = [r.profit_factor for r in results]
        if len(pfs) > 1:
            avg_pf = sum(pfs) / len(pfs)
            variance = sum((p - avg_pf) ** 2 for p in pfs) / len(pfs)
            std_dev = variance ** 0.5
            cv = std_dev / avg_pf if avg_pf > 0 else 1.0
            consistency_pct = max(0, consistency_pct - cv * 30)

        return min(100.0, consistency_pct)

    def _add_days(self, date: datetime, days: int) -> datetime:
        """Add days to datetime."""
        from datetime import timedelta

        return date + timedelta(days=days)

    def audit_validation(self, asset: str) -> Dict:
        """Audit validation results."""
        if asset not in self.validation_history:
            return {"asset": asset, "validations_run": 0}

        history = self.validation_history[asset]
        if not history:
            return {"asset": asset, "validations_run": 0}

        latest = history[-1]
        passed_count = sum(1 for r in history if r.validation_status == "passed")

        return {
            "asset": asset,
            "validations_run": len(history),
            "passed": passed_count,
            "latest_status": latest.validation_status,
            "latest_degradation": round(latest.degradation_ratio, 3),
            "latest_consistency": round(latest.consistency_score, 1),
        }
