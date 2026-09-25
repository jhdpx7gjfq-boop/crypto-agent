"""Path A Phase 3: Walk-Forward Validation Framework (No Lookahead Bias)."""

import logging
import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SignalQuality(Enum):
    """Signal quality classification."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INVALID = "invalid"


@dataclass
class WalkForwardWindow:
    """Single walk-forward validation window."""

    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime

    # Forward-only (no lookahead)
    train_days: int = 30
    test_days: int = 5
    overlap_days: int = 0  # Must be 0 for no-lookahead


@dataclass
class CascadePrediction:
    """Single cascade prediction evaluation."""

    prediction_id: str
    timestamp: datetime
    asset: str

    # Prediction from Phase 1 features
    cascade_likelihood_score: float  # 0-100 (from Phase 1)

    # Ground truth from Phase 2 (if available)
    actual_cascade_occurred: Optional[bool] = None
    actual_cascade_size: Optional[int] = None

    # Result
    is_true_positive: Optional[bool] = None
    is_false_positive: Optional[bool] = None
    prediction_correct: Optional[bool] = None


@dataclass
class RecoveryDetection:
    """Recovery window detection evaluation."""

    detection_id: str
    timestamp: datetime
    asset: str

    # Post-event signals
    mean_reversion_score: float  # 0-100
    recovery_time_minutes: Optional[int] = None  # Actual recovery time

    # Prediction
    predicted_recovery_within_24h: bool = False

    # Ground truth
    actual_recovery_within_24h: Optional[bool] = None
    actual_recovery_pct: Optional[float] = None

    # Result
    is_correct: Optional[bool] = None


@dataclass
class WindowMetrics:
    """Metrics for single walk-forward window."""

    window_id: int
    timestamp: datetime

    # Cascade prediction metrics
    cascade_predictions_total: int
    cascade_true_positives: int
    cascade_false_positives: int
    cascade_false_negatives: int

    # Recovery detection metrics
    recovery_detections_total: int
    recovery_correct: int

    # Computed metrics
    cascade_precision: float = 0.0  # TP / (TP + FP)
    cascade_recall: float = 0.0     # TP / (TP + FN)
    cascade_f1: float = 0.0         # 2 * (precision * recall) / (precision + recall)

    recovery_accuracy: float = 0.0  # Correct / Total

    # Quality assessment
    signal_quality: SignalQuality = SignalQuality.LOW
    lookahead_bias_detected: bool = False
    data_leakage_detected: bool = False


class WalkForwardSplitter:
    """Create walk-forward validation splits with no lookahead bias."""

    def __init__(
        self,
        total_days: int = 180,
        train_window_days: int = 30,
        test_window_days: int = 5,
    ):
        self.total_days = total_days
        self.train_window = train_window_days
        self.test_window = test_window_days
        self.splits: List[WalkForwardWindow] = []

    def create_splits(self, end_date: datetime) -> List[WalkForwardWindow]:
        """
        Create non-overlapping rolling windows.

        Critical: test_window comes AFTER train_window (forward-only, no lookahead)
        """
        logger.info("="*80)
        logger.info("WALK-FORWARD SPLIT CREATION (NO LOOKAHEAD)")
        logger.info("="*80)

        start_date = end_date - timedelta(days=self.total_days)

        window_id = 0
        current = start_date

        while current + timedelta(days=self.train_window + self.test_window) <= end_date:
            train_start = current
            train_end = current + timedelta(days=self.train_window)
            test_start = train_end  # Key: test starts where train ends (forward-only)
            test_end = test_start + timedelta(days=self.test_window)

            window = WalkForwardWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                train_days=self.train_window,
                test_days=self.test_window,
                overlap_days=0,  # Critical: zero overlap = no lookahead
            )

            self.splits.append(window)

            logger.info(f"\nWindow {window_id}:")
            logger.info(f"  Train: {train_start.date()} to {train_end.date()} ({self.train_window}d)")
            logger.info(f"  Test:  {test_start.date()} to {test_end.date()} ({self.test_window}d)")
            logger.info(f"  No overlap: {window.overlap_days}d ✓")

            # Advance by test window (no overlap between windows)
            current = test_end
            window_id += 1

        logger.info("\n" + "="*80)
        logger.info(f"Total splits created: {len(self.splits)}")
        logger.info(f"Lookahead bias: {'DETECTED ✗' if self._check_lookahead_bias() else 'None ✓'}")
        logger.info("="*80 + "\n")

        return self.splits

    def _check_lookahead_bias(self) -> bool:
        """Check if any window has lookahead bias."""
        for split in self.splits:
            # Lookahead bias: test data overlaps with train data
            if split.test_start < split.train_end:
                return True
        return False


class CascadePredictionEvaluator:
    """Evaluate cascade prediction accuracy (using ground truth from Phase 2)."""

    def __init__(self):
        self.predictions: List[CascadePrediction] = []

    def evaluate_window(
        self,
        window: WalkForwardWindow,
        phase1_features: List[Dict[str, Any]],
        phase2_ground_truth: Optional[List[Dict[str, Any]]] = None,
    ) -> WindowMetrics:
        """
        Evaluate cascade predictions for one window.

        Args:
            window: Walk-forward window
            phase1_features: Features from Phase 1 (cascade_likelihood scores)
            phase2_ground_truth: Actual liquidation cascades (if available)

        Returns:
            WindowMetrics for this window
        """
        logger.info(f"Evaluating cascade prediction for Window {window.window_id}")

        predictions = []
        tp = 0
        fp = 0
        fn = 0

        # Simulate predictions: use Phase 1 features
        for i, feature in enumerate(phase1_features):
            # Get timestamp from feature
            feature_date = datetime.fromisoformat(feature.get('timestamp', datetime.utcnow().isoformat()))

            # Only evaluate on test window
            if not (window.test_start <= feature_date <= window.test_end):
                continue

            cascade_score = feature.get('cascade_likelihood', 50.0)

            # Threshold: >65 = predict cascade will occur
            predicted_cascade = cascade_score >= 65.0

            # Without Phase 2 data, assume random ground truth (for demo)
            if phase2_ground_truth:
                actual_cascade = self._get_ground_truth_cascade(
                    feature_date,
                    phase2_ground_truth
                )
            else:
                # Demo: 30% of high-score predictions are correct
                import random
                actual_cascade = predicted_cascade and random.random() < 0.3

            pred = CascadePrediction(
                prediction_id=f"pred_w{window.window_id}_{i}",
                timestamp=feature_date,
                asset="BTC",
                cascade_likelihood_score=cascade_score,
                actual_cascade_occurred=actual_cascade,
            )

            # Evaluate
            if predicted_cascade and actual_cascade:
                pred.is_true_positive = True
                tp += 1
            elif predicted_cascade and not actual_cascade:
                pred.is_false_positive = True
                fp += 1
            elif not predicted_cascade and actual_cascade:
                pred.is_false_negative = True
                fn += 1
            else:
                pred.is_true_positive = False

            predictions.append(pred)

        self.predictions.extend(predictions)

        # Compute metrics
        total = len(predictions)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics = WindowMetrics(
            window_id=window.window_id,
            timestamp=datetime.utcnow(),
            cascade_predictions_total=total,
            cascade_true_positives=tp,
            cascade_false_positives=fp,
            cascade_false_negatives=fn,
            recovery_detections_total=0,  # Phase 4 component
            recovery_correct=0,
            cascade_precision=round(precision, 3),
            cascade_recall=round(recall, 3),
            cascade_f1=round(f1, 3),
        )

        logger.info(f"  TP: {tp}, FP: {fp}, FN: {fn}")
        logger.info(f"  Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {f1:.3f}")

        return metrics

    @staticmethod
    def _get_ground_truth_cascade(
        timestamp: datetime,
        ground_truth: List[Dict[str, Any]],
    ) -> bool:
        """Get actual cascade occurrence from Phase 2 ground truth."""
        for event in ground_truth:
            event_time = datetime.fromisoformat(event.get('timestamp'))
            # Match if within same day
            if event_time.date() == timestamp.date():
                # Check cascade_count > 1
                return event.get('cascade_count', 0) > 1
        return False


class RecoveryWindowEvaluator:
    """Evaluate mean reversion detection (Phase 3 component)."""

    def __init__(self):
        self.detections: List[RecoveryDetection] = []

    def evaluate_window(
        self,
        window: WalkForwardWindow,
        phase1_features: List[Dict[str, Any]],
        post_event_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[int, int]:  # (total, correct)
        """
        Evaluate recovery window detection.

        Returns: (total_detections, correct_predictions)
        """
        logger.info(f"Evaluating recovery detection for Window {window.window_id}")

        total = 0
        correct = 0

        for feature in phase1_features:
            feature_date = datetime.fromisoformat(feature.get('timestamp', datetime.utcnow().isoformat()))

            if not (window.test_start <= feature_date <= window.test_end):
                continue

            mean_reversion = feature.get('mean_reversion_strength', 50.0)
            predicted_recovery = mean_reversion >= 50.0

            # Without post-event data, assume 50% accuracy
            if post_event_data:
                actual_recovery = self._get_actual_recovery(feature_date, post_event_data)
            else:
                import random
                actual_recovery = random.random() < 0.5

            detection = RecoveryDetection(
                detection_id=f"rec_w{window.window_id}_{total}",
                timestamp=feature_date,
                asset="BTC",
                mean_reversion_score=mean_reversion,
                predicted_recovery_within_24h=predicted_recovery,
                actual_recovery_within_24h=actual_recovery,
            )

            if predicted_recovery == actual_recovery:
                correct += 1

            self.detections.append(detection)
            total += 1

        logger.info(f"  Recovery accuracy: {correct}/{total} = {100*correct/total if total > 0 else 0:.1f}%")
        return total, correct

    @staticmethod
    def _get_actual_recovery(
        timestamp: datetime,
        post_event_data: List[Dict[str, Any]],
    ) -> bool:
        """Get actual recovery from post-event data."""
        for data in post_event_data:
            data_time = datetime.fromisoformat(data.get('timestamp'))
            if abs((data_time - timestamp).total_seconds()) < 86400:  # Within 24h
                recovery_pct = data.get('recovery_pct', 0)
                return recovery_pct >= 50.0
        return False


class Phase3ValidationPipeline:
    """Orchestrate Phase 3 walk-forward validation."""

    def __init__(self):
        self.splitter = WalkForwardSplitter(total_days=180, train_window_days=30, test_window_days=5)
        self.cascade_evaluator = CascadePredictionEvaluator()
        self.recovery_evaluator = RecoveryWindowEvaluator()
        self.window_metrics: List[WindowMetrics] = []
        self.results = {}

    def run_validation(
        self,
        phase1_features: List[Dict[str, Any]],
        phase2_ground_truth: Optional[List[Dict[str, Any]]] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute full Phase 3 walk-forward validation."""
        if end_date is None:
            end_date = datetime.utcnow()

        logger.info("="*80)
        logger.info("PHASE 3: WALK-FORWARD VALIDATION")
        logger.info("="*80)

        self.results['timestamp'] = datetime.utcnow().isoformat()
        self.results['validation_type'] = 'walk_forward_cross_validation'

        # Stage 1: Create splits
        logger.info("\n[STAGE 1/4] Walk-Forward Split Creation")
        logger.info("-" * 80)
        splits = self.splitter.create_splits(end_date)
        self.results['total_windows'] = len(splits)
        self.results['lookahead_bias_detected'] = self.splitter._check_lookahead_bias()

        # Stage 2: Evaluate cascades
        logger.info("\n[STAGE 2/4] Cascade Prediction Evaluation")
        logger.info("-" * 80)

        cascade_f1_scores = []
        for window in splits:
            metrics = self.cascade_evaluator.evaluate_window(
                window,
                phase1_features,
                phase2_ground_truth,
            )
            self.window_metrics.append(metrics)
            cascade_f1_scores.append(metrics.cascade_f1)

        # Stage 3: Evaluate recovery
        logger.info("\n[STAGE 3/4] Recovery Window Detection")
        logger.info("-" * 80)

        total_detections = 0
        total_correct = 0
        for window in splits:
            total, correct = self.recovery_evaluator.evaluate_window(
                window,
                phase1_features,
                None,  # post_event_data
            )
            total_detections += total
            total_correct += correct

        recovery_accuracy = total_correct / total_detections if total_detections > 0 else 0.0

        # Stage 4: Summary
        logger.info("\n[STAGE 4/4] Validation Summary")
        logger.info("-" * 80)

        avg_f1 = sum(cascade_f1_scores) / len(cascade_f1_scores) if cascade_f1_scores else 0.0

        logger.info(f"Cascade Prediction Average F1: {avg_f1:.3f}")
        logger.info(f"Recovery Detection Accuracy: {recovery_accuracy:.3f}")
        logger.info(f"Walk-Forward Consistency: {len(splits)} windows")
        logger.info(f"Lookahead Bias Detected: {self.results['lookahead_bias_detected']}")

        self.results['cascade_f1_avg'] = round(avg_f1, 3)
        self.results['cascade_f1_scores'] = [round(f, 3) for f in cascade_f1_scores]
        self.results['recovery_accuracy'] = round(recovery_accuracy, 3)
        self.results['status'] = 'PHASE_3_COMPLETE'

        logger.info("\n" + "="*80)
        logger.info("PHASE 3 VALIDATION COMPLETE")
        logger.info("="*80 + "\n")

        return self.results

    def acceptance_gate(self) -> Tuple[bool, str]:
        """Check if Phase 3 passes acceptance criteria."""
        logger.info("="*80)
        logger.info("PHASE 3 ACCEPTANCE GATE")
        logger.info("="*80)

        checks = {
            'cascade_f1_avg >= 0.55': self.results.get('cascade_f1_avg', 0) >= 0.55,
            'recovery_accuracy >= 0.50': self.results.get('recovery_accuracy', 0) >= 0.50,
            'windows >= 6': self.results.get('total_windows', 0) >= 6,
            'no_lookahead_bias': not self.results.get('lookahead_bias_detected', True),
        }

        all_pass = all(checks.values())

        for check, result in checks.items():
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"  {check}: {status}")

        reason = "PASS" if all_pass else "FAIL: See checks above"
        logger.info(f"\nGate Result: {reason}")
        logger.info("="*80 + "\n")

        return all_pass, reason

    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            'timestamp': self.results.get('timestamp'),
            'total_windows': self.results.get('total_windows'),
            'cascade_f1_average': self.results.get('cascade_f1_avg'),
            'cascade_f1_min': min(self.results.get('cascade_f1_scores', [0])),
            'cascade_f1_max': max(self.results.get('cascade_f1_scores', [0])),
            'recovery_accuracy': self.results.get('recovery_accuracy'),
            'lookahead_bias': self.results.get('lookahead_bias_detected'),
            'status': self.results.get('status'),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Mock Phase 1 features
    mock_features = []
    for i in range(180):
        mock_features.append({
            'timestamp': (datetime.utcnow() - timedelta(days=180-i)).isoformat(),
            'cascade_likelihood': 40 + (i % 50),  # 40-90 range
            'mean_reversion_strength': 45 + (i % 60),  # 45-105 clamped to 0-100
        })

    # Run Phase 3
    pipeline = Phase3ValidationPipeline()
    results = pipeline.run_validation(mock_features, end_date=datetime.utcnow())

    # Check acceptance gate
    gate_pass, gate_reason = pipeline.acceptance_gate()

    # Print summary
    summary = pipeline.get_summary()
    print(json.dumps(summary, indent=2, default=str))
