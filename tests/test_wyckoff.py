"""Wyckoff phase detection and Bottom Confirmation Engine tests."""

from datetime import UTC, datetime

from src.models.wyckoff.base import BCE_Signal, WyckoffSignal
from src.models.wyckoff.detector import BottomConfirmationEngine, WyckoffDetector


class TestWyckoffDetector:
    """Wyckoff phase detection tests."""

    def test_detector_initialization(self) -> None:
        """Initialize detector."""
        detector = WyckoffDetector()
        assert detector.history == []

    def test_accumulation_phase_detection(self) -> None:
        """Detect accumulation phase (low prices, RSI oversold)."""
        detector = WyckoffDetector()
        signal = WyckoffSignal(
            timestamp=datetime.now(UTC),
            price=10.0,
            volume=1000000.0,
            high_52w=50.0,
            low_52w=5.0,
            price_change_7d=-5.0,
            price_change_30d=-10.0,
            volume_ma_20=1200000.0,
            rsi_14=25.0,
            macd_signal=-0.5,
            lookback_days=60,
        )

        phase = detector.detect(signal)

        assert phase.name == "ACCUMULATION"
        assert phase.confidence > 0.6
        assert len(detector.history) == 1

    def test_markup_phase_detection(self) -> None:
        """Detect markup phase (rising prices, RSI 30-70)."""
        detector = WyckoffDetector()
        signal = WyckoffSignal(
            timestamp=datetime.now(UTC),
            price=35.0,
            volume=1500000.0,
            high_52w=50.0,
            low_52w=5.0,
            price_change_7d=10.0,
            price_change_30d=15.0,
            volume_ma_20=1400000.0,
            rsi_14=55.0,
            macd_signal=0.3,
            lookback_days=60,
        )

        phase = detector.detect(signal)

        assert phase.name == "MARKUP"
        assert phase.confidence > 0.5

    def test_distribution_phase_detection(self) -> None:
        """Detect distribution phase (high prices, RSI overbought)."""
        detector = WyckoffDetector()
        signal = WyckoffSignal(
            timestamp=datetime.now(UTC),
            price=45.0,
            volume=1200000.0,
            high_52w=50.0,
            low_52w=5.0,
            price_change_7d=-2.0,
            price_change_30d=5.0,
            volume_ma_20=1100000.0,
            rsi_14=75.0,
            macd_signal=0.2,
            lookback_days=60,
        )

        phase = detector.detect(signal)

        assert phase.name == "DISTRIBUTION"
        assert phase.confidence > 0.5

    def test_markdown_phase_detection(self) -> None:
        """Detect markdown phase (falling prices, RSI high)."""
        detector = WyckoffDetector()
        signal = WyckoffSignal(
            timestamp=datetime.now(UTC),
            price=40.0,
            volume=1800000.0,
            high_52w=50.0,
            low_52w=5.0,
            price_change_7d=-8.0,
            price_change_30d=-12.0,
            volume_ma_20=1600000.0,
            rsi_14=72.0,
            macd_signal=-0.1,
            lookback_days=60,
        )

        phase = detector.detect(signal)

        assert phase.name == "MARKDOWN"
        assert phase.confidence > 0.5

    def test_confidence_in_range(self) -> None:
        """Confidence should always be [0, 1]."""
        detector = WyckoffDetector()
        signal = WyckoffSignal(
            timestamp=datetime.now(UTC),
            price=25.0,
            volume=1000000.0,
            high_52w=50.0,
            low_52w=5.0,
            price_change_7d=0.0,
            price_change_30d=0.0,
            volume_ma_20=1000000.0,
            rsi_14=50.0,
            macd_signal=0.0,
            lookback_days=60,
        )

        phase = detector.detect(signal)

        assert 0.0 <= phase.confidence <= 1.0

    def test_price_range_calculated(self) -> None:
        """Price range should be calculated."""
        detector = WyckoffDetector()
        signal = WyckoffSignal(
            timestamp=datetime.now(UTC),
            price=25.0,
            volume=1000000.0,
            high_52w=50.0,
            low_52w=10.0,
            price_change_7d=0.0,
            price_change_30d=0.0,
            volume_ma_20=1000000.0,
            rsi_14=50.0,
            macd_signal=0.0,
            lookback_days=60,
        )

        phase = detector.detect(signal)

        assert phase.price_range[0] < phase.price_range[1]
        assert phase.price_range[0] > 10.0
        assert phase.price_range[1] < 50.0

    def test_history_accumulation(self) -> None:
        """History should accumulate detections."""
        detector = WyckoffDetector()

        for i in range(3):
            signal = WyckoffSignal(
                timestamp=datetime.now(UTC),
                price=10.0 + i * 5.0,
                volume=1000000.0,
                high_52w=50.0,
                low_52w=5.0,
                price_change_7d=-5.0,
                price_change_30d=-10.0,
                volume_ma_20=1200000.0,
                rsi_14=25.0 + i * 10.0,
                macd_signal=-0.5,
                lookback_days=60,
            )
            detector.detect(signal)

        assert len(detector.history) == 3


