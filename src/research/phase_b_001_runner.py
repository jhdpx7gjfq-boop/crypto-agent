"""Phase B-001 Runner: Full Ablation WFV

Executes models A-G across regimes with PIT validation.

Usage:
    python -m src.research.phase_b_001_runner --source yfinance --start 2021-01-01
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
import json
import os
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.validation.data_sourcing import get_btc_data
from src.validation.level_4_oos_wfv import WFVPipeline, RegimeDefinition, WFVWindow, REGIMES
from src.research.ablation_framework import AblationFramework
from src.research.spring_context_predictor import (
    model_a, model_b, model_c, model_d, model_e, model_f, model_g
)


@dataclass
class ModelConfig:
    """Model definition."""
    name: str
    factory: callable


MODELS = [
    ModelConfig("A", model_a),
    ModelConfig("B", model_b),
    ModelConfig("C", model_c),
    ModelConfig("D", model_d),
    ModelConfig("E", model_e),
    ModelConfig("F", model_f),
    ModelConfig("G", model_g),
]


class PhaseB001Runner:
    """Orchestrates Phase B-001 ablation study."""

    def __init__(self):
        self.pipeline = WFVPipeline(train_period_days=180, test_period_days=30, overlap_days=0)
        self.framework = AblationFramework()
        self.results = {}

    def run_model_on_window(self,
                           model_config: ModelConfig,
                           df: pd.DataFrame,
                           window: WFVWindow) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run one model on one window, return (signals, returns).

        PIT-compliant.
        """
        # Filter data by date range
        train_mask = (df.index >= window.train_start) & (df.index <= window.train_end)
        test_mask = (df.index >= window.test_start) & (df.index <= window.test_end)

        train_data = df[train_mask]
        test_data = df[test_mask]

        if len(test_data) < 5:
            return np.array([]), np.array([])

        # Initialize model on full data (no look-ahead in params)
        model = model_config.factory(df)

        # Generate signals + actuals for test period
        signals = []
        actuals = []

        for test_timestamp in test_data.index:
            # PIT: use ONLY data before test_timestamp
            pit_data = df[df.index < test_timestamp]

            if len(pit_data) < 30:
                continue

            # Predict
            signal = model.predict(pit_data, len(pit_data) - 1)
            signals.append(signal)

            # Actual return
            next_close = test_data.loc[test_timestamp, "close"] if test_timestamp in test_data.index else None
            if next_close is None:
                continue

            current_close = pit_data["close"].iloc[-1]
            actual_return = (next_close - current_close) / current_close
            actuals.append(actual_return)

        return np.array(signals), np.array(actuals)

    def run_ablation(self, df: pd.DataFrame) -> Dict:
        """
        Run all models A-G across all regimes.

        Returns:
            {
                "A": {...results...},
                "B": {...},
                ...,
                "G": {...}
            }
        """
        logger.info("=" * 60)
        logger.info("PHASE B-001: ABLATION STUDY")
        logger.info("=" * 60)

        # Collect windows and data across all regimes
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

        # Run each model
        model_results = {}

        for model_config in MODELS:
            logger.info(f"\n[MODEL {model_config.name}]")

            signals_list = []
            returns_list = []

            for i, window in enumerate(all_windows):
                signals, returns = self.run_model_on_window(model_config, df, window)

                if len(signals) > 0:
                    signals_list.append(signals)
                    returns_list.append(returns)
                else:
                    signals_list.append(np.array([]))
                    returns_list.append(np.array([]))

                if (i + 1) % 5 == 0:
                    logger.info(f"  Window {i + 1}/{len(all_windows)}")

            # Score this model
            result = self.framework.test_model(
                model_name=model_config.name,
                signals_list=signals_list,
                returns_list=returns_list,
                window_ids=window_ids,
                regimes=regime_names
            )

            model_results[model_config.name] = result

            logger.info(f"  IC Mean: {result['ic_mean']:.6f} (±{result['ic_std']:.6f})")
            logger.info(f"  HR Mean: {result['hr_mean']:.4f}")
            logger.info(f"  Expectancy: {result['expectancy_mean']:.6f}")

        return model_results

    def compute_gate(self, deltas: Dict[str, float]) -> Tuple[bool, str]:
        """
        Evaluate Phase B gate.

        Gate PASS if:
        1. Incremental IC(B) - IC(A) > 0.005 (Spring adds signal)
        2. AND IC(E) - IC(C) > 0.003 (Spring + Regime synergy)
        """
        criteria = []

        delta_b_a = deltas.get("delta_ic_b_a", 0.0)
        delta_e_c = deltas.get("delta_ic_e_c", 0.0)

        criteria.append(("Spring alone IC delta", delta_b_a, 0.005, delta_b_a > 0.005))
        criteria.append(("Spring + Regime IC delta", delta_e_c, 0.003, delta_e_c > 0.003))

        passed = all(c[3] for c in criteria)

        msg = "PHASE B-001 GATE:\n"
        for name, value, threshold, result in criteria:
            status = "✅" if result else "❌"
            msg += f"  {status} {name}: {value:.6f} (target >{threshold})\n"

        return passed, msg

    def generate_report(self, model_results: Dict, output_path: str):
        """Generate final ablation report."""
        deltas = self.framework.compute_deltas(model_results)
        per_regime = self.framework.per_regime_summary(model_results)

        gate_passed, gate_msg = self.compute_gate(deltas)

        report = {
            "phase": "B-001",
            "frozen": "Spring P0.4 (Phase A IC=0.000 REJECTED)",
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
    parser.add_argument("--source", default="yfinance", help="Data source: yfinance, binance, or CSV path")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--output", default="reports/research/phase_b_001_ablation.json")
    args = parser.parse_args()

    logger.info("Loading BTC data...")
    df = get_btc_data(source=args.source, start_date=args.start)

    if df is None:
        logger.error("Failed to load data")
        exit(1)

    logger.info(f"Loaded {len(df)} candles ({df.index[0]} to {df.index[-1]})")

    runner = PhaseB001Runner()
    model_results = runner.run_ablation(df)

    runner.generate_report(model_results, args.output)

    logger.info("\n" + "=" * 60)
    logger.info("PHASE B-001 COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Gate Status: {'PASS ✅' if report['gate']['passed'] else 'FAIL ❌'}")
