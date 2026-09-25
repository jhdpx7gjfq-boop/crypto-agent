"""Tests for liquidation feature engineering — F001-F006 computation."""

from datetime import UTC, datetime, timedelta

import pytest

from src.validation.liquidation.features import LiquidationFeatureEngine


class TestLiquidationFeatureEngine:
    """LiquidationFeatureEngine tests."""

    @pytest.fixture
    def engine(self) -> LiquidationFeatureEngine:
        """Create feature engine."""
        return LiquidationFeatureEngine(window_hours=4)

    @pytest.fixture
    def base_time(self) -> datetime:
        """Base observation time."""
        return datetime(2026, 9, 25, 18, 0, 0, tzinfo=UTC)

    @pytest.fixture
    def sample_events(self, base_time) -> list[dict]:
        """Generate sample liquidation events."""
        return [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "symbol": "BTCUSDT",
                "side": "long",
                "quantity": 1.0,
                "price": 65000.0,
                "usd_value": 65000.0,
                "source": "binance_websocket",
                "source_id": "evt_1",
            },
            {
                "timestamp": base_time - timedelta(minutes=60),
                "symbol": "ETHUSDT",
                "side": "short",
                "quantity": 10.0,
                "price": 2500.0,
                "usd_value": 25000.0,
                "source": "binance_websocket",
                "source_id": "evt_2",
            },
            {
                "timestamp": base_time - timedelta(minutes=120),
                "symbol": "BTCUSDT",
                "side": "long",
                "quantity": 0.5,
                "price": 65000.0,
                "usd_value": 32500.0,
                "source": "coinglass",
                "source_id": "evt_3",
            },
        ]

    def test_engine_initialization(self, engine) -> None:
        """Initialize feature engine."""
        assert engine.window_hours == 4
        assert engine.window_timedelta == timedelta(hours=4)

    def test_f001_volume_rolling_sum_basic(self, engine, sample_events, base_time) -> None:
        """F001: Compute rolling sum volume."""
        volume = engine.compute_f001_volume_rolling_sum(sample_events, base_time)

        # All three events are within 4-hour window
        expected = 65000.0 + 25000.0 + 32500.0
        assert volume == expected

    def test_f001_volume_rolling_sum_pit_compliance(self, engine, base_time) -> None:
        """F001: PIT compliance — exclude events at observation_time."""
        events = [
            {
                "timestamp": base_time,
                "symbol": "BTCUSDT",
                "side": "long",
                "usd_value": 65000.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=1),
                "symbol": "BTCUSDT",
                "side": "long",
                "usd_value": 32500.0,
            },
        ]

        volume = engine.compute_f001_volume_rolling_sum(events, base_time)

        # Event at observation_time should be excluded
        assert volume == 32500.0

    def test_f001_volume_rolling_sum_empty(self, engine, base_time) -> None:
        """F001: No events in window."""
        events = [
            {
                "timestamp": base_time - timedelta(hours=5),
                "usd_value": 65000.0,
            }
        ]

        volume = engine.compute_f001_volume_rolling_sum(events, base_time)

        assert volume == 0.0

    def test_f002_long_short_ratio_basic(self, engine, sample_events, base_time) -> None:
        """F002: Compute long/short ratio."""
        ratio = engine.compute_f002_long_short_ratio(sample_events, base_time)

        # 2 long events (65000 + 32500 = 97500), 1 short event (25000)
        expected = 97500.0 / 25000.0
        assert ratio == pytest.approx(expected)

    def test_f002_long_short_ratio_no_shorts(self, engine, base_time) -> None:
        """F002: Ratio when no short liquidations."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "side": "long",
                "usd_value": 65000.0,
            }
        ]

        ratio = engine.compute_f002_long_short_ratio(events, base_time)

        # No shorts: return 0
        assert ratio == 0.0

    def test_f002_long_short_ratio_equal(self, engine, base_time) -> None:
        """F002: Equal long and short liquidations."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "side": "long",
                "usd_value": 50000.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=60),
                "side": "short",
                "usd_value": 50000.0,
            },
        ]

        ratio = engine.compute_f002_long_short_ratio(events, base_time)

        assert ratio == pytest.approx(1.0)

    def test_f003_volume_volatility_zero(self, engine, base_time) -> None:
        """F003: Volatility when no events."""
        events = []

        volatility = engine.compute_f003_volume_volatility(events, base_time)

        assert volatility == 0.0

    def test_f003_volume_volatility_single_bucket(self, engine, base_time) -> None:
        """F003: Volatility when all volume is in single bucket."""
        # All events in first 15-min bucket
        events = [
            {
                "timestamp": base_time - timedelta(minutes=1),
                "usd_value": 10000.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=5),
                "usd_value": 5000.0,
            },
        ]

        volatility = engine.compute_f003_volume_volatility(events, base_time)

        # All volume in one bucket, others empty → high volatility
        assert volatility > 0.5  # Significant variation

    def test_f003_volume_volatility_uneven(self, engine, base_time) -> None:
        """F003: Volatility when volume is uneven."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=5),
                "usd_value": 100000.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=20),
                "usd_value": 10000.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=35),
                "usd_value": 10000.0,
            },
        ]

        volatility = engine.compute_f003_volume_volatility(events, base_time)

        # Should be > 0 due to uneven distribution
        assert volatility > 0.0

    def test_f004_time_of_day_asia(self, engine) -> None:
        """F004: Time-of-day pattern — Asia session."""
        asia_time = datetime(2026, 9, 25, 4, 0, 0, tzinfo=UTC)  # 04:00 UTC = Asia
        events = [
            {
                "timestamp": asia_time - timedelta(minutes=30),
                "usd_value": 50000.0,
            }
        ]

        patterns = engine.compute_f004_time_of_day_pattern(events, asia_time)

        assert patterns["asia"] == 50000.0
        assert patterns["europe"] == 0.0
        assert patterns["americas"] == 0.0

    def test_f004_time_of_day_europe(self, engine) -> None:
        """F004: Time-of-day pattern — Europe session."""
        europe_time = datetime(2026, 9, 25, 12, 0, 0, tzinfo=UTC)  # 12:00 UTC = Europe
        events = [
            {
                "timestamp": europe_time - timedelta(minutes=30),
                "usd_value": 50000.0,
            }
        ]

        patterns = engine.compute_f004_time_of_day_pattern(events, europe_time)

        assert patterns["asia"] == 0.0
        assert patterns["europe"] == 50000.0
        assert patterns["americas"] == 0.0

    def test_f004_time_of_day_americas(self, engine) -> None:
        """F004: Time-of-day pattern — Americas session."""
        americas_time = datetime(2026, 9, 25, 20, 0, 0, tzinfo=UTC)  # 20:00 UTC = Americas
        events = [
            {
                "timestamp": americas_time - timedelta(minutes=30),
                "usd_value": 50000.0,
            }
        ]

        patterns = engine.compute_f004_time_of_day_pattern(events, americas_time)

        assert patterns["asia"] == 0.0
        assert patterns["europe"] == 0.0
        assert patterns["americas"] == 50000.0

    def test_f005_source_concentration_monopoly(self, engine, base_time) -> None:
        """F005: Source concentration — single source (monopoly)."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "source": "binance",
                "usd_value": 100000.0,
            }
        ]

        hhi = engine.compute_f005_source_concentration(events, base_time)

        # Single source → HHI = 1.0
        assert hhi == pytest.approx(1.0)

    def test_f005_source_concentration_equal(self, engine, base_time) -> None:
        """F005: Source concentration — equal distribution."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "source": "binance",
                "usd_value": 50000.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=60),
                "source": "coinglass",
                "usd_value": 50000.0,
            },
        ]

        hhi = engine.compute_f005_source_concentration(events, base_time)

        # Equal sources → HHI = 0.5^2 + 0.5^2 = 0.5
        assert hhi == pytest.approx(0.5)

    def test_f005_source_concentration_three_equal(self, engine, base_time) -> None:
        """F005: Source concentration — three equal sources."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "source": "source_1",
                "usd_value": 33333.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=60),
                "source": "source_2",
                "usd_value": 33333.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=90),
                "source": "source_3",
                "usd_value": 33334.0,
            },
        ]

        hhi = engine.compute_f005_source_concentration(events, base_time)

        # Three equal sources → HHI ≈ 3 * (1/3)^2 = 1/3 ≈ 0.333
        assert hhi == pytest.approx(1.0 / 3, abs=0.01)

    def test_f006_regime_alignment_normal(self, engine, base_time) -> None:
        """F006: Regime alignment — at baseline."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "usd_value": 1_000_000.0,
            }
        ]

        regime = engine.compute_f006_regime_alignment(
            events, base_time, baseline_volume=1_000_000.0
        )

        # Volume = baseline → regime = 1.0
        assert regime == pytest.approx(1.0)

    def test_f006_regime_alignment_above_baseline(self, engine, base_time) -> None:
        """F006: Regime alignment — above baseline."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "usd_value": 2_000_000.0,
            }
        ]

        regime = engine.compute_f006_regime_alignment(
            events, base_time, baseline_volume=1_000_000.0
        )

        # Volume = 2x baseline → regime = 2.0
        assert regime == pytest.approx(2.0)

    def test_f006_regime_alignment_below_baseline(self, engine, base_time) -> None:
        """F006: Regime alignment — below baseline."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "usd_value": 500_000.0,
            }
        ]

        regime = engine.compute_f006_regime_alignment(
            events, base_time, baseline_volume=1_000_000.0
        )

        # Volume = 0.5x baseline → regime = 0.5
        assert regime == pytest.approx(0.5)

    def test_compute_all_features(self, engine, sample_events, base_time) -> None:
        """Compute all features (F001-F006)."""
        features = engine.compute_all_features(sample_events, base_time)

        # Verify structure
        assert "timestamp" in features
        assert "f001_volume_rolling_sum" in features
        assert "f002_long_short_ratio" in features
        assert "f003_volume_volatility" in features
        assert "f004_time_of_day" in features
        assert "f005_source_concentration" in features
        assert "f006_regime_alignment" in features

        # Verify types
        assert isinstance(features["timestamp"], str)
        assert isinstance(features["f001_volume_rolling_sum"], (int, float))
        assert isinstance(features["f002_long_short_ratio"], (int, float))
        assert isinstance(features["f003_volume_volatility"], (int, float))
        assert isinstance(features["f004_time_of_day"], dict)
        assert isinstance(features["f005_source_concentration"], (int, float))
        assert isinstance(features["f006_regime_alignment"], (int, float))

    def test_compute_all_features_empty_events(self, engine, base_time) -> None:
        """Compute features with no events."""
        features = engine.compute_all_features([], base_time)

        assert features["f001_volume_rolling_sum"] == 0.0
        assert features["f002_long_short_ratio"] == 0.0
        assert features["f003_volume_volatility"] == 0.0
        assert features["f004_time_of_day"]["asia"] == 0.0
        assert features["f005_source_concentration"] == 0.0
        assert features["f006_regime_alignment"] == 0.0

    def test_features_with_iso_string_timestamps(self, engine, base_time) -> None:
        """Handle ISO string timestamps from DuckDB."""
        events = [
            {
                "timestamp": (base_time - timedelta(minutes=30)).isoformat(),
                "side": "long",
                "usd_value": 65000.0,
            },
            {
                "timestamp": (base_time - timedelta(minutes=60)).isoformat(),
                "side": "short",
                "usd_value": 25000.0,
            },
        ]

        # Should handle ISO strings correctly
        volume = engine.compute_f001_volume_rolling_sum(events, base_time)
        assert volume == 90000.0

        ratio = engine.compute_f002_long_short_ratio(events, base_time)
        assert ratio == pytest.approx(65000.0 / 25000.0)

    def test_features_pit_compliance_multiple_observations(self, engine, base_time) -> None:
        """PIT compliance across multiple observation times."""
        events = [
            {
                "timestamp": base_time - timedelta(minutes=30),
                "usd_value": 65000.0,
            },
            {
                "timestamp": base_time - timedelta(minutes=90),
                "usd_value": 32500.0,
            },
        ]

        # Observation at T
        volume_t = engine.compute_f001_volume_rolling_sum(events, base_time)
        assert volume_t == 97500.0

        # Observation at T-30 (earlier)
        earlier_time = base_time - timedelta(minutes=30)
        volume_earlier = engine.compute_f001_volume_rolling_sum(events, earlier_time)
        # Only event at T-90 should be included
        assert volume_earlier == 32500.0

    def test_features_window_boundary_precision(self, engine, base_time) -> None:
        """Test precise window boundary handling."""
        events = [
            {
                "timestamp": base_time - timedelta(hours=4, seconds=1),
                "usd_value": 65000.0,
            },
            {
                "timestamp": base_time - timedelta(hours=4),
                "usd_value": 32500.0,
            },
        ]

        volume = engine.compute_f001_volume_rolling_sum(events, base_time)

        # Event at exactly 4-hour mark should be included (>=)
        # Event beyond 4 hours should be excluded
        assert volume == 32500.0
