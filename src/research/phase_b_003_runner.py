"""Phase B-003 Runner: Macro Layer (NARM-P+) Validation

Tests models A (Baseline), H (+ NARM-P+), I (Full stack v2).
WFV with PIT validation.

Usage:
    python -m src.research.phase_b_003_runner --source yfinance --start 2021-01-01
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging
import json
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.validation.data_sourcing import get_btc_data
from src.validation.level_4_oos_wfv import WFVPipeline, REGIMES, WFVWindow
from src.research.ablation_framework import AblationFramework
from src.research.narm_data_layer import NARMDataLayer
from src.research.spring_context_predictor import model_a
from src.research.narm_predictor import model_h, model_i


class PhaseB003Runner:
    """Orchestrates Phase B-003 macro layer validation."""

    def __init__(self):
        self.pipeline = WFVPipeline(train_period_days=180, test_period_days=30, overlap_days=0)
        self.framework = AblationFramework()
        self.narm = NARMDataLayer()

    def fetch_narm_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fetch and merge NARM components with OHLCV (PIT-safe)."""
        logger.info("[1/3] Fetching macro narrative data...")

        start_date = df.index.min().strftime("%Y-%m-%d")
        end_date = df.index.max().strftime("%Y-%m-%d")

        # Fetch NARM components
        sentiment_df = self.narm.fetch_sentiment(start_date, end_date)
        adoption_df = self.narm.fetch_adoption(start_date, end_date)
        dev_df = self.narm.fetch_dev_activity(start_date, end_date)
        sector_df = self.narm.fetch_sector_rotation(start_date, end_date)

        # Merge with OHLCV
        df_narm = NARMDataLayer.merge_narm_with_ohlcv(df, sentiment_df, adoption_df, dev_df, sector_df)

        logger.info(f"✅ Merged NARM data: {len(df_narm)} rows")
        return df_narm

    def run_model_on_window(self,
                           model_factory,
                           df: pd.DataFrame,
                           window: WFVWindow) -> Tuple[np.ndarray, np.ndarray]:
        """Run one model on one window (PIT-safe)."""
        train_mask = (df.index >= window.train_start) & (df.index <= window.train_end)
        test_mask = (df.index >= window.test_start) & (df.index <= window.test_end)

        train_data = df[train_mask]
        test_data = df[test_mask]

        if len(test_data) < 5:
            return np.array([]), np.array([])

        model = model_factory(df)

        signals = []
        actuals = []

        for test_timestamp in test_data.index:
            pit_data = df[df.index < test_timestamp]

            if len(pit_data) < 30:
                continue

            signal = model.predict(pit_data, len(pit_data) - 1)
            signals.append(signal)

            next_close = test_data.loc[test_timestamp, "close"] if test_timestamp in test_data.index else None
            if next_close is None:
                continue

            current_close = pit_data["close"].iloc[-1]
            actual_return = (next_close - current_close) / current_close
            actuals.append(actual_return)

        return np.array(signals), np.array(actuals)

    def run_ablation(self, df_narm: pd.DataFrame) -> Dict:
        """Run models A, H, I across all regimes."""
        logger.info("=" * 60)
        logger.info("PHASE B-003: MACRO LAYER (NARM-P+) VALIDATION")
        logger.info("=" * 60)

        all_windows = []
        window_ids = []
        regime_names = []

        for regime in REGIMES:
            logger.info(f"\nRegime: {regime.name}")
            windows = self.pipeline.create_windows(regime)
            logger.info(f"  Created {len(windows)} windows")

            for window in windows:
                all_windows.append(window)
                window_ids.append(window.window_id)
                regime_names.append(regime.name)

        logger.info(f"\nTotal windows: {len(all_windows)}")

        models = [
            ("A", model_a),
            ("H", model_h),
            ("I", model_i),
        ]

        model_results = {}

        for model_name, model_factory in models:
            logger.info(f"\n[MODEL {model_name}]")

            signals_list = []
            returns_list = []

            for i, window in enumerate(all_windows):
                signals, returns = self.run_model_on_window(model_factory, df_narm, window)

                if len(signals) > 0:
                    signals_list.append(signals)
                    returns_list.append(returns)
                else:
                    signals_list.append(np.array([]))
                    returns_list.append(np.array([]))

                if (i + 1) % 5 == 0:
                    logger.info(f"  Window {i + 1}/{len(all_windows)}")

            result = self.framework.test_model(
                model_name=model_name,
                signals_list=signals_list,
                returns_list=returns_list,
                window_ids=window_ids,
                regimes=regime_names
            )

            model_results[model_name] = result

            logger.info(f"  IC Mean: {result['ic_mean']:.6f} (±{result['ic_std']:.6f})")
            logger.info(f"  HR Mean: {result['hr_mean']:.4f}")
            logger.info(f"  Expectancy: {result['expectancy_mean']:.6f}")

        return model_results

    def compute_gate(self, deltas: Dict[str, float], model_results: Dict) -> Tuple[bool, str]:
        """Evaluate Phase B-003 gate."""
        criteria = []

        # NARM contribution: H - A
        delta_h_a = deltas.get("delta_ic_h_a", 0.0)
        ic_h = model_results.get("H", {}).get("ic_mean", 0.0)
        hr_h = model_results.get("H", {}).get("hr_mean", 0.5)
        ic_a = model_results.get("A", {}).get("ic_mean", 0.0)

        criteria.append(("NARM-P+ IC delta (H-A)", delta_h_a, 0.005, delta_h_a > 0.005))
        criteria.append(("NARM-P+ HR", hr_h, 0.50, hr_h > 0.50))

        passed = all(c[3] for c in criteria)

        msg = "PHASE B-003 GATE:\n"
        for name, value, threshold, result in criteria:
            status = "✅" if result else "❌"
            msg += f"  {status} {name}: {value:.6f} (target >{threshold})\n"

        msg += f"\nNARRM Context:\n"
        msg += f"  IC(A) baseline: {ic_a:.6f}\n"
        msg += f"  IC(H) w/NARM: {ic_h:.6f}\n"

        if "I" in model_results:
            ic_i = model_results["I"].get("ic_mean", 0.0)
            delta_i_h = ic_i - ic_h
            msg += f"  IC(I) full stack v2: {ic_i:.6f}\n"
            msg += f"  Spring/Regime value in NARM context (I-H): {delta_i_h:.6f}\n"

        return passed, msg

    def generate_report(self, model_results: Dict, output_path: str):
        """Generate final report."""
        deltas = self.framework.compute_deltas(model_results)
        per_regime = self.framework.per_regime_summary(model_results)

        gate_passed, gate_msg = self.compute_gate(deltas, model_results)

        report = {
            "phase": "B-003",
            "frozen": "Baseline (A), Spring, Regime, Flow",
            "timestamp": datetime.now().isoformat(),
            "models": model_results,
            "deltas": deltas,
            "per_regime": per_regime,
            "gate": {
                "passed": gate_passed,
                "message": gate_msg
            }
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"\n✅ Report saved: {output_path}")
        logger.info(gate_msg)

        return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="yfinance")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--output", default="reports/research/phase_b_003_ablation.json")
    args = parser.parse_args()

    logger.info("Loading BTC data...")
    df = get_btc_data(source=args.source, start_date=args.start)

    if df is None:
        logger.error("Failed to load data")
        exit(1)

    logger.info(f"Loaded {len(df)} candles ({df.index[0]} to {df.index[-1]})")

    runner = PhaseB003Runner()

    logger.info("\n[2/3] Fetching macro narrative data...")
    df_narm = runner.fetch_narm_data(df)

    logger.info("\n[3/3] Running WFV ablation (A, H, I)...")
    model_results = runner.run_ablation(df_narm)

    runner.generate_report(model_results, args.output)

    logger.info("\n" + "=" * 60)
    logger.info("PHASE B-003 COMPLETE")
    logger.info("=" * 60)
