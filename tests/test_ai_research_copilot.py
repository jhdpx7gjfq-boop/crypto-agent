"""Tests for IGWT-PF26 Phase 9: AI Research Copilot."""

import pytest
from datetime import datetime
from src.agent.ai_research_copilot import (
    AIResearchCopilot,
    ApprovalGate,
    AnalysisScope,
    ResearchProposal,
    AnomalyReport,
    ComparisonScenario,
)


@pytest.fixture
def copilot():
    """Initialize AI Research Copilot in read-only mode."""
    return AIResearchCopilot(read_only=True)


def test_copilot_initialization():
    """Verify copilot initializes in read-only mode only."""
    copilot = AIResearchCopilot(read_only=True)
    assert copilot.read_only is True
    assert len(copilot.proposals) == 0
    assert len(copilot.anomalies) == 0
    assert len(copilot.scenarios) == 0


def test_copilot_cannot_initialize_writable():
    """Ensure write mode is blocked."""
    with pytest.raises(ValueError, match="read-only"):
        AIResearchCopilot(read_only=False)


def test_propose_hypothesis_valid(copilot):
    """Verify hypothesis proposal with valid confidence."""
    proposal = copilot.propose_hypothesis(
        coin_id="bitcoin",
        hypothesis="Bitcoin approaching accumulation zone based on Wyckoff structure",
        confidence=0.72,
        supporting_metrics={"wyckoff_score": 5.2, "rsi": 42, "volume_trend": "increasing"},
        conflicting_metrics={"momentum": 0.3, "sentiment": "neutral"},
        data_sources=["coingecko", "technical_indicators"],
        assumptions=["CEX data reliable", "Historical patterns repeat"],
        risk_factors=["Macro shock", "Regulatory change"],
    )

    assert proposal.coin_id == "bitcoin"
    assert proposal.confidence == 0.72
    assert proposal.approval_status == ApprovalGate.PENDING
    assert proposal.pit_oos_wfv_status == "research_phase"
    assert len(proposal.supporting_metrics) == 3
    assert len(proposal.risk_factors) == 2


def test_propose_hypothesis_invalid_confidence(copilot):
    """Reject confidence outside 0-1 range."""
    with pytest.raises(ValueError, match="Confidence must be 0-1"):
        copilot.propose_hypothesis(
            coin_id="ethereum",
            hypothesis="Test",
            confidence=1.5,  # Invalid
            supporting_metrics={},
            conflicting_metrics={},
            data_sources=[],
            assumptions=[],
            risk_factors=[],
        )


def test_detect_anomaly(copilot):
    """Verify anomaly detection with statistical confidence."""
    anomaly = copilot.detect_anomaly(
        coin_id="ethereum",
        anomaly_type="volume_surge",
        baseline=1e9,
        current=3.5e9,
        sigma=3.2,
        affected_layers=["feature_store", "wyckoff_bce"],
        likely_causes=["Institutional accumulation", "Exchange listing"],
        severity="high",
    )

    assert anomaly.coin_id == "ethereum"
    assert anomaly.anomaly_type == "volume_surge"
    assert anomaly.current_value == 3.5e9
    assert anomaly.deviation_sigma == 3.2
    assert anomaly.severity == "high"
    assert anomaly.human_verified is False
    assert anomaly.approval_gate == ApprovalGate.PENDING


def test_detect_anomaly_low_sigma_warning(copilot, caplog):
    """Warn when anomaly sigma < 2."""
    copilot.detect_anomaly(
        coin_id="token",
        anomaly_type="price_change",
        baseline=100,
        current=110,
        sigma=1.5,  # Low sigma
        affected_layers=["price_data"],
        likely_causes=["Normal volatility"],
        severity="low",
    )
    assert "Anomaly severity low" in caplog.text


def test_compare_scenarios(copilot):
    """Verify side-by-side coin comparison analysis."""
    scenario = copilot.compare_scenarios(
        coins=["bitcoin", "ethereum", "solana"],
        metrics={
            "price_momentum": {"bitcoin": 0.45, "ethereum": 0.38, "solana": 0.52},
            "tight_convergence": {"bitcoin": 100, "ethereum": 101, "solana": 102},
            "volume_trend": {"bitcoin": 0.2, "ethereum": 0.8, "solana": 0.75},
        },
    )

    assert len(scenario.coins_analyzed) == 3
    assert len(scenario.dimensions) == 3
    assert "volume_trend" in scenario.divergences  # >30% spread
    assert "tight_convergence" in scenario.convergence_signals  # <10% spread
    assert scenario.approval_required is True


