"""
IGWT-PF26 Phase 9: AI Research Copilot
=======================================

Read-only AI research assistant for hypothesis generation and anomaly detection.
Human-gated validation pipeline. No parameter modification, trade execution, or signal approval.

Constraints:
✅ READ data from all layers
✅ Run analyses
✅ Propose hypotheses
✅ Report findings
✅ Challenge assumptions
❌ Modify parameters
❌ Execute trades
❌ Approve signals
❌ Bypass validation

Version: 1.0.0
Status: Research Phase (No lookahead protection yet)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ApprovalGate(Enum):
    """Status of human approval requirement."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class AnalysisScope(Enum):
    """What layers of analysis to access."""
    DATA_ONLY = "data_only"
    INDICATORS = "indicators"
    TECHNICAL_ANALYSIS = "technical_analysis"
    NARRATIVE_ANALYSIS = "narrative_analysis"
    ROTATION_ANALYSIS = "rotation_analysis"
    REVIVAL_ANALYSIS = "revival_analysis"
    ALL_LAYERS = "all_layers"


@dataclass
class ResearchProposal:
    """Structured research hypothesis for human review."""
    proposal_id: str
    timestamp: datetime
    coin_id: str
    hypothesis: str
    confidence: float  # 0-1
    supporting_metrics: Dict[str, Any]
    conflicting_metrics: Dict[str, Any]
    data_sources_used: List[str]
    assumptions: List[str]
    risk_factors: List[str]
    approval_status: ApprovalGate = ApprovalGate.PENDING
    approval_comment: Optional[str] = None
    experimental_validation: Optional[str] = None
    analysis_scope: AnalysisScope = AnalysisScope.ALL_LAYERS
    is_backed_by_walk_forward: bool = False
    pit_oos_wfv_status: str = "research_phase"  # research_phase | pit_validated | oos_tested | wfv_confirmed


@dataclass
class AnomalyReport:
    """Detected anomaly with statistical confidence."""
    report_id: str
    timestamp: datetime
    coin_id: str
    anomaly_type: str  # e.g., "volume_surge", "narrative_reversal", "rotation_acceleration"
    severity: str  # low, medium, high, critical
    baseline_value: float
    current_value: float
    deviation_sigma: float  # Standard deviations from mean
    affected_layers: List[str]
    likely_causes: List[str]
    approval_gate: ApprovalGate = ApprovalGate.PENDING
    human_verified: bool = False


@dataclass
class ComparisonScenario:
    """Side-by-side analysis of multiple coins/timeframes."""
    scenario_id: str
    timestamp: datetime
    coins_analyzed: List[str]
    dimensions: Dict[str, Dict[str, float]]  # {metric: {coin: value}}
    divergences: Dict[str, List[str]]  # Metrics where coins differ significantly
    convergence_signals: List[str]  # Where coins align (potential rotation signal)
    approval_required: bool = True
    analysis_depth: str = "research"  # research | validated


