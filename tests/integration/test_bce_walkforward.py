"""
Walk-Forward Validation for Phase 3 Component 4.

Tests BCE engine on 2-5 year historical data with proper walk-forward
methodology:
- 50/50 train/test splits
- Out-of-sample validation
- Performance degradation tracking
- Constraint enforcement (trades >= 200, PF > 1.3, DD < 25%)

Note: This is a framework test. Real execution requires historical data
from the Feature Store.
"""

import pytest
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np


@dataclass
class WFVResult:
    """Walk-forward validation result for one window."""
    asset: str
    window_id: int
    start_date: datetime
    end_date: datetime
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime

    # Performance metrics
    train_trades: int
    test_trades: int
    train_profit_factor: float
    test_profit_factor: float
    train_max_drawdown: float
    test_max_drawdown: float
    train_win_rate: float
    test_win_rate: float
    train_sharpe: float
    test_sharpe: float

    # Validation status
    passes_constraints: bool
    constraint_failures: List[str]

    # Degradation analysis
    trade_degradation: float  # Test trades / train trades
    pf_degradation: float  # (Train PF - Test PF) / Train PF
    dd_degradation: float  # (Test DD - Train DD) / Train DD
    wr_degradation: float  # (Train WR - Test WR) / Train WR


@dataclass
class WFVSummary:
    """Summary of walk-forward validation across all windows."""
    asset: str
    num_windows: int
    all_results: List[WFVResult]

    # Pass/fail statistics
    passes: int
    failures: int
    pass_rate: float

    # Average degradation
    avg_trade_degradation: float
    avg_pf_degradation: float
    avg_dd_degradation: float
    avg_wr_degradation: float

    # Stability metrics
    pf_std_dev: float  # Variation in profit factor across windows
    wr_std_dev: float  # Variation in win rate across windows

    # Final verdict
    is_valid: bool  # True if all windows pass constraints and degradation is acceptable


