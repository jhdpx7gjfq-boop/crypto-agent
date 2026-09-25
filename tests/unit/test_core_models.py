"""Unit tests for core data models."""

import pytest
from datetime import datetime

from src.core.models import (
    OHLCV, MarketRegime, RegimeType, WyckoffSignal,
    SignalType, DecisionSignal,
)


class TestOHLCVModel:
    """Tests for OHLCV dataclass."""

    def test_valid_ohlcv(self):
        """Valid OHLCV should not raise."""
        ohlcv = OHLCV(
            timestamp=datetime.utcnow(),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1e9,
        )
        assert ohlcv.close == 105.0

    def test_invalid_high_low(self):
        """High < Low should raise."""
        with pytest.raises(ValueError, match="Low.*must be.*High"):
            OHLCV(
                timestamp=datetime.utcnow(),
                open=100.0,
                high=90.0,  # Less than low
                low=110.0,
                close=100.0,
                volume=1e9,
            )

    def test_invalid_open_outside_range(self):
        """Open outside [Low, High] should raise."""
        with pytest.raises(ValueError, match="Open.*between.*Low.*High"):
            OHLCV(
                timestamp=datetime.utcnow(),
                open=120.0,  # Above high
                high=110.0,
                low=90.0,
                close=100.0,
                volume=1e9,
            )

    def test_invalid_negative_volume(self):
        """Negative volume should raise."""
        with pytest.raises(ValueError, match="Volume.*negative"):
            OHLCV(
                timestamp=datetime.utcnow(),
                open=100.0,
                high=110.0,
                low=90.0,
                close=105.0,
                volume=-1e9,
            )


class TestMarketRegimeModel:
    """Tests for MarketRegime dataclass."""

    def test_valid_market_regime(self):
        """Valid regime should not raise."""
        regime = MarketRegime(
            timestamp=datetime.utcnow(),
            regime=RegimeType.BULL,
            btc_dominance=55.0,
            funding_rate=0.0005,
            open_interest_change=10.0,
        )
        assert regime.regime == RegimeType.BULL

    def test_invalid_btc_dominance_high(self):
        """BTC dominance > 100 should raise."""
        with pytest.raises(ValueError, match="BTC dominance.*0-100"):
            MarketRegime(
                timestamp=datetime.utcnow(),
                regime=RegimeType.BULL,
                btc_dominance=105.0,  # Invalid
                funding_rate=0.0005,
                open_interest_change=10.0,
            )

    def test_invalid_btc_dominance_negative(self):
        """BTC dominance < 0 should raise."""
        with pytest.raises(ValueError, match="BTC dominance.*0-100"):
            MarketRegime(
                timestamp=datetime.utcnow(),
                regime=RegimeType.BEAR,
                btc_dominance=-5.0,  # Invalid
                funding_rate=-0.0005,
                open_interest_change=-10.0,
            )


class TestWyckoffSignal:
    """Tests for WyckoffSignal and BCE scoring."""

    def test_bce_score_computation(self):
        """BCE score should be average of 6 components."""
        signal = WyckoffSignal(
            timestamp=datetime.utcnow(),
            asset="BTC",
            bce_score=0,  # Will be computed
            wyckoff_structure=1.0,
            volume_analysis=1.0,
            selling_exhaustion=1.0,
            smart_money_accumulation=0.5,
            market_structure=0.5,
            momentum_confirmation=0.0,
        )
        # __post_init__ computes: (1+1+1+0.5+0.5+0)/6 = 4/6 ≈ 0.67
        assert signal.bce_score == pytest.approx(2.5 / 6, abs=0.01)

    def test_valid_signal_threshold(self):
        """Signal with score >= 5.0 should be valid."""
        # 5/6 * 6 = 5.0
        signal = WyckoffSignal(
            timestamp=datetime.utcnow(),
            asset="BTC",
            bce_score=0,
            wyckoff_structure=5/6,
            volume_analysis=5/6,
            selling_exhaustion=5/6,
            smart_money_accumulation=5/6,
            market_structure=5/6,
            momentum_confirmation=5/6,
        )
        assert signal.valid is True

    def test_invalid_signal_threshold(self):
        """Signal with score < 5.0 should be invalid."""
        signal = WyckoffSignal(
            timestamp=datetime.utcnow(),
            asset="BTC",
            bce_score=0,
            wyckoff_structure=0.7,
            volume_analysis=0.7,
            selling_exhaustion=0.7,
            smart_money_accumulation=0.7,
            market_structure=0.7,
            momentum_confirmation=0.7,
        )
        assert signal.valid is False  # Score = 4.2/6 < 5.0


class TestDecisionSignal:
    """Tests for final decision signals."""

    def test_decision_signal_creation(self):
        """Decision signal should accept all components."""
        decision = DecisionSignal(
            timestamp=datetime.utcnow(),
            asset="BTC",
            signal_type=SignalType.LONG,
            confidence=75.0,
            bce_score=5.2,
            regime=RegimeType.BULL,
            reason="Multi-confirmation test",
        )
        assert decision.signal_type == SignalType.LONG
        assert decision.confidence == 75.0

    def test_confidence_bounds(self):
        """Confidence should be 0-100."""
        decision = DecisionSignal(
            timestamp=datetime.utcnow(),
            asset="BTC",
            signal_type=SignalType.NEUTRAL,
            confidence=50.0,
        )
        assert 0 <= decision.confidence <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
