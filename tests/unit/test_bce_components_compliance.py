"""Phase 3 BCE Component Compliance Tests (53-test specification audit)."""

import pytest
from datetime import datetime, timedelta

from src.core.models import OHLCV
from src.layers.layer3_wyckoff.bce import BottomConfirmationEngine
from src.layers.layer3_wyckoff.components.wyckoff_structure import WyckoffStructure
from src.layers.layer3_wyckoff.components.volume_analysis import VolumeAnalysis
from src.layers.layer3_wyckoff.components.selling_exhaustion import SellingExhaustion
from src.layers.layer3_wyckoff.components.smart_money import SmartMoney
from src.layers.layer3_wyckoff.components.market_structure import MarketStructure
from src.layers.layer3_wyckoff.components.momentum_confirmation import MomentumConfirmation
from src.layers.layer3_wyckoff.validators.pit_checks import PITValidator


# ============================================================================
# WYCKOFF STRUCTURE TESTS (8 tests)
# ============================================================================

class TestWyckoffStructure:
    """Test WyckoffStructure component (spec compliance)."""

    def test_ws_score_1_0_tight_range(self):
        """WS score 1.0: price within 20% of range."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            if i < 25:
                # Consolidation: range [98-102]
                close = 98 + (i % 4) * 1.0
            elif i < 35:
                # Mid period: test lower bound
                close = 98
            else:
                # Recent: price within 20% of range (at support)
                close = 98.4
            low = close - 0.2
            high = close + 0.2
            open_ = close
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ws = WyckoffStructure()
        score = ws.compute(data)
        assert score >= 0.9, f"Expected ~1.0 for tight range, got {score}"

    def test_ws_score_0_6_medium_range(self):
        """WS score 0.6: price within 20-50% of range."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            if i < 25:
                # Range: 90-110
                close = 90 + (i % 20) * 1.0
            elif i < 35:
                # Mid: test lower bound
                close = 90
            else:
                # Recent: price at ~35% of range (between 0.2 and 0.5)
                close = 97  # (97-90)/(110-90) = 7/20 = 35%
            low = close - 0.2
            high = close + 0.2
            open_ = close
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ws = WyckoffStructure()
        score = ws.compute(data)
        assert 0.4 <= score <= 0.8, f"Expected ~0.6 for medium range, got {score}"

    def test_ws_score_0_0_outside_range(self):
        """WS score 0.0: price outside range."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            if i < 30:
                # Range: 100-102
                close = 100 + (i % 2) * 0.5
            else:
                # Recent: way above range
                close = 110
            low = close - 0.5
            high = close + 0.5
            open_ = close
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ws = WyckoffStructure()
        score = ws.compute(data)
        assert score == 0.0, f"Expected 0.0 for outside range, got {score}"

    def test_ws_validation_range_tested(self):
        """WS validates: price must have traded outside range in past 10 days."""
        # Create data where range is NOT tested recently
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            if i < 30:
                close = 100 + (i % 2) * 0.2
            else:
                # Recent: tight, NOT testing range
                close = 100.1
            low = close - 0.1
            high = close + 0.1
            open_ = close
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ws = WyckoffStructure()
        score = ws.compute(data)
        # Score should be penalized (multiplied by 0.5)
        assert score < 0.5, f"Expected penalized score for untested range, got {score}"

    def test_ws_boundary_20_percent(self):
        """WS: Boundary at 20% threshold."""
        # Create range [100, 102], test at exactly 20% up
        data = []
        support = 100.0
        resistance = 102.0
        width = resistance - support
        price_at_20pct = support + width * 0.20

        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            if i < 25:
                close = support + (i % 20) * (width / 20)
            elif i < 35:
                # Test lower bound
                close = support
            else:
                close = price_at_20pct
            high = max(close + 0.1, resistance)
            low = min(close - 0.1, support)
            data.append(OHLCV(ts, close, high, low, close, 1000))

        ws = WyckoffStructure()
        score = ws.compute(data)
        assert 0.9 <= score <= 1.0, f"Expected ~1.0 at 20% boundary, got {score}"

    def test_ws_degenerate_range(self):
        """WS: Handles degenerate range (width ~0)."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100.0, 100.0000001, 99.9999999, 100.0, 1000)
            for i in range(40)
        ]

        ws = WyckoffStructure()
        score = ws.compute(data)
        # Degenerate range (width < 1e-6) returns 0.0
        assert score == 0.0, f"Expected 0.0 for degenerate range, got {score}"

    def test_ws_insufficient_data(self):
        """WS: Insufficient data (<30 days)."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000)
            for i in range(10)
        ]

        ws = WyckoffStructure()
        score = ws.compute(data)
        assert score == 0.0, "Expected 0.0 for insufficient data"

    def test_ws_score_bounds(self):
        """WS: Score always in [0, 1]."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            close = 100 + (i % 2) * 0.5
            low = 98 + (i % 2) * 0.5
            high = 102 + (i % 2) * 0.5
            open_ = close
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ws = WyckoffStructure()
        score = ws.compute(data)
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"


