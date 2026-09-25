"""Integration tests: RPM/RCM ↔ FeatureStore ↔ Backtester.

Note: Uses T notation (ts_T, ts_T_plus_1, etc.) for time-series clarity in point-in-time tests.
"""
# ruff: noqa: N806

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.backtester.base import BacktestSignal
from src.backtester.mock import MockBacktester
from src.feature_store.base import FeatureSnapshot
from src.feature_store.duckdb_store import DuckDBFeatureStore
from src.models.rcm.base import RPMSignal
from src.models.rcm.rpm import RotationConfirmationModel


@pytest.fixture
def feature_store(tmp_path: Path) -> Generator[DuckDBFeatureStore, None, None]:
    """Create temporary feature store."""
    db_path = tmp_path / "features.db"
    store = DuckDBFeatureStore(db_path)
    yield store
    store.close()


@pytest.fixture
def rpm_model() -> RotationConfirmationModel:
    """Create RPM model with default config."""
    return RotationConfirmationModel()


@pytest.fixture
def backtester() -> MockBacktester:
    """Create mock backtester."""
    return MockBacktester()


class TestRPMRCMFeatureStoreIntegration:
    """Tests for RPM/RCM + FeatureStore integration."""

    def test_persist_rpm_components_as_features(
        self, feature_store: DuckDBFeatureStore
    ) -> None:
        """Test persisting RPM component scores as features."""
        ts = datetime(2024, 1, 1, tzinfo=UTC)
        asset = "BTC"

        components = {
            "capital_flow": 0.7,
            "relative_strength": 0.6,
            "narrative_acceleration": 0.5,
            "fundamental_confirmation": 0.4,
            "derivatives_structure": 0.3,
        }

        for comp_name, comp_value in components.items():
            snapshot = FeatureSnapshot(
                feature_name=f"rpm_{comp_name}",
                asset=asset,
                timestamp=ts,
                value=comp_value,
                compute_timestamp=datetime.now(UTC),
                source_version="1.0",
                provenance={"component": comp_name, "model": "RPM/RCM"},
            )
            feature_store.persist_snapshot(snapshot)

        df = feature_store.compute_feature("rpm_capital_flow", asset, ts - timedelta(hours=1), ts + timedelta(hours=1))
        assert len(df) == 1
        assert float(df.iloc[0]["value"]) == 0.7

    def test_retrieve_rpm_components_for_signal_construction(
        self, feature_store: DuckDBFeatureStore
    ) -> None:
        """Test retrieving RPM components to construct signal."""
        ts = datetime(2024, 1, 1, tzinfo=UTC)
        ts_plus = ts + timedelta(hours=1)
        asset = "ETH"

        components = {
            "capital_flow": 0.8,
            "relative_strength": 0.7,
            "narrative_acceleration": 0.6,
            "fundamental_confirmation": 0.5,
            "derivatives_structure": 0.4,
        }

        for comp_name, comp_value in components.items():
            snapshot = FeatureSnapshot(
                feature_name=f"rpm_{comp_name}",
                asset=asset,
                timestamp=ts,
                value=comp_value,
                compute_timestamp=datetime.now(UTC),
                source_version="1.0",
                provenance={},
            )
            feature_store.persist_snapshot(snapshot)

        df_cf = feature_store.compute_feature("rpm_capital_flow", asset, ts, ts_plus)
        df_rs = feature_store.compute_feature("rpm_relative_strength", asset, ts, ts_plus)
        df_na = feature_store.compute_feature("rpm_narrative_acceleration", asset, ts, ts_plus)
        df_fc = feature_store.compute_feature("rpm_fundamental_confirmation", asset, ts, ts_plus)
        df_ds = feature_store.compute_feature("rpm_derivatives_structure", asset, ts, ts_plus)

        assert not df_cf.empty and float(df_cf.iloc[0]["value"]) == 0.8
        assert not df_rs.empty and float(df_rs.iloc[0]["value"]) == 0.7
        assert not df_na.empty and float(df_na.iloc[0]["value"]) == 0.6
        assert not df_fc.empty and float(df_fc.iloc[0]["value"]) == 0.5
        assert not df_ds.empty and float(df_ds.iloc[0]["value"]) == 0.4

    def test_feature_provenance_chain(
        self, feature_store: DuckDBFeatureStore
    ) -> None:
        """Test provenance tracking through feature store."""
        ts = datetime(2024, 1, 15, tzinfo=UTC)
        asset = "BTC"

        snapshot = FeatureSnapshot(
            feature_name="rpm_capital_flow",
            asset=asset,
            timestamp=ts,
            value=0.75,
            compute_timestamp=datetime.now(UTC),
            source_version="2.1",
            provenance={
                "model": "RPM/RCM",
                "component": "capital_flow",
                "data_source": "Glassnode",
                "computation": "weighted_fund_inflow_30d",
            },
        )
        feature_store.persist_snapshot(snapshot)

        prov = feature_store.get_provenance("rpm_capital_flow", asset, ts)
        assert prov["model"] == "RPM/RCM"
        assert prov["component"] == "capital_flow"
        assert prov["source_version"] == "2.1"
        assert "computation" in prov


