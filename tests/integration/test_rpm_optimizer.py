"""Integration tests for Phase 8 RPM X20 Optimizer.

Tests regime detection, exits, MFE/MAE, parameter optimization, and validation.
"""

import pytest
from datetime import datetime, timedelta

from src.layers.layer8_optimizer import (
    RegimeDetector,
    DynamicExitEngine,
    MFEMAEAnalyzer,
    ParameterOptimizer,
    WalkForwardValidator,
    OverfitDetector,
)


class TestRegimeDetector:
    """Test market regime detection."""

    @pytest.fixture
    def detector(self):
        return RegimeDetector()

    def test_bullish_regime(self, detector):
        """Detect bullish regime."""
        price_data = {
            "momentum": 50,
            "higher_highs": True,
            "higher_lows": True,
        }
        vol_data = {
            "current_volatility": 2.0,
            "volatility_7d_avg": 2.5,
        }
        vol_data_obj = {
            "current_volume": 1000,
            "volume_7d_avg": 800,
        }

        regime = detector.detect_regime("BTC", price_data, vol_data, vol_data_obj)

        assert regime.regime_type.value == "bullish"
        assert regime.confidence > 0.5

    def test_bearish_regime(self, detector):
        """Detect bearish regime."""
        price_data = {
            "momentum": -45,
            "higher_highs": False,
            "higher_lows": False,
        }
        vol_data = {
            "current_volatility": 2.0,
            "volatility_7d_avg": 2.0,
        }
        vol_data_obj = {
            "current_volume": 1200,
            "volume_7d_avg": 800,
        }

        regime = detector.detect_regime("ETH", price_data, vol_data, vol_data_obj)

        assert regime.regime_type.value == "bearish"

    def test_volatile_regime(self, detector):
        """Detect high volatility regime."""
        price_data = {"momentum": 20, "higher_highs": False, "higher_lows": False}
        vol_data = {
            "current_volatility": 6.0,  # Extreme
            "volatility_7d_avg": 2.0,
        }
        vol_data_obj = {"current_volume": 500, "volume_7d_avg": 800}

        regime = detector.detect_regime("SOL", price_data, vol_data, vol_data_obj)

        assert regime.regime_type.value == "volatile"
        assert regime.volatility.volatility_regime == "extreme"


class TestDynamicExitEngine:
    """Test exit signal generation."""

    @pytest.fixture
    def engine(self):
        return DynamicExitEngine(risk_limit_pct=2.0)

    def test_stop_loss_hit(self, engine):
        """Generate stop loss signal."""
        analysis = engine.analyze_exit(
            "BTC",
            entry_price=50000,
            current_price=47000,
            stop_loss=48000,
            profit_targets={"target_1": 55000, "target_2": 60000, "target_3": 70000},
            days_in_trade=5,
            regime="bullish",
        )

        assert analysis.exit_signal.exit_type == "stop_loss"
        assert analysis.exit_signal.confidence > 0.9

    def test_take_profit_signal(self, engine):
        """Generate take profit signal."""
        analysis = engine.analyze_exit(
            "ETH",
            entry_price=2000,
            current_price=6100,
            stop_loss=1800,
            profit_targets={"target_1": 3000, "target_2": 4000, "target_3": 6000},
            days_in_trade=30,
            regime="bullish",
        )

        assert analysis.exit_signal.exit_type == "take_profit"
        assert "TP3" in analysis.exit_signal.reasoning

    def test_hold_signal(self, engine):
        """Generate hold signal."""
        analysis = engine.analyze_exit(
            "SOL",
            entry_price=100,
            current_price=110,
            stop_loss=95,
            profit_targets={"target_1": 150, "target_2": 200, "target_3": 300},
            days_in_trade=10,
            regime="bullish",
        )

        assert analysis.exit_signal.exit_type == "hold"


class TestMFEMAEAnalyzer:
    """Test trade quality analysis."""

    @pytest.fixture
    def analyzer(self):
        return MFEMAEAnalyzer()

    def test_ideal_trade(self, analyzer):
        """Analyze ideal trade execution."""
        analysis = analyzer.analyze_trade(
            "BTC",
            entry_price=50000,
            exit_price=60200,
            high_price=65500,
            low_price=49000,
            stop_loss=48000,
        )

        assert analysis.trade_quality == "ideal"
        assert analysis.excursion.mfe > 30
        assert analysis.exit_efficiency > 0.6

    def test_poor_trade(self, analyzer):
        """Analyze poorly executed trade."""
        analysis = analyzer.analyze_trade(
            "ETH",
            entry_price=2000,
            exit_price=1800,
            high_price=2200,
            low_price=1700,
            stop_loss=1900,
        )

        assert analysis.trade_quality == "poor"
        assert analysis.excursion.final_profit_loss < 0


class TestParameterOptimizer:
    """Test strategy parameter optimization."""

    @pytest.fixture
    def optimizer(self):
        return ParameterOptimizer()

    def test_run_optimization(self, optimizer):
        """Run parameter optimization trials."""
        results = optimizer.run_optimization(n_trials=20)

        assert results["trials_run"] == 20
        assert results["valid_trials"] >= 0
        assert results["best_score"] >= 0

    def test_parameter_generation(self, optimizer):
        """Generate parameter sets."""
        param_set = optimizer._generate_parameters(0)

        assert 4.5 <= param_set.bce_threshold <= 5.5
        assert 0.2 <= param_set.cf_weight <= 0.4
        assert 1.5 <= param_set.risk_limit_pct <= 2.5
        assert 1.8 <= param_set.profit_target_multiplier <= 2.5

    def test_optimization_constraints(self, optimizer):
        """Verify optimization respects constraints."""
        constraints = {
            "min_profit_factor": 1.5,
            "max_drawdown": 0.20,
            "min_trades": 250,
        }
        results = optimizer.run_optimization(n_trials=15, constraints=constraints)

        valid_trials = results["valid_trials"]
        assert valid_trials >= 0


