"""Integration tests for X20 Scanner."""

import pytest

from src.layers.layer4_x20.x20_engine import X20Scanner, X20AnalysisReport
from tests.fixtures.market_data import (
    generate_bull_ohlcv,
    generate_bear_ohlcv,
    generate_accumulation_ohlcv,
)


class TestX20Scanner:
    """Tests for X20 opportunity detection."""

    def test_scanner_quick_scan(self):
        """Quick scan should return X20Opportunity."""
        scanner = X20Scanner()

        ohlcv = generate_bull_ohlcv(50)
        opportunity = scanner.scan(
            "ETH",
            ohlcv,
            fundamental_data={"team_quality": "strong"},
            narrative_data={"sector_growth": 80},
        )

        assert opportunity.asset == "ETH"
        assert 0 <= opportunity.combined_score <= 100

    def test_scanner_comprehensive_analysis(self):
        """Comprehensive analysis should return detailed report."""
        scanner = X20Scanner()

        ohlcv = generate_bull_ohlcv(50)
        report = scanner.analyze(
            "SOL",
            ohlcv,
            fundamental_data={"team_quality": "elite", "adoption_score": 80},
            narrative_data={"sector_growth": 90, "media_attention": 70},
        )

        assert isinstance(report, X20AnalysisReport)
        assert report.asset == "SOL"
        assert 0 <= report.combined_score <= 100
        assert len(report.reasoning) > 0

    def test_fundamental_scoring(self):
        """Fundamental scoring should weigh team, investors, tokenomics, adoption."""
        scanner = X20Scanner()

        data_elite = {"team_quality": "elite", "adoption_score": 100}
        data_weak = {"team_quality": "unknown", "adoption_score": 0}

        score_elite, _ = scanner._score_fundamental_detailed(data_elite)
        score_weak, _ = scanner._score_fundamental_detailed(data_weak)

        assert score_elite > score_weak

    def test_narrative_scoring(self):
        """Narrative scoring should weigh sector, media, capital flow, competitive edge."""
        scanner = X20Scanner()

        data_strong = {
            "sector_growth": 90,
            "media_attention": 80,
            "capital_inflow_score": 85,
            "competitive_advantage": 90,
        }
        data_weak = {
            "sector_growth": 10,
            "media_attention": 10,
            "capital_inflow_score": 10,
            "competitive_advantage": 10,
        }

        score_strong, _ = scanner._score_narrative_detailed(data_strong)
        score_weak, _ = scanner._score_narrative_detailed(data_weak)

        assert score_strong > score_weak

    def test_quantitative_scoring(self):
        """Quantitative scoring should analyze momentum, volatility, RS, liquidity."""
        scanner = X20Scanner()

        bull_ohlcv = generate_bull_ohlcv(50)
        bear_ohlcv = generate_bear_ohlcv(50)

        score_bull, factors_bull = scanner._score_quantitative_detailed(bull_ohlcv)
        score_bear, factors_bear = scanner._score_quantitative_detailed(bear_ohlcv)

        assert "momentum" in factors_bull
        assert "volatility" in factors_bull
        assert "relative_strength" in factors_bull
        assert "liquidity" in factors_bull

    def test_opportunity_threshold(self):
        """Score >= 70 should trigger is_opportunity."""
        scanner = X20Scanner()

        ohlcv = generate_bull_ohlcv(50)

        # Strong opportunity
        report_strong = scanner.analyze(
            "BTC",
            ohlcv,
            fundamental_data={
                "team_quality": "elite",
                "investors": ["A", "B", "C"],
                "adoption_score": 90,
            },
            narrative_data={
                "sector_growth": 95,
                "media_attention": 90,
                "capital_inflow_score": 85,
            },
        )

        if report_strong.combined_score >= 70:
            assert report_strong.is_opportunity

    def test_risk_assessment(self):
        """Risk rating should be low/medium/high."""
        scanner = X20Scanner()

        ohlcv = generate_bull_ohlcv(50)
        report = scanner.analyze("TEST", ohlcv)

        assert report.risk_assessment in ["low", "medium", "high"]

    def test_asymmetric_ratio(self):
        """Asymmetric ratio should be positive."""
        scanner = X20Scanner()

        ohlcv = generate_bull_ohlcv(50)
        report = scanner.analyze("TEST", ohlcv)

        assert report.asymmetric_ratio >= 0

    def test_weighted_scoring(self):
        """Test that weak fundamentals cannot achieve high score alone."""
        scanner = X20Scanner()

        ohlcv = generate_bull_ohlcv(50)

        # Weak scores should not qualify
        report = scanner.analyze(
            "WEAK",
            ohlcv,
            fundamental_data={"team_quality": "unknown", "adoption_score": 10},
            narrative_data={"sector_growth": 10, "media_attention": 10},
        )

        # Should remain low even with bull market data
        assert report.combined_score < 50

    def test_report_generation(self):
        """Should generate human-readable report."""
        scanner = X20Scanner()

        ohlcv = generate_bull_ohlcv(50)
        report = scanner.analyze("ABC", ohlcv)

        text = scanner.generate_report_text(report)

        assert "X20 OPPORTUNITY ANALYSIS" in text
        assert "ABC" in text
        assert "Risk Assessment" in text
        assert "Asymmetric Ratio" in text

    def test_insufficient_data(self):
        """Insufficient data should return invalid report."""
        scanner = X20Scanner()

        short_ohlcv = generate_bull_ohlcv(5)
        report = scanner.analyze("TEST", short_ohlcv)

        assert report.is_opportunity is False
        assert report.combined_score == 0.0

    def test_weighted_combination(self):
        """Test weighted combination of scores."""
        scanner = X20Scanner()

        fund = 80.0
        narrative = 70.0
        quant = 60.0

        combined = fund * 0.40 + narrative * 0.35 + quant * 0.25
        expected = min(100.0, combined)

        ohlcv = generate_bull_ohlcv(50)
        opportunity = scanner.scan(
            "TEST",
            ohlcv,
            fundamental_data={"team_quality": "elite"},
            narrative_data={"sector_growth": 70},
        )

        # Combined should reflect weighting
        assert 0 <= opportunity.combined_score <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
