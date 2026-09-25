"""Tests for RPM/RCM (Rotation Confirmation Model)."""

from datetime import UTC, datetime

import pytest

from src.models.rcm.base import RPMConfig, RPMPrediction, RPMSignal
from src.models.rcm.rpm import RotationConfirmationModel


class TestRPMConfig:
    """Tests for RPMConfig."""

    def test_default_config_weights_sum_to_one(self) -> None:
        """Test default config weights sum to 1.0."""
        cfg = RPMConfig()
        total = (
            cfg.capital_flow_weight
            + cfg.relative_strength_weight
            + cfg.narrative_acceleration_weight
            + cfg.fundamental_confirmation_weight
            + cfg.derivatives_structure_weight
        )
        assert abs(total - 1.0) < 1e-6

    def test_config_validate_weights_raises_on_mismatch(self) -> None:
        """Test validate_weights raises if weights don't sum to 1.0."""
        cfg = RPMConfig(capital_flow_weight=0.5, relative_strength_weight=0.3)
        with pytest.raises(ValueError):
            cfg.validate_weights()

    def test_config_frozen_thresholds(self) -> None:
        """Test config has frozen B-004 thresholds."""
        cfg = RPMConfig()
        assert cfg.long_threshold == 0.60
        assert cfg.neutral_threshold == 0.40
        assert cfg.lookback_days == 60


class TestRPMSignal:
    """Tests for RPMSignal."""

    def test_signal_valid(self) -> None:
        """Test valid RPMSignal creation."""
        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.7,
            relative_strength=0.6,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.4,
            derivatives_structure=0.3,
        )
        assert sig.asset == "BTC"
        assert sig.lookahead_flag is False

    def test_signal_component_bounds(self) -> None:
        """Test signal components must be [0, 1]."""
        ts = datetime.now(UTC)
        with pytest.raises(ValueError):
            RPMSignal(
                timestamp=ts,
                asset="BTC",
                capital_flow=1.5,
                relative_strength=0.5,
                narrative_acceleration=0.5,
                fundamental_confirmation=0.5,
                derivatives_structure=0.5,
            )

    def test_signal_lookahead_flag_defaults_false(self) -> None:
        """Test lookahead_flag defaults to False."""
        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivatives_structure=0.5,
        )
        assert sig.lookahead_flag is False