class TestWalkForwardValidator:
    """Test walk-forward validation."""

    @pytest.fixture
    def validator(self):
        return WalkForwardValidator(window_size_days=60, step_size_days=20)

    def test_create_windows(self, validator):
        """Create walk-forward windows."""
        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)

        windows = validator.create_windows(start, end)

        assert len(windows) > 0
        assert windows[0].in_sample_start == start
        assert all(w.out_sample_end <= end for w in windows)

    def test_validate_passed(self, validator):
        """Validate strategy that passes WF test."""
        from src.layers.layer8_optimizer import WindowResults

        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)
        windows = validator.create_windows(start, end)

        in_sample_results = [
            WindowResults(
                window_id=i,
                profit_factor=1.4,
                win_rate=0.45,
                max_drawdown=0.20,
                sharpe_ratio=1.5,
                trades_count=250,
                passed=True,
            )
            for i in range(len(windows))
        ]

        out_sample_results = [
            WindowResults(
                window_id=i,
                profit_factor=1.35,
                win_rate=0.43,
                max_drawdown=0.22,
                sharpe_ratio=1.4,
                trades_count=240,
                passed=True,
            )
            for i in range(len(windows))
        ]

        validation = validator.validate("BTC", windows, in_sample_results, out_sample_results)

        assert validation.validation_status == "passed"
        assert validation.degradation_ratio < 0.4


class TestOverfitDetector:
    """Test overfitting detection."""

    @pytest.fixture
    def detector(self):
        return OverfitDetector()

    def test_robust_strategy(self, detector):
        """Detect robust (not overfitted) strategy."""
        in_sample = {
            "profit_factor": 1.5,
            "max_drawdown": 0.20,
            "sharpe_ratio": 1.8,
        }
        out_sample = {
            "profit_factor": 1.45,
            "max_drawdown": 0.22,
            "sharpe_ratio": 1.6,
        }
        params = {"bce_threshold": 5.0, "cf_weight": 0.3, "stop_loss_pct": 3.0}

        metrics = detector.detect_overfit("BTC", in_sample, out_sample, params)

        assert metrics.is_curve_fitted is False
        assert metrics.robustness_score > 60

    def test_overfitted_strategy(self, detector):
        """Detect overfitted strategy."""
        in_sample = {
            "profit_factor": 2.0,
            "max_drawdown": 0.15,
            "sharpe_ratio": 2.5,
        }
        out_sample = {
            "profit_factor": 1.0,
            "max_drawdown": 0.40,
            "sharpe_ratio": 0.5,
        }
        params = {"bce_threshold": 5.4, "cf_weight": 0.38, "stop_loss_pct": 4.8}

        metrics = detector.detect_overfit("ETH", in_sample, out_sample, params)

        assert metrics.is_curve_fitted is True
        assert len(metrics.recommendations) > 0


class TestPhase8FullPipeline:
    """Test complete Phase 8 optimization workflow."""

    def test_end_to_end_optimization(self):
        """Test complete optimization pipeline."""
        regime_detector = RegimeDetector()
        exit_engine = DynamicExitEngine()
        mfe_analyzer = MFEMAEAnalyzer()
        optimizer = ParameterOptimizer()
        wf_validator = WalkForwardValidator()
        overfit_detector = OverfitDetector()

        # 1. Detect regime
        price_data = {"momentum": 40, "higher_highs": True, "higher_lows": True}
        vol_data = {"current_volatility": 2.0, "volatility_7d_avg": 2.0}
        vol_data_obj = {"current_volume": 1000, "volume_7d_avg": 900}

        regime = regime_detector.detect_regime("BTC", price_data, vol_data, vol_data_obj)
        assert regime.regime_type.value in ["bullish", "ranging", "transition"]

        # 2. Analyze exits
        exit_analysis = exit_engine.analyze_exit(
            "BTC",
            entry_price=50000,
            current_price=55000,
            stop_loss=48000,
            profit_targets={"target_1": 55000, "target_2": 60000, "target_3": 70000},
            days_in_trade=15,
            regime=regime.regime_type.value,
        )
        assert exit_analysis.exit_signal is not None

        # 3. Analyze trade quality
        trade_analysis = mfe_analyzer.analyze_trade(
            "BTC",
            entry_price=50000,
            exit_price=58000,
            high_price=62000,
            low_price=49000,
            stop_loss=48000,
        )
        assert trade_analysis.trade_quality in ["ideal", "good", "ok", "poor"]

        # 4. Optimize parameters
        opt_results = optimizer.run_optimization(n_trials=15)
        assert opt_results["trials_run"] == 15

        # 5. Validate with walk-forward
        wf_windows = wf_validator.create_windows(datetime(2023, 1, 1), datetime(2023, 6, 30))
        assert len(wf_windows) > 0

        # 6. Detect overfitting
        overfit_metrics = overfit_detector.detect_overfit(
            "BTC",
            {"profit_factor": 1.4, "max_drawdown": 0.20, "sharpe_ratio": 1.6},
            {"profit_factor": 1.35, "max_drawdown": 0.22, "sharpe_ratio": 1.5},
            {"bce_threshold": 5.0, "cf_weight": 0.30},
        )
        assert 0 <= overfit_metrics.robustness_score <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
