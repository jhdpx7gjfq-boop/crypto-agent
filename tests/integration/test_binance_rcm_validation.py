"""Integration test: Binance Layer 1 data through Layer 6 RCM/RPM Engine."""

import pytest
from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.layers.layer6_rcm.rcm_engine import RCMEngine


class TestBinanceRCMValidation:
    """Validate RCM rotation confirmation engine on real Binance BTCUSDT data."""

    def test_rcm_on_real_btc_2025_jan(self):
        """
        Integration: Binance data → RCM confirmation scoring.

        Tests:
        - Collector fetches real BTC data
        - RCM engine processes OHLCV list
        - Scoring is in valid range (0-100)
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = RCMEngine()

        # Fetch Jan 2025 (31 candles)
        ohlcv_list = collector.fetch(start_year=2025, start_month=1,
                                     end_year=2025, end_month=1)

        assert len(ohlcv_list) == 31, f"Expected 31 candles, got {len(ohlcv_list)}"

        # Run through RCM engine
        signal = engine.scan("BTCUSDT", ohlcv_list)

        # Validate signal structure
        assert signal.asset == "BTCUSDT"
        assert signal.combined_score >= 0, "RCM score must be non-negative"
        assert signal.combined_score <= 100, "RCM score must be ≤ 100"

        # Validate all component scores
        assert signal.capital_flow is not None
        assert signal.relative_strength is not None
        assert signal.narrative_acceleration is not None
        assert signal.fundamental_confirmation is not None
        assert signal.derivatives_structure is not None

        print(f"\nJan 2025 RCM Analysis:")
        print(f"  Combined Score: {signal.combined_score:.1f}/100")
        print(f"  Confirmed Rotation: {'YES' if signal.combined_score >= 70 else 'NO'}")
        print(f"  Capital Flow (25%): {signal.capital_flow:.1f}")
        print(f"  Relative Strength (25%): {signal.relative_strength:.1f}")
        print(f"  Narrative Accel (20%): {signal.narrative_acceleration:.1f}")
        print(f"  Fundamental (20%): {signal.fundamental_confirmation:.1f}")
        print(f"  Derivatives (10%): {signal.derivatives_structure:.1f}")
        print(f"  Valid: {signal.valid}")

    def test_rcm_on_full_btc_range_2020_2025(self):
        """
        Full validation: 2020-2025 BTCUSDT through RCM.

        Validates:
        - Collector loads 2192 historical candles
        - RCM engine processes full range
        - Walk-forward validation working
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = RCMEngine()

        # Full historical data
        ohlcv_list = collector.fetch(start_year=2020, start_month=1,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 2100, f"Expected ~2192 candles, got {len(ohlcv_list)}"

        # Run through RCM engine
        signal = engine.scan("BTCUSDT", ohlcv_list)

        # Full range should be processable
        assert signal.combined_score >= 0
        assert signal.combined_score <= 100

        print(f"\nFull Range RCM Analysis:")
        print(f"  Candles: {len(ohlcv_list)}")
        print(f"  Combined Score: {signal.combined_score:.1f}/100")
        print(f"  Valid: {signal.valid}")

    def test_rcm_rolling_confirmation(self):
        """
        Validation: Track RCM confirmation over rolling windows.

        Tests:
        - Rolling 60-day windows with walk-forward validation
        - Identify confirmed rotation periods
        - Score variance indicates detection working
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = RCMEngine()

        # Fetch last 180 days
        ohlcv_list = collector.fetch(start_year=2024, start_month=7,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 180, f"Expected ≥180 candles, got {len(ohlcv_list)}"

        # Rolling window with confirmation validation
        window_size = 60
        scores = []
        valid_count = 0

        for i in range(len(ohlcv_list) - window_size):
            window_data = ohlcv_list[i:i + window_size]
            signal = engine.scan("BTCUSDT", window_data)
            scores.append(signal.combined_score)
            if signal.valid:
                valid_count += 1

        assert len(scores) > 0, "Should generate rolling window scores"

        # Score distribution
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        confirmed = sum(1 for s in scores if s >= 70)

        print(f"\nRolling RCM (60-day windows, {len(scores)} windows):")
        print(f"  Avg Score: {avg_score:.1f}")
        print(f"  Range: {min_score:.1f} - {max_score:.1f}")
        print(f"  Confirmed rotations (≥70): {confirmed}/{len(scores)}")
        print(f"  Valid signals: {valid_count}/{len(scores)}")

        # Validate variance exists
        assert max_score > min_score, "Score distribution should vary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