class WalkForwardValidator:
    """
    Validates BCE signals using walk-forward methodology.

    Implements:
    - Multi-window train/test splits (50/50)
    - Constraint checking per window
    - Performance degradation tracking
    - Stability analysis
    """

    # Validation constraints (from Phase 2)
    MIN_TRADES = 200
    MIN_PROFIT_FACTOR = 1.3
    MAX_DRAWDOWN = 0.25
    MIN_WIN_RATE = 0.4

    # Degradation thresholds
    MAX_DEGRADATION = 0.30  # 30% max OOS degradation
    MAX_PF_DEGRADATION = 0.25  # PF drop max 25%
    MAX_DD_DEGRADATION = 0.50  # DD increase max 50%

    def __init__(self, min_window_trades: int = 200):
        """Initialize validator."""
        self.min_window_trades = min_window_trades
        self.results: List[WFVResult] = []

    def validate_asset(
        self,
        asset: str,
        ohlcv_data: List[dict],
        num_windows: int = 4,
        window_overlap: float = 0.0,
    ) -> WFVSummary:
        """
        Validate BCE on asset across multiple windows.

        Args:
            asset: Asset symbol (e.g., 'BTCUSDT')
            ohlcv_data: List of OHLCV dicts with 'timestamp', 'open', 'high', 'low', 'close', 'volume'
            num_windows: Number of walk-forward windows (default 4 = ~4 years in 1-year windows)
            window_overlap: Overlap between windows as fraction (0.0 = no overlap)

        Returns:
            WFVSummary with results and verdict
        """
        if not ohlcv_data or len(ohlcv_data) < 500:
            raise ValueError("Insufficient data for walk-forward validation")

        self.results.clear()

        # Generate windows
        windows = self._generate_windows(
            ohlcv_data,
            num_windows,
            window_overlap
        )

        for window_id, (train_data, test_data) in enumerate(windows):
            result = self._validate_window(
                asset,
                window_id,
                train_data,
                test_data
            )
            self.results.append(result)

        # Create summary
        summary = self._create_summary(asset)
        return summary

    def _generate_windows(
        self,
        ohlcv_data: List[dict],
        num_windows: int,
        overlap: float,
    ) -> List[Tuple[List[dict], List[dict]]]:
        """Generate train/test window pairs."""
        windows = []
        data_len = len(ohlcv_data)
        window_size = data_len // (num_windows + 1)  # Leave room for test windows

        for i in range(num_windows):
            # Calculate boundaries (50/50 train/test split)
            train_size = window_size // 2
            test_size = window_size // 2

            # Adjust for overlap
            overlap_points = int(train_size * overlap)

            train_start = i * train_size - overlap_points
            train_end = train_start + train_size
            test_start = train_end
            test_end = test_start + test_size

            # Ensure bounds
            train_start = max(0, train_start)
            train_end = min(data_len, train_end)
            test_start = min(data_len - 1, test_start)
            test_end = min(data_len, test_end)

            if test_end > data_len:
                break  # Not enough data for this window

            train_data = ohlcv_data[train_start:train_end]
            test_data = ohlcv_data[test_start:test_end]

            if len(train_data) > 0 and len(test_data) > 0:
                windows.append((train_data, test_data))

        return windows

    def _validate_window(
        self,
        asset: str,
        window_id: int,
        train_data: List[dict],
        test_data: List[dict],
    ) -> WFVResult:
        """Validate BCE on single train/test window."""

        # Simulate BCE scoring (in real system, compute from BCE engine)
        train_metrics = self._simulate_backtest(train_data)
        test_metrics = self._simulate_backtest(test_data)

        # Get timestamps
        train_start = train_data[0].get('timestamp', datetime.now())
        train_end = train_data[-1].get('timestamp', datetime.now())
        test_start = test_data[0].get('timestamp', datetime.now())
        test_end = test_data[-1].get('timestamp', datetime.now())

        # Check constraints
        constraint_failures = []
        if train_metrics['trades'] < self.MIN_TRADES:
            constraint_failures.append(f"Train trades {train_metrics['trades']} < {self.MIN_TRADES}")
        if test_metrics['trades'] < self.MIN_TRADES:
            constraint_failures.append(f"Test trades {test_metrics['trades']} < {self.MIN_TRADES}")
        if train_metrics['pf'] < self.MIN_PROFIT_FACTOR:
            constraint_failures.append(f"Train PF {train_metrics['pf']:.2f} < {self.MIN_PROFIT_FACTOR}")
        if test_metrics['pf'] < self.MIN_PROFIT_FACTOR:
            constraint_failures.append(f"Test PF {test_metrics['pf']:.2f} < {self.MIN_PROFIT_FACTOR}")
        if train_metrics['dd'] > self.MAX_DRAWDOWN:
            constraint_failures.append(f"Train DD {train_metrics['dd']:.1%} > {self.MAX_DRAWDOWN:.1%}")
        if test_metrics['dd'] > self.MAX_DRAWDOWN:
            constraint_failures.append(f"Test DD {test_metrics['dd']:.1%} > {self.MAX_DRAWDOWN:.1%}")

        # Calculate degradation
        trade_deg = test_metrics['trades'] / train_metrics['trades'] if train_metrics['trades'] > 0 else 0
        pf_deg = (train_metrics['pf'] - test_metrics['pf']) / train_metrics['pf'] if train_metrics['pf'] > 0 else 0
        dd_deg = (test_metrics['dd'] - train_metrics['dd']) / train_metrics['dd'] if train_metrics['dd'] > 0 else 0
        wr_deg = (train_metrics['wr'] - test_metrics['wr']) / train_metrics['wr'] if train_metrics['wr'] > 0 else 0

        # Check degradation limits
        if pf_deg > self.MAX_PF_DEGRADATION:
            constraint_failures.append(f"PF degradation {pf_deg:.1%} > {self.MAX_PF_DEGRADATION:.1%}")
        if dd_deg > self.MAX_DD_DEGRADATION:
            constraint_failures.append(f"DD degradation {dd_deg:.1%} > {self.MAX_DD_DEGRADATION:.1%}")

        passes = len(constraint_failures) == 0

        return WFVResult(
            asset=asset,
            window_id=window_id,
            start_date=train_start,
            end_date=test_end,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            train_trades=train_metrics['trades'],
            test_trades=test_metrics['trades'],
            train_profit_factor=train_metrics['pf'],
            test_profit_factor=test_metrics['pf'],
            train_max_drawdown=train_metrics['dd'],
            test_max_drawdown=test_metrics['dd'],
            train_win_rate=train_metrics['wr'],
            test_win_rate=test_metrics['wr'],
            train_sharpe=train_metrics['sharpe'],
            test_sharpe=test_metrics['sharpe'],
            passes_constraints=passes,
            constraint_failures=constraint_failures,
            trade_degradation=trade_deg,
            pf_degradation=pf_deg,
            dd_degradation=dd_deg,
            wr_degradation=wr_deg,
        )

    def _simulate_backtest(self, ohlcv_data: List[dict]) -> dict:
        """
        Simulate backtest results (placeholder for real BCE scoring).

        In production, this would use the actual BCE engine to:
        1. Score each candle
        2. Generate entry signals (BCE >= 5/6)
        3. Track entries/exits
        4. Calculate performance metrics
        """
        if not ohlcv_data or len(ohlcv_data) < 10:
            return {
                'trades': 0,
                'pf': 0.0,
                'dd': 0.0,
                'wr': 0.0,
                'sharpe': 0.0,
            }

        # Simulate trades based on data variation
        prices = np.array([d.get('close', 100) for d in ohlcv_data])
        returns = np.diff(prices) / prices[:-1]

        # Simulate: signals generated from price momentum
        volatility = np.std(returns)
        signal_count = max(1, int(len(ohlcv_data) / 50))  # ~2% signal rate

        # Random trade outcomes (weighted by momentum)
        wins = max(1, int(signal_count * 0.6))  # 60% win rate
        losses = signal_count - wins

        avg_win = np.mean(prices) * 0.02 * np.abs(np.mean(returns[returns > 0]))
        avg_loss = np.mean(prices) * 0.01 * np.abs(np.mean(returns[returns < 0]))

        pf = (wins * avg_win) / (losses * avg_loss) if losses > 0 else (wins * avg_win) / 0.01

        # Simulate drawdown
        cum_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cum_returns)
        dd = np.min((cum_returns - running_max) / running_max)

        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

        return {
            'trades': signal_count,
            'pf': max(1.0, pf),
            'dd': abs(dd),
            'wr': wins / signal_count if signal_count > 0 else 0,
            'sharpe': sharpe,
        }

    def _create_summary(self, asset: str) -> WFVSummary:
        """Create summary from all window results."""
        passes = sum(1 for r in self.results if r.passes_constraints)
        failures = len(self.results) - passes

        pf_values = [r.train_profit_factor for r in self.results]
        wr_values = [r.train_win_rate for r in self.results]

        pf_std = np.std(pf_values) if len(pf_values) > 1 else 0
        wr_std = np.std(wr_values) if len(wr_values) > 1 else 0

        avg_trade_deg = np.mean([r.trade_degradation for r in self.results])
        avg_pf_deg = np.mean([r.pf_degradation for r in self.results])
        avg_dd_deg = np.mean([r.dd_degradation for r in self.results])
        avg_wr_deg = np.mean([r.wr_degradation for r in self.results])

        # Verdict: pass if all windows pass constraints and degradation acceptable
        is_valid = (
            passes == len(self.results) and
            avg_pf_deg <= self.MAX_PF_DEGRADATION and
            pf_std <= 0.2  # PF variation < 20%
        )

        return WFVSummary(
            asset=asset,
            num_windows=len(self.results),
            all_results=self.results,
            passes=passes,
            failures=failures,
            pass_rate=passes / len(self.results) if self.results else 0,
            avg_trade_degradation=avg_trade_deg,
            avg_pf_degradation=avg_pf_deg,
            avg_dd_degradation=avg_dd_deg,
            avg_wr_degradation=avg_wr_deg,
            pf_std_dev=pf_std,
            wr_std_dev=wr_std,
            is_valid=is_valid,
        )


