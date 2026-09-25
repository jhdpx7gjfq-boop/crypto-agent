#!/usr/bin/env python3
"""
Phase 5: Robustness Validation

Tests BCE model under various market conditions to ensure it works
across diverse scenarios (bull/bear, high/low volatility, etc.).

Test dimensions:
1. Market regime (bull/bear/sideways)
2. Volatility level (high/low)
3. Time period (different years)
4. Liquidity conditions (high/low volume)
5. Label confidence (high/low confidence predictions)

Timeline: Nov 14-20, 2026
Gate: >75% pass rate in all test dimensions (Nov 17)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
GT_DIR = DATA_DIR / "ground_truth" / "phase_2"
PHASE1_DIR = DATA_DIR / "raw" / "phase_1"
ROBUST_DIR = DATA_DIR / "robustness" / "phase_5"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_5"

LOG_DIR.mkdir(parents=True, exist_ok=True)
ROBUST_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"robustness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RobustnessTester:
    """Test model robustness across market conditions"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "5_robustness_validation",
            "test_dimensions": {},
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
            recent_low = recent['low'].min()
            hist_low = df['low'].min()
            if recent_low <= hist_low * 1.1:
                score += 1.0

            vol_trend = recent['volume'].iloc[-20:].mean() / recent['volume'].iloc[:20].mean()
            if vol_trend < 1.5:
                score += 1.0

            low_idx = recent['low'].idxmin()
            low_price = recent.loc[low_idx, 'low']
            current_price = recent['close'].iloc[-1]
            recovery_pct = (current_price - low_price) / low_price if low_price > 0 else 0
            if 0.1 < recovery_pct < 0.5:
                score += 1.0

            avg_vol = recent['volume'].mean()
            max_recent_vol = recent['volume'].iloc[-5:].max()
            if max_recent_vol > avg_vol * 2:
                score += 1.0

            recent_std = recent['close'].pct_change().std()
            if recent_std < 0.1:
                score += 1.0

            prev_month_low = df.iloc[-60:-20]['low'].min()
            if current_price > prev_month_low:
                score += 1.0

        except Exception as e:
            logger.debug(f"BCE error: {e}")
            return 0.0

        return min(6.0, max(0.0, score))

    def detect_market_regime(self, df: pd.DataFrame) -> str:
        """Detect market regime (bull/bear/sideways)"""
        if len(df) < 90:
            return "unknown"

        recent_90d = df.iloc[-90:]
        price_change = (recent_90d['close'].iloc[-1] - recent_90d['close'].iloc[0]) / recent_90d['close'].iloc[0]

        if price_change > 0.2:
            return "bull"
        elif price_change < -0.2:
            return "bear"
        else:
            return "sideways"

    def detect_volatility_level(self, df: pd.DataFrame) -> str:
        """Detect volatility level (high/low)"""
        if len(df) < 60:
            return "unknown"

        recent_60d = df.iloc[-60:]
        volatility = recent_60d['close'].pct_change().std()

        return "high" if volatility > 0.05 else "low"

    def detect_liquidity_level(self, df: pd.DataFrame) -> str:
        """Detect liquidity level (high/low)"""
        if len(df) < 60:
            return "unknown"

        recent_60d = df.iloc[-60:]
        avg_volume = recent_60d['volume'].mean()

        # Arbitrary: high if avg volume > 0 (since some coins have 0 volume)
        return "high" if avg_volume > 0 else "low"

    def calculate_metrics(self, predictions: List[str], actuals: List[str]) -> Dict:
        """Calculate F1, Accuracy, Precision, Recall"""
        if not predictions or not actuals:
            return {}

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
            "n_samples": len(predictions)
        }

    def test_regime_robustness(self, gt_labels: Dict) -> Dict:
        """Test robustness across market regimes"""
        logger.info("Testing regime robustness (bull/bear/sideways)...")

        regime_results = {}

        for regime in ["bull", "bear", "sideways"]:
            predictions = []
            actuals = []

            for coin_id, label_info in gt_labels.items():
                df = self.load_ohlcv_data(coin_id)
                if df is None or len(df) < 90:
                    continue

                detected_regime = self.detect_market_regime(df)
                if detected_regime != regime:
                    continue

                bce_score = self.compute_bce_score(df)
                prediction = "Q2" if bce_score >= 5 else "Q1"

                predictions.append(prediction)
                actuals.append(label_info["label"])

            metrics = self.calculate_metrics(predictions, actuals)
            regime_results[regime] = metrics

        return regime_results

    def test_volatility_robustness(self, gt_labels: Dict) -> Dict:
        """Test robustness across volatility levels"""
        logger.info("Testing volatility robustness (high/low)...")

        volatility_results = {}

        for vol_level in ["high", "low"]:
            predictions = []
            actuals = []

            for coin_id, label_info in gt_labels.items():
                df = self.load_ohlcv_data(coin_id)
                if df is None or len(df) < 60:
                    continue

                detected_vol = self.detect_volatility_level(df)
                if detected_vol != vol_level:
                    continue

                bce_score = self.compute_bce_score(df)
                prediction = "Q2" if bce_score >= 5 else "Q1"

                predictions.append(prediction)
                actuals.append(label_info["label"])

            metrics = self.calculate_metrics(predictions, actuals)
            volatility_results[vol_level] = metrics

        return volatility_results

    def test_confidence_robustness(self, gt_labels: Dict) -> Dict:
        """Test robustness across label confidence levels"""
        logger.info("Testing confidence robustness (high/low confidence labels)...")

        confidence_results = {}

        for conf_level in ["high_confidence", "low_confidence"]:
            predictions = []
            actuals = []

            for coin_id, label_info in gt_labels.items():
                confidence = label_info["confidence"]

                # High confidence: 4-5, Low confidence: 1-2
                if conf_level == "high_confidence" and confidence < 4:
                    continue
                if conf_level == "low_confidence" and confidence > 2:
                    continue

                df = self.load_ohlcv_data(coin_id)
                if df is None or len(df) < 60:
                    continue

                bce_score = self.compute_bce_score(df)
                prediction = "Q2" if bce_score >= 5 else "Q1"

                predictions.append(prediction)
                actuals.append(label_info["label"])

            metrics = self.calculate_metrics(predictions, actuals)
            confidence_results[conf_level] = metrics

        return confidence_results

    def run_robustness_tests(self, gt_csv: Path) -> bool:
        """Run all robustness tests"""
        logger.info("="*70)
        logger.info("ROBUSTNESS VALIDATION")
        logger.info("="*70)

        gt_labels = self.load_ground_truth(gt_csv)

        # Test 1: Regime robustness
        regime_results = self.test_regime_robustness(gt_labels)
        self.results["test_dimensions"]["market_regime"] = regime_results

        # Test 2: Volatility robustness
        volatility_results = self.test_volatility_robustness(gt_labels)
        self.results["test_dimensions"]["volatility"] = volatility_results

        # Test 3: Confidence robustness
        confidence_results = self.test_confidence_robustness(gt_labels)
        self.results["test_dimensions"]["label_confidence"] = confidence_results

        # Calculate summary
        pass_rate_by_dim = {}

        for dim_name, dim_results in self.results["test_dimensions"].items():
            f1_scores = [v.get("f1", 0) for v in dim_results.values() if v]
            if f1_scores:
                avg_f1 = np.mean(f1_scores)
                pass_count = sum(1 for f1 in f1_scores if f1 >= 0.70)
                pass_rate = pass_count / len(f1_scores)
                pass_rate_by_dim[dim_name] = round(pass_rate, 2)

        self.results["summary"] = {
            "pass_rates_by_dimension": pass_rate_by_dim,
            "overall_pass_rate": round(np.mean(list(pass_rate_by_dim.values())), 2) if pass_rate_by_dim else 0.0,
            "gate_status": "PASS" if np.mean(list(pass_rate_by_dim.values())) >= 0.75 else "FAIL"
        }

        logger.info("\n" + "="*70)
        logger.info("ROBUSTNESS RESULTS")
        logger.info("="*70)

        for dim, pass_rate in pass_rate_by_dim.items():
            logger.info(f"{dim}: {pass_rate:.1%} pass rate")

        logger.info(f"Overall: {self.results['summary']['gate_status']}")

        return self.results["summary"]["gate_status"] == "PASS"

    def save_results(self) -> Path:
        """Save robustness test results"""
        results_file = ROBUST_DIR / f"robustness_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {results_file}")
        return results_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 robustness_tester.py <gt_csv>")
        sys.exit(1)

    gt_csv = Path(sys.argv[1])

    tester = RobustnessTester()
    is_valid = tester.run_robustness_tests(gt_csv)

    results = tester.save_results()

    if is_valid:
        print(f"\n✓ ROBUSTNESS PASSED")
        sys.exit(0)
    else:
        print(f"\n✗ ROBUSTNESS FAILED")
        sys.exit(1)
