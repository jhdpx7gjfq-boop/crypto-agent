"""Integration tests for RRP Engine."""

import pytest

from src.layers.layer7_rrp.rrp_engine import RRPEngine
from tests.fixtures.market_data import generate_bull_ohlcv


class TestRRPEngine:
    """Tests for revival radar pipeline."""

    def test_engine_scan(self):
        """Quick scan should return RRPSignal."""
        engine = RRPEngine()
        ohlcv = generate_bull_ohlcv(50)
        signal = engine.scan("DOGE", ohlcv)

        assert signal.asset == "DOGE"
        assert 0 <= signal.revival_probability <= 100

    def test_revival_probability(self):
        """Revival probability should be computed correctly."""
        engine = RRPEngine()
        ohlcv = generate_bull_ohlcv(50)
        signal = engine.scan(
            "TEST",
            ohlcv,
            snapshot_data={"whale_accumulation": 80},
            community_data={"social_mentions": 70},
        )

        assert signal.revival_probability > 0
        assert signal.revival_probability <= 100

    def test_stage_detection(self):
        """Stage should be dead/awakening/revival/momentum."""
        engine = RRPEngine()
        ohlcv = generate_bull_ohlcv(50)
        signal = engine.scan("TEST", ohlcv)

        assert signal.stage in ["dead", "awakening", "revival", "momentum"]

    def test_snapshot_health(self):
        """Snapshot health should score on-chain metrics."""
        engine = RRPEngine()
        data = {"holder_concentration": 85, "whale_accumulation": 80}
        score = engine._score_snapshot_health(data)

        assert 0 <= score <= 100

    def test_volume_signature(self):
        """Volume signature should detect unusual activity."""
        engine = RRPEngine()
        ohlcv = generate_bull_ohlcv(50)
        score = engine._score_volume_signature(ohlcv)

        assert 0 <= score <= 100

    def test_community_activity(self):
        """Community activity should score engagement."""
        engine = RRPEngine()
        data = {"social_mentions": 80, "dev_activity": 75}
        score = engine._score_community_activity(data)

        assert score >= 0

    def test_technical_confirmation(self):
        """Technical confirmation should score price action."""
        engine = RRPEngine()
        ohlcv = generate_bull_ohlcv(50)
        score = engine._score_technical_confirmation(ohlcv)

        assert 0 <= score <= 100

    def test_insufficient_data(self):
        """Insufficient data should return stage=dead."""
        engine = RRPEngine()
        short_ohlcv = generate_bull_ohlcv(5)
        signal = engine.scan("TEST", short_ohlcv)

        assert signal.revival_probability == 0.0
        assert signal.stage == "dead"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