class AIResearchCopilot:
    """
    Read-only research assistant.

    Generates hypotheses, detects anomalies, proposes experiments.
    All proposals require human approval before any action.
    Cannot modify parameters or execute trades.
    """

    def __init__(self, read_only: bool = True):
        """Initialize copilot in read-only mode (mandatory)."""
        if not read_only:
            raise ValueError("AIResearchCopilot must operate in read-only mode.")
        self.read_only = read_only
        self.proposals: Dict[str, ResearchProposal] = {}
        self.anomalies: Dict[str, AnomalyReport] = {}
        self.scenarios: Dict[str, ComparisonScenario] = {}
        logger.info("AI Research Copilot initialized (read-only, human-gated)")

    def propose_hypothesis(
        self,
        coin_id: str,
        hypothesis: str,
        confidence: float,
        supporting_metrics: Dict[str, Any],
        conflicting_metrics: Dict[str, Any],
        data_sources: List[str],
        assumptions: List[str],
        risk_factors: List[str],
    ) -> ResearchProposal:
        """
        Generate structured hypothesis for human review.

        Args:
            coin_id: Token identifier
            hypothesis: English description of proposed hypothesis
            confidence: 0-1 confidence level
            supporting_metrics: {metric_name: value} that support hypothesis
            conflicting_metrics: {metric_name: value} that contradict hypothesis
            data_sources: ["coingecko", "glassnode", "on_chain", etc.]
            assumptions: List of assumptions made
            risk_factors: Potential failure modes

        Returns:
            ResearchProposal (requires human approval before use)
        """
        if not 0 <= confidence <= 1:
            raise ValueError(f"Confidence must be 0-1, got {confidence}")

        proposal = ResearchProposal(
            proposal_id=f"hp_{coin_id}_{datetime.now().isoformat()}",
            timestamp=datetime.now(),
            coin_id=coin_id,
            hypothesis=hypothesis,
            confidence=confidence,
            supporting_metrics=supporting_metrics,
            conflicting_metrics=conflicting_metrics,
            data_sources_used=data_sources,
            assumptions=assumptions,
            risk_factors=risk_factors,
            approval_status=ApprovalGate.PENDING,
            pit_oos_wfv_status="research_phase",
        )

        self.proposals[proposal.proposal_id] = proposal
        logger.info(f"Hypothesis proposed for {coin_id}: {proposal.proposal_id}")
        return proposal

    def detect_anomaly(
        self,
        coin_id: str,
        anomaly_type: str,
        baseline: float,
        current: float,
        sigma: float,
        affected_layers: List[str],
        likely_causes: List[str],
        severity: str = "medium",
    ) -> AnomalyReport:
        """
        Report statistical anomaly (e.g., 3-sigma volume spike).

        Args:
            coin_id: Token identifier
            anomaly_type: "volume_surge", "narrative_reversal", "rotation_acceleration", etc.
            baseline: Normal/expected value
            current: Observed value
            sigma: Standard deviations from mean
            affected_layers: Which analysis layers detected this
            likely_causes: Hypothesized root causes
            severity: low | medium | high | critical

        Returns:
            AnomalyReport (flagged for human verification)
        """
        if sigma < 2:
            logger.warning(f"Anomaly severity low ({sigma} sigma), consider raising threshold")

        report = AnomalyReport(
            report_id=f"anom_{coin_id}_{datetime.now().isoformat()}",
            timestamp=datetime.now(),
            coin_id=coin_id,
            anomaly_type=anomaly_type,
            severity=severity,
            baseline_value=baseline,
            current_value=current,
            deviation_sigma=sigma,
            affected_layers=affected_layers,
            likely_causes=likely_causes,
            approval_gate=ApprovalGate.PENDING,
            human_verified=False,
        )

        self.anomalies[report.report_id] = report
        logger.warning(f"Anomaly detected ({severity}): {anomaly_type} for {coin_id}")
        return report

    def compare_scenarios(
        self,
        coins: List[str],
        metrics: Dict[str, Dict[str, float]],
        scenario_description: str = "",
    ) -> ComparisonScenario:
        """
        Side-by-side comparison of coins across metrics.

        Args:
            coins: List of coin_ids to compare
            metrics: {metric_name: {coin_id: value}}
            scenario_description: Context for analysis

        Returns:
            ComparisonScenario with divergences and convergences highlighted
        """
        divergences = {}
        convergence_signals = []

        for metric, values in metrics.items():
            if len(values) > 1:
                vals = list(values.values())
                if max(vals) > 0:
                    spread = (max(vals) - min(vals)) / (max(vals) + 1e-6)
                    if spread > 0.3:  # >30% divergence
                        divergences[metric] = [c for c in coins if c in values]
                    elif spread < 0.1:  # <10% convergence
                        convergence_signals.append(metric)

        scenario = ComparisonScenario(
            scenario_id=f"scen_{datetime.now().isoformat()}",
            timestamp=datetime.now(),
            coins_analyzed=coins,
            dimensions=metrics,
            divergences=divergences,
            convergence_signals=convergence_signals,
            approval_required=True,
            analysis_depth="research",
        )

        self.scenarios[scenario.scenario_id] = scenario
        logger.info(f"Scenario analysis: {len(coins)} coins, {len(divergences)} divergence metrics")
        return scenario

    def challenge_assumption(
        self,
        assumption: str,
        supporting_evidence: List[str],
        contradicting_evidence: List[str],
        alternative_hypotheses: List[str],
    ) -> Dict[str, Any]:
        """
        Challenge a hypothesis assumption with evidence.

        Args:
            assumption: The assumption to challenge
            supporting_evidence: Data supporting the assumption
            contradicting_evidence: Data contradicting it
            alternative_hypotheses: Different explanations

        Returns:
            Challenge report for human review
        """
        confidence_in_assumption = len(supporting_evidence) / (
            len(supporting_evidence) + len(contradicting_evidence) + 1e-6
        )

        challenge = {
            "timestamp": datetime.now(),
            "assumption": assumption,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": contradicting_evidence,
            "confidence_in_assumption": confidence_in_assumption,
            "alternative_hypotheses": alternative_hypotheses,
            "recommendation": "INVESTIGATE" if confidence_in_assumption < 0.6 else "HOLDS",
            "approval_required": True,
        }

        logger.info(f"Assumption challenged: {assumption} (confidence: {confidence_in_assumption:.2f})")
        return challenge

    def propose_experiment(
        self,
        hypothesis_id: str,
        experiment_type: str,
        parameters: Dict[str, Any],
        success_criteria: List[str],
        failure_modes: List[str],
    ) -> Dict[str, Any]:
        """
        Propose an experiment to validate hypothesis.

        Experiment types:
        - pit_backtest: In-sample historical validation
        - oos_validation: Out-of-sample test on held-out data
        - walk_forward: Walk-forward simulation
        - monte_carlo: Statistical robustness check
        - sensitivity: Parameter sensitivity analysis

        Args:
            hypothesis_id: Proposal ID to test
            experiment_type: Type of validation experiment
            parameters: Test parameters
            success_criteria: Metrics that must pass
            failure_modes: Known failure conditions

        Returns:
            Experiment proposal (requires approval before execution)
        """
        proposal = self.proposals.get(hypothesis_id)
        if not proposal:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        experiment = {
            "proposal_id": hypothesis_id,
            "experiment_id": f"exp_{hypothesis_id}_{datetime.now().isoformat()}",
            "timestamp": datetime.now(),
            "experiment_type": experiment_type,
            "parameters": parameters,
            "success_criteria": success_criteria,
            "failure_modes": failure_modes,
            "approval_status": ApprovalGate.PENDING,
            "validation_depth": "full",
        }

        logger.info(f"Experiment proposed: {experiment_type} for {hypothesis_id}")
        return experiment

    def format_research_report(
        self,
        proposal_id: str,
        executive_summary: str,
        detailed_findings: str,
        data_quality_notes: str,
    ) -> str:
        """
        Format research proposal into readable report for human review.

        Returns:
            Markdown-formatted report
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        report = f"""
# AI Research Report: {proposal.coin_id}

