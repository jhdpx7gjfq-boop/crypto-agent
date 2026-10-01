"""Integration tests for Phase 9: Dashboard & Agent IA.

Tests dashboard API models, data formatting, agent orchestration.
"""

import pytest
from datetime import datetime
from src.layers.layer9_dashboard import (
    DashboardService,
    SignalAlert,
    SignalType as DashboardSignalType,
    ActionType,
    Severity,
    RegimeType,
)
from src.core.agent_ia import (
    AgentOrchestrator,
    Signal,
    SignalType,
    AgentDecision,
    ReportGenerator,
)


class TestDashboardService:
    """Test dashboard service."""

    @pytest.fixture
    def service(self):
        return DashboardService()

    @pytest.fixture
    def mock_data(self):
        return {
            "regime": {
                "regime_type": "bullish",
                "confidence": 0.75,
                "expected_duration_days": 21,
                "days_in_regime": 7,
            },
            "bce_signals": {
                "BTC": {"score": 5.2, "confidence": 0.87, "entry_ready": True, "stage": "accumulation"},
                "ETH": {"score": 4.1, "confidence": 0.65, "entry_ready": False, "stage": "mixed"},
            },
            "x20_scores": {
                "SOL": {"score": 82, "asymmetric_potential": 5.5},
                "ARB": {"score": 65, "asymmetric_potential": 2.1},
            },
            "rrp_candidates": {
                "DOGE": {"score": 65, "stage": "emerging", "acceleration_rate": 125.0, "confidence": 0.68},
                "SHIB": {"score": 35, "stage": "dormant", "acceleration_rate": 5.0, "confidence": 0.42},
            },
            "rcm_rotations": {
                "ADA": {
                    "rotation_type": "accumulation",
                    "confidence": 0.72,
                    "capital_flow_strength": 0.65,
                },
                "XRP": {"rotation_type": "distribution", "confidence": 0.58, "capital_flow_strength": -0.42},
            },
        }

    @pytest.mark.asyncio
    async def test_generate_summary(self, service, mock_data):
        """Generate dashboard summary."""
        summary = await service.generate_summary(
            mock_data["regime"],
            mock_data["bce_signals"],
            mock_data["x20_scores"],
            mock_data["rrp_candidates"],
            mock_data["rcm_rotations"],
        )

        assert summary.market_regime.regime_type == RegimeType.BULLISH
        assert summary.critical_alerts >= 0
        assert len(summary.top_signals) > 0
        assert summary.assets_under_watch > 0

    @pytest.mark.asyncio
    async def test_bce_analysis_conversion(self, service, mock_data):
        """Convert BCE data to dashboard format."""
        bce_analysis = await service.get_bce_analysis("BTC", mock_data["bce_signals"]["BTC"])

        assert bce_analysis.asset == "BTC"
        assert bce_analysis.overall_score == 5.2
        assert bce_analysis.validity is True
        assert bce_analysis.entry_ready is True

    @pytest.mark.asyncio
    async def test_x20_report_generation(self, service, mock_data):
        """Generate X20 opportunity report."""
        report = await service.get_x20_report(mock_data["x20_scores"])

        assert len(report.opportunities) > 0
        assert report.opportunities[0].rank == 1
        assert report.opportunities[0].score >= report.opportunities[-1].score
        assert report.total_tracked == 2

    @pytest.mark.asyncio
    async def test_rrp_report_generation(self, service, mock_data):
        """Generate RRP revival radar report."""
        report = await service.get_rrp_report(mock_data["rrp_candidates"])

        assert "emerging" in report.by_stage
        assert "dormant" in report.by_stage
        assert len(report.by_stage["emerging"]) >= 1
        assert len(report.by_stage["dormant"]) >= 1

    @pytest.mark.asyncio
    async def test_rcm_report_generation(self, service, mock_data):
        """Generate RCM rotation report."""
        report = await service.get_rcm_report(mock_data["rcm_rotations"])

        assert len(report.active_rotations) >= 1
        assert any(r.capital_flow_strength > 0.5 for r in report.active_rotations)

    @pytest.mark.asyncio
    async def test_watchlist_management(self, service):
        """Test watchlist add and retrieval."""
        service.add_watchlist_item("BTC", "ready", "Accumulation pattern confirmed")

        watchlist = await service.get_watchlist()

        assert len(watchlist.watchlist) == 1
        assert watchlist.watchlist[0].asset == "BTC"
        assert watchlist.watchlist[0].watch_status == "ready"

    def test_alert_severity_scoring(self, service):
        """Test alert severity classification."""
        assert service._score_to_severity(95) == Severity.CRITICAL
        assert service._score_to_severity(75) == Severity.HIGH
        assert service._score_to_severity(60) == Severity.MEDIUM
        assert service._score_to_severity(30) == Severity.LOW