class TestBottomConfirmationEngine:
    """Bottom Confirmation Engine tests."""

    def test_bce_initialization(self) -> None:
        """Initialize BCE."""
        bce = BottomConfirmationEngine()
        assert bce.history == []
        assert bce.VERDICT_THRESHOLD == 5

    def test_bce_all_components_pass(self) -> None:
        """BCE should pass (score >= 5) when all 6 components pass."""
        bce = BottomConfirmationEngine()
        signal = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.8,
            spring_detected=True,
            sign_of_strength=True,
            volume_pattern=0.8,
            divergence_score=0.8,
            structure_quality=0.8,
        )

        verdict = bce.evaluate(signal)

        assert verdict.score == 6
        assert verdict.verdict is True
        assert verdict.confidence == 1.0

    def test_bce_exactly_5_components(self) -> None:
        """BCE should pass with exactly 5 components."""
        bce = BottomConfirmationEngine()
        signal = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.8,
            spring_detected=True,
            sign_of_strength=True,
            volume_pattern=0.8,
            divergence_score=0.8,
            structure_quality=0.2,
        )

        verdict = bce.evaluate(signal)

        assert verdict.score == 5
        assert verdict.verdict is True

    def test_bce_4_components_fail(self) -> None:
        """BCE should fail (score < 5)."""
        bce = BottomConfirmationEngine()
        signal = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.8,
            spring_detected=True,
            sign_of_strength=True,
            volume_pattern=0.8,
            divergence_score=0.2,
            structure_quality=0.2,
        )

        verdict = bce.evaluate(signal)

        assert verdict.score == 4
        assert verdict.verdict is False

    def test_bce_selling_exhaustion_component(self) -> None:
        """Selling exhaustion component should score individually."""
        bce = BottomConfirmationEngine()

        signal_pass = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.6,
            spring_detected=False,
            sign_of_strength=False,
            volume_pattern=0.0,
            divergence_score=0.0,
            structure_quality=0.0,
        )

        signal_fail = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.4,
            spring_detected=False,
            sign_of_strength=False,
            volume_pattern=0.0,
            divergence_score=0.0,
            structure_quality=0.0,
        )

        verdict_pass = bce.evaluate(signal_pass)
        verdict_fail = bce.evaluate(signal_fail)

        assert verdict_pass.components["selling_exhaustion"] == 1
        assert verdict_fail.components["selling_exhaustion"] == 0

    def test_bce_spring_detection_boolean(self) -> None:
        """Spring detection should be boolean (0 or 1)."""
        bce = BottomConfirmationEngine()

        signal_spring = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.0,
            spring_detected=True,
            sign_of_strength=False,
            volume_pattern=0.0,
            divergence_score=0.0,
            structure_quality=0.0,
        )

        verdict = bce.evaluate(signal_spring)
        assert verdict.components["spring"] == 1

    def test_bce_sign_of_strength_boolean(self) -> None:
        """Sign of strength should be boolean (0 or 1)."""
        bce = BottomConfirmationEngine()

        signal_sos = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.0,
            spring_detected=False,
            sign_of_strength=True,
            volume_pattern=0.0,
            divergence_score=0.0,
            structure_quality=0.0,
        )

        verdict = bce.evaluate(signal_sos)
        assert verdict.components["sign_of_strength"] == 1

    def test_bce_confidence_calculation(self) -> None:
        """Confidence should be score / 6."""
        bce = BottomConfirmationEngine()

        signal_3 = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.8,
            spring_detected=True,
            sign_of_strength=True,
            volume_pattern=0.0,
            divergence_score=0.0,
            structure_quality=0.0,
        )

        verdict = bce.evaluate(signal_3)
        assert verdict.score == 3
        assert abs(verdict.confidence - 0.5) < 0.01

    def test_bce_metadata_present(self) -> None:
        """Verdict should include metadata."""
        bce = BottomConfirmationEngine()
        signal = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.8,
            spring_detected=True,
            sign_of_strength=True,
            volume_pattern=0.8,
            divergence_score=0.8,
            structure_quality=0.8,
        )

        verdict = bce.evaluate(signal)

        assert "threshold" in verdict.metadata
        assert verdict.metadata["threshold"] == 5
        assert "component_threshold" in verdict.metadata
        assert "timestamp" in verdict.metadata

    def test_bce_history_accumulation(self) -> None:
        """BCE should accumulate evaluation history."""
        bce = BottomConfirmationEngine()

        for i in range(3):
            signal = BCE_Signal(
                timestamp=datetime.now(UTC),
                price=10.0 + i,
                selling_exhaustion_score=0.5 + i * 0.1,
                spring_detected=i > 0,
                sign_of_strength=i > 1,
                volume_pattern=0.5,
                divergence_score=0.5,
                structure_quality=0.5,
            )
            bce.evaluate(signal)

        assert len(bce.history) == 3

    def test_bce_zero_components(self) -> None:
        """BCE with no components should score 0 and fail."""
        bce = BottomConfirmationEngine()
        signal = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.0,
            spring_detected=False,
            sign_of_strength=False,
            volume_pattern=0.0,
            divergence_score=0.0,
            structure_quality=0.0,
        )

        verdict = bce.evaluate(signal)

        assert verdict.score == 0
        assert verdict.verdict is False
        assert verdict.confidence == 0.0

    def test_bce_boundary_threshold(self) -> None:
        """Test BCE at exact threshold boundary."""
        bce = BottomConfirmationEngine()

        signal_5 = BCE_Signal(
            timestamp=datetime.now(UTC),
            price=10.0,
            selling_exhaustion_score=0.51,
            spring_detected=True,
            sign_of_strength=True,
            volume_pattern=0.51,
            divergence_score=0.51,
            structure_quality=0.0,
        )

        verdict = bce.evaluate(signal_5)
        assert verdict.score == 5
        assert verdict.verdict is True
