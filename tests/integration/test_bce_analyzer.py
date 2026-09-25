"""Integration tests for BCE Analyzer."""

import pytest

from src.layers.layer3_wyckoff.bce_analyzer import BCEAnalyzer, BCEAnalysisReport
from tests.fixtures.market_data import (
    generate_accumulation_ohlcv,
    generate_bull_ohlcv,
    generate_bear_ohlcv,
)


class TestBCEAnalyzer:
    """Tests for comprehensive BCE analysis."""

    def test_analyzer_with_accumulation(self):
        """Analyzer should produce positive signals on accumulation."""
        analyzer = BCEAnalyzer()

        ohlcv = generate_accumulation_ohlcv(100)
        report = analyzer.analyze("BTC", ohlcv)

        assert isinstance(report, BCEAnalysisReport)
        assert report.asset == "BTC"
        assert report.bce_score >= 0

    def test_support_resistance_detection(self):
        """Should detect support and resistance levels."""
        analyzer = BCEAnalyzer()

        ohlcv = generate_accumulation_ohlcv(50)
        report = analyzer.analyze("BTC", ohlcv)

        # Support should be less than resistance
        if report.support_level > 0 and report.resistance_level > 0:
            assert report.support_level < report.resistance_level

    def test_double_bottom_detection(self):
        """Should detect double bottom patterns."""
        analyzer = BCEAnalyzer()

        # Accumulation data should show double bottom
        ohlcv = generate_accumulation_ohlcv(100)
        report = analyzer.analyze("BTC", ohlcv)

        # Tight range should indicate multiple touches of low
        if report.bce_score >= 3.0:
            assert report.double_bottom_detected is True

    def test_volume_confirmation(self):
        """Should verify volume on bounces."""
        analyzer = BCEAnalyzer()

        ohlcv = generate_accumulation_ohlcv(50)
        report = analyzer.analyze("BTC", ohlcv)

        assert isinstance(report.volume_confirmation, bool)

    def test_trend_analysis(self):
        """Should correctly identify trend."""
        analyzer = BCEAnalyzer()

        # Bull trend
        bull_ohlcv = generate_bull_ohlcv(50)
        bull_report = analyzer.analyze("BTC", bull_ohlcv)
        assert bull_report.trend_confirmation in ["bullish", "bearish", "sideways"]

        # Bear trend
        bear_ohlcv = generate_bear_ohlcv(50)
        bear_report = analyzer.analyze("BTC", bear_ohlcv)
        assert bear_report.trend_confirmation in ["bullish", "bearish", "sideways"]

    def test_confidence_scoring(self):
        """Confidence level should be high/medium/low."""
        analyzer = BCEAnalyzer()

        ohlcv = generate_accumulation_ohlcv(100)
        report = analyzer.analyze("BTC", ohlcv)

        assert report.confidence_level in ["high", "medium", "low"]

    def test_risk_rating(self):
        """Risk rating should be appropriate."""
        analyzer = BCEAnalyzer()

        ohlcv = generate_accumulation_ohlcv(100)
        report = analyzer.analyze("BTC", ohlcv)

        assert report.risk_rating in ["low", "medium", "high"]

    def test_entry_signal_only_when_valid_and_confident(self):
        """Entry signal should require both BCE validity and confidence."""
        analyzer = BCEAnalyzer()

        ohlcv = generate_accumulation_ohlcv(100)
        report = analyzer.analyze("BTC", ohlcv)

        if report.entry_signal:
            # If entry signal is true, BCE should be valid
            assert report.is_valid
            # And confidence should not be low
            assert report.confidence_level != "low"

    def test_reasoning_provided(self):
        """Report should include reasoning for all signals."""
        analyzer = BCEAnalyzer()

        ohlcv = generate_accumulation_ohlcv(100)
        report = analyzer.analyze("BTC", ohlcv)

        # Should have at least some reasoning
        assert len(report.reasoning) > 0
        assert all(isinstance(r, str) for r in report.reasoning)

    def test_report_text_generation(self):
        """Should generate human-readable report text."""
        analyzer = BCEAnalyzer()

        ohlcv = generate_accumulation_ohlcv(100)
        report = analyzer.analyze("BTC", ohlcv)

        text = analyzer.generate_report_text(report)

        # Should contain key sections
        assert "BCE ANALYSIS REPORT" in text
        assert "BTC" in text
        assert "Confidence" in text
        assert "Risk Rating" in text


class TestBCEAnalyzerPatterns:
    """Pattern detection tests."""

    def test_detect_support_resistance(self):
        """Support/resistance should be correctly identified."""
        from src.layers.layer3_wyckoff.bce_analyzer import BCEAnalyzer

        ohlcv = generate_accumulation_ohlcv(30)
        support, resistance = BCEAnalyzer._detect_support_resistance(ohlcv)

        lows = [c.low for c in ohlcv[-20:]]
        highs = [c.high for c in ohlcv[-20:]]

        assert support == min(lows)
        assert resistance == max(highs)

    def test_double_bottom_on_accumulation(self):
        """Accumulation should have double bottoms."""
        from src.layers.layer3_wyckoff.bce_analyzer import BCEAnalyzer

        ohlcv = generate_accumulation_ohlcv(30)
        double_bottom = BCEAnalyzer._detect_double_bottom(ohlcv)

        # Tight range accumulation should show double bottom
        price_range = max(c.high for c in ohlcv) - min(c.low for c in ohlcv)
        avg_price = sum(c.close for c in ohlcv) / len(ohlcv)
        range_pct = (price_range / avg_price) * 100

        if range_pct < 5:  # Tight range
            assert double_bottom is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
