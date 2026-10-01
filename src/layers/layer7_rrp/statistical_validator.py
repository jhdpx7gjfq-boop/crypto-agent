"""Statistical Validator — Walk-forward validation for revival predictions.

Validates revival predictions against realized outcomes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics


@dataclass
class RevivalOutcome:
    """Actual outcome of a revival prediction."""

    asset: str
    prediction_date: datetime
    predicted_score: float
    predicted_stage: str
    actual_peak_date: Optional[datetime]
    peak_price: float
    realized_gain: float  # % gain from base
    days_to_peak: Optional[int]
    accuracy_score: float  # 0-1


@dataclass
class StatisticalValidation:
    """Statistical validation results."""

    asset: str
    predictions_tested: int
    accurate_predictions: int  # score >= threshold
    accuracy_rate: float  # 0-1
    avg_days_to_peak: float
    avg_realized_gain: float
    profit_factor: float  # gains / losses
    max_drawdown: float
    sharpe_ratio: Optional[float]
    validation_passed: bool


class RevivalValidator:
    """Validates revival predictions with walk-forward analysis."""

    def __init__(self, accuracy_threshold: float = 0.6):
        """Initialize validator."""
        self.accuracy_threshold = accuracy_threshold
        self.prediction_history: Dict[str, List[RevivalOutcome]] = {}
        self.validation_results: Dict[str, StatisticalValidation] = {}

    def record_prediction(
        self,
        asset: str,
        predicted_score: float,
        predicted_stage: str,
        base_price: float,
    ) -> None:
        """Record a revival prediction for later validation."""
        if asset not in self.prediction_history:
            self.prediction_history[asset] = []

        # Create placeholder outcome (to be filled when price data arrives)
        outcome = RevivalOutcome(
            asset=asset,
            prediction_date=datetime.utcnow(),
            predicted_score=predicted_score,
            predicted_stage=predicted_stage,
            actual_peak_date=None,
            peak_price=base_price,
            realized_gain=0.0,
            days_to_peak=None,
            accuracy_score=0.0,
        )
        self.prediction_history[asset].append(outcome)

    def validate_prediction(
        self,
        asset: str,
        prediction_index: int,
        peak_price: float,
        peak_date: Optional[datetime] = None,
    ) -> Optional[RevivalOutcome]:
        """
        Validate a prediction against realized outcome.

        Args:
            asset: Asset symbol
            prediction_index: Index of prediction to validate
            peak_price: Actual peak price reached
            peak_date: Date peak was reached

        Returns:
            Updated RevivalOutcome
        """
        if asset not in self.prediction_history:
            return None

        if prediction_index >= len(self.prediction_history[asset]):
            return None

        outcome = self.prediction_history[asset][prediction_index]
        base_price = outcome.peak_price  # Initial price

        outcome.peak_price = peak_price
        outcome.actual_peak_date = peak_date or datetime.utcnow()
        outcome.realized_gain = ((peak_price - base_price) / base_price * 100) if base_price > 0 else 0

        if outcome.actual_peak_date:
            days = (outcome.actual_peak_date - outcome.prediction_date).days
            outcome.days_to_peak = max(0, days)

        # Calculate accuracy
        outcome.accuracy_score = self._calc_accuracy(
            outcome.predicted_score, outcome.realized_gain, outcome.predicted_stage
        )

        return outcome

    def validate_asset(self, asset: str) -> Optional[StatisticalValidation]:
        """
        Run walk-forward validation for asset.

        Minimum: >=20 predictions, accuracy >=50%, profit factor >1.0
        """
        if asset not in self.prediction_history:
            return None

        outcomes = self.prediction_history[asset]
        if len(outcomes) < 20:
            return None

        # Filter completed outcomes
        completed = [o for o in outcomes if o.days_to_peak is not None]
        if len(completed) < 20:
            return None

        accurate = sum(1 for o in completed if o.accuracy_score >= self.accuracy_threshold)
        accuracy_rate = accurate / len(completed) if completed else 0.0

        gains = [o.realized_gain for o in completed if o.realized_gain > 0]
        losses = [abs(o.realized_gain) for o in completed if o.realized_gain < 0]

        avg_gain = sum(gains) / len(gains) if gains else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 1.0

        profit_factor = (sum(gains) / sum(losses)) if losses and sum(losses) > 0 else float("inf")
        max_dd = self._calc_max_drawdown(completed)

        validation = StatisticalValidation(
            asset=asset,
            predictions_tested=len(completed),
            accurate_predictions=accurate,
            accuracy_rate=accuracy_rate,
            avg_days_to_peak=(
                sum(o.days_to_peak for o in completed if o.days_to_peak) / len(completed)
                if completed
                else 0.0
            ),
            avg_realized_gain=sum(o.realized_gain for o in completed) / len(completed)
            if completed
            else 0.0,
            profit_factor=min(profit_factor, 100.0),  # Cap at 100x
            max_drawdown=max_dd,
            sharpe_ratio=self._calc_sharpe_ratio(completed),
            validation_passed=self._check_validation_pass(
                accuracy_rate, profit_factor, len(completed)
            ),
        )

        self.validation_results[asset] = validation
        return validation

    def _calc_accuracy(self, predicted_score: float, realized_gain: float, stage: str) -> float:
        """Calculate prediction accuracy 0-1."""
        # Score based on stage alignment and gain
        if stage == "confirmed":
            target_gain = 100.0
        elif stage == "emerging":
            target_gain = 50.0
        elif stage == "early_signs":
            target_gain = 20.0
        else:
            target_gain = 0.0

        if target_gain == 0:
            return 0.0

        # How close realized_gain was to target
        accuracy = 1.0 - abs(realized_gain - target_gain) / (target_gain + 1)
        return max(0.0, min(1.0, accuracy))

    def _calc_max_drawdown(self, outcomes: List[RevivalOutcome]) -> float:
        """Calculate max drawdown from outcomes."""
        if not outcomes:
            return 0.0

        cumulative = 1.0
        peak = 1.0
        max_dd = 0.0

        for outcome in sorted(outcomes, key=lambda x: x.prediction_date):
            ret = 1.0 + (outcome.realized_gain / 100.0)
            cumulative *= ret
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / peak
            max_dd = max(max_dd, dd)

        return max_dd

    def _calc_sharpe_ratio(self, outcomes: List[RevivalOutcome]) -> Optional[float]:
        """Calculate Sharpe ratio."""
        if len(outcomes) < 2:
            return None

        returns = [o.realized_gain / 100.0 for o in outcomes]
        if not returns or len(returns) < 2:
            return None

        mean_ret = statistics.mean(returns)
        std_ret = statistics.stdev(returns)

        if std_ret == 0:
            return None

        # Annual Sharpe (simplified)
        return (mean_ret * 252) / (std_ret * (252 ** 0.5))

    def _check_validation_pass(self, accuracy: float, pf: float, count: int) -> bool:
        """Check if validation passes criteria."""
        return accuracy >= 0.5 and pf > 1.0 and count >= 20

    def audit_validation(self, asset: str) -> Dict:
        """Audit validation results."""
        if asset not in self.validation_results:
            return {"asset": asset, "validation_status": "not_run"}

        val = self.validation_results[asset]
        return {
            "asset": asset,
            "predictions_tested": val.predictions_tested,
            "accuracy_rate": round(val.accuracy_rate, 3),
            "profit_factor": round(val.profit_factor, 2),
            "max_drawdown": round(val.max_drawdown, 3),
            "validation_passed": val.validation_passed,
        }
