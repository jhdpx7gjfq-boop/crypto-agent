"""X20 Engine tests: asymmetric opportunity detection."""

from datetime import UTC, datetime

from src.models.x20.base import X20Signal
from src.models.x20.detector import X20Engine


class TestX20Engine:
    """X20 opportunity detection tests."""

    def test_engine_initialization(self) -> None:
        """Initialize X20 engine."""
        engine = X20Engine()
        assert engine.history == []
        assert engine.LOW_THRESHOLD == 0.3
        assert engine.MEDIUM_THRESHOLD == 0.5
        assert engine.HIGH_THRESHOLD == 0.7

    def test_high_potential_opportunity(self) -> None:
        """Detect high-potential opportunity."""
        engine = X20Engine()
        signal = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-X20-HIGH",
            price=0.01,
            market_cap=50_000_000.0,
            volume_24h=10_000_000.0,
            volatility_30d=0.4,
            rsi_14=35.0,
            momentum_score=0.7,
            adoption_growth=20.0,
            narrative_relevance=0.8,
            lookback_days=60,
        )

        score = engine.evaluate(signal)

        assert score.asset_id == "TEST-X20-HIGH"
        assert score.x20_potential in ["HIGH", "VERY_HIGH"]
        assert score.confidence > 0.5
        assert len(score.reasoning) > 0

    def test_low_potential_opportunity(self) -> None:
        """Detect low-potential opportunity."""
        engine = X20Engine()
        signal = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-X20-LOW",
            price=100.0,
            market_cap=1_000_000_000.0,
            volume_24h=50_000_000.0,
            volatility_30d=0.1,
            rsi_14=55.0,
            momentum_score=-0.5,
            adoption_growth=0.0,
            narrative_relevance=0.2,
            lookback_days=60,
        )

        score = engine.evaluate(signal)

        assert score.asset_id == "TEST-X20-LOW"
        assert score.x20_potential in ["LOW", "MEDIUM"]

    def test_fundamental_score_composition(self) -> None:
        """Fundamental score should weight components correctly."""
        engine = X20Engine()
        signal = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-FUND",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=40.0,
            momentum_score=0.5,
            adoption_growth=15.0,
            narrative_relevance=0.6,
        )

        score = engine.evaluate(signal)

        assert "fundamental" in score.components
        assert "team_quality" in score.components["fundamental"]
        assert "adoption_trajectory" in score.components["fundamental"]
        assert 0.0 <= score.fundamental_score <= 1.0

    def test_narrative_score_with_high_adoption(self) -> None:
        """Narrative score should increase with high adoption growth."""
        engine = X20Engine()
        signal_low = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-NARR-LOW",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=40.0,
            momentum_score=0.5,
            adoption_growth=0.0,
            narrative_relevance=0.5,
        )

        signal_high = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-NARR-HIGH",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=40.0,
            momentum_score=0.5,
            adoption_growth=30.0,
            narrative_relevance=0.5,
        )

        score_low = engine.evaluate(signal_low)
        score_high = engine.evaluate(signal_high)

        assert score_high.narrative_score > score_low.narrative_score

    def test_quantitative_score_with_high_momentum(self) -> None:
        """Quantitative score should increase with strong momentum."""
        engine = X20Engine()
        signal_weak = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-QUANT-WEAK",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=40.0,
            momentum_score=-0.8,
            adoption_growth=10.0,
            narrative_relevance=0.5,
        )

        signal_strong = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-QUANT-STRONG",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=75.0,
            momentum_score=0.9,
            adoption_growth=10.0,
            narrative_relevance=0.5,
        )

        score_weak = engine.evaluate(signal_weak)
        score_strong = engine.evaluate(signal_strong)

        assert score_strong.quantitative_score > score_weak.quantitative_score

    def test_confidence_calculation(self) -> None:
        """Confidence should reflect consistency across dimensions."""
        engine = X20Engine()
        signal = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CONF",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=40.0,
            momentum_score=0.5,
            adoption_growth=15.0,
            narrative_relevance=0.6,
        )

        score = engine.evaluate(signal)

        assert 0.0 <= score.confidence <= 1.0

    def test_x20_potential_classification(self) -> None:
        """X20 potential should classify based on thresholds."""
        engine = X20Engine()

        signal_very_high = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-VH",
            price=0.01,
            market_cap=50_000_000.0,
            volume_24h=15_000_000.0,
            volatility_30d=0.5,
            rsi_14=30.0,
            momentum_score=0.8,
            adoption_growth=25.0,
            narrative_relevance=0.9,
        )

        signal_low = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-LOW",
            price=100.0,
            market_cap=1_000_000_000.0,
            volume_24h=30_000_000.0,
            volatility_30d=0.1,
            rsi_14=50.0,
            momentum_score=-0.6,
            adoption_growth=0.0,
            narrative_relevance=0.1,
        )

        score_vh = engine.evaluate(signal_very_high)
        score_low = engine.evaluate(signal_low)

        assert score_vh.x20_potential in ["HIGH", "VERY_HIGH"]
        assert score_low.x20_potential in ["LOW", "MEDIUM"]

    def test_reasoning_generation(self) -> None:
        """X20 score should include human-readable reasoning."""
        engine = X20Engine()
        signal = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-REASON",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.4,
            rsi_14=35.0,
            momentum_score=0.7,
            adoption_growth=20.0,
            narrative_relevance=0.8,
        )

        score = engine.evaluate(signal)

        assert isinstance(score.reasoning, list)
        assert len(score.reasoning) > 0
        assert all(isinstance(r, str) for r in score.reasoning)

    def test_metadata_present(self) -> None:
        """X20 score should include metadata."""
        engine = X20Engine()
        signal = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-META",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=40.0,
            momentum_score=0.5,
            adoption_growth=10.0,
            narrative_relevance=0.5,
        )

        score = engine.evaluate(signal)

        assert "composite_score" in score.metadata
        assert isinstance(score.metadata["composite_score"], float)
        assert 0.0 <= score.metadata["composite_score"] <= 1.0

    def test_history_accumulation(self) -> None:
        """Engine should accumulate evaluation history."""
        engine = X20Engine()

        for i in range(3):
            signal = X20Signal(
                timestamp=datetime.now(UTC),
                asset_id=f"TEST-HIST-{i}",
                price=0.05 + i * 0.02,
                market_cap=100_000_000.0 + i * 50_000_000.0,
                volume_24h=20_000_000.0 + i * 5_000_000.0,
                volatility_30d=0.3 + i * 0.05,
                rsi_14=40.0 + i * 5.0,
                momentum_score=0.5 + i * 0.1,
                adoption_growth=10.0 + i * 5.0,
                narrative_relevance=0.5,
            )
            engine.evaluate(signal)

        assert len(engine.history) == 3

    def test_composite_score_calculation(self) -> None:
        """Composite score should weight three dimensions."""
        engine = X20Engine()
        signal = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-COMP",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=40.0,
            momentum_score=0.5,
            adoption_growth=15.0,
            narrative_relevance=0.6,
        )

        score = engine.evaluate(signal)

        expected_composite = (
            score.fundamental_score * 0.35
            + score.narrative_score * 0.35
            + score.quantitative_score * 0.30
        )

        assert abs(score.metadata["composite_score"] - expected_composite) < 0.01

    def test_small_market_cap_small_price(self) -> None:
        """Small market cap with small price should show high potential."""
        engine = X20Engine()
        signal = X20Signal(
            timestamp=datetime.now(UTC),
            asset_id="TEST-SMALL-CAP",
            price=0.001,
            market_cap=10_000_000.0,
            volume_24h=2_000_000.0,
            volatility_30d=0.5,
            rsi_14=25.0,
            momentum_score=0.6,
            adoption_growth=30.0,
            narrative_relevance=0.7,
        )

        score = engine.evaluate(signal)

        assert score.x20_potential in ["MEDIUM", "HIGH", "VERY_HIGH"]

    def test_timestamp_preserved(self) -> None:
        """Timestamp should be preserved in score."""
        engine = X20Engine()
        now = datetime.now(UTC)
        signal = X20Signal(
            timestamp=now,
            asset_id="TEST-TS",
            price=0.05,
            market_cap=100_000_000.0,
            volume_24h=20_000_000.0,
            volatility_30d=0.3,
            rsi_14=40.0,
            momentum_score=0.5,
            adoption_growth=10.0,
            narrative_relevance=0.5,
        )

        score = engine.evaluate(signal)

        assert score.timestamp == now
