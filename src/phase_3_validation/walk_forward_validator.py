#!/usr/bin/env python3
"""
Phase 3: Walk-Forward Validation (WFV)

Validates BCE and scoring models against ground truth with no lookahead bias.

Architecture:
1. PIT (Period In Time): In-sample backtest with cross-validation
2. OOS (Out-Of-Sample): Hold-out test set (20% coins)
3. WFV (Walk-Forward): Rolling time windows (no lookahead)

Timeline: Oct 24-Nov 6, 2026
Gate: Validation Pass Rate ≥75% (Oct 31 checkpoint)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
GT_DIR = DATA_DIR / "ground_truth" / "phase_2"
PHASE1_DIR = DATA_DIR / "raw" / "phase_1"
VAL_DIR = DATA_DIR / "validation" / "phase_3"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_3"

LOG_DIR.mkdir(parents=True, exist_ok=True)
VAL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"wfv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WalkForwardValidator:
    """Walk-Forward Validation engine with no lookahead bias"""

    def __init__(self, test_start_date="2024-01-01", test_end_date="2026-12-31"):
        self.test_start = pd.to_datetime(test_start_date)
        self.test_end = pd.to_datetime(test_end_date)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "3_walk_forward_validation",
            "windows": [],
            "summary": {}
        }

    def load_ground_truth(self, gt_csv: Path) -> Dict:
        """Load Phase 2 ground truth labels"""
        logger.info(f"Loading ground truth from {gt_csv}")

        df = pd.read_csv(gt_csv)
        gt = {}

        for _, row in df.iterrows():
            coin_id = row.get("coin_id")
            if coin_id:
                gt[coin_id] = {
                    "symbol": row.get("symbol"),
                    "label": row.get("label"),  # Q1, Q2, SKIP
                    "confidence": int(row.get("confidence", 0))
                }

        logger.info(f"Loaded {len(gt)} labeled coins")
        return gt

    def load_ohlcv_data(self, coin_id: str) -> Optional[pd.DataFrame]:
        """Load Phase 1 OHLCV data for a coin"""
        try:
            # Try to find parquet file
            coin_files = list(PHASE1_DIR.glob(f"*_{coin_id}.parquet"))
            if not coin_files:
                return None

            df = pd.read_parquet(coin_files[0])
            df.index = pd.to_datetime(df.index)
            return df.sort_index()
        except Exception as e:
            logger.debug(f"Could not load data for {coin_id}: {e}")
            return None

    def split_train_test(self, all_coins: List[str], test_ratio=0.2) -> Tuple[List[str], List[str]]:
        """Split coins into train (PIT) and test (OOS)"""
        n_test = max(1, int(len(all_coins) * test_ratio))
        test_coins = all_coins[-n_test:]  # Last 20% (deterministic)
        train_coins = all_coins[:-n_test]  # First 80%

        logger.info(f"Train (PIT): {len(train_coins)} coins")
        logger.info(f"Test (OOS): {len(test_coins)} coins")

        return train_coins, test_coins

    def create_windows(self) -> List[Tuple[datetime, datetime, datetime]]:
        """Create rolling time windows for WFV"""
        windows = []

        # 6 rolling windows: 2-year training, 12-month testing
        train_window = timedelta(days=730)  # ~2 years
        test_window = timedelta(days=365)   # ~1 year

        # Start from 2022 to allow 2-year training window before test period
        window_start = pd.to_datetime("2022-01-01")

        while window_start + train_window + test_window <= self.test_end:
            train_start = window_start
            train_end = window_start + train_window
            test_start = train_end
            test_end = train_end + test_window

            windows.append((train_start, train_end, test_start, test_end))

            # Move window forward by 6 months
            window_start += timedelta(days=180)

        logger.info(f"Created {len(windows)} rolling windows")
        for i, (ts, te, vs, ve) in enumerate(windows):
            logger.info(f"  Window {i+1}: Train {ts.date()}-{te.date()}, Test {vs.date()}-{ve.date()}")

        return windows

    def compute_bce_score(self, df: pd.DataFrame, lookback_periods=60) -> float:
        """
        Compute Bottom Confirmation Engine (BCE) score

        Score 0-6 based on:
        1. Wyckoff structure (recent low vs historical)
        2. Volume exhaustion (volume declining trend)
        3. Active addresses trend
        4. Price momentum
        5. Support hold
        6. Buy signal confirmation

        Returns: score 0-6 (where ≥5 = Q2 candidate)
        """
        if len(df) < lookback_periods:
            return 0.0

        score = 0.0
        recent = df.iloc[-lookback_periods:]

        try:
            # 1. Relative price position (low point detection)
            recent_low = recent['low'].min()
            hist_low = df['low'].min()
            if recent_low <= hist_low * 1.1:  # Within 10% of all-time low
                score += 1.0

            # 2. Volume trend (declining = exhaustion)
            vol_trend = recent['volume'].iloc[-20:].mean() / recent['volume'].iloc[:20].mean()
            if vol_trend < 1.5:  # Volume not rising dramatically
                score += 1.0

            # 3. Price recovery from low
            low_idx = recent['low'].idxmin()
            low_price = recent.loc[low_idx, 'low']
            current_price = recent['close'].iloc[-1]
            recovery_pct = (current_price - low_price) / low_price if low_price > 0 else 0
            if 0.1 < recovery_pct < 0.5:  # 10-50% recovery (not too much)
                score += 1.0

            # 4. Recent volume spike (institutional entry)
            avg_vol = recent['volume'].mean()
            max_recent_vol = recent['volume'].iloc[-5:].max()
            if max_recent_vol > avg_vol * 2:
                score += 1.0

            # 5. Volatility cluster (tight range, preparing to break)
            recent_std = recent['close'].pct_change().std()
            if recent_std < 0.1:  # Low volatility = consolidation
                score += 1.0

            # 6. Support hold (price stays above previous low)
            prev_month_low = df.iloc[-60:-20]['low'].min()
            if current_price > prev_month_low:
                score += 1.0

        except Exception as e:
            logger.debug(f"BCE calculation error: {e}")
            return 0.0

        return min(6.0, max(0.0, score))

    def validate_window(self,
                       gt_labels: Dict,
                       train_coins: List[str],
                       test_coins: List[str],
                       train_start: datetime,
                       train_end: datetime,
                       test_start: datetime,
                       test_end: datetime) -> Dict:
        """Validate a single rolling window"""

        predictions = []
        actuals = []

        # Validate on test window (OOS coins in test period)
        for coin_id in test_coins:
            if coin_id not in gt_labels:
                continue

            actual_label = gt_labels[coin_id]["label"]
            if actual_label not in ["Q1", "Q2"]:
                continue

            # Load OHLCV data
            df = self.load_ohlcv_data(coin_id)
            if df is None or len(df) < 60:
                continue

            # Filter to test period
            test_data = df[(df.index >= test_start) & (df.index <= test_end)]
            if len(test_data) < 20:
                continue

            # Compute BCE score (looking back from test_end only)
            bce_score = self.compute_bce_score(test_data)

            # Predict Q2 if BCE ≥5
            prediction = "Q2" if bce_score >= 5 else "Q1"

            predictions.append(prediction)
            actuals.append(actual_label)

        # Calculate metrics
        metrics = self._calculate_metrics(predictions, actuals)

        return {
            "train_period": f"{train_start.date()} to {train_end.date()}",
            "test_period": f"{test_start.date()} to {test_end.date()}",
            "n_test_samples": len(predictions),
            "metrics": metrics
        }

    def _calculate_metrics(self, predictions: List[str], actuals: List[str]) -> Dict:
        """Calculate validation metrics (Precision, Recall, F1, Accuracy)"""
        if not predictions or not actuals:
            return {"error": "No predictions"}

        # Binary: Q2=1, Q1=0
        pred_binary = [1 if p == "Q2" else 0 for p in predictions]
        actual_binary = [1 if a == "Q2" else 0 for a in actuals]

        tp = sum(1 for p, a in zip(pred_binary, actual_binary) if p == 1 and a == 1)
        fp = sum(1 for p, a in zip(pred_binary, actual_binary) if p == 1 and a == 0)
        fn = sum(1 for p, a in zip(pred_binary, actual_binary) if p == 0 and a == 1)
        tn = sum(1 for p, a in zip(pred_binary, actual_binary) if p == 0 and a == 0)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / len(predictions) if predictions else 0.0

        return {
            "accuracy": round(accuracy, 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn
        }

    def validate_all_windows(self, gt_csv: Path) -> bool:
        """Run walk-forward validation across all windows"""
        logger.info("="*60)
        logger.info("WALK-FORWARD VALIDATION")
        logger.info("="*60)

        # Load ground truth
        gt_labels = self.load_ground_truth(gt_csv)
        all_coins = list(gt_labels.keys())

        # Split into train/test
        train_coins, test_coins = self.split_train_test(all_coins)

        # Create windows
        windows = self.create_windows()

        # Validate each window
        overall_f1 = []
        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            logger.info(f"\nWindow {i+1}/{len(windows)}")

            window_result = self.validate_window(
                gt_labels, train_coins, test_coins,
                train_start, train_end, test_start, test_end
            )

            self.results["windows"].append(window_result)

            f1 = window_result["metrics"].get("f1", 0)
            overall_f1.append(f1)

            logger.info(f"  F1: {f1:.3f}, Accuracy: {window_result['metrics'].get('accuracy', 0):.3f}")

        # Summary
        avg_f1 = np.mean(overall_f1) if overall_f1 else 0.0
        self.results["summary"] = {
            "n_windows": len(windows),
            "avg_f1": round(avg_f1, 3),
            "gate_status": "PASS" if avg_f1 >= 0.75 else "FAIL",
            "min_f1": round(min(overall_f1), 3) if overall_f1 else 0.0,
            "max_f1": round(max(overall_f1), 3) if overall_f1 else 0.0
        }

        logger.info(f"\n{'='*60}")
        logger.info("WFV RESULTS")
        logger.info(f"{'='*60}")
        logger.info(f"Windows: {len(windows)}")
        logger.info(f"Average F1: {avg_f1:.3f}")
        logger.info(f"Gate Status: {self.results['summary']['gate_status']}")

        return avg_f1 >= 0.75

    def save_results(self) -> Path:
        """Save validation results"""
        results_file = VAL_DIR / f"wfv_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {results_file}")
        return results_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 walk_forward_validator.py <gt_csv>")
        sys.exit(1)

    gt_csv = Path(sys.argv[1])

    validator = WalkForwardValidator()
    is_valid = validator.validate_all_windows(gt_csv)

    results = validator.save_results()

    if is_valid:
        print(f"\n✓ WFV PASSED")
        print(f"  Results: {results}")
        sys.exit(0)
    else:
        print(f"\n✗ WFV FAILED")
        print(f"  Results: {results}")
        sys.exit(1)
