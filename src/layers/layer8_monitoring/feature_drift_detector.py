"""Feature Drift Detection. Monitors statistical distribution shifts."""

from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np


class DriftStatus(Enum):
    """Feature drift status."""
    STABLE = "stable"
    DRIFTING = "drifting"
    SEVERE = "severe"


@dataclass
class DriftMetrics:
    """Feature drift metrics."""
    feature_name: str
    comparison_period: str
    baseline_mean: float
    current_mean: float
    mean_shift_pct: float
    baseline_std: float
    current_std: float
    volatility_shift_pct: float
    ks_statistic: float
    ks_pvalue: float
    drift_status: DriftStatus
    lookback_days: int


class FeatureDriftDetector:
    """Detects statistical drift in feature distributions."""

    def calculate_mean_shift(self, baseline: List[float], current: List[float]) -> Tuple[float, float, float]:
        """
        Calculate mean shift between baseline and current periods.

        Args:
            baseline: Historical baseline values
            current: Current period values

        Returns:
            (baseline_mean, current_mean, shift_percentage)
        """
        if not baseline or not current or len(baseline) == 0 or len(current) == 0:
            return 0.0, 0.0, 0.0

        baseline_mean = float(np.mean(baseline))
        current_mean = float(np.mean(current))

        if baseline_mean == 0:
            shift_pct = 0.0 if current_mean == 0 else 100.0
        else:
            shift_pct = float((current_mean - baseline_mean) / abs(baseline_mean) * 100)

        return baseline_mean, current_mean, shift_pct

    def calculate_volatility_shift(
        self, baseline: List[float], current: List[float]
    ) -> Tuple[float, float, float]:
        """
        Calculate volatility shift (std deviation) between periods.

        Args:
            baseline: Historical baseline values
            current: Current period values

        Returns:
            (baseline_std, current_std, shift_percentage)
        """
        if not baseline or not current or len(baseline) < 2 or len(current) < 2:
            return 0.0, 0.0, 0.0

        baseline_std = float(np.std(baseline))
        current_std = float(np.std(current))

        if baseline_std == 0:
            shift_pct = 0.0 if current_std == 0 else 100.0
        else:
            shift_pct = float((current_std - baseline_std) / baseline_std * 100)

        return baseline_std, current_std, shift_pct

    def ks_test(self, baseline: List[float], current: List[float]) -> Tuple[float, float]:
        """
        Kolmogorov-Smirnov test for distribution difference.

        Args:
            baseline: Historical baseline values
            current: Current period values

        Returns:
            (ks_statistic 0-1, p_value 0-1)
        """
        if not baseline or not current or len(baseline) < 2 or len(current) < 2:
            return 0.0, 1.0

        baseline_arr = np.array(baseline)
        current_arr = np.array(current)

        # Manual KS implementation (approximate)
        baseline_sorted = np.sort(baseline_arr)
        current_sorted = np.sort(current_arr)

        # Empirical CDFs
        baseline_cdf = np.arange(1, len(baseline_sorted) + 1) / len(baseline_sorted)
        current_cdf = np.arange(1, len(current_sorted) + 1) / len(current_sorted)

        # Maximum distance between CDFs (approximate)
        all_vals = np.sort(np.concatenate([baseline_sorted, current_sorted]))
        max_dist = 0.0

        for val in all_vals:
            baseline_cdf_val = float(np.mean(baseline_arr <= val))
            current_cdf_val = float(np.mean(current_arr <= val))
            dist = abs(baseline_cdf_val - current_cdf_val)
            max_dist = max(max_dist, dist)

        # Simple p-value approximation based on KS statistic
        # Higher KS → lower p-value (more significant difference)
        ks_stat = float(max_dist)
        p_value = float(np.exp(-2.0 * len(baseline_arr) * len(current_arr) / (len(baseline_arr) + len(current_arr)) * ks_stat ** 2))
        p_value = min(p_value, 1.0)

        return ks_stat, p_value

    def get_drift_status(
        self, mean_shift_pct: float, volatility_shift_pct: float, ks_pvalue: float
    ) -> DriftStatus:
        """
        Determine drift status from metrics.

        Args:
            mean_shift_pct: Mean shift as percentage
            volatility_shift_pct: Volatility shift as percentage
            ks_pvalue: KS test p-value

        Returns:
            Status: STABLE (<10% shifts, p>0.05)
                   DRIFTING (10-25% shifts OR p 0.01-0.05)
                   SEVERE (>25% shifts OR p<0.01)
        """
        abs_mean_shift = abs(mean_shift_pct)
        abs_vol_shift = abs(volatility_shift_pct)

        # KS test significance
        if ks_pvalue < 0.01:
            return DriftStatus.SEVERE
        elif ks_pvalue < 0.05:
            return DriftStatus.DRIFTING

        # Mean shift severity
        if abs_mean_shift > 25.0 or abs_vol_shift > 25.0:
            return DriftStatus.SEVERE
        elif abs_mean_shift > 10.0 or abs_vol_shift > 10.0:
            return DriftStatus.DRIFTING

        return DriftStatus.STABLE

    def detect_feature_drift(
        self,
        feature_name: str,
        baseline: List[float],
        current: List[float],
        comparison_period: str = "7d",
        lookback_days: int = 90,
    ) -> DriftMetrics:
        """
        Complete feature drift detection pipeline.

        Args:
            feature_name: Feature identifier
            baseline: Baseline period values
            current: Current period values
            comparison_period: Period label for comparison
            lookback_days: Lookback window in days

        Returns:
            DriftMetrics with all calculations
        """
        baseline_mean, current_mean, mean_shift = self.calculate_mean_shift(baseline, current)
        baseline_std, current_std, vol_shift = self.calculate_volatility_shift(baseline, current)
        ks_stat, ks_p = self.ks_test(baseline, current)

        status = self.get_drift_status(mean_shift, vol_shift, ks_p)

        return DriftMetrics(
            feature_name=feature_name,
            comparison_period=comparison_period,
            baseline_mean=baseline_mean,
            current_mean=current_mean,
            mean_shift_pct=mean_shift,
            baseline_std=baseline_std,
            current_std=current_std,
            volatility_shift_pct=vol_shift,
            ks_statistic=ks_stat,
            ks_pvalue=ks_p,
            drift_status=status,
            lookback_days=lookback_days,
        )

    def rank_features_by_drift(self, metrics: List[DriftMetrics]) -> List[DriftMetrics]:
        """
        Rank features by drift severity.

        Args:
            metrics: List of DriftMetrics

        Returns:
            Sorted by KS p-value (ascending, most significant first)
        """
        return sorted(metrics, key=lambda m: m.ks_pvalue)

    def filter_by_drift_status(self, metrics: List[DriftMetrics], max_status: str = "DRIFTING") -> List[DriftMetrics]:
        """
        Filter features by drift status severity.

        Args:
            metrics: List of DriftMetrics
            max_status: Maximum acceptable status ("STABLE", "DRIFTING", "SEVERE")

        Returns:
            Filtered list meeting maximum status
        """
        status_order = {"STABLE": 0, "DRIFTING": 1, "SEVERE": 2}
        max_level = status_order.get(max_status, 2)

        return [m for m in metrics if status_order.get(m.drift_status.value, 3) <= max_level]

    def identify_severe_drifts(self, metrics: List[DriftMetrics]) -> List[DriftMetrics]:
        """
        Identify all severely drifting features.

        Args:
            metrics: List of DriftMetrics

        Returns:
            Filtered list with SEVERE status only
        """
        return [m for m in metrics if m.drift_status == DriftStatus.SEVERE]

    def generate_drift_summary(self, metrics: DriftMetrics) -> Dict[str, str]:
        """
        Generate human-readable drift summary.

        Args:
            metrics: DriftMetrics

        Returns:
            Summary dict with text descriptions
        """
        return {
            "feature": metrics.feature_name,
            "status": metrics.drift_status.value.upper(),
            "period": metrics.comparison_period,
            "baseline_mean": f"{metrics.baseline_mean:.4f}",
            "current_mean": f"{metrics.current_mean:.4f}",
            "mean_shift": f"{metrics.mean_shift_pct:.2f}%",
            "baseline_std": f"{metrics.baseline_std:.4f}",
            "current_std": f"{metrics.current_std:.4f}",
            "volatility_shift": f"{metrics.volatility_shift_pct:.2f}%",
            "ks_statistic": f"{metrics.ks_statistic:.4f}",
            "ks_pvalue": f"{metrics.ks_pvalue:.6f}",
            "action": "INVESTIGATE" if metrics.drift_status == DriftStatus.SEVERE else "MONITOR" if metrics.drift_status == DriftStatus.DRIFTING else "OK",
        }

    def correlation_matrix_shift(
        self, baseline_features: Dict[str, List[float]], current_features: Dict[str, List[float]]
    ) -> Tuple[float, List[Tuple[str, str, float]]]:
        """
        Detect shifts in feature correlation structure.

        Args:
            baseline_features: Dict of feature_name -> values (baseline)
            current_features: Dict of feature_name -> values (current)

        Returns:
            (overall_correlation_shift, list of (feature1, feature2, correlation_change))
        """
        if not baseline_features or not current_features:
            return 0.0, []

        # Get common features
        common_keys = set(baseline_features.keys()) & set(current_features.keys())
        if len(common_keys) < 2:
            return 0.0, []

        # Convert to arrays for correlation
        baseline_arrays = {k: np.array(baseline_features[k]) for k in common_keys}
        current_arrays = {k: np.array(current_features[k]) for k in common_keys}

        # Calculate correlation matrices
        baseline_keys = sorted(common_keys)
        baseline_data = np.array([baseline_arrays[k] for k in baseline_keys]).T
        current_data = np.array([current_arrays[k] for k in baseline_keys]).T

        if baseline_data.shape[0] < 2 or current_data.shape[0] < 2:
            return 0.0, []

        baseline_corr = np.corrcoef(baseline_data.T)
        current_corr = np.corrcoef(current_data.T)

        # Identify correlation changes
        shifts = []
        total_shift = 0.0

        for i in range(len(baseline_keys)):
            for j in range(i + 1, len(baseline_keys)):
                baseline_rho = baseline_corr[i, j] if not np.isnan(baseline_corr[i, j]) else 0.0
                current_rho = current_corr[i, j] if not np.isnan(current_corr[i, j]) else 0.0
                shift = abs(current_rho - baseline_rho)
                total_shift += shift
                if shift > 0.1:  # Significant shift threshold
                    shifts.append((baseline_keys[i], baseline_keys[j], shift))

        avg_shift = total_shift / max(len(baseline_keys) * (len(baseline_keys) - 1) / 2, 1)

        return float(avg_shift), shifts
