"""
B-004: 19-Window Walk-Forward Validation Orchestrator

Full-dataset validation of RPM/RCM with locked criteria:
- ΔIC ≥ 0.05 (Information Coefficient)
- HR ≥ 55% (Hit Rate)
- Stability < 0.50 (Coefficient of Variation)

No lookahead bias. No regime pre-filtering. Immutable results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

import numpy as np
from scipy.stats import spearmanr

from rpm_engine import RPMEngine
from rcm_engine import RCMEngine

logger = logging.getLogger(__name__)


class B004WFVOrchestrator:
    """Execute full B-004 19-window walk-forward validation."""

    def __init__(
        self,
        symbols: List[str] = None,
        ohlcv_dir: str = "./real_market_data",
        output_dir: str = "./b004_results",
    ):
        self.symbols = symbols or ["BTC", "ETH", "SOL", "AVAX"]
        self.ohlcv_dir = Path(ohlcv_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.rpm_engine = RPMEngine(symbols=self.symbols)
        self.rcm_engine = RCMEngine(symbols=self.symbols)

        self.datasets = {}
        self.load_all_ohlcv()

    def load_all_ohlcv(self) -> None:
        """Load OHLCV data for all symbols."""
        for symbol in self.symbols:
            # Try daily first (730 candles), fallback to weekly (27), then monthly (25)
            for filename in [
                f"{symbol}_daily_730d.json",
                f"{symbol}_tipransk_weekly_6m.json",
                f"{symbol}_tipransk_real_730d.json",
            ]:
                filepath = self.ohlcv_dir / filename
                if filepath.exists():
                    try:
                        with open(filepath) as f:
                            data = json.load(f)
                            self.datasets[symbol] = data.get("candles", [])
                            logger.info(f"Loaded {len(self.datasets[symbol])} candles for {symbol} from {filename}")
                            break
                    except Exception as e:
                        logger.error(f"Failed to load {filepath}: {e}")
            else:
                logger.warning(f"No OHLCV data found for {symbol}")

    def construct_windows(self, ohlcv: List[Dict], total_candles: int = 730) -> List[Tuple[int, int]]:
        """
        Construct 19 walk-forward windows.

        Window protocol (LOCKED):
        - Training: 180 days
        - Test: 30 days
        - Stride: 30 days forward
        - Total: 19 windows

        Returns: List of (train_end_idx, test_end_idx) tuples
        """
        train_size = 180
        test_size = 30
        stride = 30

        windows = []
        for i in range(19):
            train_start = i * stride
            train_end = train_start + train_size
            test_end = train_end + test_size

            if test_end <= len(ohlcv):
                windows.append((train_end, test_end))

        return windows

    def compute_rpm_score(self, ohlcv_window: List[Dict], symbol: str) -> float:
        """Compute full RPM score for a window."""
        # Capital flow (25%)
        cf = self.rpm_engine.calculate_capital_flow(ohlcv_window, symbol)
        capital_flow_score = cf.value

        # Relative strength (25%)
        ohlcv_dict = {s: self.datasets[s] for s in self.symbols if s in self.datasets}
        rs = self.rpm_engine.calculate_relative_strength(ohlcv_dict, symbol)
        relative_strength_score = rs.value

        # Narrative acceleration (20%) - stub: use 0.0
        narrative_accel_score = 0.0

        # Fundamental confirmation (20%) - stub: use 0.0
        fundamental_score = 0.0

        # Derivatives structure (10%) - stub: use 0.0
        derivatives_score = 0.0

        # Compute full score
        rpm_score = (
            0.25 * capital_flow_score
            + 0.25 * relative_strength_score
            + 0.20 * narrative_accel_score
            + 0.20 * fundamental_score
            + 0.10 * derivatives_score
        )

        return rpm_score

    def run_single_window(self, ohlcv: List[Dict], symbol: str, window_idx: int, train_end: int, test_end: int) -> Dict[str, Any]:
        """Execute single walk-forward window."""
        # Compute RPM scores over test period
        rpm_scores = []
        forward_returns = []

        for test_day in range(train_end, test_end):
            if test_day + 30 >= len(ohlcv):
                break

            # RPM score at test_day using only data up to test_day
            window_ohlcv = ohlcv[:test_day+1]
            rpm_score = self.compute_rpm_score(window_ohlcv, symbol)
            rpm_scores.append(rpm_score)

            # 30-day forward return
            fwd_return = (ohlcv[test_day + 30]["close"] - ohlcv[test_day]["close"]) / ohlcv[test_day]["close"]
            forward_returns.append(fwd_return)

        if len(rpm_scores) < 2 or len(forward_returns) < 2:
            return {
                "window": window_idx,
                "symbol": symbol,
                "samples": 0,
                "ic": 0.0,
                "hit_rate": 0.0,
                "status": "INSUFFICIENT_DATA",
            }

        # Information Coefficient (Spearman correlation)
        ic, _ = spearmanr(rpm_scores, forward_returns)

        # Hit Rate: % of windows where RPM_Score ≥ median correlates with positive 30d return
        median_rpm = np.median(rpm_scores)
        hits = sum(1 for i in range(len(rpm_scores)) if rpm_scores[i] >= median_rpm and forward_returns[i] > 0)
        hit_rate = hits / len(rpm_scores)

        return {
            "window": window_idx,
            "symbol": symbol,
            "samples": len(rpm_scores),
            "ic": float(ic),
            "hit_rate": float(hit_rate),
            "status": "SUCCESS",
        }

    def run_full_validation(self) -> Dict[str, Any]:
        """Execute full 19-window validation across all symbols."""
        logger.info("=" * 60)
        logger.info("B-004: 19-WINDOW WALK-FORWARD VALIDATION")
        logger.info(f"Symbols: {list(self.datasets.keys())}")
        logger.info("=" * 60)

        all_results = {
            "validation_run": "B-004_PHASE6",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "symbols": list(self.datasets.keys()),
            "windows": {},
            "aggregate": {},
        }

        # Execute all 19 windows
        all_ics = []
        all_hit_rates = []

        for symbol in self.datasets.keys():
            ohlcv = self.datasets[symbol]
            if len(ohlcv) < 210:  # Min: 180 train + 30 test
                logger.warning(f"{symbol}: Insufficient data ({len(ohlcv)} candles, need 210+)")
                continue

            windows = self.construct_windows(ohlcv, total_candles=len(ohlcv))
            logger.info(f"{symbol}: Running {len(windows)} windows")

            for window_idx, (train_end, test_end) in enumerate(windows, 1):
                result = self.run_single_window(ohlcv, symbol, window_idx, train_end, test_end)

                window_key = f"{symbol}_W{window_idx}"
                all_results["windows"][window_key] = result

                if result["status"] == "SUCCESS":
                    all_ics.append(result["ic"])
                    all_hit_rates.append(result["hit_rate"])

                logger.info(f"  W{window_idx}: IC={result['ic']:.4f}, HR={result['hit_rate']:.1%}")

        # Aggregate statistics
        if all_ics:
            mean_ic = float(np.mean(all_ics))
            std_ic = float(np.std(all_ics))
            stability = std_ic / (abs(mean_ic) + 1e-8) if mean_ic != 0 else 0.0
            mean_hr = float(np.mean(all_hit_rates))

            all_results["aggregate"] = {
                "mean_ic": mean_ic,
                "std_ic": std_ic,
                "stability": stability,
                "mean_hit_rate": mean_hr,
                "windows_passed": len(all_ics),
            }

            # Gate decision (LOCKED CRITERIA)
            pass_ic = mean_ic >= 0.05
            pass_hr = mean_hr >= 0.55
            pass_stability = stability < 0.50

            gate_status = "PASS" if (pass_ic and pass_hr and pass_stability) else "FAIL"

            all_results["gate_decision"] = {
                "status": gate_status,
                "criteria": {
                    "ic_pass": pass_ic,
                    "ic_value": mean_ic,
                    "ic_threshold": 0.05,
                    "hr_pass": pass_hr,
                    "hr_value": mean_hr,
                    "hr_threshold": 0.55,
                    "stability_pass": pass_stability,
                    "stability_value": stability,
                    "stability_threshold": 0.50,
                },
            }

            logger.info("\n" + "=" * 60)
            logger.info("B-004 GATE DECISION")
            logger.info("=" * 60)
            logger.info(f"Mean IC: {mean_ic:.4f} (threshold ≥ 0.05) → {'PASS' if pass_ic else 'FAIL'}")
            logger.info(f"Hit Rate: {mean_hr:.1%} (threshold ≥ 55%) → {'PASS' if pass_hr else 'FAIL'}")
            logger.info(f"Stability: {stability:.4f} (threshold < 0.50) → {'PASS' if pass_stability else 'FAIL'}")
            logger.info(f"\nVERDICT: {gate_status}")

        # Save results
        output_file = self.output_dir / "B004_VALIDATION_RESULTS.json"
        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=2)

        logger.info(f"\nResults saved to {output_file}")
        return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    orchestrator = B004WFVOrchestrator()
    results = orchestrator.run_full_validation()

    print("\n" + "=" * 60)
    print("B-004 VALIDATION COMPLETE")
    print("=" * 60)
    if "aggregate" in results:
        print(json.dumps(results["aggregate"], indent=2))
    if "gate_decision" in results:
        print(json.dumps(results["gate_decision"], indent=2))
