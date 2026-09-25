"""Integration tests for Layer 3 — BCE Engine."""

import pytest

from src.layers.layer3_wyckoff.bce_engine import BottomConfirmationEngine
from tests.fixtures.market_data import (
    generate_accumulation_ohlcv,
    generate_bull_ohlcv,
    generate_bear_ohlcv,
)


class TestBCEEngine:
    """Tests for Bottom Confirmation Engine."""

    def test_bce_with_accumulation_pattern(self):
        """BCE should score high on accumulation pattern."""
        engine = BottomConfirmationEngine()

        ohlcv = generate_accumulation_ohlcv(100)
        signal = engine.analyze("BTC", ohlcv)

        # Accumulation pattern should score well
        assert signal.bce_score >= 3.0, f"Expected score >= 3.0, got {signal.bce_score}"
        assert signal.smart_money_accumulation >= 0.5
        assert signal.selling_exhaustion >= 0.3

    def test_bce_with_uptrend(self):
        """BCE should score moderately on uptrend (less bottoming)."""
        engine = BottomConfirmationEngine()

        ohlcv = generate_bull_ohlcv(100)
        signal = engine.analyze("BTC", ohlcv)

        # Uptrend is not bottom formation
        assert signal.bce_score < 5.0, "Uptrend should not trigger strong BCE"

    def test_bce_with_downtrend(self):
        """BCE should score low on downtrend (continued selling)."""
        engine = BottomConfirmationEngine()

        ohlcv = generate_bear_ohlcv(100)
        signal = engine.analyze("BTC", ohlcv)

        # Downtrend shows low exhaustion
        assert signal.selling_exhaustion < 0.5
        assert signal.market_structure < 0.5

    def test_bce_insufficient_data(self):
        """BCE with < 20 candles should return invalid."""
        engine = BottomConfirmationEngine()

        short_data = generate_accumulation_ohlcv(5)
        signal = engine.analyze("BTC", short_data)

        assert signal.valid is False
        assert signal.bce_score == 0

    def test_bce_validity_threshold(self):
        """BCE.valid should only be True if score >= 5.0."""
        engine = BottomConfirmationEngine()

        ohlcv = generate_accumulation_ohlcv(100)
        signal = engine.analyze("BTC", ohlcv)

        # Check that valid flag matches threshold
        if signal.bce_score >= 5.0:
            assert signal.valid is True
        else:
            assert signal.valid is False

    def test_bce_component_scoring_bounds(self):
        """All BCE components should be in [0, 1] range."""
        engine = BottomConfirmationEngine()

        ohlcv = generate_accumulation_ohlcv(100)
        signal = engine.analyze("BTC", ohlcv)

        components = [
            signal.wyckoff_structure,
            signal.volume_analysis,
            signal.selling_exhaustion,
            signal.smart_money_accumulation,
            signal.market_structure,
            signal.momentum_confirmation,
        ]

        for comp in components:
            assert 0 <= comp <= 1, f"Component {comp} outside [0, 1]"


class TestBCEEdgeCases:
    """Edge case tests for BCE."""

    def test_bce_exact_threshold_boundary(self):
        """BCE at exactly 5.0 should be valid."""
        engine = BottomConfirmationEngine()
        ohlcv = generate_accumulation_ohlcv(100)
        signal = engine.analyze("BTC", ohlcv)

        # If score happens to be 5.0, should be valid
        if signal.bce_score == 5.0:
            assert signal.valid is True

    def test_bce_empty_data(self):
        """BCE with empty data should handle gracefully."""
        engine = BottomConfirmationEngine()

        signal = engine.analyze("BTC", [])

        assert signal.valid is False
        assert signal.bce_score == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