**Generated:** {proposal.timestamp.isoformat()}
**Approval Status:** {proposal.approval_status.value}
**Data Validation:** {proposal.pit_oos_wfv_status}

## Executive Summary
{executive_summary}

## Hypothesis
{proposal.hypothesis}

**Confidence:** {proposal.confidence:.1%}

## Supporting Evidence
{chr(10).join(f"- {k}: {v}" for k, v in proposal.supporting_metrics.items())}

## Conflicting Evidence
{chr(10).join(f"- {k}: {v}" for k, v in proposal.conflicting_metrics.items())}

## Assumptions
{chr(10).join(f"1. {a}" for a in proposal.assumptions)}

## Risk Factors
{chr(10).join(f"- {r}" for r in proposal.risk_factors)}

## Detailed Findings
{detailed_findings}

## Data Sources
{chr(10).join(f"- {s}" for s in proposal.data_sources_used)}

## Data Quality Notes
{data_quality_notes}

---

**IMPORTANT:** This is research output only. All findings require:
1. ✅ Human review and approval
2. ✅ Independent validation (PIT/OOS/WFV)
3. ✅ Experimental confirmation before any use

**NO automatic execution. NO trade approval. Human decision required.**
"""
        return report

    def get_pending_approvals(self) -> Tuple[List[ResearchProposal], List[AnomalyReport]]:
        """Return all items pending human approval."""
        pending_proposals = [
            p for p in self.proposals.values()
            if p.approval_status == ApprovalGate.PENDING
        ]
        pending_anomalies = [
            a for a in self.anomalies.values()
            if not a.human_verified
        ]
        return pending_proposals, pending_anomalies

    def mark_proposal_approved(
        self,
        proposal_id: str,
        approver_comment: str,
    ) -> ResearchProposal:
        """
        Human approves a hypothesis.
        (This does NOT execute; only marks for experimental validation.)
        """
        proposal = self.proposals[proposal_id]
        proposal.approval_status = ApprovalGate.APPROVED
        proposal.approval_comment = approver_comment
        logger.info(f"Proposal approved by human: {proposal_id}")
        return proposal

    def mark_proposal_rejected(
        self,
        proposal_id: str,
        rejection_reason: str,
    ) -> ResearchProposal:
        """Human rejects a hypothesis."""
        proposal = self.proposals[proposal_id]
        proposal.approval_status = ApprovalGate.REJECTED
        proposal.approval_comment = rejection_reason
        logger.info(f"Proposal rejected: {proposal_id}")
        return proposal

    def mark_anomaly_verified(
        self,
        anomaly_id: str,
        verification_notes: str,
    ) -> AnomalyReport:
        """Human verifies an anomaly is real."""
        anomaly = self.anomalies[anomaly_id]
        anomaly.human_verified = True
        logger.info(f"Anomaly verified: {anomaly_id}")
        return anomaly

    def cannot_modify_parameters(self):
        """
        Stub: Intentionally raises error if anyone tries to modify model parameters.
        This is a read-only copilot.
        """
        raise PermissionError(
            "AIResearchCopilot is read-only. Cannot modify parameters, "
            "execute trades, or approve signals. Human decision required."
        )

    def cannot_execute_trade(self):
        """Intentionally raises error on trade execution attempts."""
        raise PermissionError(
            "AIResearchCopilot cannot execute trades. "
            "All decisions require human approval and manual execution."
        )

    def cannot_approve_signal(self):
        """Intentionally raises error on signal approval attempts."""
        raise PermissionError(
            "AIResearchCopilot cannot approve signals. "
            "Human review required for all signals."
        )
