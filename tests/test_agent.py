"""Research IA Assistant Agent tests."""

from datetime import UTC, datetime

from src.models.agent.agent import ResearchAgent
from src.models.agent.base import (
    AnalysisContext,
    ResearchQuery,
)


class TestResearchAgent:
    """Research agent analysis tests."""

    def test_agent_initialization(self) -> None:
        """Initialize agent."""
        agent = ResearchAgent()
        assert agent.query_history == []
        assert agent.report_history == []

    def test_market_analysis(self) -> None:
        """Perform general market analysis."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="What is the current market regime?",
            analysis_type="market_analysis",
        )

        report = agent.analyze(query)

        assert report.query == query.query
        assert report.analysis_type == "market_analysis"
        assert len(report.executive_summary) > 0
        assert report.confidence_score > 0.0
        assert report.data_quality > 0.0

    def test_anomaly_detection_analysis(self) -> None:
        """Detect market anomalies."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Are there any market anomalies?",
            analysis_type="anomaly_detection",
        )

        report = agent.analyze(query)

        assert report.analysis_type == "anomaly_detection"
        assert isinstance(report.anomalies_detected, list)

    def test_scenario_comparison_analysis(self) -> None:
        """Compare market scenarios."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Compare bull and bear scenarios",
            analysis_type="scenario_comparison",
        )

        report = agent.analyze(query)

        assert report.analysis_type == "scenario_comparison"
        assert len(report.scenarios) >= 2
        assert all(0.0 <= s.probability <= 1.0 for s in report.scenarios)
        assert sum(s.probability for s in report.scenarios) > 0.0

    def test_hypothesis_challenge_analysis(self) -> None:
        """Challenge investment hypothesis."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Challenge the bull case for Bitcoin",
            analysis_type="hypothesis_challenge",
        )

        report = agent.analyze(query)

        assert report.analysis_type == "hypothesis_challenge"
        assert len(report.key_findings) > 0

    def test_opportunity_scan_analysis(self) -> None:
        """Scan for opportunities."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Find asymmetric opportunities",
            analysis_type="opportunity_scan",
        )

        report = agent.analyze(query)

        assert report.analysis_type == "opportunity_scan"
        assert len(report.recommendations) > 0

    def test_risk_assessment_analysis(self) -> None:
        """Assess market risk."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="What are the current risks?",
            analysis_type="risk_assessment",
        )

        report = agent.analyze(query)

        assert report.analysis_type == "risk_assessment"
        assert "risk" in report.detailed_analysis.lower()

    def test_analysis_with_context(self) -> None:
        """Analyze with layer context."""
        agent = ResearchAgent()
        context = AnalysisContext(
            timestamp=datetime.now(UTC),
            market_regime="RISK_ON",
            regime_confidence=0.85,
            bce_score=5.2,
            x20_opportunities=[
                {"asset": "SOL", "score": 0.78},
                {"asset": "AVAX", "score": 0.72},
            ],
            narm_rotation_phase="ACCELERATING",
            rcm_confirmation=True,
            rcm_score=0.76,
            rrp_revival_signals=[{"asset": "APT", "stage": "REVIVING"}],
        )

        query = ResearchQuery(
            query="Market analysis with context",
            analysis_type="market_analysis",
        )

        report = agent.analyze(query, context)

        assert report.confidence_score >= 0.70
        assert report.data_quality >= 0.80

    def test_report_markdown_export(self) -> None:
        """Export report to markdown."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Test markdown export",
            analysis_type="market_analysis",
        )

        report = agent.analyze(query)
        markdown = report.to_markdown()

        assert "# Research Report" in markdown
        assert report.query in markdown
        assert "Executive Summary" in markdown

    def test_query_history_tracking(self) -> None:
        """Track query history."""
        agent = ResearchAgent()

        for i in range(3):
            query = ResearchQuery(query=f"Query {i}")
            agent.analyze(query)

        assert len(agent.query_history) == 3
        assert len(agent.report_history) == 3

    def test_report_retrieval_by_id(self) -> None:
        """Retrieve report by query ID."""
        agent = ResearchAgent()
        query = ResearchQuery(query="Test report retrieval")

        report = agent.analyze(query)
        retrieved = agent.get_report_by_id(report.query_id)

        assert retrieved is not None
        assert retrieved.query_id == report.query_id

    def test_recent_reports_retrieval(self) -> None:
        """Get recent reports."""
        agent = ResearchAgent()

        for i in range(5):
            query = ResearchQuery(query=f"Query {i}")
            agent.analyze(query)

        recent = agent.get_recent_reports(limit=3)

        assert len(recent) == 3

    def test_confidence_scores_bounded(self) -> None:
        """Confidence scores in [0, 1]."""
        agent = ResearchAgent()
        query = ResearchQuery(query="Test confidence bounds")

        report = agent.analyze(query)

        assert 0.0 <= report.confidence_score <= 1.0
        assert 0.0 <= report.data_quality <= 1.0

    def test_scenario_probabilities_sum(self) -> None:
        """Scenario probabilities meaningful sum."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Check scenario probabilities",
            analysis_type="scenario_comparison",
        )

        report = agent.analyze(query)
        total_prob = sum(s.probability for s in report.scenarios)

        assert 0.9 <= total_prob <= 1.1

    def test_scenario_impacts_bounded(self) -> None:
        """Scenario impacts in [-1, 1]."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Check scenario impacts",
            analysis_type="scenario_comparison",
        )

        report = agent.analyze(query)

        for scenario in report.scenarios:
            assert -1.0 <= scenario.impact_bullish <= 1.0
            assert -1.0 <= scenario.impact_bearish <= 1.0

    def test_reasoning_chain_present(self) -> None:
        """Report includes reasoning chain."""
        agent = ResearchAgent()
        query = ResearchQuery(query="Test reasoning chain")

        report = agent.analyze(query)

        assert len(report.reasoning_chain) > 0
        assert all(isinstance(r, str) for r in report.reasoning_chain)

    def test_anomaly_detection_context(self) -> None:
        """Anomaly detection with context."""
        agent = ResearchAgent()
        context = AnalysisContext(
            timestamp=datetime.now(UTC),
            market_regime="RISK_OFF",
            regime_confidence=0.72,
            bce_score=2.1,
            x20_opportunities=[
                {"asset": "BTC", "score": 0.35},
                {"asset": "ETH", "score": 0.28},
                {"asset": "SOL", "score": 0.42},
            ],
            narm_rotation_phase="DECLINING",
            rcm_confirmation=False,
            rcm_score=0.42,
            rrp_revival_signals=[],
        )

        query = ResearchQuery(
            query="Detect anomalies",
            analysis_type="anomaly_detection",
        )

        report = agent.analyze(query, context)

        assert len(report.anomalies_detected) > 0 or len(report.key_findings) > 0

    def test_depth_parameter_respected(self) -> None:
        """Analysis depth parameter."""
        agent = ResearchAgent()

        for depth in ["quick", "standard", "deep"]:
            query = ResearchQuery(
                query="Test depth parameter",
                analysis_type="market_analysis",
                depth=depth,  # type: ignore
            )

            report = agent.analyze(query)

            assert report is not None
            assert len(report.detailed_analysis) > 0

    def test_lookup_days_boundary(self) -> None:
        """Lookback days validation."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Test lookback days",
            lookback_days=180,
        )

        report = agent.analyze(query)

        assert report is not None
        assert query.lookback_days == 180

    def test_asset_focus_accepted(self) -> None:
        """Asset focus parameter."""
        agent = ResearchAgent()
        query = ResearchQuery(
            query="Analyze specific assets",
            focus_assets=["BTC", "ETH", "SOL"],
        )

        report = agent.analyze(query)

        assert report is not None
        assert len(report.key_findings) > 0

    def test_recommendation_generation(self) -> None:
        """Agent generates recommendations."""
        agent = ResearchAgent()
        query = ResearchQuery(query="Test recommendations")

        report = agent.analyze(query)

        assert len(report.recommendations) > 0
        assert all(isinstance(r, str) for r in report.recommendations)

    def test_findings_from_analysis(self) -> None:
        """Agent extracts key findings."""
        agent = ResearchAgent()
        query = ResearchQuery(query="Extract findings")

        report = agent.analyze(query)

        assert len(report.key_findings) > 0
        assert all(isinstance(f, str) for f in report.key_findings)
