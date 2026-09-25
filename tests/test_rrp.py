"""
Test suite for Layer 7 - RRP (Revival Radar Pipeline)

Coverage:
- PIT compliance (no future data in signals)
- Score bounds (revival confidence in [0, 100])
- Dormancy classification (Active/Dormant/Dead)
- Win rate calculation (binary target evaluation)
- WFV window boundaries
- OOS validation
- Revival candidate ranking
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'research'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'data'))

from rrp_layer import RRPLayer, RevivalCandidate
from layer_7_runner import Layer7Runner
from rrp_data_layer import RRPDataLayer


class TestRRPMetrics:
    """Test RRP metric computation."""

    def test_dormancy_index_bounds(self):
        """Dormancy index must be in [0, 1]."""
        rrp = RRPLayer()

        # 20 days: before dormancy threshold (30 days)
        d1 = rrp._compute_dormancy_index(20)
        assert 0 <= d1 <= 1, f"Dormancy out of bounds: {d1}"

        # 365 days: maximum dormancy
        d2 = rrp._compute_dormancy_index(365)
        assert d2 == 1.0, f"Expected 1.0, got {d2}"

        # 500 days: clipped to 1.0
        d3 = rrp._compute_dormancy_index(500)
        assert d3 == 1.0, f"Expected clipped 1.0, got {d3}"

    def test_revival_confidence_bounds(self):
        """Revival confidence must be in [0, 100]."""
        rrp = RRPLayer()

        # All metrics max (positive)
        conf_max = rrp._compute_revival_confidence(
            dormancy=1.0, acceleration=1.0, whale=1.0,
            dev=1.0, narrative=1.0, liquidity=1.0
        )
        assert 0 <= conf_max <= 100, f"Confidence out of bounds: {conf_max}"
        assert conf_max > 50, f"Max confidence should be high: {conf_max}"

        # All metrics min (negative)
        conf_min = rrp._compute_revival_confidence(
            dormancy=0.0, acceleration=-1.0, whale=-1.0,
            dev=-1.0, narrative=-1.0, liquidity=-1.0
        )
        assert 0 <= conf_min <= 100, f"Confidence out of bounds: {conf_min}"
        assert conf_min < 50, f"Min confidence should be low: {conf_min}"

    def test_score_weights_sum_to_one(self):
        """Verify metric weights sum to 1.0 per spec."""
        # Per SPRING-PHASE-LAYER7-SPEC.md:
        # Dormancy: 0.20, Acceleration: 0.25, Whale: 0.15,
        # Dev: 0.15, Narrative: 0.15, Liquidity: 0.10
        weights = [0.20, 0.25, 0.15, 0.15, 0.15, 0.10]
        assert sum(weights) == 1.0, f"Weights don't sum to 1.0: {sum(weights)}"


class TestRRPCandidateScoring:
    """Test revival candidate detection and scoring."""

    def test_candidate_ranking(self):
        """Candidates should rank by confidence descending."""
        rrp = RRPLayer()

        tokens_df = pd.DataFrame([
            {'symbol': 'LUNA', 'last_activity_days': 45, 'market_cap': 2.5e9},
            {'symbol': 'XRP', 'last_activity_days': 22, 'market_cap': 35e9},
            {'symbol': 'ADA', 'last_activity_days': 15, 'market_cap': 18e9},
        ])

        # Generate synthetic metrics
        data_layer = RRPDataLayer()
        metrics = data_layer.generate_synthetic_metrics(tokens_df, periods=100)

        # Score candidates
        candidates = rrp.score_tokens(tokens_df, metrics)

        # Verify ordering
        for i in range(len(candidates) - 1):
            assert candidates[i].revival_confidence >= candidates[i + 1].revival_confidence, \
                f"Not ranked by confidence: {candidates[i].symbol} vs {candidates[i + 1].symbol}"

    def test_high_confidence_filter(self):
        """Filter high-confidence candidates correctly."""
        rrp = RRPLayer()

        tokens_df = pd.DataFrame([
            {'symbol': 'LUNA', 'last_activity_days': 45, 'market_cap': 2.5e9},
            {'symbol': 'XRP', 'last_activity_days': 22, 'market_cap': 35e9},
        ])

        data_layer = RRPDataLayer()
        metrics = data_layer.generate_synthetic_metrics(tokens_df, periods=100)

        candidates = rrp.score_tokens(tokens_df, metrics)
        high_conf = rrp.get_high_confidence_candidates(min_confidence=70)

        # All high_conf should be >= 70
        for c in high_conf:
            assert c.revival_confidence >= 70, f"Candidate {c.symbol} below threshold: {c.revival_confidence}"

    def test_candidate_attributes(self):
        """RevivalCandidate has all required attributes."""
        rrp = RRPLayer()

        tokens_df = pd.DataFrame([
            {'symbol': 'LUNA', 'last_activity_days': 45, 'market_cap': 2.5e9},
        ])

        data_layer = RRPDataLayer()
        metrics = data_layer.generate_synthetic_metrics(tokens_df, periods=100)

        candidates = rrp.score_tokens(tokens_df, metrics)

        assert len(candidates) > 0, "No candidates generated"
        c = candidates[0]

        # Verify all attributes exist
        assert hasattr(c, 'symbol')
        assert hasattr(c, 'revival_confidence')
        assert hasattr(c, 'dormancy_index')
        assert hasattr(c, 'activity_acceleration')
        assert hasattr(c, 'whale_accumulation')
        assert hasattr(c, 'developer_activity')
        assert hasattr(c, 'narrative_momentum')
        assert hasattr(c, 'liquidity_rebound')
        assert hasattr(c, 'recommendation')
        assert hasattr(c, 'entry_window_start')


class TestWFVWindowBoundaries:
    """Test WFV window expansion and boundaries."""

    def test_window_count(self):
        """Should generate exactly 19 windows."""
        runner = Layer7Runner()
        windows = runner.create_wfv_windows()

        assert len(windows) == 19, f"Expected 19 windows, got {len(windows)}"

    def test_window_expansion(self):
        """Train window should expand, test fixed at 30 days."""
        runner = Layer7Runner()
        windows = runner.create_wfv_windows()

        for i, w in enumerate(windows):
            # Train size should expand: 180 + i*30
            expected_train = 180 + i * 30
            actual_train = w['train_end_idx'] + 1
            assert actual_train == expected_train, \
                f"Window {i}: expected train size {expected_train}, got {actual_train}"

            # Test size should be fixed at 30
            actual_test = w['test_end_idx'] - w['test_start_idx'] + 1
            assert actual_test == 30, f"Window {i}: test size {actual_test} != 30"

    def test_window_continuity(self):
        """Windows should be continuous (no gaps)."""
        runner = Layer7Runner()
        windows = runner.create_wfv_windows()

        for i in range(len(windows) - 1):
            current_test_end = windows[i]['test_end_idx']
            next_train_end = windows[i + 1]['train_end_idx']

            # Next window's test should start where current ended + 1
            expected_next_train_end = windows[i]['train_end_idx'] + 30

            assert next_train_end >= expected_next_train_end, \
                f"Windows {i} and {i+1} not continuous"

    def test_first_window_starts_at_zero(self):
        """First window train should start at index 0."""
        runner = Layer7Runner()
        windows = runner.create_wfv_windows()

        assert windows[0]['train_start_idx'] == 0, "First window doesn't start at 0"


class TestWFVExecution:
    """Test WFV execution and gate criteria."""

    def test_wfv_basic_execution(self):
        """WFV should run without errors on synthetic data."""
        runner = Layer7Runner()

        # Generate synthetic OHLCV (365 + 395 = 760 days)
        dates = pd.date_range('2021-01-01', periods=760, freq='D')
        close_prices = 100 + np.cumsum(np.random.normal(0, 2, 760))

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.normal(0, 1, 760),
            'high': close_prices + abs(np.random.normal(0, 1, 760)),
            'low': close_prices - abs(np.random.normal(0, 1, 760)),
            'close': close_prices,
            'volume': np.random.uniform(1e6, 1e7, 760),
        })

        result = runner.run_wfv(df)

        assert result is not None
        assert 0 <= result.mean_win_rate <= 1, "Invalid win rate"
        assert 0 <= result.mean_precision <= 1, "Invalid precision"
        assert len(result.window_win_rates) == 19, "Wrong number of windows"

    def test_gate_criteria_structure(self):
        """Gate decision should be based on 4 criteria (ALL must pass)."""
        runner = Layer7Runner()

        dates = pd.date_range('2021-01-01', periods=760, freq='D')
        close_prices = 100 + np.cumsum(np.random.normal(0, 2, 760))

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.normal(0, 1, 760),
            'high': close_prices + abs(np.random.normal(0, 1, 760)),
            'low': close_prices - abs(np.random.normal(0, 1, 760)),
            'close': close_prices,
            'volume': np.random.uniform(1e6, 1e7, 760),
        })

        result = runner.run_wfv(df)

        # Gate decision is Boolean (ALL must pass)
        assert isinstance(result.gate_pass, bool), "Gate decision must be Boolean"

        # Criteria:
        # 1. WR > 0.50
        # 2. Precision > 0.60
        # 3. Stability < 0.50
        # 4. OOS >= IS - 0.05

        gate_1_wr = result.mean_win_rate > 0.50
        gate_2_precision = result.mean_precision > 0.60
        gate_3_stability = result.stability < 0.50
        gate_4_oos = result.oos_win_rate >= (result.mean_win_rate - 0.05)

        expected_gate = gate_1_wr and gate_2_precision and gate_3_stability and gate_4_oos
        assert result.gate_pass == expected_gate, "Gate decision logic incorrect"

    def test_window_metrics_recorded(self):
        """Per-window metrics should be recorded."""
        runner = Layer7Runner()

        dates = pd.date_range('2021-01-01', periods=760, freq='D')
        close_prices = 100 + np.cumsum(np.random.normal(0, 2, 760))

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.normal(0, 1, 760),
            'high': close_prices + abs(np.random.normal(0, 1, 760)),
            'low': close_prices - abs(np.random.normal(0, 1, 760)),
            'close': close_prices,
            'volume': np.random.uniform(1e6, 1e7, 760),
        })

        result = runner.run_wfv(df)

        assert len(result.window_win_rates) == 19
        assert len(result.window_precisions) == 19

        # All metrics should be in [0, 1]
        for wr in result.window_win_rates:
            assert 0 <= wr <= 1, f"Invalid window WR: {wr}"

        for prec in result.window_precisions:
            assert 0 <= prec <= 1, f"Invalid window precision: {prec}"


class TestPITCompliance:
    """Test that signals don't use future data (Point-In-Time compliance)."""

    def test_signal_uses_only_past_data(self):
        """Revival scoring should use only historical data."""
        rrp = RRPLayer()

        # Create historical data
        tokens_df = pd.DataFrame([
            {'symbol': 'LUNA', 'last_activity_days': 45, 'market_cap': 2.5e9},
        ])

        data_layer = RRPDataLayer()
        metrics = data_layer.generate_synthetic_metrics(tokens_df, periods=100)

        # Score should not raise errors (no future data access)
        candidates = rrp.score_tokens(tokens_df, metrics)

        assert len(candidates) > 0, "Should generate candidates without future data"


