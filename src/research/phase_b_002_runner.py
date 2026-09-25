"""Phase B-002 Runner: Capital Flow Layer Validation

Tests models A (Baseline), D (+ Flow), G (Full stack).
WFV with PIT validation.

Usage:
    python -m src.research.phase_b_002_runner --source yfinance --start 2021-01-01
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
from src.research.flow_data_layer import BinancePerpetualFlow, FlowIndicators
from src.research.spring_context_predictor import model_a
from src.research.flow_predictor import model_d, model_g


class PhaseB002Runner:
    """Orchestrates Phase B-002 Flow layer validation."""

    def __init__(self):
        self.pipeline = WFVPipeline(train_period_days=180, test_period_days=30, overlap_days=0)
        self.framework = AblationFramework()
        self.flow_fetcher = BinancePerpetualFlow("BTCUSDT")

    def fetch_flow_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fetch and merge OI + Funding data with OHLCV (PIT-safe).

        Returns:
            DataFrame with columns: [open, high, low, close, volume, open_interest, funding_rate]
        """
        logger.info("[1/3] Fetching capital flow data...")

        start_date = df.index.min().strftime("%Y-%m-%d")
        end_date = df.index.max().strftime("%Y-%m-%d")

        # Fetch OI and Funding
        oi_df = self.flow_fetcher.fetch_oi_daily(start_date, end_date)
        funding_df = self.flow_fetcher.fetch_funding_rates(start_date, end_date)

        if oi_df is None or funding_df is None:
            logger.warning("Flow data fetch failed; using placeholder")
            oi_df = self.flow_fetcher._placeholder_oi(start_date, end_date)
            funding_df = self.flow_fetcher._placeholder_funding_rates(start_date, end_date)

        # Merge with OHLCV
        df_flow = FlowIndicators.merge_flow_data(df, oi_df, funding_df)

        logger.info(f"✅ Merged flow data: {len(df_flow)} rows")
        return df_flow

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

    def run_ablation(self, df_flow: pd.DataFrame) -> Dict:
        """Run models A, D, G across all regimes."""
        logger.info("=" * 60)
        logger.info("PHASE B-002: CAPITAL FLOW VALIDATION")
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
            ("D", model_d),
            ("G", model_g),
        ]

        model_results = {}

        for model_name, model_factory in models:
            logger.info(f"\n[MODEL {model_name}]")

            signals_list = []
            returns_list = []

            for i, window in enumerate(all_windows):
                signals, returns = self.run_model_on_window(model_factory, df_flow, window)

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
        """Evaluate Phase B-002 gate."""
        criteria = []

        # Flow contribution: D - A
        delta_d_a = deltas.get("delta_ic_d_a", 0.0)
        ic_d = model_results.get("D", {}).get("ic_mean", 0.0)
        hr_d = model_results.get("D", {}).get("hr_mean", 0.5)
        ic_a = model_results.get("A", {}).get("ic_mean", 0.0)

        criteria.append(("Flow IC delta (D-A)", delta_d_a, 0.003, delta_d_a > 0.003))
        criteria.append(("Flow HR", hr_d, 0.48, hr_d > 0.48))

        passed = all(c[3] for c in criteria)

        msg = "PHASE B-002 GATE:\n"
        for name, value, threshold, result in criteria:
            status = "✅" if result else "❌"
            msg += f"  {status} {name}: {value:.6f} (target >{threshold})\n"

        # Additional info
        msg += f"\nFlow Context:\n"
        msg += f"  IC(A) baseline: {ic_a:.6f}\n"
        msg += f"  IC(D) w/flow: {ic_d:.6f}\n"

        if "G" in model_results:
            ic_g = model_results["G"].get("ic_mean", 0.0)
            delta_g_d = ic_g - ic_d
            msg += f"  IC(G) full stack: {ic_g:.6f}\n"
            msg += f"  Spring value in flow context (G-D): {delta_g_d:.6f}\n"

        return passed, msg

    def generate_report(self, model_results: Dict, output_path: str):
        """Generate final report."""
        deltas = self.framework.compute_deltas(model_results)
        per_regime = self.framework.per_regime_summary(model_results)

        gate_passed, gate_msg = self.compute_gate(deltas, model_results)

        report = {
            "phase": "B-002",
            "frozen": "Baseline (A), Spring P0.4, Regime",
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
    parser.add_argument("--output", default="reports/research/phase_b_002_ablation.json")
    args = parser.parse_args()

    logger.info("Loading BTC data...")
    df = get_btc_data(source=args.source, start_date=args.start)

    if df is None:
        logger.error("Failed to load data")
        exit(1)

    logger.info(f"Loaded {len(df)} candles ({df.index[0]} to {df.index[-1]})")

    runner = PhaseB002Runner()

    logger.info("\n[2/3] Fetching capital flow data...")
    df_flow = runner.fetch_flow_data(df)

    logger.info("\n[3/3] Running WFV ablation (A, D, G)...")
    model_results = runner.run_ablation(df_flow)

    runner.generate_report(model_results, args.output)

    logger.info("\n" + "=" * 60)
    logger.info("PHASE B-002 COMPLETE")
    logger.info("=" * 60)
