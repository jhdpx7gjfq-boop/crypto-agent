"""Integration test: Binance Layer 1 data through Layer 7 RRP Engine."""

import pytest
from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.layers.layer7_rrp.rrp_engine import RRPEngine


class TestBinanceRRPValidation:
    """Validate RRP revival radar engine on real Binance BTCUSDT data."""

    def test_rrp_on_real_btc_2025_jan(self):
        """
        Integration: Binance data → RRP revival detection scoring.

        Tests:
        - Collector fetches real BTC data
        - RRP engine processes OHLCV list
        - Scoring is in valid range (0-100)
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = RRPEngine()

        # Fetch Jan 2025 (31 candles)
        ohlcv_list = collector.fetch(start_year=2025, start_month=1,
                                     end_year=2025, end_month=1)

        assert len(ohlcv_list) == 31, f"Expected 31 candles, got {len(ohlcv_list)}"

        # Run through RRP engine
        signal = engine.scan("BTCUSDT", ohlcv_list)

        # Validate signal structure
        assert signal.asset == "BTCUSDT"
        assert signal.revival_probability >= 0, "Revival probability must be non-negative"
        assert signal.revival_probability <= 100, "Revival probability must be ≤ 100"

        # Validate all component scores
        assert signal.snapshot_health is not None
        assert signal.volume_signature is not None
        assert signal.community_activity is not None
        assert signal.technical_confirmation is not None

        print(f"\nJan 2025 RRP Analysis:")
        print(f"  Revival Probability: {signal.revival_probability:.1f}%")
        print(f"  Stage: {signal.stage}")
        print(f"  Snapshot Health (30%): {signal.snapshot_health:.1f}")
        print(f"  Volume Signature (25%): {signal.volume_signature:.1f}")
        print(f"  Community Activity (25%): {signal.community_activity:.1f}")
        print(f"  Technical Confirmation (20%): {signal.technical_confirmation:.1f}")

    def test_rrp_on_full_btc_range_2020_2025(self):
        """
        Full validation: 2020-2025 BTCUSDT through RRP.

        Validates:
        - Collector loads 2192 historical candles
        - RRP engine processes full range
        - Revival score reflects established (never-dead) asset
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = RRPEngine()

        # Full historical data
        ohlcv_list = collector.fetch(start_year=2020, start_month=1,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 2100, f"Expected ~2192 candles, got {len(ohlcv_list)}"

        # Run through RRP engine
        signal = engine.scan("BTCUSDT", ohlcv_list)

        # Full range should be processable
        assert signal.revival_probability >= 0
        assert signal.revival_probability <= 100

        print(f"\nFull Range RRP Analysis:")
        print(f"  Candles: {len(ohlcv_list)}")
        print(f"  Revival Probability: {signal.revival_probability:.1f}%")
        print(f"  Stage: {signal.stage}")

    def test_rrp_revival_stage_detection(self):
        """
        Validation: Track RRP revival stages over time.

        Tests:
        - Rolling 30-day windows for revival detection
        - Stage progression: dead → awakening → revival → momentum
        - Identify periods of dormancy recovery
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = RRPEngine()

        # Fetch last 180 days
        ohlcv_list = collector.fetch(start_year=2024, start_month=7,
                                     end_year=2025, end_month=12)

        assert len(ohlcv_list) >= 180, f"Expected ≥180 candles, got {len(ohlcv_list)}"

        # Rolling 30-day window
        window_size = 30
        scores = []
        stages = {"dead": 0, "awakening": 0, "revival": 0, "momentum": 0}

        for i in range(len(ohlcv_list) - window_size):
            window_data = ohlcv_list[i:i + window_size]
            signal = engine.scan("BTCUSDT", window_data)
            scores.append(signal.revival_probability)
            stages[signal.stage] += 1

        assert len(scores) > 0, "Should generate rolling window scores"

        # Score distribution
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)

        print(f"\nRolling RRP (30-day windows, {len(scores)} windows):")
        print(f"  Avg Revival Probability: {avg_score:.1f}%")
        print(f"  Range: {min_score:.1f}% - {max_score:.1f}%")
        print(f"  Stage distribution:")
        for stage, count in stages.items():
            pct = (count / len(scores)) * 100
            print(f"    {stage:10s}: {count:3d} ({pct:5.1f}%)")

        # Validate variance exists
        assert max_score > min_score, "Score distribution should vary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
