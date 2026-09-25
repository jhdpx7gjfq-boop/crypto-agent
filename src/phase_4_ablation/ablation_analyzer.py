#!/usr/bin/env python3
"""
Phase 4: Ablation Analysis

Analyzes which BCE components contribute most to model accuracy.
Removes one component at a time, measures impact on F1/Accuracy.

Components:
1. Relative price position (Wyckoff structure)
2. Volume exhaustion (declining volume)
3. Price recovery
4. Recent volume spike
5. Volatility cluster (consolidation)
6. Support hold

Timeline: Nov 7-13, 2026
Gate: Identify critical components (Nov 10)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# Configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
GT_DIR = DATA_DIR / "ground_truth" / "phase_2"
PHASE1_DIR = DATA_DIR / "raw" / "phase_1"
ABLATION_DIR = DATA_DIR / "ablation" / "phase_4"
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "phase_4"

LOG_DIR.mkdir(parents=True, exist_ok=True)
ABLATION_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"ablation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# BCE Component Names
COMPONENTS = {
    1: "relative_price_position",
    2: "volume_exhaustion",
    3: "price_recovery",
    4: "volume_spike",
    5: "volatility_cluster",
    6: "support_hold"
}


class AblationAnalyzer:
    """Ablation analysis for BCE components"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "4_ablation_analysis",
            "baseline": {},
            "ablations": {},
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

    def compute_bce_score(self, df: pd.DataFrame,
                         exclude_components: set = None) -> float:
        """
        Compute BCE score with optional component exclusion

        exclude_components: set of component IDs (1-6) to ignore
        """
        if exclude_components is None:
            exclude_components = set()

        if len(df) < 60:
            return 0.0

        score = 0.0
        recent = df.iloc[-60:]

        try:
            # 1. Relative price position
            if 1 not in exclude_components:
                recent_low = recent['low'].min()
                hist_low = df['low'].min()
                if recent_low <= hist_low * 1.1:
                    score += 1.0

            # 2. Volume exhaustion
            if 2 not in exclude_components:
                vol_trend = recent['volume'].iloc[-20:].mean() / recent['volume'].iloc[:20].mean()
                if vol_trend < 1.5:
                    score += 1.0

            # 3. Price recovery
            if 3 not in exclude_components:
                low_idx = recent['low'].idxmin()
                low_price = recent.loc[low_idx, 'low']
                current_price = recent['close'].iloc[-1]
                recovery_pct = (current_price - low_price) / low_price if low_price > 0 else 0
                if 0.1 < recovery_pct < 0.5:
                    score += 1.0

            # 4. Recent volume spike
            if 4 not in exclude_components:
                avg_vol = recent['volume'].mean()
                max_recent_vol = recent['volume'].iloc[-5:].max()
                if max_recent_vol > avg_vol * 2:
                    score += 1.0

            # 5. Volatility cluster
            if 5 not in exclude_components:
                recent_std = recent['close'].pct_change().std()
                if recent_std < 0.1:
                    score += 1.0

            # 6. Support hold
            if 6 not in exclude_components:
                prev_month_low = df.iloc[-60:-20]['low'].min()
                current_price = recent['close'].iloc[-1]
                if current_price > prev_month_low:
                    score += 1.0

        except Exception as e:
            logger.debug(f"BCE error: {e}")
            return 0.0

        return min(6.0, max(0.0, score))

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
            "f1": round(f1, 3)
        }

    def run_ablation_study(self, gt_csv: Path) -> bool:
        """Run complete ablation study"""
        logger.info("="*70)
        logger.info("ABLATION ANALYSIS: BCE COMPONENT IMPORTANCE")
        logger.info("="*70)

        # Load ground truth
        gt_labels = self.load_ground_truth(gt_csv)
        all_coins = list(gt_labels.keys())

        # Baseline (all components)
        logger.info("\nComputing BASELINE (all 6 components)...")

        baseline_pred = []
        baseline_actual = []

        for coin_id in all_coins:
            actual_label = gt_labels[coin_id]["label"]
            df = self.load_ohlcv_data(coin_id)

            if df is None or len(df) < 60:
                continue

            bce_score = self.compute_bce_score(df)
            prediction = "Q2" if bce_score >= 5 else "Q1"

            baseline_pred.append(prediction)
            baseline_actual.append(actual_label)

        baseline_metrics = self.calculate_metrics(baseline_pred, baseline_actual)
        self.results["baseline"] = {
            "n_coins": len(baseline_pred),
            "metrics": baseline_metrics
        }

        logger.info(f"Baseline F1: {baseline_metrics.get('f1', 0):.3f}")

        # Ablation: Remove each component
        for exclude_component in range(1, 7):
            logger.info(f"\nAblating COMPONENT {exclude_component}: {COMPONENTS[exclude_component]}...")

            ablation_pred = []
            ablation_actual = []

            for coin_id in all_coins:
                actual_label = gt_labels[coin_id]["label"]
                df = self.load_ohlcv_data(coin_id)

                if df is None or len(df) < 60:
                    continue

                bce_score = self.compute_bce_score(df, exclude_components={exclude_component})
                prediction = "Q2" if bce_score >= 5 else "Q1"

                ablation_pred.append(prediction)
                ablation_actual.append(actual_label)

            ablation_metrics = self.calculate_metrics(ablation_pred, ablation_actual)

            # Calculate impact
            baseline_f1 = baseline_metrics.get("f1", 0)
            ablation_f1 = ablation_metrics.get("f1", 0)
            impact = baseline_f1 - ablation_f1

            self.results["ablations"][exclude_component] = {
                "component_name": COMPONENTS[exclude_component],
                "n_coins": len(ablation_pred),
                "metrics": ablation_metrics,
                "f1_impact": round(impact, 3)
            }

            logger.info(f"  Without {COMPONENTS[exclude_component]}: F1={ablation_f1:.3f}, Impact={impact:+.3f}")

        # Rank components by importance
        logger.info("\n" + "="*70)
        logger.info("COMPONENT IMPORTANCE RANKING")
        logger.info("="*70)

        ranked = sorted(
            self.results["ablations"].items(),
            key=lambda x: x[1]["f1_impact"],
            reverse=True
        )

        for rank, (comp_id, result) in enumerate(ranked, 1):
            impact = result["f1_impact"]
            logger.info(f"{rank}. {result['component_name']:30s} Impact: {impact:+.3f}")

        # Identify critical vs non-critical
        critical_threshold = 0.05  # >5% impact is critical
        critical_components = [
            comp_id for comp_id, result in self.results["ablations"].items()
            if result["f1_impact"] >= critical_threshold
        ]

        self.results["summary"] = {
            "baseline_f1": baseline_metrics.get("f1", 0),
            "critical_components": critical_components,
            "n_critical": len(critical_components),
            "ranking": [
                {
                    "rank": rank,
                    "component": result["component_name"],
                    "impact": result["f1_impact"]
                }
                for rank, (_, result) in enumerate(ranked, 1)
            ]
        }

        return True

    def save_results(self) -> Path:
        """Save ablation results"""
        results_file = ABLATION_DIR / f"ablation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {results_file}")
        return results_file


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 ablation_analyzer.py <gt_csv>")
        sys.exit(1)

    gt_csv = Path(sys.argv[1])

    analyzer = AblationAnalyzer()
    analyzer.run_ablation_study(gt_csv)

    results = analyzer.save_results()
    print(f"\n✓ Ablation analysis complete: {results}")