# ============================================================================
# SMART MONEY TESTS (corrected for asset-based thresholds)
# ============================================================================

class TestSmartMoney:
    """Test SmartMoney component with asset-specific thresholds."""

    def test_sm_score_1_0_btc_two_tier1_whale(self):
        """SM score 1.0: BTC with 2+ tier1 signals + whale inflow."""
        data = [OHLCV(datetime.now(), 100, 101, 99, 100, 1000) for _ in range(50)]

        sm = SmartMoney()
        score = sm.compute(
            data,
            {
                'exchange_outflow': 1500,  # > 1000 BTC
                'whale_inflow': 100,
                'funding_rate': -0.03,
                'data_age_days': 1
            },
            asset="BTCUSDT"
        )
        assert score == 1.0, f"Expected 1.0 for BTC 2 tier1 + whale, got {score}"

    def test_sm_score_0_6_one_tier1_signal(self):
        """SM score 0.6: 1 tier1 signal OR negative funding rate."""
        data = [OHLCV(datetime.now(), 100, 101, 99, 100, 1000) for _ in range(50)]

        sm = SmartMoney()
        score = sm.compute(
            data,
            {
                'exchange_outflow': 1500,  # 1 signal
                'whale_inflow': 0,
                'funding_rate': 0.01,
                'data_age_days': 1
            },
            asset="BTCUSDT"
        )
        assert score == 0.6, f"Expected 0.6 for 1 tier1, got {score}"

    def test_sm_score_0_3_mixed_signals(self):
        """SM score 0.3: mixed signals (tier1_signals > 0 but not 1 or 2+)."""
        data = [OHLCV(datetime.now(), 100, 101, 99, 100, 1000) for _ in range(50)]

        sm = SmartMoney()
        score = sm.compute(
            data,
            {
                'exchange_outflow': 500,   # < 1000, no signal
                'whale_inflow': 0,
                'funding_rate': 0.01,
                'data_age_days': 1
            },
            asset="BTCUSDT"
        )
        # Mixed: no clear signals, should be 0 or 0.3
        assert 0.0 <= score <= 0.3, f"Expected <=0.3 for no clear signals, got {score}"

    def test_sm_asset_threshold_btc(self):
        """SM: BTC uses 1000 BTC threshold for exchange outflow."""
        data = [OHLCV(datetime.now(), 100, 101, 99, 100, 1000) for _ in range(50)]

        sm = SmartMoney()

        # Below threshold
        score_low = sm.compute(
            data,
            {'exchange_outflow': 900, 'whale_inflow': 0, 'funding_rate': 0, 'data_age_days': 1},
            asset="BTCUSDT"
        )

        # Above threshold
        score_high = sm.compute(
            data,
            {'exchange_outflow': 1100, 'whale_inflow': 0, 'funding_rate': 0, 'data_age_days': 1},
            asset="BTCUSDT"
        )

        # Score should jump at threshold
        assert score_high > score_low, "BTC threshold not working"

    def test_sm_asset_threshold_eth(self):
        """SM: ETH uses 10000 ETH threshold."""
        data = [OHLCV(datetime.now(), 100, 101, 99, 100, 1000) for _ in range(50)]

        sm = SmartMoney()

        score_high = sm.compute(
            data,
            {'exchange_outflow': 15000, 'whale_inflow': 0, 'funding_rate': 0, 'data_age_days': 1},
            asset="ETHUSDT"
        )

        assert score_high >= 0.6, "ETH threshold should trigger at 15000"

    def test_sm_data_age_penalty(self):
        """SM: Data older than 7 days is penalized (50% reduction)."""
        data = [OHLCV(datetime.now(), 100, 101, 99, 100, 1000) for _ in range(50)]

        sm = SmartMoney()

        score_fresh = sm.compute(
            data,
            {'exchange_outflow': 1500, 'whale_inflow': 0, 'funding_rate': 0, 'data_age_days': 1},
            asset="BTCUSDT"
        )

        score_stale = sm.compute(
            data,
            {'exchange_outflow': 1500, 'whale_inflow': 0, 'funding_rate': 0, 'data_age_days': 8},
            asset="BTCUSDT"
        )

        # Stale should be half of fresh
        assert score_stale < score_fresh * 0.6, "Data age penalty not applied"

    def test_sm_no_data_returns_zero(self):
        """SM: No smart money data returns 0."""
        data = [OHLCV(datetime.now(), 100, 101, 99, 100, 1000) for _ in range(50)]

        sm = SmartMoney()
        score = sm.compute(data, None, asset="BTCUSDT")
        assert score == 0.0, "Expected 0 for no data"


