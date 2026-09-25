"""
Phase 6: Final Validation Gate (Aggregate Validation)

Consolidates Phase 3 (Walk-Forward), Phase 4 (Ablation), and Phase 5 (Robustness)
results into a single production-readiness assessment.

Authority: B-004_SPEC.md §"Validation & Walk-Forward Testing (Frozen)"
Status: 🟢 Phase 6 (Final Validation Gate)
Date: 2026-09-25
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from .walkforward_validator import WFVReport
from .ablation_analyzer import AblationReport
from .robustness_validator import RobustnessReport


class ProductionReadiness(Enum):
    """Production readiness status."""
    APPROVED = "approved_for_production"
    CONDITIONAL = "conditional_approval"
    REJECTED = "not_ready_for_production"


@dataclass
class GateResult:
    """Single phase gate result."""
    phase_name: str
    gate_requirement: str
    actual_result: str
    passes: bool
    notes: str


@dataclass
class FinalValidationReport:
    """Complete final validation report."""
    spec_version: str
    validation_date: str

    # Individual phase gates
    phase3_gate: GateResult  # WFV: F1_avg ≥ 0.55
    phase4_gate: GateResult  # Ablation: ≥1 critical component
    phase5_gate: GateResult  # Robustness: >75% pass rate

    # Aggregate status
    all_gates_pass: bool
    production_readiness: str  # approved/conditional/rejected

    # Summary metrics
    wfv_f1_avg: float
    ablation_critical_count: int
    robustness_pass_rate: int

    # Audit trail
    validation_chain: str  # Frozen spec → Phase 3 → Phase 4 → Phase 5 → Final

    # Next step
    next_step: str


class FinalValidationGate:
    """
    Aggregates Phases 3-5 validation results.

    Gate Requirements (ALL must pass):
    - Phase 3 (WFV): F1_avg ≥ 0.55 + pass_rate ≥ 80%
    - Phase 4 (Ablation): ≥1 critical component identified
    - Phase 5 (Robustness): >75% regime pass rate (≥6 of 7)

    Production Status:
    - APPROVED: All 3 gates pass
    - CONDITIONAL: 2 of 3 gates pass (requires exception review)
    - REJECTED: <2 gates pass (requires redesign)
    """

    def __init__(self):
        """Initialize final validation gate."""
        self.wfv_report: Optional[WFVReport] = None
        self.ablation_report: Optional[AblationReport] = None
        self.robustness_report: Optional[RobustnessReport] = None

    def load_wfv_report(self, wfv_report: WFVReport) -> None:
        """Load Walk-Forward Validation report."""
        if not isinstance(wfv_report, WFVReport):
            raise TypeError("wfv_report must be WFVReport instance")
        self.wfv_report = wfv_report

    def load_ablation_report(self, ablation_report: AblationReport) -> None:
        """Load Ablation Analysis report."""
        if not isinstance(ablation_report, AblationReport):
            raise TypeError("ablation_report must be AblationReport instance")
        self.ablation_report = ablation_report

    def load_robustness_report(self, robustness_report: RobustnessReport) -> None:
        """Load Robustness Validation report."""
        if not isinstance(robustness_report, RobustnessReport):
            raise TypeError("robustness_report must be RobustnessReport instance")
        self.robustness_report = robustness_report

    def validate_phase3_gate(self) -> GateResult:
        """Validate Phase 3 Walk-Forward gate."""
        if not self.wfv_report:
            raise ValueError("WFV report not loaded")

        passes = self.wfv_report.passes_wfv_gate
        passes_count = int(len(self.wfv_report.windows) * self.wfv_report.passes_rate / 100)

        return GateResult(
            phase_name="Phase 3: Walk-Forward Validation",
            gate_requirement="F1_avg ≥ 0.55 AND pass_rate ≥ 80%",
            actual_result=f"F1_avg={self.wfv_report.f1_avg:.3f}, pass_rate={self.wfv_report.passes_rate}%",
            passes=passes,
            notes=f"{len(self.wfv_report.windows)} rolling windows, {passes_count}/{len(self.wfv_report.windows)} pass"
        )

    def validate_phase4_gate(self) -> GateResult:
        """Validate Phase 4 Ablation gate."""
        if not self.ablation_report:
            raise ValueError("Ablation report not loaded")

        passes = self.ablation_report.critical_components_identified

        return GateResult(
            phase_name="Phase 4: Ablation Analysis",
            gate_requirement="≥1 critical component identified",
            actual_result=f"Critical: {self.ablation_report.critical_count}, Important: {self.ablation_report.important_count}",
            passes=passes,
            notes=f"6 components: {self.ablation_report.critical_count} critical, {self.ablation_report.important_count} important, {self.ablation_report.optional_count} optional, {self.ablation_report.redundant_count} redundant"
        )

    def validate_phase5_gate(self) -> GateResult:
        """Validate Phase 5 Robustness gate."""
        if not self.robustness_report:
            raise ValueError("Robustness report not loaded")

        passes = self.robustness_report.passes_robustness_gate

        return GateResult(
            phase_name="Phase 5: Robustness Validation",
            gate_requirement=">75% regime pass rate (≥6 of 7)",
            actual_result=f"Pass rate: {self.robustness_report.passes_rate}% ({self.robustness_report.passes_count}/7)",
            passes=passes,
            notes=f"7 market regimes tested, {self.robustness_report.passes_count} pass F1 ≥ 0.55"
        )

    def generate_report(self) -> FinalValidationReport:
        """
        Generate final validation gate report.

        Returns:
            FinalValidationReport with all phase gates and production readiness
        """
        if not all([self.wfv_report, self.ablation_report, self.robustness_report]):
            raise ValueError("All phase reports must be loaded before generating final report")

        # Validate each phase gate
        phase3 = self.validate_phase3_gate()
        phase4 = self.validate_phase4_gate()
        phase5 = self.validate_phase5_gate()

        # Count passing gates
        passes_count = sum([phase3.passes, phase4.passes, phase5.passes])
        all_pass = passes_count == 3

        # Determine production readiness
        if all_pass:
            readiness = ProductionReadiness.APPROVED.value
        elif passes_count >= 2:
            readiness = ProductionReadiness.CONDITIONAL.value
        else:
            readiness = ProductionReadiness.REJECTED.value

        report = FinalValidationReport(
            spec_version="b_004_spec_2026_09_25",
            validation_date=datetime.now().isoformat(),
            phase3_gate=phase3,
            phase4_gate=phase4,
            phase5_gate=phase5,
            all_gates_pass=all_pass,
            production_readiness=readiness,
            wfv_f1_avg=self.wfv_report.f1_avg,
            ablation_critical_count=self.ablation_report.critical_count,
            robustness_pass_rate=self.robustness_report.passes_rate,
            validation_chain="B-004_SPEC (Frozen 2026-09-25) → Phase 3 (WFV) → Phase 4 (Ablation) → Phase 5 (Robustness) → Phase 6 (Final Gate)",
            next_step="Phase 7: RRP Revival Radar" if all_pass else "Remediate failing gates before Phase 7"
        )

        return report

    def save_report(self, report: FinalValidationReport, output_path: str = "validation_reports/FINAL_VALIDATION_REPORT.json"):
        """
        Save final validation report to JSON.

        Args:
            report: FinalValidationReport object
            output_path: Output file path
        """
        from pathlib import Path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        report_dict = asdict(report)
        report_dict['phase3_gate'] = asdict(report.phase3_gate)
        report_dict['phase4_gate'] = asdict(report.phase4_gate)
        report_dict['phase5_gate'] = asdict(report.phase5_gate)

        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

    def audit_trail_all_gates_evaluated(self) -> Dict:
        """
        Verify all 3 phases were evaluated.

        Returns:
            Audit dict with verification status
        """
        audit = {
            "all_gates_evaluated": "PASS" if all([self.wfv_report, self.ablation_report, self.robustness_report]) else "FAIL",
            "phase3_loaded": self.wfv_report is not None,
            "phase4_loaded": self.ablation_report is not None,
            "phase5_loaded": self.robustness_report is not None,
            "verification_date": datetime.now().isoformat()
        }

        return audit

    def get_failing_phases(self) -> list:
        """
        Get list of phases that fail their gates.

        Returns:
            List of phase names failing gates
        """
        if not all([self.wfv_report, self.ablation_report, self.robustness_report]):
            raise ValueError("All phase reports must be loaded")

        failing = []

        if not self.wfv_report.passes_wfv_gate:
            failing.append("Phase 3: Walk-Forward Validation")
        if not self.ablation_report.critical_components_identified:
            failing.append("Phase 4: Ablation Analysis")
        if not self.robustness_report.passes_robustness_gate:
            failing.append("Phase 5: Robustness Validation")

        return failing

    def get_readiness_summary(self) -> Dict[str, Any]:
        """
        Get production readiness summary.

        Returns:
            Dict with readiness status and key metrics
        """
        if not all([self.wfv_report, self.ablation_report, self.robustness_report]):
            raise ValueError("All phase reports must be loaded")

        passes_count = sum([
            self.wfv_report.passes_wfv_gate,
            self.ablation_report.critical_components_identified,
            self.robustness_report.passes_robustness_gate
        ])

        if passes_count == 3:
            status = ProductionReadiness.APPROVED.value
        elif passes_count >= 2:
            status = ProductionReadiness.CONDITIONAL.value
        else:
            status = ProductionReadiness.REJECTED.value

        return {
            "production_readiness": status,
            "gates_passed": passes_count,
            "gates_total": 3,
            "wfv_f1_avg": self.wfv_report.f1_avg,
            "ablation_critical": self.ablation_report.critical_count,
            "robustness_pass_rate": f"{self.robustness_report.passes_rate}%"
        }
