"""Integration test: Binance Layer 1 data through Layer 3 BCE Engine."""

import pytest
from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.layers.layer3_wyckoff.bce_engine import BottomConfirmationEngine


class TestBinanceBCEValidation:
    """Validate BCE engine on real Binance BTCUSDT data."""

    def test_bce_on_real_btc_2025_jan(self):
        """
        Integration: Binance data → BCE scoring.

        Tests:
        - Collector fetches real BTC data
        - BCE engine processes OHLCV list
        - Scoring is in valid range (0-6)
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = BottomConfirmationEngine()

        # Fetch Jan 2025 (31 candles)
        ohlcv_list = collector.fetch(start_year=2025, start_month=1,
                                     end_year=2025, end_month=1)

        assert len(ohlcv_list) == 31, f"Expected 31 candles, got {len(ohlcv_list)}"

        # Run through BCE
        signal = engine.analyze("BTCUSDT", ohlcv_list)

        # Validate signal structure
        assert signal.asset == "BTCUSDT"
        assert signal.bce_score >= 0, "BCE score must be non-negative"
        assert signal.bce_score <= 6, "BCE score must be ≤ 6"

        # Validate all components are scored
        assert signal.wyckoff_structure is not None
        assert signal.volume_analysis is not None
        assert signal.selling_exhaustion is not None
        assert signal.smart_money_accumulation is not None
        assert signal.market_structure is not None
        assert signal.momentum_confirmation is not None

    def test_bce_on_full_btc_range_2020_2025(self):
        """
        Full validation: 2020-2025 BTCUSDT through BCE.

        Validates:
        - Collector loads 2192 historical candles
        - BCE processes full range
        - Score distribution makes sense
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = BottomConfirmationEngine()

        # Full historical data
        ohlcv_list = collector.fetch(start_year=2020, start_month=1,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 2100, f"Expected ~2192 candles, got {len(ohlcv_list)}"

        # Run through BCE
        signal = engine.analyze("BTCUSDT", ohlcv_list)

        # Full range should be processable
        assert signal.valid is not None
        assert signal.bce_score >= 0
        assert signal.bce_score <= 6

        # Log final state
        print(f"\nFull Range BCE Analysis:")
        print(f"  Candles: {len(ohlcv_list)}")
        print(f"  BCE Score: {signal.bce_score:.2f}/6.0")
        print(f"  Valid: {signal.valid}")

    def test_bce_sliding_window_analysis(self):
        """
        Validation: Run BCE on sliding windows of recent data.

        Tests:
        - 60-day window BCE scoring pattern
        - Multiple windows show score variance
        - Identifies periods of strong/weak confirmation
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = BottomConfirmationEngine()

        # Fetch last 180 days (2 quarters)
        ohlcv_list = collector.fetch(start_year=2024, start_month=7,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 180, f"Expected ≥180 candles, got {len(ohlcv_list)}"

        # Sliding 60-day window
        window_size = 60
        scores = []

        for i in range(len(ohlcv_list) - window_size):
            window_data = ohlcv_list[i:i + window_size]
            signal = engine.analyze("BTCUSDT", window_data)
            scores.append(signal.bce_score)

        assert len(scores) > 0, "Should generate sliding window scores"

        # Score distribution
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)

        print(f"\nSliding Window BCE (60-day, {len(scores)} windows):")
        print(f"  Avg Score: {avg_score:.2f}")
        print(f"  Range: {min_score:.2f} - {max_score:.2f}")
        print(f"  Strong (≥5): {sum(1 for s in scores if s >= 5)} windows")

        # Validate variance exists (not flat)
        assert max_score > min_score, "Score distribution should vary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