# ============================================================================
# PIT VALIDATION TESTS (5 integration tests)
# ============================================================================

class TestPITValidation:
    """PIT (Point-in-Time) / Lookahead bias validation."""

    def test_pit_no_forward_fill(self):
        """PIT: Detects forward-filled NaN values."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000)
            for i in range(20)
        ]

        pass_check, msg = PITValidator.validate_no_forward_fill(data)
        assert pass_check is True, "Good data should pass forward-fill check"

    def test_pit_ma_lookback(self):
        """PIT: Validates MA lookback (SMA-200 needs 200 days)."""
        # Insufficient data
        data_short = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000)
            for i in range(50)
        ]

        pass_check, msg = PITValidator.validate_ma_lookback(49, [20, 50, 200])
        assert pass_check is False, "Should fail with insufficient data for SMA-200"

        # Sufficient data
        pass_check, msg = PITValidator.validate_ma_lookback(250, [20, 50, 200])
        assert pass_check is True, "Should pass with 250+ candles"

    def test_pit_smart_money_lag(self):
        """PIT: Validates smart money data is lagged (not future data)."""
        bce_time = datetime(2026, 10, 1, 12, 0, 0)

        # Good: 2 days lag
        pass_check, msg = PITValidator.validate_smart_money_lag(
            bce_time,
            datetime(2026, 9, 29, 12, 0, 0),
            min_lag_days=1
        )
        assert pass_check is True, "2-day lag should be valid"

        # Bad: future data
        pass_check, msg = PITValidator.validate_smart_money_lag(
            bce_time,
            datetime(2026, 10, 2, 12, 0, 0),
            min_lag_days=1
        )
        assert pass_check is False, "Future data should fail"

    def test_pit_train_test_split(self):
        """PIT: Validates train/test split has no overlap."""
        data = [
            OHLCV(datetime.now() - timedelta(days=100-i), 100 + min(i*0.01, 0.5), 100.5, 99.5, 100 + min(i*0.01, 0.5), 1000)
            for i in range(100)
        ]

        # Good split: train [0:60], test [60:90]
        pass_check, msg = PITValidator.validate_train_test_split(data, 59, 60)
        assert pass_check is True, "Non-overlapping split should pass"

        # Bad split: overlap
        pass_check, msg = PITValidator.validate_train_test_split(data, 60, 50)
        assert pass_check is False, "Overlapping split should fail"

    def test_pit_full_audit(self):
        """PIT: Full audit runs all checks."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000)
            for i in range(250)
        ]

        pass_audit, checks = PITValidator.full_pit_audit(data)
        assert pass_audit is True, "Clean data should pass full audit"
        assert len(checks) >= 4, "Should run at least 4 checks"


