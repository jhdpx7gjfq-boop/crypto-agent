"""RCM/RPM Engine tests: rotation confirmation model."""

from datetime import UTC, datetime

from src.models.rcm_rpm.base import RCMSignal
from src.models.rcm_rpm.detector import RCMEngine


class TestRCMEngine:
    """RCM rotation confirmation tests."""

    def test_engine_initialization(self) -> None:
        """Initialize RCM engine."""
        engine = RCMEngine()
        assert engine.history == []
        assert engine.CONFIRMATION_THRESHOLD == 0.65

    def test_strong_confirmation_signal(self) -> None:
        """Detect strong rotation confirmation."""
        engine = RCMEngine()
        signal = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CONFIRM-STRONG",
            capital_flow_score=0.8,
            relative_strength=0.8,
            narrative_acceleration=0.75,
            fundamental_confirmation=0.7,
            derivative_funding=0.05,
            open_interest_change=40.0,
            lookback_days=60,
        )

        verdict = engine.evaluate(signal)

        assert verdict.rotation_confirmed is True
        assert verdict.confirmation_strength in ["STRONG", "VERY_STRONG"]
        assert verdict.rcm_score >= 0.65

    def test_weak_confirmation_signal(self) -> None:
        """Detect weak rotation signal."""
        engine = RCMEngine()
        signal = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CONFIRM-WEAK",
            capital_flow_score=-0.6,
            relative_strength=0.3,
            narrative_acceleration=-0.5,
            fundamental_confirmation=0.2,
            derivative_funding=-0.03,
            open_interest_change=-30.0,
            lookback_days=60,
        )

        verdict = engine.evaluate(signal)

        assert verdict.rotation_confirmed is False
        assert verdict.rcm_score < 0.65

    def test_score_within_bounds(self) -> None:
        """RCM score should be [0, 1]."""
        engine = RCMEngine()
        signal = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-BOUNDS",
            capital_flow_score=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivative_funding=0.01,
            open_interest_change=10.0,
        )

        verdict = engine.evaluate(signal)

        assert 0.0 <= verdict.rcm_score <= 1.0

    def test_capital_flow_component(self) -> None:
        """Capital flow should scale with inflow."""
        engine = RCMEngine()

        signal_outflow = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CF-OUT",
            capital_flow_score=-0.8,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivative_funding=0.0,
            open_interest_change=0.0,
        )

        signal_inflow = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CF-IN",
            capital_flow_score=0.8,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivative_funding=0.0,
            open_interest_change=0.0,
        )

        verdict_out = engine.evaluate(signal_outflow)
        verdict_in = engine.evaluate(signal_inflow)

        assert verdict_in.components.capital_flow > verdict_out.components.capital_flow

    def test_relative_strength_component(self) -> None:
        """Relative strength should reflect outperformance."""
        engine = RCMEngine()

        signal_weak = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-RS-WEAK",
            capital_flow_score=0.5,
            relative_strength=0.2,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivative_funding=0.0,
            open_interest_change=0.0,
        )

        signal_strong = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-RS-STRONG",
            capital_flow_score=0.5,
            relative_strength=0.9,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivative_funding=0.0,
            open_interest_change=0.0,
        )

        verdict_weak = engine.evaluate(signal_weak)
        verdict_strong = engine.evaluate(signal_strong)

        assert verdict_strong.components.relative_strength > verdict_weak.components.relative_strength

    def test_narrative_acceleration_component(self) -> None:
        """Narrative should impact confirmation."""
        engine = RCMEngine()

        signal_negative = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-NA-NEG",
            capital_flow_score=0.5,
            relative_strength=0.5,
            narrative_acceleration=-0.8,
            fundamental_confirmation=0.5,
            derivative_funding=0.0,
            open_interest_change=0.0,
        )

        signal_positive = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-NA-POS",
            capital_flow_score=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.8,
            fundamental_confirmation=0.5,
            derivative_funding=0.0,
            open_interest_change=0.0,
        )

        verdict_neg = engine.evaluate(signal_negative)
        verdict_pos = engine.evaluate(signal_positive)

        assert verdict_pos.components.narrative_acceleration > verdict_neg.components.narrative_acceleration

    def test_derivative_funding_component(self) -> None:
        """High funding should indicate strong derivatives positioning."""
        engine = RCMEngine()

        signal_low_funding = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-DF-LOW",
            capital_flow_score=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivative_funding=-0.04,
            open_interest_change=0.0,
        )

        signal_high_funding = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-DF-HIGH",
            capital_flow_score=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivative_funding=0.08,
            open_interest_change=50.0,
        )

        verdict_low = engine.evaluate(signal_low_funding)
        verdict_high = engine.evaluate(signal_high_funding)

        assert verdict_high.components.derivatives_structure > verdict_low.components.derivatives_structure

    def test_confirmation_threshold(self) -> None:
        """Test confirmation at exact threshold."""
        engine = RCMEngine()

        signal_below = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-THRESH-BELOW",
            capital_flow_score=0.40,
            relative_strength=0.40,
            narrative_acceleration=0.40,
            fundamental_confirmation=0.40,
            derivative_funding=-0.02,
            open_interest_change=-20.0,
        )

        signal_above = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-THRESH-ABOVE",
            capital_flow_score=0.85,
            relative_strength=0.85,
            narrative_acceleration=0.80,
            fundamental_confirmation=0.80,
            derivative_funding=0.06,
            open_interest_change=50.0,
        )

        verdict_below = engine.evaluate(signal_below)
        verdict_above = engine.evaluate(signal_above)

        assert verdict_below.rotation_confirmed is False
        assert verdict_above.rotation_confirmed is True

    def test_confirmation_strength_classification(self) -> None:
        """Test strength classification at different score levels."""
        engine = RCMEngine()

        signals = [
            (0.20, "WEAK"),
            (0.58, "MODERATE"),
            (0.75, "STRONG"),
            (0.90, "VERY_STRONG"),
        ]

        for score_target, expected_strength in signals:
            signal = RCMSignal(
                timestamp=datetime.now(UTC),
                asset_id=f"TEST-STRENGTH-{score_target:.2f}",
                capital_flow_score=score_target,
                relative_strength=score_target,
                narrative_acceleration=score_target,
                fundamental_confirmation=score_target,
                derivative_funding=score_target * 0.1 - 0.02,
                open_interest_change=(score_target - 0.5) * 100,
            )

            verdict = engine.evaluate(signal)
            assert verdict.confirmation_strength == expected_strength

    def test_confidence_calculation(self) -> None:
        """Confidence should reflect consistency."""
        engine = RCMEngine()
        signal = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CONF",
            capital_flow_score=0.7,
            relative_strength=0.7,
            narrative_acceleration=0.7,
            fundamental_confirmation=0.7,
            derivative_funding=0.03,
            open_interest_change=30.0,
        )

        verdict = engine.evaluate(signal)

        assert 0.0 <= verdict.confidence <= 1.0

    def test_reasoning_generation(self) -> None:
        """Verdict should include reasoning."""
        engine = RCMEngine()
        signal = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-REASON",
            capital_flow_score=0.8,
            relative_strength=0.75,
            narrative_acceleration=0.70,
            fundamental_confirmation=0.65,
            derivative_funding=0.06,
            open_interest_change=45.0,
        )

        verdict = engine.evaluate(signal)

        assert isinstance(verdict.reasoning, list)
        assert len(verdict.reasoning) > 0
        assert any("CONFIRM" in r for r in verdict.reasoning)

    def test_metadata_present(self) -> None:
        """Verdict should include metadata."""
        engine = RCMEngine()
        signal = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-META",
            capital_flow_score=0.6,
            relative_strength=0.6,
            narrative_acceleration=0.6,
            fundamental_confirmation=0.6,
            derivative_funding=0.02,
            open_interest_change=20.0,
        )

        verdict = engine.evaluate(signal)

        assert "threshold" in verdict.metadata
        assert verdict.metadata["threshold"] == 0.65
        assert "component_weights" in verdict.metadata

    def test_history_accumulation(self) -> None:
        """Engine should accumulate history."""
        engine = RCMEngine()

        for i in range(3):
            signal = RCMSignal(
                timestamp=datetime.now(UTC),
                asset_id=f"TEST-HIST-{i}",
                capital_flow_score=0.4 + i * 0.2,
                relative_strength=0.4 + i * 0.2,
                narrative_acceleration=0.4 + i * 0.2,
                fundamental_confirmation=0.4 + i * 0.15,
                derivative_funding=0.01 + i * 0.02,
                open_interest_change=10.0 + i * 15.0,
            )
            engine.evaluate(signal)

        assert len(engine.history) == 3

    def test_composite_score_calculation(self) -> None:
        """Composite score should reflect weighted components."""
        engine = RCMEngine()
        signal = RCMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-COMP",
            capital_flow_score=0.8,
            relative_strength=0.7,
            narrative_acceleration=0.6,
            fundamental_confirmation=0.5,
            derivative_funding=0.04,
            open_interest_change=30.0,
        )

        verdict = engine.evaluate(signal)

        components = verdict.components
        expected_composite = (
            components.capital_flow * 0.25
            + components.relative_strength * 0.25
            + components.narrative_acceleration * 0.20
            + components.fundamental_confirmation * 0.20
            + components.derivatives_structure * 0.10
        )

        assert abs(verdict.rcm_score - expected_composite) < 0.01

    def test_timestamp_preserved(self) -> None:
        """Timestamp should be preserved in verdict."""
        engine = RCMEngine()
        now = datetime.now(UTC)
        signal = RCMSignal(
            timestamp=now,
            asset_id="TEST-TS",
            capital_flow_score=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivative_funding=0.0,
            open_interest_change=0.0,
        )

        verdict = engine.evaluate(signal)

        assert verdict.timestamp == now
