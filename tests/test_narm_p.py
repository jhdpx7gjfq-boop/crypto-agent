"""NARM-P+ Engine tests: narrative adoption rotation model."""

from datetime import UTC, datetime

from src.models.narm_p.base import NARMSignal
from src.models.narm_p.detector import NARMPEngine


class TestNARMPEngine:
    """NARM-P+ narrative evaluation tests."""

    def test_engine_initialization(self) -> None:
        """Initialize NARM-P+ engine."""
        engine = NARMPEngine()
        assert engine.history == []
        assert engine.EMERGING_THRESHOLD == 40
        assert engine.ACCELERATING_THRESHOLD == 60
        assert engine.MATURE_THRESHOLD == 75

    def test_emerging_narrative(self) -> None:
        """Detect emerging narrative."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-EMERGING",
            narrative_category="AI",
            attention_score=35.0,
            attention_growth_1m=15.0,
            attention_growth_3m=25.0,
            social_volume_rank=50,
            sentiment_score=20.0,
            adoption_rate=10.0,
            network_value=5.0,
            capital_inflow=2.0,
        )

        verdict = engine.evaluate(signal)

        assert verdict.rotation_signal == "EMERGING"
        assert verdict.total_score > 0

    def test_accelerating_narrative(self) -> None:
        """Detect accelerating narrative."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-ACCELERATING",
            narrative_category="RWA",
            attention_score=75.0,
            attention_growth_1m=30.0,
            attention_growth_3m=45.0,
            social_volume_rank=10,
            sentiment_score=50.0,
            adoption_rate=30.0,
            network_value=2.0,
            capital_inflow=12.0,
        )

        verdict = engine.evaluate(signal)

        assert verdict.rotation_signal == "ACCELERATING"
        assert verdict.total_score >= 55

    def test_mature_narrative(self) -> None:
        """Detect mature narrative."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-MATURE",
            narrative_category="DeFi",
            attention_score=95.0,
            attention_growth_1m=15.0,
            attention_growth_3m=30.0,
            social_volume_rank=2,
            sentiment_score=60.0,
            adoption_rate=80.0,
            network_value=0.8,
            capital_inflow=30.0,
        )

        verdict = engine.evaluate(signal)

        assert verdict.rotation_signal in ["MATURE", "ACCELERATING"]
        assert verdict.total_score >= 70

    def test_declining_narrative(self) -> None:
        """Detect declining narrative."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-DECLINING",
            narrative_category="Meme",
            attention_score=15.0,
            attention_growth_1m=-15.0,
            attention_growth_3m=-25.0,
            social_volume_rank=100,
            sentiment_score=-30.0,
            adoption_rate=-5.0,
            network_value=20.0,
            capital_inflow=-10.0,
        )

        verdict = engine.evaluate(signal)

        assert verdict.rotation_signal == "DECLINING"

    def test_score_within_bounds(self) -> None:
        """Total score should be between 0-100."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-BOUNDS",
            narrative_category="Infrastructure",
            attention_score=50.0,
            attention_growth_1m=10.0,
            attention_growth_3m=20.0,
            social_volume_rank=30,
            sentiment_score=0.0,
            adoption_rate=15.0,
            network_value=4.0,
            capital_inflow=5.0,
        )

        verdict = engine.evaluate(signal)

        assert 0 <= verdict.total_score <= 100

    def test_narrative_strength_component(self) -> None:
        """Narrative strength should scale with attention score."""
        engine = NARMPEngine()

        signal_low = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-NS-LOW",
            narrative_category="AI",
            attention_score=20.0,
            attention_growth_1m=5.0,
            attention_growth_3m=10.0,
            social_volume_rank=60,
            sentiment_score=0.0,
            adoption_rate=5.0,
            network_value=5.0,
            capital_inflow=0.0,
        )

        signal_high = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-NS-HIGH",
            narrative_category="AI",
            attention_score=80.0,
            attention_growth_1m=5.0,
            attention_growth_3m=10.0,
            social_volume_rank=60,
            sentiment_score=0.0,
            adoption_rate=5.0,
            network_value=5.0,
            capital_inflow=0.0,
        )

        verdict_low = engine.evaluate(signal_low)
        verdict_high = engine.evaluate(signal_high)

        assert verdict_high.components.narrative_strength > verdict_low.components.narrative_strength

    def test_adoption_momentum_component(self) -> None:
        """Adoption momentum should scale with adoption rate."""
        engine = NARMPEngine()

        signal_low = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-AM-LOW",
            narrative_category="RWA",
            attention_score=50.0,
            attention_growth_1m=5.0,
            attention_growth_3m=10.0,
            social_volume_rank=30,
            sentiment_score=0.0,
            adoption_rate=2.0,
            network_value=5.0,
            capital_inflow=0.0,
        )

        signal_high = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-AM-HIGH",
            narrative_category="RWA",
            attention_score=50.0,
            attention_growth_1m=30.0,
            attention_growth_3m=10.0,
            social_volume_rank=30,
            sentiment_score=0.0,
            adoption_rate=40.0,
            network_value=5.0,
            capital_inflow=0.0,
        )

        verdict_low = engine.evaluate(signal_low)
        verdict_high = engine.evaluate(signal_high)

        assert verdict_high.components.adoption_momentum > verdict_low.components.adoption_momentum

    def test_capital_rotation_component(self) -> None:
        """Capital rotation should scale with inflows and growth."""
        engine = NARMPEngine()

        signal_low = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CR-LOW",
            narrative_category="DeFi",
            attention_score=50.0,
            attention_growth_1m=5.0,
            attention_growth_3m=0.0,
            social_volume_rank=30,
            sentiment_score=0.0,
            adoption_rate=5.0,
            network_value=5.0,
            capital_inflow=0.0,
        )

        signal_high = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CR-HIGH",
            narrative_category="DeFi",
            attention_score=50.0,
            attention_growth_1m=5.0,
            attention_growth_3m=20.0,
            social_volume_rank=30,
            sentiment_score=0.0,
            adoption_rate=5.0,
            network_value=5.0,
            capital_inflow=20.0,
        )

        verdict_low = engine.evaluate(signal_low)
        verdict_high = engine.evaluate(signal_high)

        assert verdict_high.components.capital_rotation > verdict_low.components.capital_rotation

    def test_sentiment_alignment_component(self) -> None:
        """Sentiment should impact alignment score."""
        engine = NARMPEngine()

        signal_negative = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-SENT-NEG",
            narrative_category="AI",
            attention_score=50.0,
            attention_growth_1m=5.0,
            attention_growth_3m=10.0,
            social_volume_rank=30,
            sentiment_score=-50.0,
            adoption_rate=5.0,
            network_value=5.0,
            capital_inflow=0.0,
        )

        signal_positive = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-SENT-POS",
            narrative_category="AI",
            attention_score=50.0,
            attention_growth_1m=5.0,
            attention_growth_3m=10.0,
            social_volume_rank=30,
            sentiment_score=50.0,
            adoption_rate=5.0,
            network_value=5.0,
            capital_inflow=0.0,
        )

        verdict_neg = engine.evaluate(signal_negative)
        verdict_pos = engine.evaluate(signal_positive)

        assert verdict_pos.components.sentiment_alignment > verdict_neg.components.sentiment_alignment

    def test_percentile_calculation(self) -> None:
        """Percentile should scale with score."""
        engine = NARMPEngine()

        signal_low = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-PERC-LOW",
            narrative_category="Test",
            attention_score=20.0,
            attention_growth_1m=0.0,
            attention_growth_3m=0.0,
            social_volume_rank=100,
            sentiment_score=0.0,
            adoption_rate=0.0,
            network_value=10.0,
            capital_inflow=0.0,
        )

        signal_high = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-PERC-HIGH",
            narrative_category="Test",
            attention_score=90.0,
            attention_growth_1m=20.0,
            attention_growth_3m=30.0,
            social_volume_rank=1,
            sentiment_score=80.0,
            adoption_rate=50.0,
            network_value=1.0,
            capital_inflow=25.0,
        )

        verdict_low = engine.evaluate(signal_low)
        verdict_high = engine.evaluate(signal_high)

        assert verdict_high.percentile > verdict_low.percentile

    def test_confidence_calculation(self) -> None:
        """Confidence should be [0, 1]."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CONF",
            narrative_category="Infrastructure",
            attention_score=50.0,
            attention_growth_1m=10.0,
            attention_growth_3m=15.0,
            social_volume_rank=25,
            sentiment_score=10.0,
            adoption_rate=10.0,
            network_value=4.0,
            capital_inflow=5.0,
        )

        verdict = engine.evaluate(signal)

        assert 0.0 <= verdict.confidence <= 1.0

    def test_reasoning_generated(self) -> None:
        """Verdict should include reasoning."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-REASON",
            narrative_category="AI",
            attention_score=70.0,
            attention_growth_1m=20.0,
            attention_growth_3m=30.0,
            social_volume_rank=10,
            sentiment_score=50.0,
            adoption_rate=25.0,
            network_value=2.0,
            capital_inflow=15.0,
        )

        verdict = engine.evaluate(signal)

        assert isinstance(verdict.reasoning, list)
        assert len(verdict.reasoning) > 0
        assert all(isinstance(r, str) for r in verdict.reasoning)

    def test_history_accumulation(self) -> None:
        """Engine should accumulate history."""
        engine = NARMPEngine()

        for i in range(3):
            signal = NARMSignal(
                timestamp=datetime.now(UTC),
                asset_id=f"TEST-HIST-{i}",
                narrative_category="Test",
                attention_score=30.0 + i * 15.0,
                attention_growth_1m=5.0 + i * 5.0,
                attention_growth_3m=10.0 + i * 5.0,
                social_volume_rank=50 - i * 10,
                sentiment_score=0.0 + i * 20.0,
                adoption_rate=5.0 + i * 5.0,
                network_value=5.0,
                capital_inflow=0.0 + i * 5.0,
            )
            engine.evaluate(signal)

        assert len(engine.history) == 3

    def test_metadata_present(self) -> None:
        """Verdict should include metadata."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-META",
            narrative_category="RWA",
            attention_score=60.0,
            attention_growth_1m=10.0,
            attention_growth_3m=20.0,
            social_volume_rank=20,
            sentiment_score=25.0,
            adoption_rate=15.0,
            network_value=3.0,
            capital_inflow=8.0,
        )

        verdict = engine.evaluate(signal)

        assert "attention_score" in verdict.metadata
        assert "sentiment_score" in verdict.metadata
        assert "adoption_rate" in verdict.metadata
        assert "social_volume_rank" in verdict.metadata

    def test_score_components_sum(self) -> None:
        """Score components should sum to total."""
        engine = NARMPEngine()
        signal = NARMSignal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-SUM",
            narrative_category="Infrastructure",
            attention_score=55.0,
            attention_growth_1m=12.0,
            attention_growth_3m=18.0,
            social_volume_rank=25,
            sentiment_score=15.0,
            adoption_rate=12.0,
            network_value=3.5,
            capital_inflow=6.0,
        )

        verdict = engine.evaluate(signal)

        component_sum = (
            verdict.components.narrative_strength
            + verdict.components.adoption_momentum
            + verdict.components.capital_rotation
            + verdict.components.sentiment_alignment
            + verdict.components.network_effects
        )

        assert component_sum == verdict.total_score
