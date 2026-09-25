"""Integration tests for Phase 2: Feature Store + Backtester."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.backtester.mock import MockBacktester
from src.data.contracts import DataPoint, DataSourceType, RawDataBatch
from src.feature_store.duckdb_store import DuckDBFeatureStore


class TestPhase2Integration:
    """Integration tests for Feature Store + Backtester pipeline."""

    def test_feature_store_backtester_pipeline(self, tmp_path: Path) -> None:
        """Test end-to-end Feature Store -> Backtester pipeline."""
        # Initialize Feature Store
        db_path = tmp_path / "pipeline.db"
        store = DuckDBFeatureStore(db_path)

        # Create sample data
        ts = datetime.now(UTC)
        point = DataPoint(
            timestamp=ts,
            value=65000.0,
            asset="BTC",
            source=DataSourceType.COINGECKO,
            metric="price",
        )

        # Ingest via Feature Store
        batch = RawDataBatch(datapoints=[point])
        store.ingest_raw(batch)

        # Retrieve features
        features = store.retrieve_features(
            assets=["BTC"],
            features=["raw_price"],
            start_timestamp=ts - timedelta(hours=1),
            end_timestamp=ts + timedelta(hours=1),
        )

        # Initialize Backtester
        bt = MockBacktester()
        bt.setup(
            {
                "buy_threshold": 70000,
                "sell_threshold": 60000,
                "position_size": 0.5,
            }
        )

        # Generate signals from features
        signals = bt.generate_signals(features, ts)

        # Process signals (should have LONG signal)
        assert len(signals) > 0
        for signal in signals:
            bt.on_signal(signal)

        # Verify portfolio was updated
        state = bt.get_portfolio_state()
        assert state.cash < 10000.0 or len(state.positions) > 0

        store.close()
        bt.close()

    def test_walk_forward_consistency(self, tmp_path: Path) -> None:
        """Test walk-forward prevents look-ahead bias."""
        db_path = tmp_path / "wf.db"
        store = DuckDBFeatureStore(db_path)

        # Create multiple datapoints over time
        base_ts = datetime.now(UTC)
        prices = [60000, 62000, 65000, 68000, 70000]

        for i, price in enumerate(prices):
            ts = base_ts + timedelta(hours=i)
            point = DataPoint(
                timestamp=ts,
                value=float(price),
                asset="BTC",
                source=DataSourceType.COINGECKO,
                metric="price",
            )
            batch = RawDataBatch(datapoints=[point])
            store.ingest_raw(batch)

        # Simulate walk-forward: only retrieve data up to current point
        window_start = base_ts
        window_end = base_ts + timedelta(hours=2)

        features = store.retrieve_features(
            assets=["BTC"],
            features=["raw_price"],
            start_timestamp=window_start,
            end_timestamp=window_end,
        )

        # Only first 3 datapoints should be available
        assert len(features["BTC"]) == 3

        store.close()

    def test_trade_log_completeness(self, tmp_path: Path) -> None:
        """Test all trades are logged with complete information."""
        db_path = tmp_path / "trade_log.db"
        store = DuckDBFeatureStore(db_path)

        bt = MockBacktester()
        bt.setup(
            {
                "buy_threshold": 70000,
                "sell_threshold": 60000,
                "position_size": 0.5,
            }
        )

        ts = datetime.now(UTC)

        # Create feature data
        features = {
            "BTC": pd.DataFrame({
                "raw_price": [65000.0, 75000.0],
                "timestamp": [ts, ts + timedelta(hours=1)],
            })
        }

        # Generate and process signals
        signals = bt.generate_signals(features, ts)
        for signal in signals:
            bt.on_signal(signal)

        # Generate exit signal
        signals = bt.generate_signals(
            {
                "BTC": pd.DataFrame({
                    "raw_price": [75000.0],
                    "timestamp": [ts + timedelta(hours=1)],
                })
            },
            ts + timedelta(hours=1),
        )
        for signal in signals:
            bt.on_signal(signal)

        # Verify trade log completeness
        trade_log = bt.trade_log

        if trade_log:
            trade = trade_log[0]
            assert "entry_price" in trade
            assert "exit_price" in trade
            assert "quantity" in trade
            assert "pnl" in trade
            assert "entry_time" in trade
            assert "exit_time" in trade
            assert "asset" in trade

        store.close()
        bt.close()

    def test_feature_store_no_lookahead(self, tmp_path: Path) -> None:
        """Test Feature Store compute prevents look-ahead."""
        db_path = tmp_path / "lookahead_test.db"
        store = DuckDBFeatureStore(db_path)

        base_ts = datetime.now(UTC)

        # Ingest 3 datapoints
        for i in range(3):
            ts = base_ts + timedelta(hours=i)
            point = DataPoint(
                timestamp=ts,
                value=float(60000 + i * 1000),
                asset="BTC",
                source=DataSourceType.COINGECKO,
                metric="price",
            )
            batch = RawDataBatch(datapoints=[point])
            store.ingest_raw(batch)

        # Request features only up to hour 1 (should not see hour 2)
        df = store.compute_feature(
            "raw_price",
            "BTC",
            base_ts,
            base_ts + timedelta(hours=1),
        )

        assert len(df) == 2
        assert df["value"].max() == 61000.0

        store.close()

    def test_feature_provenance_tracking(self, tmp_path: Path) -> None:
        """Test Feature Store tracks full provenance."""
        db_path = tmp_path / "prov.db"
        store = DuckDBFeatureStore(db_path)

        ts = datetime.now(UTC)
        point = DataPoint(
            timestamp=ts,
            value=65000.0,
            asset="BTC",
            source=DataSourceType.COINGECKO,
            metric="price",
            source_version="2.0",
        )

        batch = RawDataBatch(datapoints=[point])
        store.ingest_raw(batch)

        # Retrieve provenance
        prov = store.get_provenance("raw_price", "BTC", ts)

        assert "source" in prov
        assert "compute_timestamp" in prov
        assert "source_version" in prov
        assert prov["source_version"] == "2.0"

        store.close()
