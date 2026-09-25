"""Tests for liquidation label engineering — target computation."""

from datetime import UTC, datetime

import pytest

from src.validation.liquidation.labels import LiquidationLabelEngine


class TestLiquidationLabelEngine:
    """LiquidationLabelEngine tests."""

    @pytest.fixture
    def engine(self) -> LiquidationLabelEngine:
        """Create label engine."""
        return LiquidationLabelEngine(label_window_minutes=1)

    @pytest.fixture
    def observation_time(self) -> datetime:
        """Base observation time."""
        return datetime(2026, 9, 25, 18, 0, 0, tzinfo=UTC)

    def test_engine_initialization(self, engine) -> None:
        """Initialize label engine."""
        assert engine.label_window_minutes == 1
        assert engine.label_window_timedelta.total_seconds() == 60

    def test_compute_return_positive(self, engine) -> None:
        """Compute positive return."""
        # Price rises from 65000 to 65650 (+1%)
        return_value = engine.compute_return(
            price_at_t=65000.0,
            price_at_t_plus_window=65650.0,
        )

        assert return_value == pytest.approx(0.01)

    def test_compute_return_negative(self, engine) -> None:
        """Compute negative return."""
        # Price falls from 65000 to 64350 (-1%)
        return_value = engine.compute_return(
            price_at_t=65000.0,
            price_at_t_plus_window=64350.0,
        )

        assert return_value == pytest.approx(-0.01)

    def test_compute_return_zero(self, engine) -> None:
        """Compute zero return."""
        # Price unchanged
        return_value = engine.compute_return(
            price_at_t=65000.0,
            price_at_t_plus_window=65000.0,
        )

        assert return_value == pytest.approx(0.0)

    def test_compute_return_small_move(self, engine) -> None:
        """Compute small return."""
        # Price rises from 65000 to 65001 (+0.0154 bps)
        return_value = engine.compute_return(
            price_at_t=65000.0,
            price_at_t_plus_window=65001.0,
        )

        assert return_value == pytest.approx(1.0 / 65000)

    def test_compute_return_invalid_price(self, engine) -> None:
        """Handle invalid price at T."""
        return_value = engine.compute_return(
            price_at_t=0.0,
            price_at_t_plus_window=65000.0,
        )

        assert return_value == 0.0

    def test_compute_return_sign_positive(self, engine) -> None:
        """Return sign for positive movement."""
        sign = engine.compute_return_sign(
            price_at_t=65000.0,
            price_at_t_plus_window=65650.0,  # +1%
        )

        assert sign == 1

    def test_compute_return_sign_negative(self, engine) -> None:
        """Return sign for negative movement."""
        sign = engine.compute_return_sign(
            price_at_t=65000.0,
            price_at_t_plus_window=64350.0,  # -1%
        )

        assert sign == -1

    def test_compute_return_sign_flat(self, engine) -> None:
        """Return sign for flat market."""
        sign = engine.compute_return_sign(
            price_at_t=65000.0,
            price_at_t_plus_window=65000.0,  # 0%
        )

        assert sign == 0

    def test_compute_return_sign_near_zero(self, engine) -> None:
        """Return sign near zero threshold (±0.1%)."""
        # Exactly at threshold: 0.001 (not included, uses < and > not <=)
        sign_at_threshold = engine.compute_return_sign(
            price_at_t=100.0,
            price_at_t_plus_window=100.1,  # +0.1%
        )

        # Just above threshold
        sign_above = engine.compute_return_sign(
            price_at_t=100.0,
            price_at_t_plus_window=100.2,  # +0.2%
        )

        # At threshold returns flat (0), above threshold returns up (1)
        assert sign_at_threshold == 0
        assert sign_above == 1

    def test_compute_log_return_positive(self, engine) -> None:
        """Compute positive log return."""
        # Price rises from 65000 to 65650
        log_return = engine.compute_log_return(
            price_at_t=65000.0,
            price_at_t_plus_window=65650.0,
        )

        # ln(1.01) ≈ 0.00995
        assert log_return == pytest.approx(0.00995, abs=0.0001)

    def test_compute_log_return_negative(self, engine) -> None:
        """Compute negative log return."""
        # Price falls from 65000 to 64350
        log_return = engine.compute_log_return(
            price_at_t=65000.0,
            price_at_t_plus_window=64350.0,
        )

        # ln(0.99) ≈ -0.01005
        assert log_return == pytest.approx(-0.01005, abs=0.0001)

    def test_compute_log_return_large_move(self, engine) -> None:
        """Compute log return for large price move."""
        # Price doubles: log return = ln(2) ≈ 0.693
        log_return = engine.compute_log_return(
            price_at_t=65000.0,
            price_at_t_plus_window=130000.0,
        )

        assert log_return == pytest.approx(0.693, abs=0.01)

    def test_compute_log_return_half(self, engine) -> None:
        """Compute log return for 50% drop."""
        # Price halves: log return = ln(0.5) ≈ -0.693
        log_return = engine.compute_log_return(
            price_at_t=65000.0,
            price_at_t_plus_window=32500.0,
        )

        assert log_return == pytest.approx(-0.693, abs=0.01)

    def test_compute_label_complete(
        self, engine, observation_time
    ) -> None:
        """Compute complete label."""
        label = engine.compute_label(
            observation_time=observation_time,
            price_at_t=65000.0,
            price_at_t_plus_window=65650.0,
            symbol="BTCUSDT",
        )

        # Verify structure
        assert "timestamp" in label
        assert "symbol" in label
        assert "return" in label
        assert "return_sign" in label
        assert "log_return" in label
        assert "label_window_minutes" in label
        assert "price_at_t" in label
        assert "price_at_t_plus_window" in label

        # Verify values
        assert label["timestamp"] == observation_time.isoformat()
        assert label["symbol"] == "BTCUSDT"
        assert label["return"] == pytest.approx(0.01)
        assert label["return_sign"] == 1
        assert label["log_return"] == pytest.approx(0.00995, abs=0.0001)
        assert label["label_window_minutes"] == 1
        assert label["price_at_t"] == 65000.0
        assert label["price_at_t_plus_window"] == 65650.0

    def test_compute_label_negative_move(
        self, engine, observation_time
    ) -> None:
        """Compute label for negative price move."""
        label = engine.compute_label(
            observation_time=observation_time,
            price_at_t=2500.0,
            price_at_t_plus_window=2475.0,
            symbol="ETHUSDT",
        )

        assert label["return"] == pytest.approx(-0.01)
        assert label["return_sign"] == -1
        assert label["symbol"] == "ETHUSDT"

    def test_batch_compute_labels(self, engine, observation_time) -> None:
        """Compute labels for batch of observations."""
        observations = [
            {
                "observation_time": observation_time,
                "price_at_t": 65000.0,
                "price_at_t_plus_window": 65650.0,
                "symbol": "BTCUSDT",
            },
            {
                "observation_time": observation_time,
                "price_at_t": 2500.0,
                "price_at_t_plus_window": 2475.0,
                "symbol": "ETHUSDT",
            },
        ]

        labels = engine.batch_compute_labels(observations)

        assert len(labels) == 2
        assert labels[0]["symbol"] == "BTCUSDT"
        assert labels[0]["return_sign"] == 1
        assert labels[1]["symbol"] == "ETHUSDT"
        assert labels[1]["return_sign"] == -1

    def test_batch_compute_labels_empty(self, engine) -> None:
        """Compute labels for empty batch."""
        labels = engine.batch_compute_labels([])

        assert len(labels) == 0

    def test_compute_label_statistics_empty(self, engine) -> None:
        """Compute statistics on empty labels."""
        stats = engine.compute_label_statistics([])

        assert stats["count"] == 0
        assert stats["return_mean"] == 0.0
        assert stats["return_std"] == 0.0
        assert stats["sign_distribution"]["down"] == 0
        assert stats["sign_distribution"]["flat"] == 0
        assert stats["sign_distribution"]["up"] == 0

    def test_compute_label_statistics_single(self, engine, observation_time) -> None:
        """Compute statistics on single label."""
        label = engine.compute_label(
            observation_time=observation_time,
            price_at_t=65000.0,
            price_at_t_plus_window=65650.0,
        )

        stats = engine.compute_label_statistics([label])

        assert stats["count"] == 1
        assert stats["return_mean"] == pytest.approx(0.01)
        assert stats["return_std"] == pytest.approx(0.0)
        assert stats["sign_distribution"]["up"] == 1

    def test_compute_label_statistics_multiple(self, engine, observation_time) -> None:
        """Compute statistics on multiple labels."""
        labels = [
            engine.compute_label(
                observation_time=observation_time,
                price_at_t=65000.0,
                price_at_t_plus_window=65650.0,  # +1%
            ),
            engine.compute_label(
                observation_time=observation_time,
                price_at_t=65000.0,
                price_at_t_plus_window=64350.0,  # -1%
            ),
            engine.compute_label(
                observation_time=observation_time,
                price_at_t=65000.0,
                price_at_t_plus_window=65000.0,  # 0%
            ),
        ]

        stats = engine.compute_label_statistics(labels)

        assert stats["count"] == 3
        assert stats["return_mean"] == pytest.approx(0.0, abs=0.01)
        assert stats["sign_distribution"]["down"] == 1
        assert stats["sign_distribution"]["flat"] == 1
        assert stats["sign_distribution"]["up"] == 1

    def test_compute_label_statistics_distribution(self, engine, observation_time) -> None:
        """Compute statistics on distributed labels."""
        # 70% up, 20% flat, 10% down
        labels = []

        # 7 up labels
        for i in range(7):
            labels.append(
                engine.compute_label(
                    observation_time=observation_time,
                    price_at_t=65000.0,
                    price_at_t_plus_window=65650.0,
                )
            )

        # 2 flat labels
        for i in range(2):
            labels.append(
                engine.compute_label(
                    observation_time=observation_time,
                    price_at_t=65000.0,
                    price_at_t_plus_window=65000.0,
                )
            )

        # 1 down label
        labels.append(
            engine.compute_label(
                observation_time=observation_time,
                price_at_t=65000.0,
                price_at_t_plus_window=64350.0,
            )
        )

        stats = engine.compute_label_statistics(labels)

        assert stats["count"] == 10
        assert stats["sign_distribution"]["up"] == 7
        assert stats["sign_distribution"]["flat"] == 2
        assert stats["sign_distribution"]["down"] == 1

    def test_labels_pit_compliance(self, engine, observation_time) -> None:
        """Verify PIT compliance: labels use T+window price (not available at T)."""
        # Label computation requires price[T+1m], which is not available at time T
        # This tests that the label structure enforces separation of observation and label

        label = engine.compute_label(
            observation_time=observation_time,
            price_at_t=65000.0,
            price_at_t_plus_window=65650.0,
        )

        # Label should record both prices separately
        assert label["price_at_t"] == 65000.0  # Available at observation
        assert label["price_at_t_plus_window"] == 65650.0  # Available after window

        # Label timestamp matches observation time (when we made the observation)
        assert label["timestamp"] == observation_time.isoformat()

    def test_custom_window_size(self) -> None:
        """Test engine with custom label window."""
        engine_5m = LiquidationLabelEngine(label_window_minutes=5)

        assert engine_5m.label_window_minutes == 5
        assert engine_5m.label_window_timedelta.total_seconds() == 300

    def test_large_price_moves(self, engine, observation_time) -> None:
        """Test label computation with very large price moves."""
        # 10x price increase
        label_up = engine.compute_label(
            observation_time=observation_time,
            price_at_t=1.0,
            price_at_t_plus_window=10.0,
        )

        assert label_up["return"] == pytest.approx(9.0)
        assert label_up["return_sign"] == 1
        assert label_up["log_return"] == pytest.approx(2.3026, abs=0.01)

        # 90% price drop
        label_down = engine.compute_label(
            observation_time=observation_time,
            price_at_t=100.0,
            price_at_t_plus_window=10.0,
        )

        assert label_down["return"] == pytest.approx(-0.9)
        assert label_down["return_sign"] == -1
        assert label_down["log_return"] == pytest.approx(-2.3026, abs=0.01)

    def test_label_precision(self, engine, observation_time) -> None:
        """Test label computation precision."""
        # Exact 0.1% move (at threshold, not above)
        label = engine.compute_label(
            observation_time=observation_time,
            price_at_t=1000.0,
            price_at_t_plus_window=1001.0,  # +0.1%
        )

        # Return should be precise
        assert label["return"] == pytest.approx(0.001, abs=1e-6)

        # Sign at threshold returns flat (0), not up
        assert label["return_sign"] == 0

        # Just above threshold should return up
        label_above = engine.compute_label(
            observation_time=observation_time,
            price_at_t=1000.0,
            price_at_t_plus_window=1002.0,  # +0.2%
        )
        assert label_above["return"] == pytest.approx(0.002, abs=1e-6)
        assert label_above["return_sign"] == 1