class TestWalkForwardValidation:
    """Integration tests for walk-forward validation framework."""

    @pytest.fixture
    def sample_ohlcv(self):
        """Generate sample OHLCV data (2 years worth)."""
        data = []
        price = 100.0
        start = datetime(2024, 1, 1)

        for i in range(730):  # ~2 years of daily data
            timestamp = start + timedelta(days=i)

            # Simulate price movement
            daily_return = np.random.normal(0.0005, 0.02)
            price = price * (1 + daily_return)

            open_p = price * 0.99
            high_p = price * 1.01
            low_p = price * 0.98
            close_p = price
            volume = np.random.uniform(1000000, 5000000)

            data.append({
                'timestamp': timestamp,
                'open': open_p,
                'high': high_p,
                'low': low_p,
                'close': close_p,
                'volume': volume,
            })

        return data

    def test_wfv_framework_instantiation(self):
        """Test WalkForwardValidator creation."""
        validator = WalkForwardValidator()

        assert validator.MIN_TRADES == 200
        assert validator.MIN_PROFIT_FACTOR == 1.3
        assert validator.MAX_DRAWDOWN == 0.25

    def test_window_generation(self, sample_ohlcv):
        """Test walk-forward window generation."""
        validator = WalkForwardValidator()

        windows = validator._generate_windows(sample_ohlcv, num_windows=4, overlap=0.0)

        assert len(windows) == 4

        # Each window should have train and test data
        for train, test in windows:
            assert len(train) > 0
            assert len(test) > 0

            # Test data should be after train data
            train_end = train[-1]['timestamp']
            test_start = test[0]['timestamp']
            assert test_start >= train_end

    def test_single_window_validation(self, sample_ohlcv):
        """Test validation on single window."""
        validator = WalkForwardValidator()

        train_data = sample_ohlcv[:365]
        test_data = sample_ohlcv[365:365+180]

        result = validator._validate_window(
            asset='BTC',
            window_id=0,
            train_data=train_data,
            test_data=test_data
        )

        assert result.asset == 'BTC'
        assert result.window_id == 0
        assert result.train_trades > 0
        assert result.test_trades > 0

    def test_full_wfv_validation(self, sample_ohlcv):
        """Test complete walk-forward validation flow."""
        validator = WalkForwardValidator()

        summary = validator.validate_asset(
            asset='BTC',
            ohlcv_data=sample_ohlcv,
            num_windows=4,
        )

        assert summary.asset == 'BTC'
        assert summary.num_windows == 4
        assert len(summary.all_results) == 4

        # Check metrics exist
        for result in summary.all_results:
            assert result.train_trades > 0
            assert result.test_trades > 0
            assert result.train_profit_factor > 0
            assert 0 <= result.train_win_rate <= 1

    def test_degradation_calculation(self, sample_ohlcv):
        """Test out-of-sample degradation metrics."""
        validator = WalkForwardValidator()

        summary = validator.validate_asset(
            asset='ETH',
            ohlcv_data=sample_ohlcv,
            num_windows=2,
        )

        # Degradation should be reasonable (not negative, not extreme)
        assert summary.avg_pf_degradation >= -1.0
        assert summary.avg_pf_degradation <= 1.0
        assert summary.avg_dd_degradation >= -1.0
        assert summary.avg_dd_degradation <= 1.0

    def test_insufficient_data_error(self):
        """Test error on insufficient data."""
        validator = WalkForwardValidator()
        small_data = [{'timestamp': datetime.now(), 'close': 100}]

        with pytest.raises(ValueError, match="Insufficient data"):
            validator.validate_asset('BTC', small_data)

    def test_multi_asset_validation(self, sample_ohlcv):
        """Test validation on multiple assets."""
        validator = WalkForwardValidator()

        assets = ['BTC', 'ETH', 'SOL']
        results = {}

        for asset in assets:
            summary = validator.validate_asset(
                asset=asset,
                ohlcv_data=sample_ohlcv,
                num_windows=2,
            )
            results[asset] = summary

        assert len(results) == 3
        for asset in assets:
            assert results[asset].asset == asset
            assert results[asset].pass_rate >= 0.0
            assert results[asset].pass_rate <= 1.0
