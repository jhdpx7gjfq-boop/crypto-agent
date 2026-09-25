"""
Phase B-004: RPM/RCM Walk-Forward Validation Runner

Executes 19-window expanding WFV per B-004_SPEC.md Section 4.
- No pre-filtering to Bull/Bear (full dataset first)
- Freeze results before post-hoc regime analysis
- Gate criteria: ΔIC > 0.005, HR > 0.50, Stability > 0.65 (ALL pass)
"""

import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from typing import Tuple, Dict, List
from dataclasses import dataclass

try:
    from .rpm_layer import RPMLayer, RPMSignal
    from .rcm_layer import RCMLayer
    from .baseline_predictor import BaselinePredictor
except ImportError:
    from rpm_layer import RPMLayer, RPMSignal
    from rcm_layer import RCMLayer
    from baseline_predictor import BaselinePredictor


@dataclass
class WFVWindowResult:
    """Results for single WFV window."""
    window_idx: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    ic_j: float  # RPM alone IC
    ic_k: float  # RCM IC
    ic_l: float  # Full stack IC
    hit_rate_j: float
    hit_rate_k: float
    hit_rate_l: float


@dataclass
class WFVAggregateResult:
    """Aggregated results across 19 windows."""
    mean_ic_j: float
    std_ic_j: float
    mean_ic_k: float
    std_ic_k: float
    mean_ic_l: float
    std_ic_l: float
    mean_hr_j: float
    mean_hr_k: float
    mean_hr_l: float
    stability_j: float  # 1 - (std / mean)
    stability_k: float
    stability_l: float
    delta_ic_j: float  # IC_J - IC_A (baseline)
    delta_ic_k: float
    delta_ic_l: float
    gate_pass_j: bool  # ΔIC > 0.005 AND HR > 0.50 AND Stability > 0.65
    gate_pass_k: bool
    gate_pass_l: bool
    window_results: List[WFVWindowResult]


