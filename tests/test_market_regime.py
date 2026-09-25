"""Tests for Market Regime Engine (Layer 2)."""

from datetime import UTC, datetime

import pytest

from src.models.regime import (
    MarketRegimeDetector,
    RegimeContext,
    RegimeScores,
    RegimeSignal,
)


class TestRegimeSignal:
    """Tests for RegimeSignal contract."""

    def test_regime_signal_valid(self) -> None:
        """Test valid regime signal creation."""
        signal = RegimeSignal(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            dxy=102.5,
            us10y=4.2,
            cpi_yoy=3.5,
            m2_yoy=2.0,
            funding_rate=0.01,
            open_interest=0.65,
            btc_price=42500.0,
        )

        assert signal.dxy == 102.5
        assert signal.us10y == 4.2
        assert signal.btc_price == 42500.0

    def test_regime_signal_bounds(self) -> None:
        """Test regime signal validates bounds."""
        with pytest.raises(ValueError):
            RegimeSignal(
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                dxy=-10.0,
                us10y=4.2,
                cpi_yoy=3.5,
                m2_yoy=2.0,
                funding_rate=0.01,
                open_interest=0.65,
                btc_price=42500.0,
            )


class TestMarketRegimeDetector:
    """Tests for MarketRegimeDetector."""

    def test_detector_init(self) -> None:
        """Test detector initialization."""
        detector = MarketRegimeDetector()
        assert detector.history == []

    def test_detect_risk_on_regime(self) -> None:
        """Test detection of RISK_ON regime."""
        detector = MarketRegimeDetector()
        signal = RegimeSignal(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            dxy=95.0,
            us10y=2.5,
            cpi_yoy=1.5,
            m2_yoy=5.0,
            funding_rate=0.03,
            open_interest=0.75,
            btc_price=50000.0,
        )

        context = detector.detect(signal)

        assert context.regime == "RISK_ON"
        assert context.confidence > 0.0
        assert len(detector.history) == 1

    def test_detect_risk_off_regime(self) -> None:
        """Test detection of RISK_OFF regime."""
        detector = MarketRegimeDetector()
        signal = RegimeSignal(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            dxy=108.0,
            us10y=5.0,
            cpi_yoy=5.5,
            m2_yoy=-1.0,
            funding_rate=-0.02,
            open_interest=0.3,
            btc_price=30000.0,
        )

        context = detector.detect(signal)

        assert context.regime == "RISK_OFF"
        assert context.confidence > 0.0

    def test_detect_transitional_regime(self) -> None:
        """Test detection of TRANSITIONAL regime."""
        detector = MarketRegimeDetector()
        signal = RegimeSignal(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            dxy=100.5,
            us10y=3.5,
            cpi_yoy=3.0,
            m2_yoy=2.0,
            funding_rate=0.00,
            open_interest=0.5,
            btc_price=40000.0,
        )

        context = detector.detect(signal)

        assert context.regime == "TRANSITIONAL"
        assert context.confidence > 0.0

    def test_regime_scores_calculation(self) -> None:
        """Test regime scores calculation."""
        detector = MarketRegimeDetector()
        signal = RegimeSignal(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            dxy=100.0,
            us10y=4.0,
            cpi_yoy=3.0,
            m2_yoy=2.0,
            funding_rate=0.01,
            open_interest=0.5,
            btc_price=40000.0,
        )

        context = detector.detect(signal)
        scores = context.scores

        assert 0.0 <= scores.dxy_strength <= 1.0
        assert 0.0 <= scores.rates_regime <= 1.0
        assert 0.0 <= scores.crypto_momentum <= 1.0
        assert 0.0 <= scores.inflation_pressure <= 1.0

    def test_regime_history_tracking(self) -> None:
        """Test regime context history tracking."""
        detector = MarketRegimeDetector()

        signal1 = RegimeSignal(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            dxy=95.0, us10y=2.5, cpi_yoy=1.5, m2_yoy=5.0,
            funding_rate=0.03, open_interest=0.75, btc_price=50000.0,
        )
        detector.detect(signal1)

        signal2 = RegimeSignal(
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            dxy=108.0, us10y=5.0, cpi_yoy=5.5, m2_yoy=-1.0,
            funding_rate=-0.02, open_interest=0.3, btc_price=30000.0,
        )
        detector.detect(signal2)

        assert len(detector.history) == 2
        assert detector.history[0].regime == "RISK_ON"
        assert detector.history[1].regime == "RISK_OFF"

    def test_regime_context_complete(self) -> None:
        """Test RegimeContext has all required fields."""
        detector = MarketRegimeDetector()
        signal = RegimeSignal(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            dxy=100.0, us10y=4.0, cpi_yoy=3.0, m2_yoy=2.0,
            funding_rate=0.01, open_interest=0.5, btc_price=40000.0,
        )

        context = detector.detect(signal)

        assert isinstance(context, RegimeContext)
        assert context.timestamp is not None
        assert context.regime in ["RISK_ON", "RISK_OFF", "TRANSITIONAL"]
        assert -1.0 <= context.regime_score <= 1.0
        assert 0.0 <= context.confidence <= 1.0
        assert isinstance(context.scores, RegimeScores)
        assert isinstance(context.metadata, dict)