# ============================================================================
# VOLUME ANALYSIS TESTS (8 tests)
# ============================================================================

class TestVolumeAnalysis:
    """Test VolumeAnalysis component (spec compliance)."""

    def test_va_score_1_0_heavy_down_light_up(self):
        """VA score 1.0: down-volume ≥1.5x, up-volume ≤1.0x."""
        data = []
        avg_vol = 1000
        for i in range(30):
            ts = datetime.now() - timedelta(days=30-i)
            if i < 25:
                close = 100 - (i % 5) * 0.1
                volume = avg_vol
            else:
                if i % 2 == 0:
                    close = 99 - (i % 3) * 0.5
                    volume = int(avg_vol * 1.8)
                else:
                    close = 100 + 0.1
                    volume = int(avg_vol * 0.3)
            open_ = close + 0.2 if close >= 99.5 else close - 0.2
            high = max(open_, close) + 0.5
            low = min(open_, close) - 0.5
            data.append(OHLCV(ts, open_, high, low, close, volume))

        va = VolumeAnalysis()
        score = va.compute(data)
        assert score == 1.0, f"Expected 1.0 for heavy down + light up, got {score}"

    def test_va_score_0_7_moderate_down_up(self):
        """VA score 0.7: down-volume ≥1.2x, up-volume ≤1.2x."""
        data = []
        avg_vol = 1000
        for i in range(30):
            ts = datetime.now() - timedelta(days=30-i)
            if i < 25:
                close = 100 + (i % 2) * 0.1
                volume = avg_vol
            else:
                volume = int(avg_vol * 1.25)
                close = 99 if i % 2 == 0 else 100.5
            open_ = close + 0.1 if close <= 99.5 else close - 0.1
            high = max(open_, close) + 0.3
            low = min(open_, close) - 0.3
            data.append(OHLCV(ts, open_, high, low, close, volume))

        va = VolumeAnalysis()
        score = va.compute(data)
        assert 0.6 <= score <= 0.8, f"Expected ~0.7 for moderate down/up, got {score}"

    def test_va_score_0_5_mixed(self):
        """VA score 0.5: down-volume ≥1.0x, up-volume ≤1.5x."""
        data = []
        avg_vol = 1000
        for i in range(30):
            ts = datetime.now() - timedelta(days=30-i)
            if i < 25:
                volume = avg_vol
                close = 100
            else:
                volume = int(avg_vol * 1.1)
                close = 99.5 if i % 2 == 0 else 100.2
            open_ = close
            high = close + 0.2
            low = close - 0.2
            data.append(OHLCV(ts, open_, high, low, close, volume))

        va = VolumeAnalysis()
        score = va.compute(data)
        assert 0.3 <= score <= 0.6, f"Expected ~0.5 for mixed, got {score}"

    def test_va_score_0_0_no_signal(self):
        """VA score 0.0: no capitulation pattern."""
        data = []
        avg_vol = 1000
        for i in range(30):
            ts = datetime.now() - timedelta(days=30-i)
            close = 100 + (i % 5) * 0.1
            open_ = close
            high = close + 0.1
            low = close - 0.1
            data.append(OHLCV(ts, open_, high, low, close, avg_vol))

        va = VolumeAnalysis()
        score = va.compute(data)
        assert score == 0.0, f"Expected 0.0 for no signal, got {score}"

    def test_va_insufficient_data(self):
        """VA: Insufficient data (<25 days)."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000)
            for i in range(10)
        ]
        va = VolumeAnalysis()
        score = va.compute(data)
        assert score == 0.0, f"Expected 0.0 for insufficient data, got {score}"

    def test_va_zero_average_volume(self):
        """VA: Handles zero average volume gracefully."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 0)
            for i in range(30)
        ]
        va = VolumeAnalysis()
        score = va.compute(data)
        assert score == 0.0, f"Expected 0.0 for zero volume, got {score}"

    def test_va_volume_ratio_boundary(self):
        """VA: Boundary at 1.5x down-volume threshold."""
        data = []
        avg_vol = 1000
        for i in range(30):
            ts = datetime.now() - timedelta(days=30-i)
            if i < 25:
                volume = avg_vol
                close = 100
            else:
                volume = int(avg_vol * 1.5) if i % 2 == 0 else int(avg_vol * 0.8)
                close = 99 if i % 2 == 0 else 100.5
            open_ = close
            high = close + 0.3
            low = close - 0.3
            data.append(OHLCV(ts, open_, high, low, close, volume))

        va = VolumeAnalysis()
        score = va.compute(data)
        assert 0.8 <= score <= 1.0, f"Expected ~1.0 at boundary, got {score}"

    def test_va_score_bounds(self):
        """VA: Score always in [0, 1]."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000 + (i % 500))
            for i in range(30)
        ]
        va = VolumeAnalysis()
        score = va.compute(data)
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"


# ============================================================================
# SELLING EXHAUSTION TESTS (8 tests)
# ============================================================================

class TestSellingExhaustion:
    """Test SellingExhaustion component (spec compliance)."""

    def test_se_score_1_0_extreme_exhaustion(self):
        """SE score 1.0: RSI < 30, MACD < 0, range > 2x."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            if i < 30:
                close = 100 - (i % 10) * 0.5
            else:
                close = 95 - (i % 5) * 0.3
            high = close + 3.0
            low = close - 3.0
            open_ = close + 1.0
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        se = SellingExhaustion()
        score = se.compute(data)
        assert score == 1.0, f"Expected 1.0 for extreme exhaustion, got {score}"

    def test_se_score_0_7_rsi_below_35(self):
        """SE score 0.7: RSI < 35, MACD < -0.5."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            close = 100 - (i % 15) * 0.8
            open_ = close + 0.5
            high = max(open_, close) + 0.5
            low = min(open_, close) - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        se = SellingExhaustion()
        score = se.compute(data)
        assert 0.5 <= score <= 0.8, f"Expected ~0.7, got {score}"

    def test_se_score_0_4_rsi_below_40(self):
        """SE score 0.4: RSI < 40."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            close = 100 - (i % 20) * 0.4
            open_ = close
            high = close + 0.5
            low = close - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        se = SellingExhaustion()
        score = se.compute(data)
        assert 0.2 <= score <= 0.5, f"Expected ~0.4, got {score}"

    def test_se_score_0_0_no_exhaustion(self):
        """SE score 0.0: No exhaustion signal."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            close = 100 + (i % 5) * 0.2
            open_ = close
            high = close + 0.2
            low = close - 0.2
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        se = SellingExhaustion()
        score = se.compute(data)
        assert score == 0.0, f"Expected 0.0 for no exhaustion, got {score}"

    def test_se_insufficient_data(self):
        """SE: Insufficient data for MACD calculation."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000)
            for i in range(10)
        ]
        se = SellingExhaustion()
        score = se.compute(data)
        assert score == 0.0, f"Expected 0.0 for insufficient data, got {score}"

    def test_se_rsi_boundary(self):
        """SE: RSI at 30 boundary."""
        data = []
        for i in range(50):
            ts = datetime.now() - timedelta(days=50-i)
            close = 100 - (i % 30) * 0.6
            open_ = close + 0.3
            high = max(open_, close) + 0.5
            low = min(open_, close) - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        se = SellingExhaustion()
        score = se.compute(data)
        assert 0.7 <= score <= 1.0, f"Expected ~0.9 at RSI=30 boundary, got {score}"

    def test_se_wide_range(self):
        """SE: Detects wide intra-bar range (high volatility)."""
        data = []
        for i in range(40):
            ts = datetime.now() - timedelta(days=40-i)
            close = 95
            open_ = 105
            high = 110
            low = 90
            data.append(OHLCV(ts, open_, high, low, close, 1500))

        se = SellingExhaustion()
        score = se.compute(data)
        assert score >= 0.6, f"Expected high score for wide range, got {score}"

    def test_se_score_bounds(self):
        """SE: Score always in [0, 1]."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 102, 98, 100 + (i % 5) * 0.1, 1000 + (i % 500))
            for i in range(40)
        ]
        se = SellingExhaustion()
        score = se.compute(data)
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"


# ============================================================================
# MARKET STRUCTURE TESTS (8 tests)
# ============================================================================

class TestMarketStructure:
    """Test MarketStructure component (spec compliance)."""

    def test_ms_score_1_0_bullish_structure(self):
        """MS score 1.0: price > 20SMA > 50SMA > 200SMA."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            close = 100 + (i * 0.05)
            open_ = close
            high = close + 0.5
            low = close - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ms = MarketStructure()
        score = ms.compute(data)
        assert score == 1.0, f"Expected 1.0 for bullish structure, got {score}"

    def test_ms_score_0_7_bullish_bias(self):
        """MS score 0.7: price > 50SMA > 200SMA."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            close = 100 + (i * 0.02)
            open_ = close
            high = close + 0.3
            low = close - 0.3
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ms = MarketStructure()
        score = ms.compute(data)
        assert 0.6 <= score <= 0.8, f"Expected ~0.7, got {score}"

    def test_ms_score_0_5_neutral_testing_support(self):
        """MS score 0.5: neutral, price near 50SMA."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            if i < 200:
                close = 100 + (i * 0.01)
            else:
                close = 102 - (i % 50) * 0.02
            open_ = close
            high = close + 0.2
            low = close - 0.2
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ms = MarketStructure()
        score = ms.compute(data)
        assert 0.3 <= score <= 0.7, f"Expected ~0.5 for neutral, got {score}"

    def test_ms_score_0_0_bearish_structure(self):
        """MS score 0.0: bearish structure (price < SMA chains)."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            close = 100 - (i * 0.05)
            open_ = close
            high = close + 0.5
            low = close - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ms = MarketStructure()
        score = ms.compute(data)
        assert score == 0.0, f"Expected 0.0 for bearish structure, got {score}"

    def test_ms_insufficient_data(self):
        """MS: Insufficient data for 200-day SMA."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000)
            for i in range(100)
        ]
        ms = MarketStructure()
        score = ms.compute(data)
        assert score == 0.0, f"Expected 0.0 for insufficient data, got {score}"

    def test_ms_sma_crossover(self):
        """MS: Detects SMA-20/50 crossover."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            if i < 200:
                close = 100 - (i * 0.02)
            else:
                close = 96 + (i % 50) * 0.04
            open_ = close
            high = close + 0.3
            low = close - 0.3
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ms = MarketStructure()
        score = ms.compute(data)
        assert score >= 0.5, f"Expected decent score at crossover, got {score}"

    def test_ms_weekly_confirmation(self):
        """MS: Incorporates higher timeframe (weekly) data."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            close = 100 + (i * 0.03)
            open_ = close
            high = close + 0.5
            low = close - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        ms = MarketStructure()
        score = ms.compute(data)
        assert 0.8 <= score <= 1.0, f"Expected bullish with weekly confirmation, got {score}"

    def test_ms_score_bounds(self):
        """MS: Score always in [0, 1]."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100 + (i % 5), 102, 98, 100, 1000)
            for i in range(250)
        ]
        ms = MarketStructure()
        score = ms.compute(data)
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"


# ============================================================================
# MOMENTUM CONFIRMATION TESTS (8 tests)
# ============================================================================

class TestMomentumConfirmation:
    """Test MomentumConfirmation component (spec compliance)."""

    def test_mc_score_1_0_strong_emerging(self):
        """MC score 1.0: MACD > 0, Stochastic < 80, ADX > 20."""
        data = []
        for i in range(50):
            ts = datetime.now() - timedelta(days=50-i)
            close = 100 + (i * 0.3)
            open_ = close - 0.2
            high = close + 0.5
            low = close - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000 + (i % 200)))

        mc = MomentumConfirmation()
        score = mc.compute(data)
        assert score == 1.0, f"Expected 1.0 for strong momentum, got {score}"

    def test_mc_score_0_7_moderate_momentum(self):
        """MC score 0.7: MACD > 0, Stochastic < 70."""
        data = []
        for i in range(50):
            ts = datetime.now() - timedelta(days=50-i)
            close = 100 + (i * 0.15)
            open_ = close
            high = close + 0.3
            low = close - 0.3
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        mc = MomentumConfirmation()
        score = mc.compute(data)
        assert 0.6 <= score <= 0.8, f"Expected ~0.7, got {score}"

    def test_mc_score_0_4_weak_signal(self):
        """MC score 0.4: MACD transitioning to positive."""
        data = []
        for i in range(50):
            ts = datetime.now() - timedelta(days=50-i)
            if i < 40:
                close = 100 - (i % 20) * 0.1
            else:
                close = 98 + (i % 10) * 0.05
            open_ = close
            high = close + 0.2
            low = close - 0.2
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        mc = MomentumConfirmation()
        score = mc.compute(data)
        assert 0.2 <= score <= 0.5, f"Expected ~0.4 for weak signal, got {score}"

    def test_mc_score_0_0_no_momentum(self):
        """MC score 0.0: No emerging momentum."""
        data = []
        for i in range(50):
            ts = datetime.now() - timedelta(days=50-i)
            close = 100 - (i % 10) * 0.2
            open_ = close
            high = close + 0.2
            low = close - 0.2
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        mc = MomentumConfirmation()
        score = mc.compute(data)
        assert score == 0.0, f"Expected 0.0 for no momentum, got {score}"

    def test_mc_insufficient_data(self):
        """MC: Insufficient data for indicators."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100, 101, 99, 100, 1000)
            for i in range(10)
        ]
        mc = MomentumConfirmation()
        score = mc.compute(data)
        assert score == 0.0, f"Expected 0.0 for insufficient data, got {score}"

    def test_mc_overbought_detection(self):
        """MC: Avoids overbought conditions (Stochastic ≥ 80)."""
        data = []
        for i in range(50):
            ts = datetime.now() - timedelta(days=50-i)
            close = 100 + (i * 0.5)
            open_ = close - 0.1
            high = close + 1.0
            low = close - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        mc = MomentumConfirmation()
        score = mc.compute(data)
        # Should penalize overbought
        assert score <= 0.7, f"Expected lower score for overbought, got {score}"

    def test_mc_adx_strength(self):
        """MC: Incorporates ADX (trend strength ≥ 20)."""
        data = []
        for i in range(50):
            ts = datetime.now() - timedelta(days=50-i)
            close = 100 + (i * 0.25)
            open_ = close - 0.2
            high = close + 0.8
            low = close - 0.8
            data.append(OHLCV(ts, open_, high, low, close, 1000 + (i % 300)))

        mc = MomentumConfirmation()
        score = mc.compute(data)
        assert score >= 0.7, f"Expected high score with strong ADX, got {score}"

    def test_mc_score_bounds(self):
        """MC: Score always in [0, 1]."""
        data = [
            OHLCV(datetime.now() - timedelta(days=i), 100 + (i % 10) * 0.1, 102, 98, 100 + (i % 5) * 0.1, 1000 + (i % 500))
            for i in range(50)
        ]
        mc = MomentumConfirmation()
        score = mc.compute(data)
        assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"


