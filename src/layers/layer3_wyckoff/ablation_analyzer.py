"""
Phase 4: Ablation Analysis for BCE Component Importance

Evaluates individual component criticality by removing each component
and measuring F1 score impact.

Authority: B-004_SPEC.md §"Validation & Walk-Forward Testing (Frozen)"
Status: 🟢 Phase 4 (Component Validation)
Date: 2026-09-25
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Tuple
from enum import Enum


class ComponentCriticality(Enum):
    """Component importance classification."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    OPTIONAL = "optional"
    REDUNDANT = "redundant"


@dataclass
class ComponentResult:
    """Ablation result for single component."""
    component_name: str
    baseline_f1: float
    ablated_f1: float
    f1_drop: float
    f1_drop_pct: float
    criticality: str
    threshold_used: str
    notes: str


@dataclass
class AblationReport:
    """Complete ablation analysis report."""
    spec_version: str
    validation_date: str

    # Results per component
    components: List[ComponentResult]

    # Aggregate metrics
    critical_count: int
    important_count: int
    optional_count: int
    redundant_count: int

    # Gate status
    critical_components_identified: bool
    ablation_threshold: float  # F1 drop > 5% = critical

    # Next step
    next_gate: str  # Phase 5: Robustness Validation


class AblationAnalyzer:
    """
    Ablates BCE components to measure importance.

    Method:
    1. Establish baseline F1 (all 6 components)
    2. Remove each component (set to 0)
    3. Re-run validation
    4. Measure F1 drop
    5. Classify criticality

    Constraints:
    - Baseline F1 from Phase 3 (WFV result)
    - Critical: F1 drop > 5%
    - Important: F1 drop 2-5%
    - Optional: F1 drop < 2%
    - Redundant: F1 drop ≈ 0%
    """

    # BCE components
    BCE_COMPONENTS = [
        "wyckoff_structure",
        "volume_analysis",
        "selling_exhaustion",
        "smart_money_accumulation",
        "market_structure",
        "momentum_confirmation",
    ]

    # Criticality thresholds (F1 drop %)
    CRITICAL_THRESHOLD = 0.05  # > 5%
    IMPORTANT_THRESHOLD = 0.02  # 2-5%
    OPTIONAL_THRESHOLD = 0.00  # < 2%

    def __init__(self, baseline_f1: float):
        """
        Args:
            baseline_f1: Baseline F1 from Phase 3 WFV (should be ≥ 0.55)
        """
        if baseline_f1 < 0.55:
            raise ValueError(
                f"Baseline F1 must be ≥ 0.55 (Phase 3 gate). Got {baseline_f1}"
            )

        self.baseline_f1 = baseline_f1
        self.results: List[ComponentResult] = []

    def ablate_component(
        self,
        component_name: str,
        ablated_f1: float,
    ) -> ComponentResult:
        """
        Ablate a single component and measure impact.

        Args:
            component_name: Component to remove
            ablated_f1: F1 score with component set to 0

        Returns:
            ComponentResult with criticality classification
        """
        if component_name not in self.BCE_COMPONENTS:
            raise ValueError(
                f"Unknown component: {component_name}. "
                f"Valid: {self.BCE_COMPONENTS}"
            )

        # Calculate drop
        f1_drop = self.baseline_f1 - ablated_f1
        f1_drop_pct = (f1_drop / self.baseline_f1) * 100

        # Classify criticality
        if f1_drop_pct > 5:
            criticality = ComponentCriticality.CRITICAL.value
            threshold = f"{self.CRITICAL_THRESHOLD * 100}%"
        elif f1_drop_pct > 2:
            criticality = ComponentCriticality.IMPORTANT.value
            threshold = f"{self.IMPORTANT_THRESHOLD * 100}%"
        elif f1_drop_pct > 0.5:
            criticality = ComponentCriticality.OPTIONAL.value
            threshold = f"{self.OPTIONAL_THRESHOLD * 100}%"
        else:
            criticality = ComponentCriticality.REDUNDANT.value
            threshold = "~0%"

        result = ComponentResult(
            component_name=component_name,
            baseline_f1=self.baseline_f1,
            ablated_f1=ablated_f1,
            f1_drop=f1_drop,
            f1_drop_pct=f1_drop_pct,
            criticality=criticality,
            threshold_used=threshold,
            notes=f"F1 drop: {f1_drop:.4f} ({f1_drop_pct:.1f}%) → {criticality.upper()}"
        )

        self.results.append(result)
        return result

    def generate_report(self) -> AblationReport:
        """
        Generate ablation analysis report.

        Returns:
            AblationReport with aggregate metrics and gate status
        """
        if not self.results:
            raise ValueError("No ablation results yet")

        if len(self.results) != len(self.BCE_COMPONENTS):
            raise ValueError(
                f"Incomplete ablation: {len(self.results)} / {len(self.BCE_COMPONENTS)} components"
            )

        # Count criticalities
        critical_count = sum(1 for r in self.results if r.criticality == "critical")
        important_count = sum(1 for r in self.results if r.criticality == "important")
        optional_count = sum(1 for r in self.results if r.criticality == "optional")
        redundant_count = sum(1 for r in self.results if r.criticality == "redundant")

        # Gate status (must identify at least 1 critical)
        critical_components_identified = critical_count >= 1

        report = AblationReport(
            spec_version="b_004_spec_2026_09_25",
            validation_date=datetime.now().isoformat(),
            components=self.results,
            critical_count=critical_count,
            important_count=important_count,
            optional_count=optional_count,
            redundant_count=redundant_count,
            critical_components_identified=critical_components_identified,
            ablation_threshold=self.CRITICAL_THRESHOLD,
            next_gate="Phase 5: Robustness Validation"
        )

        return report

    def save_report(self, report: AblationReport, output_path: str = "validation_reports/ABLATION_REPORT.json"):
        """
        Save ablation report to JSON.

        Args:
            report: AblationReport object
            output_path: Output file path
        """
        from pathlib import Path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        report_dict = asdict(report)
        report_dict['components'] = [asdict(c) for c in report.components]

        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

    def get_component_ranking(self) -> List[Tuple[str, str, float]]:
        """
        Get components ranked by importance (F1 drop).

        Returns:
            List of (component_name, criticality, f1_drop_pct) tuples
        """
        if not self.results:
            return []

        # Sort by F1 drop (descending)
        ranked = sorted(
            self.results,
            key=lambda r: r.f1_drop_pct,
            reverse=True
        )

        return [
            (r.component_name, r.criticality, r.f1_drop_pct)
            for r in ranked
        ]

    def get_critical_components(self) -> List[str]:
        """
        Get list of critical components (must keep).

        Returns:
            List of component names marked as critical
        """
        return [
            r.component_name
            for r in self.results
            if r.criticality == "critical"
        ]

    def get_removable_components(self) -> List[str]:
        """
        Get list of optional/redundant components (can remove).

        Returns:
            List of component names that can be removed without significant impact
        """
        return [
            r.component_name
            for r in self.results
            if r.criticality in ["optional", "redundant"]
        ]

    def audit_trail_component_consistency(self) -> Dict:
        """
        Verify all 6 components were tested.

        Returns:
            Audit dict with verification status
        """
        audit = {
            "component_coverage": "PASS",
            "total_components": len(self.BCE_COMPONENTS),
            "tested_components": len(self.results),
            "verification_date": datetime.now().isoformat(),
            "missing_components": []
        }

        tested_names = {r.component_name for r in self.results}
        missing = set(self.BCE_COMPONENTS) - tested_names

        if missing:
            audit["component_coverage"] = "FAIL"
            audit["missing_components"] = list(missing)

        return audit
