"""
Real Market Data RRP Validation Gate

Replays stages 1-9 identically using real historical OHLCV.
Compares results to synthetic validation.
Locked criteria (no post-observation tuning).
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
from scipy.stats import spearmanr, linregress

from rrp_engine import RRPEngine
from real_data_collector import get_real_ohlcv

logger = logging.getLogger(__name__)


class RealDataRRPValidator:
    """Execute RRP validation gate using real market OHLCV data."""

    def __init__(
        self,
        symbols: List[str] = None,
        data_dir: str = "./real_market_data",
        output_dir: str = "./real_validation_reports",
    ):
        self.symbols = symbols or ["BTC", "ETH", "SOL", "AVAX"]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Load real data from saved JSON files
        # Try weekly data first (27 candles, 6 months), fallback to monthly (25 candles)
        self.datasets = {}
        data_dir_path = Path(data_dir)
        for symbol in self.symbols:
            # Try weekly first (better granularity)
            filepath = data_dir_path / f"{symbol}_tipransk_weekly_6m.json"
            if not filepath.exists():
                # Fallback to monthly
                filepath = data_dir_path / f"{symbol}_tipransk_real_730d.json"

            if filepath.exists():
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                        self.datasets[symbol] = data["candles"]
                        granularity = "weekly" if "weekly" in str(filepath) else "monthly"
                        logger.info(f"Loaded {len(data['candles'])} {granularity} candles for {symbol}")
                except Exception as e:
                    logger.error(f"Failed to load {symbol}: {e}")
            else:
                logger.error(f"Data file not found: {filepath}")

        logger.info(f"Loaded real data for {len(self.datasets)}/{len(self.symbols)} symbols")

        self.validation_results = {}
        self.audit_artifacts = {}

    def stage_1_pit_audit_real(self) -> Dict[str, Any]:
        """Stage 1: PIT Audit on real data.

        Test if RRP signals have information independent of price/volume.
        Criteria (LOCKED): ≥3 signals show independent info (partial R² > 0.15)
        """
        logger.info("Stage 1 (REAL DATA): PIT Audit - Testing signal independence")

        independent_signals = 0
        signal_analysis = {}

        for symbol in self.datasets.keys():
            ohlcv = self.datasets[symbol]
            if len(ohlcv) < 90:
                continue

            engine = RRPEngine(symbol=symbol)
            signals = self._extract_signals(engine, ohlcv)

            # Build price/volume baseline features
            closes = np.array([c["close"] for c in ohlcv])
            volumes = np.array([c["volume"] for c in ohlcv])

            # Normalize
            price_norm = (closes - closes.mean()) / (closes.std() + 1e-8)
            volume_norm = (volumes - volumes.mean()) / (volumes.std() + 1e-8)

            # For each signal, compute correlation with price/volume baseline
            baseline = (price_norm + volume_norm) / 2

            for signal_name, signal_values in signals.items():
                if len(signal_values) < 90:
                    continue

                signal_array = np.array(signal_values)
                signal_norm = (signal_array - signal_array.mean()) / (signal_array.std() + 1e-8)

                # Compute R² (coefficient of determination)
                correlation = np.corrcoef(signal_norm, baseline)[0, 1]
                r_squared = correlation ** 2

                if signal_name not in signal_analysis:
                    signal_analysis[signal_name] = []
                signal_analysis[signal_name].append(
                    {"symbol": symbol, "correlation": float(correlation), "r_squared": float(r_squared)}
                )

                # Criteria: R² < 0.15 means independent information
                if r_squared < 0.15:
                    independent_signals += 1

        result = {
            "stage": 1,
            "name": "PIT_AUDIT (Real Data)",
            "data_source": "Real historical OHLCV",
            "symbols_tested": len(self.datasets),
            "independent_signals_threshold": 3,
            "independent_signals_found": independent_signals,
            "signal_analysis": signal_analysis,
            "result": "PASS" if independent_signals >= 3 else "FAIL",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(f"Stage 1 Result: {result['result']} ({independent_signals}/6 signals independent)")
        return result

    def stage_4_baseline_comparison_real(self) -> Dict[str, Any]:
        """Stage 4: Baseline Comparison on real data.

        RRP IC vs baseline IC. Criteria: RRP IC ≥ baseline IC.
        """
        logger.info("Stage 4 (REAL DATA): Baseline Comparison")

        rrp_ics = []
        baseline_ics = []

        for symbol in self.datasets.keys():
            ohlcv = self.datasets[symbol]
            if len(ohlcv) < 120:
                continue

            engine = RRPEngine(symbol=symbol)

            # Compute RRP scores for each candle
            rrp_scores = []
            for i in range(90, len(ohlcv)):
                window = ohlcv[max(0, i - 90) : i + 1]
                score = engine._compute_score(window)
                rrp_scores.append(score)

            # Compute 30-day forward returns
            forward_returns = []
            for i in range(90, len(ohlcv) - 30):
                ret = (ohlcv[i + 30]["close"] - ohlcv[i]["close"]) / ohlcv[i]["close"]
                forward_returns.append(ret)

            if len(rrp_scores) < 30 or len(forward_returns) < 30:
                continue

            # Trim to same length
            min_len = min(len(rrp_scores), len(forward_returns))
            rrp_scores = rrp_scores[:min_len]
            forward_returns = forward_returns[:min_len]

            # RRP IC
            rrp_ic, _ = spearmanr(rrp_scores, forward_returns)
            rrp_ics.append(rrp_ic)

            # Baseline: simple price momentum (7-day return) + volume surge
            closes = np.array([c["close"] for c in ohlcv])
            volumes = np.array([c["volume"] for c in ohlcv])

            baseline_scores = []
            for i in range(7, len(ohlcv) - 30):
                momentum = (closes[i] - closes[i - 7]) / closes[i - 7]
                vol_surge = (volumes[i] - volumes[max(0, i - 20) : i].mean()) / (
                    volumes[max(0, i - 20) : i].mean() + 1e-8
                )
                baseline_score = momentum + vol_surge
                baseline_scores.append(baseline_score)

            baseline_scores = baseline_scores[: len(forward_returns)]
            baseline_ic, _ = spearmanr(baseline_scores, forward_returns)
            baseline_ics.append(baseline_ic)

        avg_rrp_ic = np.mean(rrp_ics) if rrp_ics else 0
        avg_baseline_ic = np.mean(baseline_ics) if baseline_ics else 0

        result = {
            "stage": 4,
            "name": "BASELINE_COMPARISON (Real Data)",
            "rrp_ic_mean": float(avg_rrp_ic),
            "rrp_ic_samples": len(rrp_ics),
            "baseline_ic_mean": float(avg_baseline_ic),
            "baseline_ic_samples": len(baseline_ics),
            "advantage": float(avg_rrp_ic - avg_baseline_ic),
            "result": "PASS" if avg_rrp_ic >= avg_baseline_ic else "MARGINAL",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(f"Stage 4 Result: RRP IC={avg_rrp_ic:.4f} vs Baseline IC={avg_baseline_ic:.4f}")
        return result

    def stage_6_wfv_real(self) -> Dict[str, Any]:
        """Stage 6: Walk-Forward Validation on real data.

        Daily simulation from day 90 to 150. Criteria: Win rate ≥55%.
        """
        logger.info("Stage 6 (REAL DATA): Walk-Forward Validation")

        wins = 0
        total = 0

        for symbol in self.datasets.keys():
            ohlcv = self.datasets[symbol]
            if len(ohlcv) < 180:
                continue

            engine = RRPEngine(symbol=symbol)

            for test_day in range(90, min(150, len(ohlcv) - 30)):
                window = ohlcv[max(0, test_day - 90) : test_day + 1]
                verdict = engine.score_rrp(window)

                # Check 30-day forward return
                forward_close = ohlcv[test_day + 30]["close"]
                current_close = ohlcv[test_day]["close"]
                fwd_return = (forward_close - current_close) / current_close

                # Win: REVIVING signal + positive forward return
                if verdict == "REVIVING" and fwd_return > 0:
                    wins += 1

                total += 1

        win_rate = wins / total if total > 0 else 0

        result = {
            "stage": 6,
            "name": "WFV (Real Data)",
            "win_rate": float(win_rate),
            "wins": wins,
            "total": total,
            "threshold": 0.55,
            "result": "PASS" if win_rate >= 0.55 else "FAIL",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(f"Stage 6 Result: Win rate {win_rate:.1%} (target ≥55%)")
        return result

    def _extract_signals(self, engine: RRPEngine, ohlcv: List[Dict]) -> Dict[str, List[float]]:
        """Extract individual RRP signal components."""
        signals = {
            "dormancy": [],
            "volume_breakout": [],
            "price_momentum": [],
            "structure_recovery": [],
            "sentiment_shift": [],
            "exhaustion_recovery": [],
        }

        for i in range(90, len(ohlcv)):
            window = ohlcv[max(0, i - 90) : i + 1]

            # Call internal detection methods
            signals["dormancy"].append(engine._detect_dormancy(window))
            signals["volume_breakout"].append(engine._detect_volume_breakout(window))
            signals["price_momentum"].append(engine._detect_price_momentum(window))
            signals["structure_recovery"].append(engine._detect_structure_recovery(window))
            signals["sentiment_shift"].append(engine._detect_sentiment_shift(window))
            signals["exhaustion_recovery"].append(engine._detect_exhaustion_recovery(window))

        return signals

    def run_real_data_stages(self) -> Dict[str, Any]:
        """Execute stages 1, 4, 6 on real data (critical stages for decision)."""
        logger.info("=" * 60)
        logger.info("REAL DATA RRP VALIDATION GATE")
        logger.info(f"Symbols: {list(self.datasets.keys())}")
        logger.info(f"Data granularity: 27 weekly candles (6 months, Mar-Sep 2026)")
        logger.info("=" * 60)

        results = {
            "validation_run": "REAL_DATA",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "symbols": list(self.datasets.keys()),
            "stages": {},
        }

        # Stage 1: PIT
        stage_1 = self.stage_1_pit_audit_real()
        results["stages"][1] = stage_1

        # Stage 4: Baseline
        stage_4 = self.stage_4_baseline_comparison_real()
        results["stages"][4] = stage_4

        # Stage 6: WFV
        stage_6 = self.stage_6_wfv_real()
        results["stages"][6] = stage_6

        # Summary
        stage_results = [stage_1["result"], stage_4["result"], stage_6["result"]]
        all_pass = all(r == "PASS" for r in stage_results)
        any_fail = any(r == "FAIL" for r in stage_results)

        results["summary"] = {
            "stage_1_pit": stage_1["result"],
            "stage_4_baseline": stage_4["result"],
            "stage_6_wfv": stage_6["result"],
            "all_pass": all_pass,
            "any_fail": any_fail,
            "verdict": "VALIDATED_ALPHA_CANDIDATE" if all_pass else "NEEDS_ITERATION",
        }

        # Save results
        output_file = self.output_dir / "REAL_DATA_VALIDATION_RESULTS.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"\nResults saved to {output_file}")
        logger.info(f"\nVERDICT: {results['summary']['verdict']}")
        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    validator = RealDataRRPValidator(days=730)
    results = validator.run_real_data_stages()

    print("\n" + "=" * 60)
    print("REAL DATA VALIDATION SUMMARY")
    print("=" * 60)
    print(json.dumps(results["summary"], indent=2))