class TestRotationConfirmationModel:
    """Tests for RotationConfirmationModel."""

    def test_init_default_config(self) -> None:
        """Test initialization with default config."""
        model = RotationConfirmationModel()
        assert model.config.model_version == "1.0"
        assert model.config.lookback_days == 60

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        cfg = RPMConfig(model_version="2.0")
        model = RotationConfirmationModel(cfg)
        assert model.config.model_version == "2.0"

    def test_score_calculation_long_case(self) -> None:
        """Test RPM score calculation (LONG case: all 1.0)."""
        model = RotationConfirmationModel()
        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=1.0,
            relative_strength=1.0,
            narrative_acceleration=1.0,
            fundamental_confirmation=1.0,
            derivatives_structure=1.0,
        )
        score = model.score(sig)
        assert abs(score - 1.0) < 1e-6

    def test_score_calculation_neutral_case(self) -> None:
        """Test RPM score calculation (NEUTRAL case: all 0.5)."""
        model = RotationConfirmationModel()
        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivatives_structure=0.5,
        )
        score = model.score(sig)
        assert abs(score - 0.5) < 1e-6

    def test_score_calculation_short_case(self) -> None:
        """Test RPM score calculation (SHORT case: all 0.0)."""
        model = RotationConfirmationModel()
        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.0,
            relative_strength=0.0,
            narrative_acceleration=0.0,
            fundamental_confirmation=0.0,
            derivatives_structure=0.0,
        )
        score = model.score(sig)
        assert abs(score - 0.0) < 1e-6

    def test_direction_long(self) -> None:
        """Test direction classification: LONG (score >= 0.60)."""
        model = RotationConfirmationModel()
        assert model.direction(0.60) == "LONG"
        assert model.direction(1.0) == "LONG"

    def test_direction_neutral(self) -> None:
        """Test direction classification: NEUTRAL (0.40 <= score < 0.60)."""
        model = RotationConfirmationModel()
        assert model.direction(0.40) == "NEUTRAL"
        assert model.direction(0.50) == "NEUTRAL"
        assert model.direction(0.599) == "NEUTRAL"

    def test_direction_short(self) -> None:
        """Test direction classification: SHORT (score < 0.40)."""
        model = RotationConfirmationModel()
        assert model.direction(0.0) == "SHORT"
        assert model.direction(0.39) == "SHORT"

    def test_predict_long_signal(self) -> None:
        """Test prediction generation (LONG case)."""
        model = RotationConfirmationModel()
        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.8,
            relative_strength=0.7,
            narrative_acceleration=0.6,
            fundamental_confirmation=0.5,
            derivatives_structure=0.4,
        )
        pred = model.predict(sig)

        assert isinstance(pred, RPMPrediction)
        assert pred.asset == "BTC"
        assert pred.predicted_direction == "LONG"
        assert pred.confidence > 0
        assert "model_version" in pred.provenance
        assert "component_scores" in pred.provenance

    def test_predict_short_signal(self) -> None:
        """Test prediction generation (SHORT case)."""
        model = RotationConfirmationModel()
        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="ETH",
            capital_flow=0.2,
            relative_strength=0.1,
            narrative_acceleration=0.0,
            fundamental_confirmation=0.0,
            derivatives_structure=0.0,
        )
        pred = model.predict(sig)

        assert pred.predicted_direction == "SHORT"

    def test_predict_lookahead_flag_raises(self) -> None:
        """Test predict raises if lookahead_flag is True."""
        model = RotationConfirmationModel()
        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivatives_structure=0.5,
            lookahead_flag=True,
        )
        with pytest.raises(ValueError):
            model.predict(sig)

    def test_batch_predict(self) -> None:
        """Test batch prediction."""
        model = RotationConfirmationModel()
        ts = datetime.now(UTC)
        sigs = [
            RPMSignal(
                timestamp=ts,
                asset="BTC",
                capital_flow=0.8,
                relative_strength=0.8,
                narrative_acceleration=0.8,
                fundamental_confirmation=0.8,
                derivatives_structure=0.8,
            ),
            RPMSignal(
                timestamp=ts,
                asset="ETH",
                capital_flow=0.2,
                relative_strength=0.1,
                narrative_acceleration=0.0,
                fundamental_confirmation=0.0,
                derivatives_structure=0.0,
            ),
        ]
        preds = model.batch_predict(sigs)

        assert len(preds) == 2
        assert preds[0].predicted_direction == "LONG"
        assert preds[1].predicted_direction == "SHORT"

    def test_train_period_provenance(self) -> None:
        """Test train period is recorded in provenance."""
        model = RotationConfirmationModel()
        start = datetime(2023, 1, 1, tzinfo=UTC)
        end = datetime(2023, 12, 31, tzinfo=UTC)
        model.set_train_period(start, end)

        ts = datetime(2024, 1, 1, tzinfo=UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivatives_structure=0.5,
        )
        pred = model.predict(sig)

        assert "train_period" in pred.provenance
        assert pred.provenance["train_period"] is not None

    def test_feature_hash_provenance(self) -> None:
        """Test feature set hash is recorded in provenance."""
        model = RotationConfirmationModel()
        model.set_feature_hash("abc123def456")

        ts = datetime.now(UTC)
        sig = RPMSignal(
            timestamp=ts,
            asset="BTC",
            capital_flow=0.5,
            relative_strength=0.5,
            narrative_acceleration=0.5,
            fundamental_confirmation=0.5,
            derivatives_structure=0.5,
        )
        pred = model.predict(sig)

        assert pred.provenance["feature_set_hash"] == "abc123def456"