def test_challenge_assumption(copilot):
    """Verify assumption challenge with evidence."""
    challenge = copilot.challenge_assumption(
        assumption="Bitcoin accumulation is institutional-driven",
        supporting_evidence=
            ["Large buy orders", "Decreased exchange outflows", "Whale wallet accumulation"],
        contradicting_evidence=["Funding rates neutral", "Open interest declining"],
        alternative_hypotheses=
            ["Retail FOMO", "Algorithm-driven accumulation", "Market maker positioning"],
    )

    assert "assumption" in challenge
    assert "timestamp" in challenge
    assert len(challenge["supporting_evidence"]) == 3
    assert len(challenge["contradicting_evidence"]) == 2
    assert "confidence_in_assumption" in challenge
    assert challenge["confidence_in_assumption"] > 0.5  # More support than contradiction


def test_propose_experiment(copilot):
    """Verify experiment proposal for hypothesis validation."""
    proposal = copilot.propose_hypothesis(
        coin_id="bitcoin",
        hypothesis="Test hypothesis",
        confidence=0.65,
        supporting_metrics={"score": 75},
        conflicting_metrics={},
        data_sources=["coingecko"],
        assumptions=["Assumption 1"],
        risk_factors=["Risk 1"],
    )

    experiment = copilot.propose_experiment(
        hypothesis_id=proposal.proposal_id,
        experiment_type="walk_forward",
        parameters={"train_days": 30, "test_days": 7, "retest_period": 5},
        success_criteria=[
            "Profit factor > 1.3",
            "Max drawdown < 25%",
            "Win rate > 45%",
        ],
        failure_modes=["Market regime change", "Overfitting on training data"],
    )

    assert experiment["experiment_type"] == "walk_forward"
    assert experiment["approval_status"] == ApprovalGate.PENDING
    assert len(experiment["success_criteria"]) == 3
    assert experiment["validation_depth"] == "full"


def test_format_research_report(copilot):
    """Verify formatted research report generation."""
    proposal = copilot.propose_hypothesis(
        coin_id="ethereum",
        hypothesis="Ethereum entering rotation cycle",
        confidence=0.68,
        supporting_metrics={"narrative_growth": 85, "capital_inflow": 1.2},
        conflicting_metrics={"funding_rates": 0.02},
        data_sources=["coingecko", "glassnode"],
        assumptions=["Data quality high"],
        risk_factors=["Macro reversal"],
    )

    report = copilot.format_research_report(
        proposal_id=proposal.proposal_id,
        executive_summary="Strong narrative tailwinds with measured inflows.",
        detailed_findings="Analysis shows 3-month adoption acceleration.",
        data_quality_notes="All sources verified. No lookahead bias detected.",
    )

    assert "Research Report" in report
    assert "ethereum" in report.lower()
    assert "pending" in report.lower()
    assert "research output only" in report.lower()
    assert "NO automatic execution" in report
    assert "NO trade approval" in report


def test_approval_workflow(copilot):
    """Verify human approval marking workflow."""
    proposal = copilot.propose_hypothesis(
        coin_id="solana",
        hypothesis="Test",
        confidence=0.70,
        supporting_metrics={},
        conflicting_metrics={},
        data_sources=[],
        assumptions=[],
        risk_factors=[],
    )

    # Initially pending
    assert proposal.approval_status == ApprovalGate.PENDING

    # Mark approved
    approved = copilot.mark_proposal_approved(
        proposal.proposal_id,
        "Hypothesis well-supported. Recommend walk-forward validation.",
    )
    assert approved.approval_status == ApprovalGate.APPROVED
    assert "walk-forward" in approved.approval_comment


def test_rejection_workflow(copilot):
    """Verify hypothesis rejection workflow."""
    proposal = copilot.propose_hypothesis(
        coin_id="doge",
        hypothesis="Test",
        confidence=0.40,
        supporting_metrics={},
        conflicting_metrics={},
        data_sources=[],
        assumptions=[],
        risk_factors=[],
    )

    rejected = copilot.mark_proposal_rejected(
        proposal.proposal_id,
        "Confidence too low (<50%). Insufficient supporting evidence.",
    )
    assert rejected.approval_status == ApprovalGate.REJECTED
    assert "Confidence too low" in rejected.approval_comment


