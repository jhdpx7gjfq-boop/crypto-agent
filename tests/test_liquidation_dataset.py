"""Tests for liquidation dataset engineering — IS/OOS split & validation."""

from datetime import UTC, datetime, timedelta

import pytest

from src.validation.liquidation.dataset import LiquidationDataset


class TestLiquidationDataset:
    """LiquidationDataset tests."""

    @pytest.fixture
    def dataset(self) -> LiquidationDataset:
        """Create empty dataset."""
        return LiquidationDataset()

    @pytest.fixture
    def sample_features(self) -> dict:
        """Sample feature dict."""
        return {
            "f001_volume_rolling_sum": 1_000_000.0,
            "f002_long_short_ratio": 1.5,
            "f003_volume_volatility": 0.25,
            "f004_time_of_day": {"asia": 100000.0, "europe": 500000.0, "americas": 400000.0},
            "f005_source_concentration": 0.6,
            "f006_regime_alignment": 1.2,
        }

    @pytest.fixture
    def sample_label(self) -> dict:
        """Sample label dict."""
        return {
            "return": 0.015,
            "return_sign": 1,
            "log_return": 0.0149,
        }

    @pytest.fixture
    def sample_pairs(self, sample_features, sample_label) -> LiquidationDataset:
        """Create dataset with sample pairs."""
        dataset = LiquidationDataset()
        base_time = datetime(2026, 9, 25, 0, 0, 0, tzinfo=UTC)

        # Add 100 pairs spread over 100 days
        for i in range(100):
            timestamp = base_time + timedelta(days=i)
            dataset.add_pair(
                timestamp=timestamp,
                symbol="BTCUSDT" if i % 2 == 0 else "ETHUSDT",
                features=sample_features,
                label=sample_label,
            )

        return dataset

    def test_dataset_initialization(self, dataset) -> None:
        """Initialize empty dataset."""
        assert len(dataset.pairs) == 0
        assert len(dataset.is_data) == 0
        assert len(dataset.oos_data) == 0
        assert dataset.split_timestamp is None

    def test_add_single_pair(self, dataset, sample_features, sample_label) -> None:
        """Add single pair to dataset."""
        timestamp = datetime(2026, 9, 25, 12, 0, 0, tzinfo=UTC)
        dataset.add_pair(
            timestamp=timestamp,
            symbol="BTCUSDT",
            features=sample_features,
            label=sample_label,
        )

        assert len(dataset.pairs) == 1
        pair = dataset.pairs[0]
        assert pair["timestamp"] == timestamp
        assert pair["symbol"] == "BTCUSDT"
        assert pair["f001_volume_rolling_sum"] == 1_000_000.0
        assert pair["return_sign"] == 1

    def test_add_multiple_pairs(self, dataset, sample_features, sample_label) -> None:
        """Add multiple pairs to dataset."""
        base_time = datetime(2026, 9, 25, 0, 0, 0, tzinfo=UTC)

        for i in range(10):
            timestamp = base_time + timedelta(days=i)
            dataset.add_pair(
                timestamp=timestamp,
                symbol="BTCUSDT",
                features=sample_features,
                label=sample_label,
            )

        assert len(dataset.pairs) == 10

    def test_split_chronological_basic(self, sample_pairs) -> None:
        """Split dataset chronologically."""
        is_data, oos_data = sample_pairs.split_chronological(split_ratio=0.7)

        # 70/30 split on 100 pairs = 70 IS, 30 OOS
        assert len(is_data) == 70
        assert len(oos_data) == 30

    def test_split_chronological_ordering(self, sample_pairs) -> None:
        """Verify chronological ordering after split."""
        is_data, oos_data = sample_pairs.split_chronological(split_ratio=0.7)

        # IS should come before OOS chronologically
        is_max_ts = max(p["timestamp"] for p in is_data)
        oos_min_ts = min(p["timestamp"] for p in oos_data)

        assert is_max_ts < oos_min_ts

    def test_split_chronological_50_50(self, sample_pairs) -> None:
        """Split with 50/50 ratio."""
        is_data, oos_data = sample_pairs.split_chronological(split_ratio=0.5)

        assert len(is_data) == 50
        assert len(oos_data) == 50

    def test_split_chronological_80_20(self, sample_pairs) -> None:
        """Split with 80/20 ratio."""
        is_data, oos_data = sample_pairs.split_chronological(split_ratio=0.8)

        assert len(is_data) == 80
        assert len(oos_data) == 20

    def test_split_empty_dataset(self, dataset) -> None:
        """Split empty dataset."""
        is_data, oos_data = dataset.split_chronological()

        assert len(is_data) == 0
        assert len(oos_data) == 0

    def test_split_single_pair(self, dataset, sample_features, sample_label) -> None:
        """Split dataset with single pair."""
        dataset.add_pair(
            timestamp=datetime(2026, 9, 25, 0, 0, 0, tzinfo=UTC),
            symbol="BTCUSDT",
            features=sample_features,
            label=sample_label,
        )

        is_data, oos_data = dataset.split_chronological(split_ratio=0.5)

        # With only 1 pair, should get 1 IS, 0 OOS
        assert len(is_data) >= 1 or len(oos_data) >= 1

    def test_validate_no_leakage_pass(self, sample_pairs) -> None:
        """Validate no data leakage — pass case."""
        sample_pairs.split_chronological(split_ratio=0.7)

        assert sample_pairs.validate_no_leakage() is True

    def test_validate_no_leakage_fail_overlap(self, dataset, sample_features, sample_label) -> None:
        """Validate no data leakage — fail with overlapping times."""
        base_time = datetime(2026, 9, 25, 0, 0, 0, tzinfo=UTC)

        # Add 10 pairs
        for i in range(10):
            timestamp = base_time + timedelta(days=i)
            dataset.add_pair(timestamp, "BTCUSDT", sample_features, sample_label)

        # Manually create IS/OOS with overlap
        dataset.is_data = dataset.pairs[:7]
        dataset.oos_data = dataset.pairs[5:]  # Overlaps with IS

        assert dataset.validate_no_leakage() is False

    def test_get_dataset_statistics_empty(self, dataset) -> None:
        """Get statistics from empty dataset."""
        stats = dataset.get_dataset_statistics()

        assert stats["total_pairs"] == 0
        assert stats["symbols"] == []
        assert stats["date_range"]["start"] is None

    def test_get_dataset_statistics_populated(self, sample_pairs) -> None:
        """Get statistics from populated dataset."""
        stats = sample_pairs.get_dataset_statistics()

        assert stats["total_pairs"] == 100
        assert "BTCUSDT" in stats["symbols"]
        assert "ETHUSDT" in stats["symbols"]
        assert "label_distribution" in stats
        assert "feature_statistics" in stats

    def test_get_dataset_statistics_label_distribution(self, dataset, sample_features, sample_label) -> None:
        """Verify label distribution in statistics."""
        base_time = datetime(2026, 9, 25, 0, 0, 0, tzinfo=UTC)

        # Add pairs with different labels
        label_up = {**sample_label, "return_sign": 1}
        label_down = {**sample_label, "return_sign": -1}
        label_flat = {**sample_label, "return_sign": 0}

        for i in range(5):
            dataset.add_pair(base_time + timedelta(minutes=i), "BTCUSDT", sample_features, label_up)

        for i in range(3):
            dataset.add_pair(base_time + timedelta(minutes=i + 5), "BTCUSDT", sample_features, label_down)

        for i in range(2):
            dataset.add_pair(base_time + timedelta(minutes=i + 8), "BTCUSDT", sample_features, label_flat)

        stats = dataset.get_dataset_statistics()

        assert stats["label_distribution"]["up"] == 5
        assert stats["label_distribution"]["down"] == 3
        assert stats["label_distribution"]["flat"] == 2

    def test_get_is_oos_statistics(self, sample_pairs) -> None:
        """Get separate IS/OOS statistics."""
        sample_pairs.split_chronological(split_ratio=0.7)

        stats = sample_pairs.get_is_oos_statistics()

        assert "is" in stats
        assert "oos" in stats
        assert stats["is"]["count"] == 70
        assert stats["oos"]["count"] == 30

    def test_export_to_dataframe(self, sample_pairs) -> None:
        """Export dataset to pandas DataFrame."""
        df = sample_pairs.export_to_dataframe()

        assert len(df) == 100
        assert "timestamp" in df.columns
        assert "symbol" in df.columns
        assert "f001_volume_rolling_sum" in df.columns
        assert "return_sign" in df.columns

    def test_export_to_dataframe_empty(self, dataset) -> None:
        """Export empty dataset to DataFrame."""
        df = dataset.export_to_dataframe()

        assert len(df) == 0

    def test_pit_compliance_check_pass(self, sample_pairs) -> None:
        """PIT compliance check — pass case."""
        sample_pairs.split_chronological(split_ratio=0.7)

        checks = sample_pairs.pit_compliance_check()

        assert checks["has_timestamps"] is True
        assert checks["has_features"] is True
        assert checks["has_labels"] is True
        assert checks["chronological_order"] is True
        assert checks["no_leakage"] is True

    def test_pit_compliance_check_empty(self, dataset) -> None:
        """PIT compliance check on empty dataset."""
        checks = dataset.pit_compliance_check()

        # Should pass basic checks (no data = no violations)
        assert checks["has_timestamps"] is True  # Empty set satisfies this
        assert checks["chronological_order"] is True

    def test_summary_report_structure(self, sample_pairs) -> None:
        """Verify summary report structure."""
        sample_pairs.split_chronological(split_ratio=0.7)

        report = sample_pairs.summary_report()

        # Check for key sections
        assert "Liquidation Dataset Summary" in report
        assert "Dataset Overview" in report
        assert "Label Distribution" in report
        assert "In-Sample / Out-of-Sample Split" in report
        assert "PIT Compliance Audit" in report
        assert "Feature Statistics" in report

    def test_summary_report_contains_metrics(self, sample_pairs) -> None:
        """Verify summary report contains actual metrics."""
        sample_pairs.split_chronological(split_ratio=0.7)

        report = sample_pairs.summary_report()

        # Check for specific numbers from dataset
        assert "100" in report  # Total pairs
        assert "70" in report or "69" in report  # IS pairs (70 ± 1)
        assert "30" in report or "31" in report  # OOS pairs (30 ± 1)

    def test_split_stores_timestamp(self, sample_pairs) -> None:
        """Verify split stores boundary timestamp."""
        sample_pairs.split_chronological(split_ratio=0.7)

        assert sample_pairs.split_timestamp is not None
        # Split timestamp should match last IS timestamp
        assert sample_pairs.split_timestamp == sample_pairs.is_data[-1]["timestamp"]

    def test_chronological_preservation(self, dataset, sample_features, sample_label) -> None:
        """Verify dataset maintains chronological order internally."""
        base_time = datetime(2026, 9, 25, 0, 0, 0, tzinfo=UTC)

        # Add pairs in random order
        indices = [5, 2, 8, 1, 9, 0, 3, 7, 4, 6]
        for idx in indices:
            timestamp = base_time + timedelta(days=idx)
            dataset.add_pair(timestamp, "BTCUSDT", sample_features, sample_label)

        is_data, oos_data = dataset.split_chronological(split_ratio=0.7)

        # After split, should be ordered
        for i in range(len(is_data) - 1):
            assert is_data[i]["timestamp"] <= is_data[i + 1]["timestamp"]

    def test_feature_statistics_computed(self, sample_pairs) -> None:
        """Verify feature statistics are computed."""
        stats = sample_pairs.get_dataset_statistics()

        # Check F001
        assert "f001_volume_rolling_sum" in stats["feature_statistics"]
        f001_stats = stats["feature_statistics"]["f001_volume_rolling_sum"]
        assert "mean" in f001_stats
        assert "std" in f001_stats
        assert "min" in f001_stats
        assert "max" in f001_stats

        # All values should be present
        assert f001_stats["mean"] > 0
        assert f001_stats["min"] >= 0
        assert f001_stats["max"] >= f001_stats["min"]

    def test_return_statistics_computed(self, sample_pairs) -> None:
        """Verify return statistics are computed."""
        stats = sample_pairs.get_dataset_statistics()

        assert "return_statistics" in stats
        ret_stats = stats["return_statistics"]
        assert "mean" in ret_stats
        assert "std" in ret_stats
        assert "positive_pct" in ret_stats

        # Positive percentage should be between 0 and 100
        assert 0 <= ret_stats["positive_pct"] <= 100

    def test_symbol_tracking(self, dataset, sample_features, sample_label) -> None:
        """Verify symbols are tracked correctly."""
        base_time = datetime(2026, 9, 25, 0, 0, 0, tzinfo=UTC)

        dataset.add_pair(base_time, "BTCUSDT", sample_features, sample_label)
        dataset.add_pair(base_time + timedelta(hours=1), "ETHUSDT", sample_features, sample_label)
        dataset.add_pair(base_time + timedelta(hours=2), "BNBUSDT", sample_features, sample_label)

        stats = dataset.get_dataset_statistics()

        assert "BTCUSDT" in stats["symbols"]
        assert "ETHUSDT" in stats["symbols"]
        assert "BNBUSDT" in stats["symbols"]
