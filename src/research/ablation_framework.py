"""Ablation Framework: Models A-G

Systematic testing of Spring + Regime + Flow combinations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.stats import spearmanr
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AblationResult:
    """Result for one model on one window."""
    model: str
    window_id: int
    regime: str
    ic: float
    hit_rate: float
    expectancy: float
    n_predictions: int


class AblationMetrics:
    """Compute IC, HR, expectancy."""

    @staticmethod
    def compute_ic(signals: np.ndarray, returns: np.ndarray) -> float:
        """Information Coefficient = Spearman correlation."""
        if len(signals) < 2:
            return 0.0

        # Remove NaNs
        valid = ~(np.isnan(signals) | np.isnan(returns))
        signals_clean = signals[valid]
        returns_clean = returns[valid]

        if len(signals_clean) < 2:
            return 0.0

        corr, _ = spearmanr(signals_clean, returns_clean)
        return float(corr) if not np.isnan(corr) else 0.0

    @staticmethod
    def compute_hit_rate(signals: np.ndarray, returns: np.ndarray) -> float:
        """% of times sign(signal) matches sign(return)."""
        if len(signals) < 1:
            return 0.5

        signal_direction = np.sign(signals)
        return_direction = np.sign(returns)

        correct = (signal_direction == return_direction).sum()
        total = len(signals)

        return float(correct / total) if total > 0 else 0.5

    @staticmethod
    def compute_expectancy(signals: np.ndarray, returns: np.ndarray) -> float:
        """Average return magnitude weighted by signal strength."""
        if len(signals) < 1:
            return 0.0

        # Normalize signals to [-1, 1]
        signal_strength = signals / (np.abs(signals).max() + 1e-8)

        # Expectancy: avg(return * sign(signal))
        expected = np.mean(returns * np.sign(signal_strength))
        return float(expected)


class AblationFramework:
    """Orchestrates A-G model testing."""

    def __init__(self):
        self.results: List[AblationResult] = []

    def test_model(self,
                   model_name: str,
                   signals_list: List[np.ndarray],  # [signals per window]
                   returns_list: List[np.ndarray],  # [returns per window]
                   window_ids: List[int],
                   regimes: List[str]) -> Dict:
        """
        Test one model (A-G) across all windows.

        Args:
            model_name: "A", "B", "C", ..., "G"
            signals_list: Array of signal scores per window
            returns_list: Array of next-candle returns per window
            window_ids: Window identifiers
            regimes: Regime names

        Returns:
            {
                "model": name,
                "ic_mean": float,
                "ic_std": float,
                "hr_mean": float,
                "expectancy_mean": float,
                "n_windows": int,
                "per_window": [AblationResult, ...]
            }
        """
        per_window = []
        ics = []
        hrs = []
        expectancies = []

        for i, (signals, returns) in enumerate(zip(signals_list, returns_list)):
            if len(signals) < 2:
                continue

            ic = AblationMetrics.compute_ic(signals, returns)
            hr = AblationMetrics.compute_hit_rate(signals, returns)
            expectancy = AblationMetrics.compute_expectancy(signals, returns)

            result = AblationResult(
                model=model_name,
                window_id=window_ids[i],
                regime=regimes[i],
                ic=ic,
                hit_rate=hr,
                expectancy=expectancy,
                n_predictions=len(signals)
            )

            per_window.append(result)
            ics.append(ic)
            hrs.append(hr)
            expectancies.append(expectancy)

        summary = {
            "model": model_name,
            "ic_mean": float(np.mean(ics)) if ics else 0.0,
            "ic_std": float(np.std(ics)) if ics else 0.0,
            "ic_min": float(np.min(ics)) if ics else 0.0,
            "ic_max": float(np.max(ics)) if ics else 0.0,
            "hr_mean": float(np.mean(hrs)) if hrs else 0.5,
            "hr_std": float(np.std(hrs)) if hrs else 0.0,
            "expectancy_mean": float(np.mean(expectancies)) if expectancies else 0.0,
            "expectancy_std": float(np.std(expectancies)) if expectancies else 0.0,
            "n_windows": len(per_window),
            "per_window": [
                {
                    "window_id": r.window_id,
                    "regime": r.regime,
                    "ic": r.ic,
                    "hit_rate": r.hit_rate,
                    "expectancy": r.expectancy,
                    "n_predictions": r.n_predictions
                } for r in per_window
            ]
        }

        self.results.extend(per_window)
        return summary

    def compute_deltas(self, results_dict: Dict[str, Dict]) -> Dict[str, float]:
        """
        Compute incremental IC (delta) between models.

        Args:
            results_dict: {"A": {...}, "B": {...}, ...}

        Returns:
            {
                "delta_ic_b_a": IC(B) - IC(A),
                "delta_ic_e_c": IC(E) - IC(C),
                ...
            }
        """
        deltas = {}

        # Spring impact: B - A
        if "A" in results_dict and "B" in results_dict:
            deltas["delta_ic_b_a"] = results_dict["B"]["ic_mean"] - results_dict["A"]["ic_mean"]

        # Regime impact: C - A
        if "A" in results_dict and "C" in results_dict:
            deltas["delta_ic_c_a"] = results_dict["C"]["ic_mean"] - results_dict["A"]["ic_mean"]

        # Flow impact: D - A
        if "A" in results_dict and "D" in results_dict:
            deltas["delta_ic_d_a"] = results_dict["D"]["ic_mean"] - results_dict["A"]["ic_mean"]

        # Spring + Regime synergy: E - C (controlling for Regime)
        if "C" in results_dict and "E" in results_dict:
            deltas["delta_ic_e_c"] = results_dict["E"]["ic_mean"] - results_dict["C"]["ic_mean"]

        # Spring + Flow synergy: F - D
        if "D" in results_dict and "F" in results_dict:
            deltas["delta_ic_f_d"] = results_dict["F"]["ic_mean"] - results_dict["D"]["ic_mean"]

        # Full vs Regime: G - C
        if "C" in results_dict and "G" in results_dict:
            deltas["delta_ic_g_c"] = results_dict["G"]["ic_mean"] - results_dict["C"]["ic_mean"]

        return deltas

    def per_regime_summary(self, results_dict: Dict[str, Dict]) -> Dict:
        """
        Aggregate results by regime.

        Returns:
            {
                "bull_2021": {"A": {...}, "B": {...}, ...},
                "bear_2022": {...},
                ...
            }
        """
        per_regime = {}

        for model_name, model_results in results_dict.items():
            for window_result in model_results["per_window"]:
                regime = window_result["regime"]
                if regime not in per_regime:
                    per_regime[regime] = {}
                if model_name not in per_regime[regime]:
                    per_regime[regime][model_name] = []

                per_regime[regime][model_name].append({
                    "ic": window_result["ic"],
                    "hr": window_result["hit_rate"],
                    "expectancy": window_result["expectancy"]
                })

        # Aggregate per model per regime
        summary = {}
        for regime, models in per_regime.items():
            summary[regime] = {}
            for model_name, values in models.items():
                ics = [v["ic"] for v in values]
                hrs = [v["hr"] for v in values]
                exps = [v["expectancy"] for v in values]

                summary[regime][model_name] = {
                    "ic_mean": float(np.mean(ics)),
                    "ic_std": float(np.std(ics)),
                    "hr_mean": float(np.mean(hrs)),
                    "expectancy_mean": float(np.mean(exps)),
                    "n_windows": len(ics)
                }

        return summary