def test_anomaly_verification(copilot):
    """Verify anomaly human verification workflow."""
    anomaly = copilot.detect_anomaly(
        coin_id="bitcoin",
        anomaly_type="volume_surge",
        baseline=1e9,
        current=2.5e9,
        sigma=2.8,
        affected_layers=["feature_store"],
        likely_causes=["Institutional buying"],
    )

    assert anomaly.human_verified is False

    verified = copilot.mark_anomaly_verified(
        anomaly.report_id,
        "Verified: Confirmed institutional accumulation pattern.",
    )
    assert verified.human_verified is True


def test_get_pending_approvals(copilot):
    """Retrieve all items awaiting human approval."""
    # Add some proposals
    p1 = copilot.propose_hypothesis(
        coin_id="bitcoin",
        hypothesis="Test 1",
        confidence=0.75,
        supporting_metrics={},
        conflicting_metrics={},
        data_sources=[],
        assumptions=[],
        risk_factors=[],
    )

    p2 = copilot.propose_hypothesis(
        coin_id="ethereum",
        hypothesis="Test 2",
        confidence=0.65,
        supporting_metrics={},
        conflicting_metrics={},
        data_sources=[],
        assumptions=[],
        risk_factors=[],
    )

    # Add anomalies
    a1 = copilot.detect_anomaly(
        coin_id="bitcoin",
        anomaly_type="price_spike",
        baseline=100,
        current=150,
        sigma=2.5,
        affected_layers=["price"],
        likely_causes=["News"],
    )

    # Approve one proposal
    copilot.mark_proposal_approved(p1.proposal_id, "OK")

    # Get pending
    pending_props, pending_anoms = copilot.get_pending_approvals()

    # Should have 1 pending proposal (p2) and 1 pending anomaly (a1)
    assert len(pending_props) == 1
    assert len(pending_anoms) == 1
    assert pending_props[0].proposal_id == p2.proposal_id


def test_read_only_constraints(copilot):
    """Verify all write operations are blocked."""
    with pytest.raises(PermissionError, match="read-only"):
        copilot.cannot_modify_parameters()

    with pytest.raises(PermissionError, match="execute trades"):
        copilot.cannot_execute_trade()

    with pytest.raises(PermissionError, match="approve signals"):
        copilot.cannot_approve_signal()


def test_hypothesis_data_sources_tracked(copilot):
    """Verify all data sources are tracked for reproducibility."""
    sources = [
        "coingecko_market_data",
        "glassnode_on_chain",
        "derived_technical_indicators",
        "sentiment_analysis",
    ]

    proposal = copilot.propose_hypothesis(
        coin_id="bitcoin",
        hypothesis="Test",
        confidence=0.70,
        supporting_metrics={"metric1": 1.0},
        conflicting_metrics={},
        data_sources=sources,
        assumptions=[],
        risk_factors=[],
    )

    assert proposal.data_sources_used == sources
    # Enables full reproducibility audit


def test_assumption_tracking(copilot):
    """Verify all assumptions are tracked."""
    assumptions = [
        "CoinGecko API returns accurate data",
        "Historical patterns repeat in similar market conditions",
        "No major regulatory changes in next 30 days",
    ]

    proposal = copilot.propose_hypothesis(
        coin_id="ethereum",
        hypothesis="Test",
        confidence=0.65,
        supporting_metrics={},
        conflicting_metrics={},
        data_sources=[],
        assumptions=assumptions,
        risk_factors=[],
    )

    assert proposal.assumptions == assumptions
    # Enables assumption validation and challenge


def test_risk_factor_documentation(copilot):
    """Verify risk factors are documented."""
    risks = [
        "Black swan macro event",
        "Regulatory crackdown",
        "Model overfitting on historical data",
        "Data source reliability",
    ]

    proposal = copilot.propose_hypothesis(
        coin_id="solana",
        hypothesis="Test",
        confidence=0.60,
        supporting_metrics={},
        conflicting_metrics={},
        data_sources=[],
        assumptions=[],
        risk_factors=risks,
    )

    assert len(proposal.risk_factors) == 4
    # Enables risk-adjusted decision making


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
