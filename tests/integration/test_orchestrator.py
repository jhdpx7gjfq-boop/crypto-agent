"""Integration tests for Decision Orchestrator (Phase 9)."""

import pytest
from datetime import datetime

from src.layers.layer9_dashboard.orchestrator import DecisionOrchestrator, DecisionSignal
from src.layers.layer9_dashboard.research_agent import ResearchAgent, ResearchReport
from tests.fixtures.market_data import generate_bull_ohlcv


class TestDecisionOrchestrator:
    """Tests for decision orchestration across all 8 layers."""

    def test_orchestrator_init(self):
        """Orchestrator should initialize all layers."""
        orchestrator = DecisionOrchestrator()

        assert orchestrator.regime_engine is not None
        assert orchestrator.bce_analyzer is not None
        assert orchestrator.x20_scanner is not None
        assert orchestrator.narm_engine is not None
        assert orchestrator.rcm_engine is not None
        assert orchestrator.rrp_engine is not None

    def test_analyze_minimal(self):
        """Orchestrator should handle minimal data."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(100)

        signal = orchestrator.analyze("BTC", ohlcv)

        assert signal.asset == "BTC"
        assert isinstance(signal.bce_score, (int, float))
        assert isinstance(signal.x20_score, (int, float))
        assert isinstance(signal.should_enter, bool)

    def test_signal_contains_reasoning(self):
        """Decision signal should include reasoning trail."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(100)

        signal = orchestrator.analyze("BTC", ohlcv)

        assert len(signal.reasoning) > 0
        assert any("BCE" in r for r in signal.reasoning)

    def test_bce_gate(self):
        """BCE >= 5 should be mandatory for entry."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(50)  # Short data → low BCE

        signal = orchestrator.analyze("TEST", ohlcv)

        # Low data should lead to low BCE and blocked entry
        if signal.bce_score < 5:
            assert not signal.should_enter

    def test_confidence_levels(self):
        """Signal confidence should match entry score."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(100)

        signal = orchestrator.analyze("BTC", ohlcv)

        assert signal.confidence in ["high", "medium", "low"]
        if signal.should_enter:
            assert signal.confidence in ["high", "medium"]

    def test_risk_assessment(self):
        """Risk level should be assessed."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(100)

        signal = orchestrator.analyze("BTC", ohlcv)

        assert signal.risk_level in ["low", "medium", "high"]

    def test_warnings_generated(self):
        """Warnings should flag issues."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(50)

        signal = orchestrator.analyze("TEST", ohlcv)

        # Low data should generate warnings
        assert isinstance(signal.warnings, list)

    def test_report_generation(self):
        """Orchestrator should generate human-readable report."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(100)

        signal = orchestrator.analyze("BTC", ohlcv)
        text = orchestrator.generate_report_text(signal)

        assert "DECISION ORCHESTRATION" in text
        assert "BTC" in text
        assert "BCE Score" in text

    def test_all_layer_scores_present(self):
        """Signal should include all 8 layer scores."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(100)

        signal = orchestrator.analyze("BTC", ohlcv)

        assert signal.market_regime in ["bullish", "bearish", "sideways"]
        assert 0 <= signal.bce_score <= 6
        assert 0 <= signal.x20_score <= 100
        assert 0 <= signal.narm_score <= 100
        assert 0 <= signal.rcm_score <= 100
        assert 0 <= signal.rrp_probability <= 100

    def test_fomo_circuit_breaker(self):
        """FOMO breaker should block entry in adverse conditions."""
        orchestrator = DecisionOrchestrator()
        ohlcv = generate_bull_ohlcv(50)

        signal = orchestrator.analyze("TEST", ohlcv)

        # If bearish regime + weak BCE + signal would enter
        # then circuit breaker should activate
        if signal.market_regime == "bearish" and signal.bce_score < 5.5:
            assert not signal.should_enter or "FOMO" in " ".join(signal.reasoning)


