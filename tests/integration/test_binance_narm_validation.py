"""Integration test: Binance Layer 1 data through Layer 5 NARM-P+ Engine."""

import pytest
from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.layers.layer5_narm.narm_engine import NARMEngine


class TestBinanceNARMValidation:
    """Validate NARM-P+ engine on real Binance BTCUSDT data."""

    def test_narm_on_real_btc_2025_jan(self):
        """
        Integration: Binance data → NARM rotation scoring.

        Tests:
        - Collector fetches real BTC data
        - NARM engine processes OHLCV list
        - Scoring is in valid range (0-100)
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = NARMEngine()

        # Fetch Jan 2025 (31 candles)
        ohlcv_list = collector.fetch(start_year=2025, start_month=1,
                                     end_year=2025, end_month=1)

        assert len(ohlcv_list) == 31, f"Expected 31 candles, got {len(ohlcv_list)}"

        # Run through NARM engine
        signal = engine.scan("BTCUSDT", ohlcv_list)

        # Validate signal structure
        assert signal.asset == "BTCUSDT"
        assert signal.narm_score >= 0, "NARM score must be non-negative"
        assert signal.narm_score <= 100, "NARM score must be ≤ 100"

        # Validate all component scores
        assert signal.narrative_strength is not None
        assert signal.adoption_velocity is not None
        assert signal.capital_rotation is not None

        print(f"\nJan 2025 NARM Analysis:")
        print(f"  Combined Score: {signal.narm_score:.1f}/100")
        print(f"  Rotation Candidate: {'YES' if signal.narm_score >= 65 else 'NO'}")
        print(f"  Narrative: {signal.narrative_strength:.1f}")
        print(f"  Adoption: {signal.adoption_velocity:.1f}")
        print(f"  Capital Rotation: {signal.capital_rotation:.1f}")
        print(f"  Valid: {signal.rotation_valid}")

    def test_narm_on_full_btc_range_2020_2025(self):
        """
        Full validation: 2020-2025 BTCUSDT through NARM.

        Validates:
        - Collector loads 2192 historical candles
        - NARM engine processes full range
        - Score distribution makes sense
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = NARMEngine()

        # Full historical data
        ohlcv_list = collector.fetch(start_year=2020, start_month=1,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 2100, f"Expected ~2192 candles, got {len(ohlcv_list)}"

        # Run through NARM engine
        signal = engine.scan("BTCUSDT", ohlcv_list)

        # Full range should be processable
        assert signal.narm_score >= 0
        assert signal.narm_score <= 100

        print(f"\nFull Range NARM Analysis:")
        print(f"  Candles: {len(ohlcv_list)}")
        print(f"  Combined Score: {signal.narm_score:.1f}/100")
        print(f"  Valid: {signal.rotation_valid}")

    def test_narm_time_series_analysis(self):
        """
        Validation: Track NARM rotation signals over time.

        Tests:
        - Rolling 60-day window NARM scoring
        - Identify periods of rotation activity
        - Score variance indicates detection working
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = NARMEngine()

        # Fetch last 180 days (2 quarters)
        ohlcv_list = collector.fetch(start_year=2024, start_month=7,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 180, f"Expected ≥180 candles, got {len(ohlcv_list)}"

        # Sliding 60-day window
        window_size = 60
        scores = []

        for i in range(len(ohlcv_list) - window_size):
            window_data = ohlcv_list[i:i + window_size]
            signal = engine.scan("BTCUSDT", window_data)
            scores.append(signal.narm_score)

        assert len(scores) > 0, "Should generate sliding window scores"

        # Score distribution
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        rotation_candidates = sum(1 for s in scores if s >= 65)

        print(f"\nTime Series NARM (60-day windows, {len(scores)} windows):")
        print(f"  Avg Score: {avg_score:.1f}")
        print(f"  Range: {min_score:.1f} - {max_score:.1f}")
        print(f"  Rotation candidates (≥65): {rotation_candidates}/{len(scores)}")

        # Validate variance exists (not flat)
        assert max_score > min_score, "Score distribution should vary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
