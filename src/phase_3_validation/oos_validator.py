#!/usr/bin/env python3
"""
Phase 3: OOS (Out-Of-Sample) Validation

Hold-out test set (20% of coins) to validate model generalization.
No lookahead bias - tests on coins never seen during development.
"""

import json
import logging
from datetime import datetime
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
        logging.FileHandler(LOG_DIR / f"oos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OOSValidator:
    """Out-Of-Sample validation with hold-out test set"""

    def __init__(self, test_ratio=0.2):
        self.test_ratio = test_ratio
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "3_oos_validation",
            "validation_type": "out_of_sample",
            "test_coins": [],
            "predictions": {},
            "summary": {}
        }

    def load_ground_truth(self, gt_csv: Path) -> Dict:
        """Load Phase 2 ground truth"""
        logger.info(f"Loading ground truth from {gt_csv}")

        df = pd.read_csv(gt_csv)
        gt = {}

        for _, row in df.iterrows():
            coin_id = row.get("coin_id")
            if coin_id and row.get("label") in ["Q1", "Q2"]:
                gt[coin_id] = {
                    "symbol": row.get("symbol"),
                    "label": row.get("label"),
                    "confidence": int(row.get("confidence", 0))
                }

        logger.info(f"Loaded {len(gt)} labeled coins")
        return gt

    def split_coins(self, all_coins: List[str]) -> Tuple[List[str], List[str]]:
        """Deterministically split into train (80%) and test (20%)"""
        n_test = max(1, int(len(all_coins) * self.test_ratio))
        test_coins = sorted(all_coins)[-n_test:]  # Last 20% alphabetically
        train_coins = sorted(all_coins)[:-n_test]

        logger.info(f"Train coins: {len(train_coins)}")
        logger.info(f"Test coins (OOS): {len(test_coins)}")

        self.results["test_coins"] = test_coins
        return train_coins, test_coins

    def load_ohlcv_data(self, coin_id: str) -> Optional[pd.DataFrame]:
        """Load Phase 1 OHLCV data"""
        try:
            coin_files = list(PHASE1_DIR.glob(f"*_{coin_id}.parquet"))
            if not coin_files:
                return None

            df = pd.read_parquet(coin_files[0])
            df.index = pd.to_datetime(df.index)
            return df.sort_index()
        except Exception as e:
            logger.debug(f"Could not load data for {coin_id}: {e}")
            return None

    def compute_bce_score(self, df: pd.DataFrame) -> float:
        """Compute BCE score"""
        if len(df) < 60:
            return 0.0

        score = 0.0
        recent = df.iloc[-60:]

        try:
            # 1. Relative price position
            recent_low = recent['low'].min()
            hist_low = df['low'].min()
            if recent_low <= hist_low * 1.1:
                score += 1.0

            # 2. Volume trend
            vol_trend = recent['volume'].iloc[-20:].mean() / recent['volume'].iloc[:20].mean()
            if vol_trend < 1.5:
                score += 1.0

            # 3. Price recovery
            low_idx = recent['low'].idxmin()
            low_price = recent.loc[low_idx, 'low']
            current_price = recent['close'].iloc[-1]
            recovery_pct = (current_price - low_price) / low_price if low_price > 0 else 0
            if 0.1 < recovery_pct < 0.5:
                score += 1.0

            # 4. Recent volume spike
            avg_vol = recent['volume'].mean()
            max_recent_vol = recent['volume'].iloc[-5:].max()
            if max_recent_vol > avg_vol * 2:
                score += 1.0

            # 5. Volatility cluster
            recent_std = recent['close'].pct_change().std()
            if recent_std < 0.1:
                score += 1.0

            # 6. Support hold
            prev_month_low = df.iloc[-60:-20]['low'].min()
            if current_price > prev_month_low:
                score += 1.0

        except Exception as e:
            logger.debug(f"BCE error: {e}")
            return 0.0

        return min(6.0, max(0.0, score))

    def validate_coin(self, coin_id: str, gt_label: str) -> Dict:
        """Validate OOS coin"""

        # Load data
        df = self.load_ohlcv_data(coin_id)
        if df is None or len(df) < 60:
            return {"status": "insufficient_data"}

        # Compute BCE score
        bce_score = self.compute_bce_score(df)

        # Predict Q2 if BCE ≥5
        prediction = "Q2" if bce_score >= 5 else "Q1"

        # Compare to ground truth
        is_correct = (prediction == gt_label)

        return {
            "status": "valid",
            "coin_id": coin_id,
            "actual": gt_label,
            "predicted": prediction,
            "bce_score": round(bce_score, 2),
            "correct": is_correct
        }

    def validate_all(self, gt_csv: Path) -> bool:
        """Run OOS validation"""
        logger.info("="*60)
        logger.info("OOS (OUT-OF-SAMPLE) VALIDATION")
        logger.info("="*60)

        # Load ground truth
        gt_labels = self.load_ground_truth(gt_csv)
        all_coins = list(gt_labels.keys())

        # Split into train/test
        train_coins, test_coins = self.split_coins(all_coins)

        # Validate only test coins
        correct = 0
        total = 0
        q1_correct = 0
        q2_correct = 0
        q1_total = 0
        q2_total = 0

        for coin_id in test_coins:
            actual_label = gt_labels[coin_id]["label"]

            result = self.validate_coin(coin_id, actual_label)

            if result["status"] == "valid":
                self.results["predictions"][coin_id] = result

                if result["correct"]:
                    correct += 1
                total += 1

                if actual_label == "Q1":
                    q1_total += 1
                    if result["correct"]:
                        q1_correct += 1
                else:
                    q2_total += 1
                    if result["correct"]:
                        q2_correct += 1

        # Calculate summary metrics
        accuracy = correct / total if total > 0 else 0.0
        q1_recall = q1_correct / q1_total if q1_total > 0 else 0.0
        q2_recall = q2_correct / q2_total if q2_total > 0 else 0.0

        self.results["summary"] = {
            "n_test_coins": total,
            "correct_predictions": correct,
            "accuracy": round(accuracy, 3),
            "q1_recall": round(q1_recall, 3),
            "q2_recall": round(q2_recall, 3),
            "gate_status": "PASS" if accuracy >= 0.70 else "FAIL"
        }

        logger.info(f"\n{'='*60}")
        logger.info("OOS RESULTS")
        logger.info(f"{'='*60}")
        logger.info(f"Test coins: {total}")
        logger.info(f"Correct: {correct}/{total} ({accuracy:.1%})")
        logger.info(f"Q1 recall: {q1_recall:.1%}")
        logger.info(f"Q2 recall: {q2_recall:.1%}")
        logger.info(f"Gate Status: {self.results['summary']['gate_status']}")

        return accuracy >= 0.70

    def save_results(self) -> Path:
        """Save OOS results"""
        results_file = VAL_DIR / f"oos_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {results_file}")
        return results_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 oos_validator.py <gt_csv>")
        sys.exit(1)

    gt_csv = Path(sys.argv[1])

    validator = OOSValidator()
    is_valid = validator.validate_all(gt_csv)

    results = validator.save_results()

    if is_valid:
        print(f"\n✓ OOS PASSED")
        sys.exit(0)
    else:
        print(f"\n✗ OOS FAILED")
        sys.exit(1)
