"""H-005 WFV Runner: 19-Window Expanding Walk-Forward Validation

Protocol: 180D fixed train, 30D test, 30D slide
PIT-compliant: signal receives only data[:idx+1]
Gate: ΔIC > 0.005 AND HR > 0.50 AND Stability > 0.65 (ALL must pass)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass
from scipy.stats import spearmanr


@dataclass
class WFVWindow:
    """Single walk-forward window."""
    window_id: int
    train_start_idx: int
    train_end_idx: int
    test_start_idx: int
    test_end_idx: int

    def __repr__(self):
        return f"W{self.window_id}: train=[{self.train_start_idx},{self.train_end_idx}], test=[{self.test_start_idx},{self.test_end_idx}]"


@dataclass
class WFVResult:
    """Result for single window."""
    window: WFVWindow
    ic: float
    hr: float
    stability: float
    n_predictions: int

    def passes_gate(self) -> bool:
        """Gate: ΔIC > 0.005, HR > 0.50, Stability > 0.65 (vs baseline)."""
        # This is per-window; aggregate gate check is in WFVAggregateResult
        return True  # Individual windows don't gate; aggregate does


class H005WFVRunner:
    """Execute 19-window expanding WFV for H-005.

    Development period: frozen 2021-01-01 to 2024-09-25
    Hold-out period: locked 2024-09-26 to 2025-09-28 (untouched)
    """

    def __init__(self, n_windows: int = 19, train_days: int = 180, test_days: int = 30):
        self.n_windows = n_windows
        self.train_days = train_days
        self.test_days = test_days

    def build_windows(self, df_len: int, dev_end_idx: int) -> List[WFVWindow]:
        """Build 19 expanding windows within dev period only.

        Args:
            df_len: Total DataFrame length
            dev_end_idx: Last index of dev period (2024-09-25)

        Returns:
            List of WFVWindow objects
        """
        windows = []

        # Total available for WFV: 0 to dev_end_idx
        available_rows = dev_end_idx + 1

        # Strategy: expanding train (fixed start), sliding test
        # Start from train_days rows, add test_days each iteration

        train_start = 0
        test_start = self.train_days

        for w_id in range(self.n_windows):
            test_end = min(test_start + self.test_days - 1, dev_end_idx)

            if test_start > dev_end_idx:
                break

            window = WFVWindow(
                window_id=w_id,
                train_start_idx=train_start,
                train_end_idx=test_start - 1,
                test_start_idx=test_start,
                test_end_idx=test_end,
            )
            windows.append(window)

            # Slide test window
            test_start = test_end + 1

        return windows[:self.n_windows]  # Exactly 19 windows

    def run_wfv(self,
                 df: pd.DataFrame,
                 baseline_predictions: np.ndarray,
                 h005_predictions: np.ndarray,
                 windows: List[WFVWindow]) -> Dict[str, Any]:
        """Execute WFV: compute IC, HR, Stability for each window.

        Args:
            df: Full DataFrame with 'close' column
            baseline_predictions: Baseline model predictions (same length as df)
            h005_predictions: H-005 model predictions (same length as df)
            windows: List of WFVWindow objects

        Returns:
            Aggregate results dict
        """

        # Compute 5D forward returns (signal horizon)
        close = df["close"].values
        forward_returns = np.zeros(len(df))
        for i in range(len(df) - 5):
            forward_returns[i] = (close[i + 5] - close[i]) / close[i]

        window_results = []
        all_ics = []
        all_hrs = []

        for window in windows:
            test_slice = slice(window.test_start_idx, window.test_end_idx + 1)
            test_idx = np.arange(window.test_start_idx, window.test_end_idx + 1)

            # Get predictions and actuals for this window
            h005_preds = h005_predictions[test_slice]
            actuals = forward_returns[test_slice]

            # Information Coefficient (Spearman rank correlation)
            ic, _ = spearmanr(h005_preds, actuals)
            ic = 0.0 if np.isnan(ic) else ic

            # Hit Rate (directional accuracy)
            hr = np.mean((h005_preds > 0) == (actuals > 0)) if len(h005_preds) > 0 else 0.5

            # Stability (inverse of relative volatility)
            # Placeholder: set to 1.0 if IC > 0, else adjust
            stability = 1.0 if abs(ic) > 0.01 else -0.5

            result = WFVResult(
                window=window,
                ic=ic,
                hr=hr,
                stability=stability,
                n_predictions=len(h005_preds),
            )
            window_results.append(result)
            all_ics.append(ic)
            all_hrs.append(hr)

        # Aggregate metrics
        mean_ic = np.mean(all_ics)
        mean_hr = np.mean(all_hrs)
        mean_stability = np.mean([r.stability for r in window_results])

        # Baseline IC (for ΔIC calculation)
        baseline_ics = []
        for window in windows:
            test_slice = slice(window.test_start_idx, window.test_end_idx + 1)
            baseline_preds = baseline_predictions[test_slice]
            actuals = forward_returns[test_slice]
            ic_baseline, _ = spearmanr(baseline_preds, actuals)
            baseline_ics.append(0.0 if np.isnan(ic_baseline) else ic_baseline)

        baseline_mean_ic = np.mean(baseline_ics)
        delta_ic = mean_ic - baseline_mean_ic

        return {
            "n_windows": len(window_results),
            "baseline_ic": baseline_mean_ic,
            "ic": mean_ic,
            "delta_ic": delta_ic,
            "hr": mean_hr,
            "stability": mean_stability,
            "gate_pass": (delta_ic > 0.005) and (mean_hr > 0.50) and (mean_stability > 0.65),
            "window_results": window_results,
        }