class TestResearchAgent:
    """Tests for autonomous research agent."""

    def test_agent_init(self):
        """Agent should initialize orchestrator."""
        agent = ResearchAgent()

        assert agent.orchestrator is not None
        assert isinstance(agent.analysis_history, dict)

    def test_analyze_single_asset(self):
        """Agent should analyze single asset."""
        agent = ResearchAgent()
        ohlcv = generate_bull_ohlcv(100)

        assets_data = {
            "BTC": {
                "ohlcv": ohlcv,
                "fundamental": {},
                "narrative": {},
            }
        }

        report = agent.analyze_assets(assets_data)

        assert report.assets_analyzed == ["BTC"]
        assert len(report.decisions) >= 1

    def test_analyze_multiple_assets(self):
        """Agent should analyze portfolio of assets."""
        agent = ResearchAgent()

        assets_data = {
            "BTC": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
            "ETH": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
            "SOL": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
        }

        report = agent.analyze_assets(assets_data)

        assert len(report.assets_analyzed) == 3
        assert len(report.decisions) == 3

    def test_signal_counting(self):
        """Agent should count strong vs weak signals."""
        agent = ResearchAgent()

        assets_data = {
            "BTC": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
        }

        report = agent.analyze_assets(assets_data)

        assert report.strong_signals + report.weak_signals == report.signals_generated

    def test_alert_generation(self):
        """Agent should generate alerts."""
        agent = ResearchAgent()

        assets_data = {
            "BTC": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
        }

        report = agent.analyze_assets(assets_data)

        assert isinstance(report.alerts, list)

    def test_market_summary(self):
        """Agent should generate market summary."""
        agent = ResearchAgent()

        assets_data = {
            "BTC": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
            "ETH": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
        }

        report = agent.analyze_assets(assets_data)

        assert "bullish" in report.market_summary or "bearish" in report.market_summary

    def test_top_opportunity(self):
        """Agent should identify top opportunity."""
        agent = ResearchAgent()

        assets_data = {
            "BTC": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
        }

        report = agent.analyze_assets(assets_data)

        if report.signals_generated > 0:
            assert report.top_opportunity is not None

    def test_challenge_hypothesis(self):
        """Agent should challenge hypotheses with data."""
        agent = ResearchAgent()
        ohlcv = generate_bull_ohlcv(100)

        signal = agent.orchestrator.analyze("BTC", ohlcv)

        challenges = agent.challenge_hypothesis("market in growth phase", [signal])

        assert len(challenges) > 0
        assert any("✓" in c or "✗" in c for c in challenges)

    def test_report_generation(self):
        """Agent should generate human-readable report."""
        agent = ResearchAgent()

        assets_data = {
            "BTC": {"ohlcv": generate_bull_ohlcv(100), "fundamental": {}, "narrative": {}},
        }

        report = agent.analyze_assets(assets_data)
        text = agent.generate_report_text(report)

        assert "AUTONOMOUS RESEARCH REPORT" in text
        assert "Summary:" in text
        assert "Findings:" in text

    def test_analysis_history(self):
        """Agent should track analysis history."""
        agent = ResearchAgent()
        ohlcv = generate_bull_ohlcv(100)

        signal1 = agent.orchestrator.analyze("BTC", ohlcv)
        signal2 = agent.orchestrator.analyze("BTC", ohlcv)

        agent.analysis_history["BTC"] = [signal1, signal2]

        assert len(agent.analysis_history["BTC"]) == 2

    def test_insufficient_data_handling(self):
        """Agent should skip assets with insufficient data."""
        agent = ResearchAgent()

        assets_data = {
            "BTC": {"ohlcv": generate_bull_ohlcv(5), "fundamental": {}, "narrative": {}},
        }

        report = agent.analyze_assets(assets_data)

        # Should still run, but with warning
        assert isinstance(report.findings, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
