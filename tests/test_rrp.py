"""RRP Engine tests: revival radar pipeline for dead token renaissance."""

from datetime import UTC, datetime

from src.models.rrp.base import RRPSnapshot
from src.models.rrp.detector import RRPEngine


class TestRRPEngine:
    """Revival Radar Pipeline tests."""

    def test_engine_initialization(self) -> None:
        """Initialize RRP engine."""
        engine = RRPEngine()
        assert engine.history == []
        assert engine.snapshots == {}
        assert engine.STIRRING_THRESHOLD == 0.3
        assert engine.AWAKENING_THRESHOLD == 0.55
        assert engine.REVIVING_THRESHOLD == 0.75

    def test_reviving_stage_detection(self) -> None:
        """Detect token in reviving stage."""
        engine = RRPEngine()
        snapshot = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-REVIVING",
            dormancy_days=100,
            price_change_30d=50.0,
            volume_24h=5000000.0,
            volume_ma_90=1000000.0,
            holders_count=50000,
            holders_growth_30d=30.0,
            social_mentions=500,
            social_growth_30d=80.0,
            whale_accumulation=0.8,
        )

        verdict = engine.evaluate(snapshot)

        assert verdict.revival_stage == "REVIVING"
        assert verdict.revival_score >= 0.75

    def test_awakening_stage_detection(self) -> None:
        """Detect token in awakening stage."""
        engine = RRPEngine()
        snapshot = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-AWAKENING",
            dormancy_days=120,
            price_change_30d=35.0,
            volume_24h=4000000.0,
            volume_ma_90=1000000.0,
            holders_count=50000,
            holders_growth_30d=25.0,
            social_mentions=400,
            social_growth_30d=60.0,
            whale_accumulation=0.6,
        )

        verdict = engine.evaluate(snapshot)

        assert verdict.revival_stage == "AWAKENING"
        assert 0.55 <= verdict.revival_score < 0.75

    def test_stirring_stage_detection(self) -> None:
        """Detect early stirring signs."""
        engine = RRPEngine()
        snapshot = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-STIRRING",
            dormancy_days=280,
            price_change_30d=15.0,
            volume_24h=2500000.0,
            volume_ma_90=1000000.0,
            holders_count=38000,
            holders_growth_30d=12.0,
            social_mentions=150,
            social_growth_30d=35.0,
            whale_accumulation=0.35,
        )

        verdict = engine.evaluate(snapshot)

        assert verdict.revival_stage == "STIRRING"
        assert 0.30 <= verdict.revival_score < 0.55

    def test_dead_stage_detection(self) -> None:
        """Detect still-dormant token."""
        engine = RRPEngine()
        snapshot = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-DEAD",
            dormancy_days=500,
            price_change_30d=-10.0,
            volume_24h=100000.0,
            volume_ma_90=500000.0,
            holders_count=5000,
            holders_growth_30d=-5.0,
            social_mentions=5,
            social_growth_30d=-30.0,
            whale_accumulation=0.0,
        )

        verdict = engine.evaluate(snapshot)

        assert verdict.revival_stage == "DEAD"
        assert verdict.revival_score < 0.30

    def test_score_within_bounds(self) -> None:
        """Revival score should be [0, 1]."""
        engine = RRPEngine()
        snapshot = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-BOUNDS",
            dormancy_days=180,
            price_change_30d=15.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=35000,
            holders_growth_30d=10.0,
            social_mentions=100,
            social_growth_30d=30.0,
            whale_accumulation=0.3,
        )

        verdict = engine.evaluate(snapshot)

        assert 0.0 <= verdict.revival_score <= 1.0

    def test_activation_signal_with_volume_spike(self) -> None:
        """Activation should increase with volume spike."""
        engine = RRPEngine()

        snapshot_low_vol = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-VOL-LOW",
            dormancy_days=100,
            price_change_30d=10.0,
            volume_24h=500000.0,
            volume_ma_90=1000000.0,
            holders_count=30000,
            holders_growth_30d=5.0,
            social_mentions=50,
            social_growth_30d=10.0,
            whale_accumulation=0.1,
        )

        snapshot_high_vol = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-VOL-HIGH",
            dormancy_days=100,
            price_change_30d=10.0,
            volume_24h=5000000.0,
            volume_ma_90=1000000.0,
            holders_count=30000,
            holders_growth_30d=5.0,
            social_mentions=50,
            social_growth_30d=10.0,
            whale_accumulation=0.1,
        )

        verdict_low = engine.evaluate(snapshot_low_vol)
        verdict_high = engine.evaluate(snapshot_high_vol)

        assert verdict_high.revival_score > verdict_low.revival_score

    def test_fundamental_shift_with_holder_growth(self) -> None:
        """Fundamentals should improve with holder growth."""
        engine = RRPEngine()

        snapshot_no_growth = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-HOLD-NO",
            dormancy_days=100,
            price_change_30d=10.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=30000,
            holders_growth_30d=-5.0,
            social_mentions=100,
            social_growth_30d=20.0,
            whale_accumulation=0.3,
        )

        snapshot_growth = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-HOLD-YES",
            dormancy_days=100,
            price_change_30d=10.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=40000,
            holders_growth_30d=25.0,
            social_mentions=100,
            social_growth_30d=20.0,
            whale_accumulation=0.3,
        )

        verdict_no = engine.evaluate(snapshot_no_growth)
        verdict_yes = engine.evaluate(snapshot_growth)

        assert verdict_yes.revival_score > verdict_no.revival_score

    def test_social_momentum_impact(self) -> None:
        """Social momentum should impact revival score."""
        engine = RRPEngine()

        snapshot_low_social = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-SOCIAL-LOW",
            dormancy_days=100,
            price_change_30d=10.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=35000,
            holders_growth_30d=10.0,
            social_mentions=10,
            social_growth_30d=-20.0,
            whale_accumulation=0.3,
        )

        snapshot_high_social = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-SOCIAL-HIGH",
            dormancy_days=100,
            price_change_30d=10.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=35000,
            holders_growth_30d=10.0,
            social_mentions=500,
            social_growth_30d=80.0,
            whale_accumulation=0.3,
        )

        verdict_low = engine.evaluate(snapshot_low_social)
        verdict_high = engine.evaluate(snapshot_high_social)

        assert verdict_high.revival_score > verdict_low.revival_score

    def test_whale_accumulation_signal(self) -> None:
        """Whale accumulation should boost revival score."""
        engine = RRPEngine()

        snapshot_no_whales = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-WHALE-NO",
            dormancy_days=100,
            price_change_30d=10.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=35000,
            holders_growth_30d=10.0,
            social_mentions=100,
            social_growth_30d=30.0,
            whale_accumulation=0.0,
        )

        snapshot_whales = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-WHALE-YES",
            dormancy_days=100,
            price_change_30d=10.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=35000,
            holders_growth_30d=10.0,
            social_mentions=100,
            social_growth_30d=30.0,
            whale_accumulation=0.8,
        )

        verdict_no = engine.evaluate(snapshot_no_whales)
        verdict_yes = engine.evaluate(snapshot_whales)

        assert verdict_yes.revival_score > verdict_no.revival_score

    def test_dormancy_penalty(self) -> None:
        """Long dormancy should reduce score (penalty)."""
        engine = RRPEngine()

        snapshot_recent = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-DORM-RECENT",
            dormancy_days=30,
            price_change_30d=20.0,
            volume_24h=2000000.0,
            volume_ma_90=1000000.0,
            holders_count=40000,
            holders_growth_30d=15.0,
            social_mentions=200,
            social_growth_30d=50.0,
            whale_accumulation=0.5,
        )

        snapshot_old = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-DORM-OLD",
            dormancy_days=300,
            price_change_30d=20.0,
            volume_24h=2000000.0,
            volume_ma_90=1000000.0,
            holders_count=40000,
            holders_growth_30d=15.0,
            social_mentions=200,
            social_growth_30d=50.0,
            whale_accumulation=0.5,
        )

        verdict_recent = engine.evaluate(snapshot_recent)
        verdict_old = engine.evaluate(snapshot_old)

        assert verdict_recent.revival_score > verdict_old.revival_score

    def test_confidence_calculation(self) -> None:
        """Confidence should be [0, 1]."""
        engine = RRPEngine()
        snapshot = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-CONF",
            dormancy_days=100,
            price_change_30d=15.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=35000,
            holders_growth_30d=10.0,
            social_mentions=100,
            social_growth_30d=30.0,
            whale_accumulation=0.3,
        )

        verdict = engine.evaluate(snapshot)

        assert 0.0 <= verdict.confidence <= 1.0

    def test_reasoning_generation(self) -> None:
        """Verdict should include reasoning."""
        engine = RRPEngine()
        snapshot = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-REASON",
            dormancy_days=100,
            price_change_30d=30.0,
            volume_24h=3000000.0,
            volume_ma_90=1000000.0,
            holders_count=45000,
            holders_growth_30d=25.0,
            social_mentions=300,
            social_growth_30d=70.0,
            whale_accumulation=0.7,
        )

        verdict = engine.evaluate(snapshot)

        assert isinstance(verdict.reasoning, list)
        assert len(verdict.reasoning) > 0
        assert all(isinstance(r, str) for r in verdict.reasoning)

    def test_history_accumulation(self) -> None:
        """Engine should accumulate history."""
        engine = RRPEngine()

        for i in range(3):
            snapshot = RRPSnapshot(
                timestamp=datetime.now(UTC),
                asset_id=f"TEST-HIST-{i}",
                dormancy_days=100 + i * 50,
                price_change_30d=10.0 + i * 5.0,
                volume_24h=1500000.0 + i * 500000.0,
                volume_ma_90=1000000.0,
                holders_count=35000 + i * 5000,
                holders_growth_30d=10.0 + i * 5.0,
                social_mentions=100 + i * 100,
                social_growth_30d=30.0 + i * 10.0,
                whale_accumulation=0.3 + i * 0.1,
            )
            engine.evaluate(snapshot)

        assert len(engine.history) == 3

    def test_snapshot_storage(self) -> None:
        """Engine should store snapshots by asset."""
        engine = RRPEngine()

        for i in range(2):
            snapshot = RRPSnapshot(
                timestamp=datetime.now(UTC),
                asset_id="TEST-STORAGE",
                dormancy_days=100 + i * 50,
                price_change_30d=10.0 + i * 5.0,
                volume_24h=1500000.0,
                volume_ma_90=1000000.0,
                holders_count=35000,
                holders_growth_30d=10.0,
                social_mentions=100,
                social_growth_30d=30.0,
                whale_accumulation=0.3,
            )
            engine.evaluate(snapshot)

        assert "TEST-STORAGE" in engine.snapshots
        assert len(engine.snapshots["TEST-STORAGE"]) == 2

    def test_metadata_present(self) -> None:
        """Verdict should include metadata."""
        engine = RRPEngine()
        snapshot = RRPSnapshot(
            timestamp=datetime.now(UTC),
            asset_id="TEST-META",
            dormancy_days=100,
            price_change_30d=15.0,
            volume_24h=1500000.0,
            volume_ma_90=1000000.0,
            holders_count=35000,
            holders_growth_30d=10.0,
            social_mentions=100,
            social_growth_30d=30.0,
            whale_accumulation=0.3,
        )

        verdict = engine.evaluate(snapshot)

        assert "volume_ratio" in verdict.metadata
        assert "holders_change" in verdict.metadata
        assert "social_change" in verdict.metadata
        assert "whale_activity" in verdict.metadata
