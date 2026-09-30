"""Integration test: Binance Layer 1 data through Layer 4 X20 Engine."""

import pytest
from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.layers.layer4_x20.x20_engine import X20Scanner


class TestBinanceX20Validation:
    """Validate X20 opportunity scanner on real Binance BTCUSDT data."""

    def test_x20_on_real_btc_2025_jan(self):
        """
        Integration: Binance data → X20 opportunity scoring.

        Tests:
        - Collector fetches real BTC data
        - X20 scanner processes OHLCV list
        - Scoring is in valid range (0-100)
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        scanner = X20Scanner()

        # Fetch Jan 2025 (31 candles)
        ohlcv_list = collector.fetch(start_year=2025, start_month=1,
                                     end_year=2025, end_month=1)

        assert len(ohlcv_list) == 31, f"Expected 31 candles, got {len(ohlcv_list)}"

        # Run through X20 scanner
        opportunity = scanner.scan("BTCUSDT", ohlcv_list)

        # Validate opportunity structure
        assert opportunity.asset == "BTCUSDT"
        assert opportunity.combined_score >= 0, "X20 score must be non-negative"
        assert opportunity.combined_score <= 100, "X20 score must be ≤ 100"

        # Validate all component scores
        assert opportunity.fundamental_score is not None
        assert opportunity.narrative_score is not None
        assert opportunity.quantitative_score is not None

        print(f"\nJan 2025 X20 Analysis:")
        print(f"  Combined Score: {opportunity.combined_score:.1f}/100")
        print(f"  Opportunity: {'YES' if opportunity.combined_score >= 70 else 'NO'}")
        print(f"  Fundamental: {opportunity.fundamental_score:.1f}")
        print(f"  Narrative: {opportunity.narrative_score:.1f}")
        print(f"  Quantitative: {opportunity.quantitative_score:.1f}")

    def test_x20_on_full_btc_range_2020_2025(self):
        """
        Full validation: 2020-2025 BTCUSDT through X20.

        Validates:
        - Collector loads 2192 historical candles
        - X20 scanner processes full range
        - Score distribution makes sense
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        scanner = X20Scanner()

        # Full historical data
        ohlcv_list = collector.fetch(start_year=2020, start_month=1,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 2100, f"Expected ~2192 candles, got {len(ohlcv_list)}"

        # Run through X20 scanner
        opportunity = scanner.scan("BTCUSDT", ohlcv_list)

        # Full range should be processable
        assert opportunity.combined_score >= 0
        assert opportunity.combined_score <= 100

        # BTC is established, should not be high X20 candidate (established not early-stage)
        print(f"\nFull Range X20 Analysis:")
        print(f"  Candles: {len(ohlcv_list)}")
        print(f"  Combined Score: {opportunity.combined_score:.1f}/100")
        print(f"  Opportunity: {'YES (potential emerging asset)' if opportunity.combined_score >= 70 else 'NO (established asset)'}")

    def test_x20_time_series_scoring(self):
        """
        Validation: Track X20 opportunity score over time.

        Tests:
        - Rolling 30-day window scoring
        - Identify periods of high/low opportunity
        - Score variance indicates detection working
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        scanner = X20Scanner()

        # Fetch last 180 days
        ohlcv_list = collector.fetch(start_year=2024, start_month=7,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 180, f"Expected ≥180 candles, got {len(ohlcv_list)}"

        # Rolling 30-day window
        window_size = 30
        scores = []

        for i in range(len(ohlcv_list) - window_size):
            window_data = ohlcv_list[i:i + window_size]
            opportunity = scanner.scan("BTCUSDT", window_data)
            scores.append(opportunity.combined_score)

        assert len(scores) > 0, "Should generate time series scores"

        # Score distribution
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        high_opportunity = sum(1 for s in scores if s >= 70)

        print(f"\nTime Series X20 (30-day windows, {len(scores)} periods):")
        print(f"  Avg Score: {avg_score:.1f}")
        print(f"  Range: {min_score:.1f} - {max_score:.1f}")
        print(f"  High opportunity (≥70): {high_opportunity}/{len(scores)}")

        # Validate variance exists
        assert max_score > min_score, "Score distribution should vary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