class TestAgentOrchestrator:
    """Test agent orchestration."""

    @pytest.fixture
    def orchestrator(self):
        return AgentOrchestrator()

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Initialize orchestrator."""
        assert orchestrator.running is False
        assert orchestrator.context.regime == "ranging"
        assert len(orchestrator.decision_history) == 0

    @pytest.mark.asyncio
    async def test_on_signal_high_confidence(self, orchestrator):
        """Trigger on high-confidence signal."""
        signal = Signal(
            signal_type=SignalType.ENTRY,
            asset="BTC",
            score=85,
            confidence=0.82,
            reasoning="Strong BCE accumulation pattern",
            timestamp=datetime.utcnow(),
        )

        decision = await orchestrator.on_signal(signal)

        assert decision.priority >= 3
        assert "BTC" in decision.assets

    @pytest.mark.asyncio
    async def test_on_signal_low_confidence(self, orchestrator):
        """Trigger on low-confidence signal."""
        signal = Signal(
            signal_type=SignalType.ANOMALY,
            asset="ETH",
            score=45,
            confidence=0.42,
            reasoning="Moderate volume spike",
            timestamp=datetime.utcnow(),
        )

        decision = await orchestrator.on_signal(signal)

        assert decision.priority <= 3

    @pytest.mark.asyncio
    async def test_challenge_hypothesis_accumulation(self, orchestrator):
        """Devil's advocate on accumulation thesis."""
        rebuttal = await orchestrator.challenge_hypothesis("accumulation", "BTC")

        assert rebuttal["thesis"] == "accumulation"
        assert len(rebuttal["counter_arguments"]) > 0
        assert rebuttal["verdict"] in ["risky", "viable"]

    @pytest.mark.asyncio
    async def test_challenge_hypothesis_breakout(self, orchestrator):
        """Devil's advocate on breakout thesis."""
        rebuttal = await orchestrator.challenge_hypothesis("breakout", "ETH")

        assert rebuttal["thesis"] == "breakout"
        assert len(rebuttal["counter_arguments"]) > 0

    def test_agent_status(self, orchestrator):
        """Get agent status."""
        status = orchestrator.get_status()

        assert "running" in status
        assert "current_regime" in status
        assert "decisions_made" in status
        assert status["running"] is False


