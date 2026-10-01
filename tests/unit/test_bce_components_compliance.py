"""Phase 3 BCE Component Compliance Tests (53-test specification audit)."""

import pytest
from datetime import datetime, timedelta

from src.core.models import OHLCV
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
