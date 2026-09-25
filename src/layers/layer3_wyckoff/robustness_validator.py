"""
Phase 5: Robustness Validation Across Market Regimes

Tests BCE engine across 7 distinct market conditions to ensure stability
across different market structures.

Authority: B-004_SPEC.md §"Validation & Walk-Forward Testing (Frozen)"
Status: 🟢 Phase 5 (Robustness Validation)
Date: 2026-09-25
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Tuple
from enum import Enum


class MarketRegime(Enum):
    """Market regime types for robustness testing."""
    BULL = "bull_market"
    BEAR = "bear_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    RISING_CORRELATION = "rising_correlation"
    FALLING_CORRELATION = "falling_correlation"
    LIQUIDATION = "liquidation_events"


@dataclass
class RegimeResult:
    """Robustness result for single market regime."""
    regime_name: str
    regime_type: str

    # Metrics
    f1_score: float
    precision: float
    recall: float
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int

    # Gate status
    passes_gate: bool  # F1 ≥ 0.55
    regime_characteristics: str
    sample_size: int
    notes: str


@dataclass
class RobustnessReport:
    """Complete robustness validation report."""
    spec_version: str
    validation_date: str

    # Results per regime
    regimes: List[RegimeResult]

    # Aggregate metrics
    f1_avg: float
    f1_min: float
    f1_max: float

    # Gate status
    passes_robustness_gate: bool  # >75% pass rate
    passes_count: int
    passes_rate: int

    # Next step
    next_gate: str  # Phase 6: Final Validation Gate


class RobustnessValidator:
    """
    Validates BCE engine across 7 market regimes.

    Regimes:
    1. Bull Market: Price sustained >20% gain
    2. Bear Market: Price sustained >20% loss
    3. High Volatility: >60-day realized vol
    4. Low Volatility: <20-day realized vol
    5. Rising Correlation: All coins track BTC (corr > 0.8)
    6. Falling Correlation: Breakdown of structure (corr < 0.5)
    7. Liquidation Events: Extreme volume spikes (>3x normal)

    Constraints:
    - Each regime F1 ≥ 0.55
    - Overall pass rate > 75% (≥6 of 7 regimes)
    - No exceptions: all regimes matter
    """

    REGIMES = [
        MarketRegime.BULL,
        MarketRegime.BEAR,
        MarketRegime.HIGH_VOLATILITY,
        MarketRegime.LOW_VOLATILITY,
        MarketRegime.RISING_CORRELATION,
        MarketRegime.FALLING_CORRELATION,
        MarketRegime.LIQUIDATION,
    ]

    F1_GATE = 0.55
    PASS_RATE_GATE = 0.75  # >75% (6 of 7)

    def __init__(self):
        """Initialize robustness validator."""
        self.results: List[RegimeResult] = []

    def validate_regime(
        self,
        regime_type: MarketRegime,
        actual_signals: List[bool],
        predicted_signals: List[bool],
        regime_characteristics: str,
    ) -> RegimeResult:
        """
        Validate BCE in a single market regime.

        Args:
            regime_type: Market regime (from MarketRegime enum)
            actual_signals: Ground truth (1 = rotation occurred)
            predicted_signals: Model predictions (1 = rotation predicted)
            regime_characteristics: Description of regime conditions

        Returns:
            RegimeResult with metrics and gate status
        """
        # Ensure same length
        assert len(actual_signals) == len(predicted_signals), \
            f"Signal length mismatch: {len(actual_signals)} vs {len(predicted_signals)}"

        # Calculate confusion matrix
        tp = sum((a == 1) and (p == 1) for a, p in zip(actual_signals, predicted_signals))
        fp = sum((a == 0) and (p == 1) for a, p in zip(actual_signals, predicted_signals))
        fn = sum((a == 1) and (p == 0) for a, p in zip(actual_signals, predicted_signals))
        tn = sum((a == 0) and (p == 0) for a, p in zip(actual_signals, predicted_signals))

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Gate check
        passes_gate = f1 >= self.F1_GATE

        # Create result
        result = RegimeResult(
            regime_name=regime_type.value,
            regime_type=regime_type.name,
            f1_score=f1,
            precision=precision,
            recall=recall,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            passes_gate=passes_gate,
            regime_characteristics=regime_characteristics,
            sample_size=len(actual_signals),
            notes=f"Regime: {regime_type.value}, F1: {f1:.3f}, Precision: {precision:.3f}, Recall: {recall:.3f}"
        )

        self.results.append(result)
        return result

    def generate_report(self) -> RobustnessReport:
        """
        Generate robustness validation report.

        Returns:
            RobustnessReport with aggregate metrics and gate status
        """
        if not self.results:
            raise ValueError("No regime results yet")

        if len(self.results) != len(self.REGIMES):
            raise ValueError(
                f"Incomplete validation: {len(self.results)} / {len(self.REGIMES)} regimes"
            )

        # Calculate aggregate metrics
        f1_scores = [r.f1_score for r in self.results]
        f1_avg = sum(f1_scores) / len(f1_scores)
        f1_min = min(f1_scores)
        f1_max = max(f1_scores)

        # Pass rate
        passes_count = sum(1 for r in self.results if r.passes_gate)
        passes_rate = (passes_count / len(self.results)) * 100

        # Gate status (>75% = at least 6 of 7)
        passes_robustness_gate = passes_rate > 75

        report = RobustnessReport(
            spec_version="b_004_spec_2026_09_25",
            validation_date=datetime.now().isoformat(),
            regimes=self.results,
            f1_avg=f1_avg,
            f1_min=f1_min,
            f1_max=f1_max,
            passes_robustness_gate=passes_robustness_gate,
            passes_count=passes_count,
            passes_rate=int(passes_rate),
            next_gate="Phase 6: Final Validation Gate"
        )

        return report

    def save_report(self, report: RobustnessReport, output_path: str = "validation_reports/ROBUSTNESS_REPORT.json"):
        """
        Save robustness report to JSON.

        Args:
            report: RobustnessReport object
            output_path: Output file path
        """
        from pathlib import Path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        report_dict = asdict(report)
        report_dict['regimes'] = [asdict(r) for r in report.regimes]

        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

    def get_regime_ranking(self) -> List[Tuple[str, float, bool]]:
        """
        Get regimes ranked by F1 score (best to worst).

        Returns:
            List of (regime_name, f1_score, passes_gate) tuples
        """
        if not self.results:
            return []

        # Sort by F1 (descending)
        ranked = sorted(
            self.results,
            key=lambda r: r.f1_score,
            reverse=True
        )

        return [
            (r.regime_name, r.f1_score, r.passes_gate)
            for r in ranked
        ]

    def get_failing_regimes(self) -> List[str]:
        """
        Get list of regimes that fail F1 ≥ 0.55 gate.

        Returns:
            List of regime names failing the gate
        """
        return [
            r.regime_name
            for r in self.results
            if not r.passes_gate
        ]

    def audit_trail_regime_coverage(self) -> Dict:
        """
        Verify all 7 regimes were tested.

        Returns:
            Audit dict with verification status
        """
        audit = {
            "regime_coverage": "PASS",
            "total_regimes": len(self.REGIMES),
            "tested_regimes": len(self.results),
            "verification_date": datetime.now().isoformat(),
            "missing_regimes": []
        }

        tested_names = {r.regime_name for r in self.results}
        expected_names = {r.value for r in self.REGIMES}
        missing = expected_names - tested_names

        if missing:
            audit["regime_coverage"] = "FAIL"
            audit["missing_regimes"] = sorted(list(missing))

        return audit