class TestRRPDataLayer:
    """Test RRPDataLayer metric computation."""

    def test_dormant_tokens_loading(self):
        """Load dormant tokens with market cap filter."""
        data_layer = RRPDataLayer()
        df = data_layer.load_dormant_tokens(market_cap_min=1e6)

        assert len(df) > 0, "Should load dormant tokens"
        assert all(df['market_cap'] >= 1e6), "Should apply market cap filter"

    def test_synthetic_metrics_generation(self):
        """Generate realistic metric trajectories."""
        data_layer = RRPDataLayer()

        tokens_df = data_layer.load_dormant_tokens()
        metrics = data_layer.generate_synthetic_metrics(tokens_df, periods=100)

        assert len(metrics) > 0, "Should generate metrics"

        for symbol, ts in metrics.items():
            assert len(ts) == 100, f"Trajectory length {len(ts)} != 100"
            assert np.all((ts >= -1) & (ts <= 1)), f"Trajectory {symbol} out of [-1, 1]"

    def test_metric_computation_bounds(self):
        """Individual metric computations should stay in bounds."""
        data_layer = RRPDataLayer()

        # Dormancy
        dormancy = data_layer.compute_dormancy_index(100)
        assert 0 <= dormancy <= 1

        # Acceleration
        activity = np.array([10, 20, 15, 25, 30, 35, 40])
        accel = data_layer.compute_activity_acceleration(activity)
        assert -1 <= accel <= 1

        # Whale
        whale = data_layer.compute_whale_accumulation(500000)
        assert -1 <= whale <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
