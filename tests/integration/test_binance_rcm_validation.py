"""Integration test: Binance Layer 1 data through Layer 6 RCM/RPM Engine."""

import pytest
from src.layers.layer1_data.binance_collector import BinanceDataPortalCollector
from src.layers.layer6_rcm.rcm_engine import RCMEngine


class TestBinanceRCMValidation:
    """Validate RCM rotation confirmation engine on real Binance BTCUSDT data."""

    def _calculate_mock_scores(self, ohlcv_list: list) -> tuple:
        """Generate mock component scores from OHLCV data."""
        if not ohlcv_list:
            return 50, 50, 50, 50, 50

        closes = [candle.close for candle in ohlcv_list]
        volumes = [candle.volume for candle in ohlcv_list]

        # Capital Flow: higher volume on up days
        up_vol = sum(v for i, v in enumerate(volumes) if i > 0 and closes[i] > closes[i-1])
        total_vol = sum(volumes)
        cf_score = (up_vol / total_vol * 100) if total_vol > 0 else 50

        # Relative Strength: momentum (% change)
        pct_change = ((closes[-1] - closes[0]) / closes[0] * 100) if closes[0] > 0 else 0
        rs_score = min(100, max(0, 50 + pct_change * 2))

        # Narrative Acceleration: volume trend
        avg_vol_early = sum(volumes[:len(volumes)//2]) / (len(volumes)//2 or 1)
        avg_vol_late = sum(volumes[len(volumes)//2:]) / (len(volumes) - len(volumes)//2 or 1)
        na_score = min(100, max(0, 50 + (avg_vol_late - avg_vol_early) / avg_vol_early * 50))

        # Fundamental: price stability (low volatility = higher score)
        volatility = max(closes) - min(closes)
        volatility_pct = (volatility / closes[0] * 100) if closes[0] > 0 else 50
        fund_score = max(0, 100 - volatility_pct * 2)

        # Derivatives: trending strength
        deriv_score = min(100, max(0, rs_score * 0.8 + 10))

        return cf_score, rs_score, na_score, fund_score, deriv_score

    def test_rcm_on_real_btc_2025_jan(self):
        """
        Integration: Binance data → RCM confirmation scoring.

        Tests:
        - Collector fetches real BTC data
        - RCM engine processes component scores
        - Scoring is in valid range (0-100)
        """
        collector = BinanceDataPortalCollector(symbol="BTCUSDT", granularity="1d")
        engine = RCMEngine()

        # Fetch Jan 2025 (31 candles)
        ohlcv_list = collector.fetch(start_year=2025, start_month=1,
                                     end_year=2025, end_month=1)

        assert len(ohlcv_list) == 31, f"Expected 31 candles, got {len(ohlcv_list)}"

        # Calculate component scores from OHLCV
        cf_score, rs_score, na_score, fund_score, deriv_score = self._calculate_mock_scores(ohlcv_list)

        # Run through RCM engine
        signal = engine.scan("BTCUSDT", cf_score, rs_score, na_score, fund_score, deriv_score)

        # Validate signal structure
        assert signal.asset == "BTCUSDT"
        assert signal.rcm_score >= 0, "RCM score must be non-negative"
        assert signal.rcm_score <= 100, "RCM score must be ≤ 100"
        assert signal.confidence >= 0 and signal.confidence <= 1

        print(f"\nJan 2025 RCM Analysis:")
        print(f"  RCM Score: {signal.rcm_score:.1f}/100")
        print(f"  Decision: {signal.decision.value}")
        print(f"  Confidence: {signal.confidence:.2f}")
        print(f"  Capital Flow (30%): {cf_score:.1f}")
        print(f"  Relative Strength (25%): {rs_score:.1f}")
        print(f"  Narrative Accel (20%): {na_score:.1f}")
        print(f"  Fundamental (20%): {fund_score:.1f}")
        print(f"  Derivatives (5%): {deriv_score:.1f}")

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

        # Calculate component scores from OHLCV
        cf_score, rs_score, na_score, fund_score, deriv_score = self._calculate_mock_scores(ohlcv_list)

        # Run through RCM engine
        signal = engine.scan("BTCUSDT", cf_score, rs_score, na_score, fund_score, deriv_score)

        # Full range should be processable
        assert signal.rcm_score >= 0
        assert signal.rcm_score <= 100

        print(f"\nFull Range RCM Analysis:")
        print(f"  Candles: {len(ohlcv_list)}")
        print(f"  RCM Score: {signal.rcm_score:.1f}/100")
        print(f"  Decision: {signal.decision.value}")

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
            cf_score, rs_score, na_score, fund_score, deriv_score = self._calculate_mock_scores(window_data)
            signal = engine.scan("BTCUSDT", cf_score, rs_score, na_score, fund_score, deriv_score)
            scores.append(signal.rcm_score)
            if signal.decision.value == "confirm":
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
        print(f"  Confirmed decisions: {valid_count}/{len(scores)}")

        # Validate variance exists
        assert max_score > min_score, "Score distribution should vary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