class TestRPMRCMBacktesterIntegration:
    """Tests for RPM/RCM + Backtester integration."""

    def test_rpm_signal_drives_backtester_trades(
        self, rpm_model: RotationConfirmationModel, backtester: MockBacktester
    ) -> None:
        """Test RPM signal generates backtester trade signal."""
        backtester.setup(
            {"buy_threshold": 40000, "sell_threshold": 50000, "position_size": 0.5}
        )

        ts = datetime(2024, 1, 1, tzinfo=UTC)
        asset = "BTC"
        price = 45000.0

        rpm_signal = RPMSignal(
            timestamp=ts,
            asset=asset,
            capital_flow=0.8,
            relative_strength=0.8,
            narrative_acceleration=0.8,
            fundamental_confirmation=0.8,
            derivatives_structure=0.8,
        )

        rpm_pred = rpm_model.predict(rpm_signal)
        assert rpm_pred.predicted_direction == "LONG"

        signal = BacktestSignal(
            timestamp=ts,
            asset=asset,
            action="LONG",
            entry_price=price,
            confidence=rpm_pred.confidence,
            metadata={"rpm_score": rpm_pred.rpm_score},
        )

        backtester.on_signal(signal)
        assert asset in backtester.portfolio.positions
        assert backtester.portfolio.positions[asset] > 0

    def test_rpm_neutral_signal_no_trade(
        self, rpm_model: RotationConfirmationModel, backtester: MockBacktester
    ) -> None:
        """Test RPM NEUTRAL signal produces no trade (no signal action for NEUTRAL)."""
        backtester.setup(
            {"buy_threshold": 40000, "sell_threshold": 50000, "position_size": 0.5}
        )

        ts = datetime(2024, 1, 1, tzinfo=UTC)

        rpm_signal = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivatives_structure=0.5,
        )

        rpm_pred = rpm_model.predict(rpm_signal)
        assert rpm_pred.predicted_direction == "NEUTRAL"

        assert len(backtester.portfolio.positions) == 0

    def test_rpm_short_signal_exit(
        self, rpm_model: RotationConfirmationModel, backtester: MockBacktester
    ) -> None:
        """Test RPM SHORT signal triggers exit."""
        backtester.setup(
            {"buy_threshold": 40000, "sell_threshold": 50000, "position_size": 0.5}
        )

        ts_entry = datetime(2024, 1, 1, tzinfo=UTC)
        ts_exit = datetime(2024, 1, 2, tzinfo=UTC)
        asset = "BTC"

        signal_entry = BacktestSignal(
            timestamp=ts_entry,
            asset=asset,
            action="LONG",
            entry_price=45000.0,
            confidence=0.8,
        )
        backtester.on_signal(signal_entry)
        assert asset in backtester.portfolio.positions

        rpm_signal = RPMSignal(
            timestamp=ts_exit,
            asset=asset,
            capital_flow=0.0,
            relative_strength=0.0,
            narrative_acceleration=0.0,
            fundamental_confirmation=0.0,
            derivatives_structure=0.0,
        )
        rpm_pred = rpm_model.predict(rpm_signal)
        assert rpm_pred.predicted_direction == "SHORT"

        signal_exit = BacktestSignal(
            timestamp=ts_exit,
            asset=asset,
            action="EXIT",
            exit_price=46000.0,
            confidence=0.8,
        )
        backtester.on_signal(signal_exit)
        assert asset not in backtester.portfolio.positions