class PhaseB004Runner:
    """
    RPM/RCM WFV orchestrator.

    Configuration (frozen per B-004_SPEC.md Section 4.1):
    - Training period: 180 days (fixed from start)
    - Testing period: 30 days per window
    - Overlap: 0 days (no gap)
    - Slide increment: 30 days
    - Total windows: 19
    """

    TRAIN_DAYS = 180
    TEST_DAYS = 30
    SLIDE_DAYS = 30
    TARGET_WINDOWS = 19

    def __init__(self, data_start: pd.Timestamp = pd.Timestamp('2021-01-01'),
                 data_end: pd.Timestamp = pd.Timestamp('2024-09-25')):
        """
        Initialize B-004 runner.

        Args:
            data_start: Start of full dataset
            data_end: End of full dataset
        """
        self.data_start = data_start
        self.data_end = data_end
        self.rpm_layer = RPMLayer()
        self.rcm_layer = RCMLayer()
        self.baseline = BaselinePredictor()

    def create_wfv_windows(self) -> List[Tuple[int, int, int, int]]:
        """
        Create 19 expanding WFV windows (train start fixed, test start slides).

        Each window: train period EXPANDS, test period is 30 days.
        Window i: train_end_idx = TRAIN_DAYS + i*SLIDE_DAYS - 1

        Returns:
            List of (train_start_idx, train_end_idx, test_start_idx, test_end_idx)
        """
        windows = []
        train_start_idx = 0

        for window_idx in range(self.TARGET_WINDOWS):
            # Expanding train: grows by SLIDE_DAYS each window
            train_end_idx = self.TRAIN_DAYS + window_idx * self.SLIDE_DAYS - 1
            test_start_idx = train_end_idx + 1
            test_end_idx = test_start_idx + self.TEST_DAYS

            windows.append((
                train_start_idx,
                train_end_idx,
                test_start_idx,
                test_end_idx,
            ))

        return windows

    def compute_target_returns(self, df: pd.DataFrame, forecast_horizon: int = 5) -> np.ndarray:
        """
        Compute 5D forward returns (target for IC calculation).

        Args:
            df: DataFrame with 'close' column
            forecast_horizon: Days ahead (default 5)

        Returns:
            Array of 5D forward returns
        """
        close = df['close'].values
        forward_returns = np.zeros_like(close, dtype=float)

        for i in range(len(close) - forecast_horizon):
            forward_returns[i] = (close[i + forecast_horizon] - close[i]) / close[i]

        return forward_returns

    def compute_ic(self, signal: np.ndarray, target: np.ndarray) -> float:
        """
        Compute Information Coefficient (Spearman rank correlation).

        Args:
            signal: Prediction signal
            target: Target returns

        Returns:
            Spearman correlation
        """
        if len(signal) < 2 or np.all(np.isnan(signal)) or np.all(np.isnan(target)):
            return 0.0

        # Remove NaNs
        valid_idx = ~(np.isnan(signal) | np.isnan(target))
        if np.sum(valid_idx) < 2:
            return 0.0

        corr, _ = spearmanr(signal[valid_idx], target[valid_idx])
        return float(corr) if not np.isnan(corr) else 0.0

    def compute_hit_rate(self, signal: np.ndarray, target: np.ndarray) -> float:
        """
        Compute hit rate (directional accuracy).

        Args:
            signal: Prediction signal
            target: Target returns

        Returns:
            Hit rate (fraction of correct direction predictions)
        """
        # Convert to binary: +1 if positive, -1 if negative
        signal_binary = np.sign(signal)
        target_binary = np.sign(target)

        # Valid predictions (non-zero signal)
        valid = signal_binary != 0
        if np.sum(valid) == 0:
            return 0.5

        hits = np.sum(signal_binary[valid] == target_binary[valid])
        return float(hits) / np.sum(valid)

    def run_window(self, df: pd.DataFrame, window_spec: Tuple[int, int, int, int],
                   regime_series: pd.Series = None) -> WFVWindowResult:
        """
        Execute single WFV window.

        Args:
            df: Full dataset
            window_spec: (train_start_idx, train_end_idx, test_start_idx, test_end_idx)
            regime_series: Regime labels (optional)

        Returns:
            WFVWindowResult with IC, HR for J, K, L
        """
        train_start, train_end, test_start, test_end = window_spec
        window_idx = (test_start - self.TRAIN_DAYS) // self.SLIDE_DAYS

        train_df = df.iloc[train_start:train_end + 1]
        test_df = df.iloc[test_start:test_end + 1]

        # Compute RPM signal on full test period (PIT-safe)
        rpm_signals = self.rpm_layer.compute_signal(test_df)
        rpm_values = np.array([s.rpm_signal for s in rpm_signals])

        # Compute RCM signal (regime-weighted)
        if regime_series is not None:
            rcm_signals = self.rcm_layer.compute_signal(rpm_signals, regime_series)
            rcm_values = np.array([s.rcm_signal for s in rcm_signals])
        else:
            rcm_values = rpm_values.copy()  # No regime: RCM = RPM

        # Compute baseline signal (momentum) for each test point
        baseline_values = np.array([
            self.baseline.predict(test_df, i) for i in range(len(test_df))
        ])

        # Blend for full stack: 0.5*baseline + 0.3*narm + 0.2*rpm
        # (narm not available yet, use 0 for now)
        full_stack_values = 0.5 * baseline_values + 0.2 * rpm_values

        # Compute target returns (5D forward)
        target = self.compute_target_returns(test_df, forecast_horizon=5)

        # Compute IC and HR for each signal
        ic_j = self.compute_ic(rpm_values, target)
        ic_k = self.compute_ic(rcm_values, target)
        ic_l = self.compute_ic(full_stack_values, target)

        hr_j = self.compute_hit_rate(rpm_values, target)
        hr_k = self.compute_hit_rate(rcm_values, target)
        hr_l = self.compute_hit_rate(full_stack_values, target)

        return WFVWindowResult(
            window_idx=window_idx,
            train_start=train_df.index[0],
            train_end=train_df.index[-1],
            test_start=test_df.index[0],
            test_end=test_df.index[-1],
            ic_j=ic_j,
            ic_k=ic_k,
            ic_l=ic_l,
            hit_rate_j=hr_j,
            hit_rate_k=hr_k,
            hit_rate_l=hr_l,
        )

    def run_wfv(self, df: pd.DataFrame, regime_series: pd.Series = None) -> WFVAggregateResult:
        """
        Execute full 19-window WFV (no pre-filtering).

        Args:
            df: Full OHLCV dataset (2021-01-01 to 2024-09-25)
            regime_series: Regime labels (optional, for RCM)

        Returns:
            WFVAggregateResult with frozen gate metrics
        """
        windows = self.create_wfv_windows()
        window_results = []

        for window_spec in windows:
            result = self.run_window(df, window_spec, regime_series)
            window_results.append(result)

        # Aggregate across 19 windows
        ic_j_values = np.array([w.ic_j for w in window_results])
        ic_k_values = np.array([w.ic_k for w in window_results])
        ic_l_values = np.array([w.ic_l for w in window_results])

        hr_j_values = np.array([w.hit_rate_j for w in window_results])
        hr_k_values = np.array([w.hit_rate_k for w in window_results])
        hr_l_values = np.array([w.hit_rate_l for w in window_results])

        mean_ic_j = float(np.mean(ic_j_values))
        std_ic_j = float(np.std(ic_j_values))
        mean_ic_k = float(np.mean(ic_k_values))
        std_ic_k = float(np.std(ic_k_values))
        mean_ic_l = float(np.mean(ic_l_values))
        std_ic_l = float(np.std(ic_l_values))

        mean_hr_j = float(np.mean(hr_j_values))
        mean_hr_k = float(np.mean(hr_k_values))
        mean_hr_l = float(np.mean(hr_l_values))

        # Stability = 1 - (std / mean)
        stability_j = 1.0 - (std_ic_j / (abs(mean_ic_j) + 1e-8))
        stability_k = 1.0 - (std_ic_k / (abs(mean_ic_k) + 1e-8))
        stability_l = 1.0 - (std_ic_l / (abs(mean_ic_l) + 1e-8))

        # Baseline IC (Model A) — computed separately for delta
        # For now, assume baseline_ic_a from prior phase (B-003: -0.1208)
        baseline_ic_a = -0.1208

        delta_ic_j = mean_ic_j - baseline_ic_a
        delta_ic_k = mean_ic_k - baseline_ic_a
        delta_ic_l = mean_ic_l - baseline_ic_a

        # Gate criteria (ALL must pass)
        gate_pass_j = (delta_ic_j > 0.005) and (mean_hr_j > 0.50) and (stability_j > 0.65)
        gate_pass_k = (delta_ic_k > 0.005) and (mean_hr_k > 0.50) and (stability_k > 0.65)
        gate_pass_l = (delta_ic_l > 0.005) and (mean_hr_l > 0.50) and (stability_l > 0.65)

        return WFVAggregateResult(
            mean_ic_j=mean_ic_j,
            std_ic_j=std_ic_j,
            mean_ic_k=mean_ic_k,
            std_ic_k=std_ic_k,
            mean_ic_l=mean_ic_l,
            std_ic_l=std_ic_l,
            mean_hr_j=mean_hr_j,
            mean_hr_k=mean_hr_k,
            mean_hr_l=mean_hr_l,
            stability_j=stability_j,
            stability_k=stability_k,
            stability_l=stability_l,
            delta_ic_j=delta_ic_j,
            delta_ic_k=delta_ic_k,
            delta_ic_l=delta_ic_l,
            gate_pass_j=gate_pass_j,
            gate_pass_k=gate_pass_k,
            gate_pass_l=gate_pass_l,
            window_results=window_results,
        )