class TestReportGenerator:
    """Test report generation."""

    @pytest.fixture
    def generator(self):
        return ReportGenerator()

    @pytest.fixture
    def market_data(self):
        return {
            "regime": {
                "regime_type": "bullish",
                "confidence": 0.72,
                "expected_duration_days": 21,
            },
            "bce_signals": {
                "BTC": {"score": 5.2, "confidence": 0.87, "stage": "accumulation"},
                "ETH": {"score": 4.8, "confidence": 0.75, "stage": "accumulation"},
            },
            "x20_scores": {
                "SOL": {"score": 82, "asymmetric_potential": 5.5},
                "ARB": {"score": 76, "asymmetric_potential": 3.2},
                "OP": {"score": 68, "asymmetric_potential": 2.1},
            },
            "rrp_candidates": {
                "DOGE": {"score": 65, "stage": "emerging"},
                "SHIB": {"score": 72, "stage": "confirmed"},
            },
            "rcm_rotations": {
                "ADA": {"rotation_type": "accumulation", "capital_flow_strength": 0.65},
            },
        }

    @pytest.mark.asyncio
    async def test_daily_summary(self, generator, market_data):
        """Generate daily summary."""
        report = await generator.daily_summary(
            market_data["regime"],
            market_data["bce_signals"],
            market_data["x20_scores"],
            market_data["rrp_candidates"],
            market_data["rcm_rotations"],
        )

        assert report.regime["type"] == "bullish"
        assert len(report.top_bce_signals) >= 0
        assert len(report.top_x20_opportunities) >= 3
        assert len(report.key_insights) > 0
        assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_asset_deep_dive(self, generator):
        """Generate asset deep dive."""
        report = await generator.asset_deep_dive(
            "BTC",
            {"score": 5.2, "stage": "accumulation"},
            {"score": 78, "asymmetric_potential": 4.5},
            {"current_price": 50000, "support": 48000, "resistance": 52000},
        )

        assert report.asset == "BTC"
        assert report.recommendation in ["entry", "research", "hold"]
        assert len(report.reasoning) > 0
        assert report.risk_reward["risk_reward_ratio"] > 0

    @pytest.mark.asyncio
    async def test_scenario_analysis(self, generator):
        """Compare market scenarios."""
        scenarios = {
            "bullish": {"probability": 0.35, "target": 75000, "reasoning": "Breakout confirmed"},
            "base": {"probability": 0.50, "target": 55000, "reasoning": "Gradual accumulation"},
            "bearish": {"probability": 0.15, "target": 40000, "reasoning": "Failed breakout"},
        }

        report = await generator.scenario_analysis("BTC", 50000, scenarios)

        assert report.most_likely == "base"
        assert 0 <= report.confidence <= 1
        assert len(report.key_assumptions) > 0
        assert len(report.trigger_events) > 0

    @pytest.mark.asyncio
    async def test_report_history_tracking(self, generator, market_data):
        """Track report history."""
        await generator.daily_summary(
            market_data["regime"],
            market_data["bce_signals"],
            market_data["x20_scores"],
            market_data["rrp_candidates"],
            market_data["rcm_rotations"],
        )

        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert today in generator.report_history
        assert len(generator.report_history[today]) == 1


class TestPhase9Integration:
    """End-to-end Phase 9 workflow."""

    @pytest.mark.asyncio
    async def test_dashboard_agent_integration(self):
        """Test dashboard and agent working together."""
        service = DashboardService()
        orchestrator = AgentOrchestrator()
        generator = ReportGenerator()

        # Mock data
        market_data = {
            "regime": {
                "regime_type": "bullish",
                "confidence": 0.75,
                "expected_duration_days": 21,
                "days_in_regime": 5,
            },
            "bce_signals": {
                "BTC": {"score": 5.3, "confidence": 0.88, "entry_ready": True, "stage": "accumulation"}
            },
            "x20_scores": {"SOL": {"score": 80, "asymmetric_potential": 5.0}},
            "rrp_candidates": {"DOGE": {"score": 68, "stage": "emerging", "acceleration_rate": 120}},
            "rcm_rotations": {"ADA": {"capital_flow_strength": 0.7, "confidence": 0.75}},
        }

        # Generate dashboard summary
        dashboard = await service.generate_summary(
            market_data["regime"],
            market_data["bce_signals"],
            market_data["x20_scores"],
            market_data["rrp_candidates"],
            market_data["rcm_rotations"],
        )

        # Generate daily report
        report = await generator.daily_summary(
            market_data["regime"],
            market_data["bce_signals"],
            market_data["x20_scores"],
            market_data["rrp_candidates"],
            market_data["rcm_rotations"],
        )

        # Simulate agent signal
        signal = Signal(
            signal_type=SignalType.ENTRY,
            asset="BTC",
            score=88,
            confidence=0.88,
            reasoning="BCE >= 5.3, bullish regime, capital inflow confirmed",
            timestamp=datetime.utcnow(),
        )

        decision = await orchestrator.on_signal(signal)

        # Validate integration
        assert dashboard.market_regime.regime_type == RegimeType.BULLISH
        assert len(dashboard.top_signals) > 0
        assert report.regime["type"] == "bullish"
        assert len(report.top_bce_signals) > 0
        assert decision.priority >= 4
        assert decision.decision_type == "research"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