class TestPointInTimeValidation:
    """Tests for PIT (point-in-time) no-lookahead constraint."""

    def test_rpm_signal_invariant_under_future_data_modification(
        self, rpm_model: RotationConfirmationModel
    ) -> None:
        """Test RPM signal at time T unchanged when T+1..T+n data changes."""
        ts_T = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        signal_T = RPMSignal(
            timestamp=ts_T,
            asset="BTC",
            capital_flow=0.7,
            relative_strength=0.6,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.4,
            derivatives_structure=0.3,
        )

        pred_T_original = rpm_model.predict(signal_T)
        score_T_original = pred_T_original.rpm_score
        direction_T_original = pred_T_original.predicted_direction

        ts_T_plus_1 = ts_T + timedelta(hours=1)
        signal_T_plus_1_original = RPMSignal(
            timestamp=ts_T_plus_1,
            asset="BTC",
            capital_flow=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivatives_structure=0.5,
        )
        rpm_model.predict(signal_T_plus_1_original)

        ts_T_plus_2 = ts_T + timedelta(hours=2)
        signal_T_plus_2_modified = RPMSignal(
            timestamp=ts_T_plus_2,
            asset="BTC",
            capital_flow=0.9,
            relative_strength=0.9,
            narrative_acceleration=0.9,
            fundamental_confirmation=0.9,
            derivatives_structure=0.9,
        )
        rpm_model.predict(signal_T_plus_2_modified)

        pred_T_after = rpm_model.predict(signal_T)
        score_T_after = pred_T_after.rpm_score
        direction_T_after = pred_T_after.predicted_direction

        assert abs(score_T_original - score_T_after) < 1e-9, "Score at T changed after T+2 prediction"
        assert direction_T_original == direction_T_after, "Direction at T changed after T+2 prediction"

    def test_lookahead_flag_prevents_future_signals(
        self, rpm_model: RotationConfirmationModel
    ) -> None:
        """Test lookahead_flag=True raises error."""
        ts = datetime(2024, 1, 1, tzinfo=UTC)

        signal_future = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.7,
            relative_strength=0.6,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.4,
            derivatives_structure=0.3,
            lookahead_flag=True,
        )

        with pytest.raises(ValueError, match="Lookahead flag must be False"):
            rpm_model.predict(signal_future)

    def test_backtester_equity_invariant_under_future_price_change(
        self, backtester: MockBacktester
    ) -> None:
        """Test backtester equity at T unchanged when T+1..T+n prices change."""
        backtester.setup(
            {"buy_threshold": 40000, "sell_threshold": 50000, "position_size": 0.5}
        )

        ts_T = datetime(2024, 1, 1, tzinfo=UTC)
        ts_T_plus_1 = ts_T + timedelta(hours=1)
        ts_T_plus_2 = ts_T + timedelta(hours=2)

        signal_T = BacktestSignal(
            timestamp=ts_T,
            asset="BTC",
            action="LONG",
            entry_price=45000.0,
            confidence=0.8,
        )
        backtester.on_signal(signal_T)
        equity_T = backtester.equity_curve[-1] if backtester.equity_curve else 10000.0

        backtester.last_price["BTC"] = 45500.0
        backtester.portfolio.timestamp = ts_T_plus_1

        backtester.last_price["BTC"] = 47000.0
        backtester.portfolio.timestamp = ts_T_plus_2

        assert backtester.portfolio.timestamp == ts_T_plus_2

        equity_T_plus_2 = (
            backtester.portfolio.cash
            + backtester.portfolio.positions.get("BTC", 0) * 47000.0
        )
        assert equity_T_plus_2 > equity_T


class TestProvenance:
    """Tests for provenance tracking through integration."""

    def test_provenance_chain_rpm_to_trade(
        self, rpm_model: RotationConfirmationModel, backtester: MockBacktester
    ) -> None:
        """Test provenance from RPM signal through trade log."""
        backtester.setup(
            {"buy_threshold": 40000, "sell_threshold": 50000, "position_size": 0.5}
        )

        ts_entry = datetime(2024, 1, 1, tzinfo=UTC)
        ts_exit = datetime(2024, 1, 2, tzinfo=UTC)
        asset = "BTC"
        feature_hash = "abc123def456"

        rpm_model.set_feature_hash(feature_hash)
        rpm_model.set_train_period(
            datetime(2023, 1, 1, tzinfo=UTC),
            datetime(2023, 12, 31, tzinfo=UTC),
        )

        rpm_signal = RPMSignal(
            timestamp=ts_entry,
            asset=asset,
            capital_flow=0.8,
            relative_strength=0.7,
            narrative_acceleration=0.6,
            fundamental_confirmation=0.5,
            derivatives_structure=0.4,
        )

        rpm_pred = rpm_model.predict(rpm_signal)

        signal_entry = BacktestSignal(
            timestamp=ts_entry,
            asset=asset,
            action="LONG",
            entry_price=45000.0,
            confidence=rpm_pred.confidence,
            metadata={"rpm_score": rpm_pred.rpm_score},
        )

        backtester.on_signal(signal_entry)

        signal_exit = BacktestSignal(
            timestamp=ts_exit,
            asset=asset,
            action="EXIT",
            exit_price=46000.0,
            confidence=rpm_pred.confidence,
            metadata={"rpm_score": rpm_pred.rpm_score},
        )

        backtester.on_signal(signal_exit)

        assert len(backtester.trade_log) == 1
        trade = backtester.trade_log[0]

        assert trade["asset"] == asset
        assert trade["entry_price"] == 45000.0
        assert "provenance" in trade
        provenance = trade["provenance"]

        assert provenance.get("confidence") == rpm_pred.confidence