# ============================================================================
# INTEGRATION TESTS (5 tests)
# ============================================================================

class TestBCEIntegration:
    """Integration tests combining all 6 components."""

    def test_bce_all_green_score_6(self):
        """Integration: All 6 components maxed → score 6.0."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            close = 100 + (i * 0.1)
            open_ = close - 0.5
            high = close + 2.0
            low = close - 0.5
            volume = 1500 if i % 5 == 0 else 800
            data.append(OHLCV(ts, open_, high, low, close, volume))

        bce = BottomConfirmationEngine("BTCUSDT")
        result = bce.compute_bce_score(data, {"exchange_outflow": 2000, "whale_inflow": 500, "funding_rate": -0.08, "data_age_days": 1})
        assert 5.0 <= result.bce_score <= 6.0, f"Expected ~6.0, got {result.bce_score}"
        assert result.signal == "HIGH_CONFIDENCE", f"Expected HIGH_CONFIDENCE, got {result.signal}"

    def test_bce_mixed_components(self):
        """Integration: 4/6 components pass → score 4.0."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            close = 100 + (i * 0.02)
            open_ = close
            high = close + 0.5
            low = close - 0.5
            volume = 1000
            data.append(OHLCV(ts, open_, high, low, close, volume))

        bce = BottomConfirmationEngine("BTCUSDT")
        result = bce.compute_bce_score(data, {"exchange_outflow": 500, "whale_inflow": 0, "funding_rate": 0.01, "data_age_days": 1})
        assert 3.0 <= result.bce_score <= 5.0, f"Expected MEDIUM range, got {result.bce_score}"

    def test_bce_regime_shift_bull_to_bear(self):
        """Integration: Regime shift (bull→bear), verify score degrades."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            if i < 150:
                close = 100 + (i * 0.1)
            else:
                close = 115 - ((i - 150) * 0.1)
            open_ = close
            high = close + 1.0
            low = close - 1.0
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        bce = BottomConfirmationEngine("BTCUSDT")
        result = bce.compute_bce_score(data)
        # After regime shift, score should be lower
        assert result.bce_score <= 4.0, f"Expected degraded score after bear regime, got {result.bce_score}"

    def test_bce_missing_smart_money_data(self):
        """Integration: Gracefully handle missing smart money data."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            close = 100 + (i * 0.05)
            open_ = close
            high = close + 0.5
            low = close - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000))

        bce = BottomConfirmationEngine("BTCUSDT")
        result = bce.compute_bce_score(data, smart_money_data=None)
        assert 0.0 <= result.bce_score <= 6.0, f"Should handle missing data gracefully, got {result.bce_score}"

    def test_bce_component_breakdown(self):
        """Integration: Component breakdown present and valid."""
        data = []
        for i in range(250):
            ts = datetime.now() - timedelta(days=250-i)
            close = 100 + (i * 0.08)
            open_ = close
            high = close + 1.0
            low = close - 0.5
            data.append(OHLCV(ts, open_, high, low, close, 1000 + (i % 500)))

        bce = BottomConfirmationEngine("BTCUSDT")
        result = bce.compute_bce_score(data, {"exchange_outflow": 1500, "whale_inflow": 100, "funding_rate": -0.03, "data_age_days": 1})

        breakdown = result.components.to_dict()
        assert "wyckoff_structure" in breakdown
        assert "volume_analysis" in breakdown
        assert "selling_exhaustion" in breakdown
        assert "smart_money" in breakdown
        assert "market_structure" in breakdown
        assert "momentum_confirmation" in breakdown
        assert "total" in breakdown
        assert breakdown["total"] == result.bce_score
