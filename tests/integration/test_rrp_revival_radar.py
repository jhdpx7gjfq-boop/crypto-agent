"""Integration tests for Phase 7 RRP Revival Radar.

Tests all components: detector, store, enricher, validator.
"""

import pytest
from datetime import datetime, timedelta

from src.layers.layer7_rrp import (
    RevivalDetector,
    ImmutableSnapshotStore,
    MetricSnapshot,
    SnapshotValidator,
    FeatureEnricher,
    RevivalValidator,
)


class TestRevivalDetector:
    """Test revival detection engine."""

    @pytest.fixture
    def detector(self):
        return RevivalDetector()

    def test_early_signs_volume_acceleration(self, detector):
        """Detect early revival signs from volume spike."""
        current_metrics = {
            "volume_7d": 1000.0,
            "dau": 5000,
            "transaction_volume": 50000,
            "whale_activity_change": 20.0,
        }
        historical_metrics = {
            "avg_volume": 200.0,
            "baseline_dau": 2000,
            "baseline_tx": 10000,
            "dormancy_days": 120,
        }
        social_data = {"mentions_7d": 50, "mentions_14d_prior": 20, "sentiment_score": 60}
        price_data = {
            "current_price": 0.50,
            "base_price": 0.30,
            "months_since_bottom": 3,
            "formation_strength": "moderate",
        }

        analysis = detector.detect_revival(
            "REVIVAL_TEST",
            current_metrics,
            historical_metrics,
            social_data,
            price_data,
        )

        assert analysis.overall_revival_score > 50
        assert analysis.revival_stage in ["early_signs", "emerging"]
        assert analysis.revival_signal.confidence > 0.4

    def test_emerging_multi_signal_confirmation(self, detector):
        """Detect emerging revival with multiple signals."""
        current_metrics = {
            "volume_7d": 5000.0,
            "dau": 15000,
            "transaction_volume": 200000,
            "whale_activity_change": 80.0,
        }
        historical_metrics = {
            "avg_volume": 1000.0,
            "baseline_dau": 5000,
            "baseline_tx": 50000,
            "dormancy_days": 180,
        }
        social_data = {"mentions_7d": 500, "mentions_14d_prior": 50, "sentiment_score": 75}
        price_data = {
            "current_price": 2.0,
            "base_price": 1.0,
            "months_since_bottom": 6,
            "formation_strength": "strong",
        }

        analysis = detector.detect_revival(
            "EMERGING_TEST",
            current_metrics,
            historical_metrics,
            social_data,
            price_data,
        )

        assert analysis.overall_revival_score > 65
        assert analysis.revival_stage in ["emerging", "confirmed"]
        assert analysis.revival_signal.momentum_direction == "accelerating"

    def test_dormant_no_signals(self, detector):
        """Dormant asset with no revival signals."""
        current_metrics = {
            "volume_7d": 100.0,
            "dau": 1000,
            "transaction_volume": 5000,
            "whale_activity_change": 0.0,
        }
        historical_metrics = {
            "avg_volume": 200.0,
            "baseline_dau": 2000,
            "baseline_tx": 10000,
            "dormancy_days": 300,
        }
        social_data = {"mentions_7d": 5, "mentions_14d_prior": 3, "sentiment_score": 20}
        price_data = {
            "current_price": 0.05,
            "base_price": 0.04,
            "months_since_bottom": 12,
            "formation_strength": "weak",
        }

        analysis = detector.detect_revival(
            "DORMANT_TEST",
            current_metrics,
            historical_metrics,
            social_data,
            price_data,
        )

        assert analysis.overall_revival_score < 40
        assert analysis.revival_stage == "dormant"

    def test_revival_stage_progression(self, detector):
        """Test stage progression over time."""
        asset = "STAGE_PROGRESSION"
        stages_seen = []

        for i, multiplier in enumerate([0.5, 1.5, 3.0, 5.0]):
            metrics = {
                "volume_7d": 100.0 * multiplier,
                "dau": 1000 * int(multiplier),
                "transaction_volume": 5000 * multiplier,
                "whale_activity_change": 10.0 * multiplier,
            }
            historical = {
                "avg_volume": 100.0,
                "baseline_dau": 1000,
                "baseline_tx": 5000,
                "dormancy_days": 180,
            }
            social = {"mentions_7d": 10 * int(multiplier), "mentions_14d_prior": 5, "sentiment_score": 50}
            price = {
                "current_price": 1.0 * multiplier,
                "base_price": 1.0,
                "months_since_bottom": 6,
                "formation_strength": "moderate",
            }

            analysis = detector.detect_revival(asset, metrics, historical, social, price)
            stages_seen.append(analysis.revival_stage)

        # Should progress from dormant -> emerging
        assert "dormant" in stages_seen
        assert stages_seen[-1] != "dormant"


class TestSnapshotStore:
    """Test immutable snapshot storage."""

    @pytest.fixture
    def store(self):
        return ImmutableSnapshotStore()

    def test_add_valid_snapshot(self, store):
        """Add valid snapshot to store."""
        snapshot = MetricSnapshot(
            asset="SNAP_TEST",
            timestamp=datetime.utcnow(),
            volume_7d=1000.0,
            volume_14d_prior=800.0,
            dau=5000,
            transaction_volume=50000,
            whale_activity_change=10.0,
            mentions_7d=100,
            mentions_14d_prior=50,
            sentiment_score=60,
            current_price=1.5,
            base_price=1.0,
            months_since_bottom=3,
        )

        result = store.add_snapshot(snapshot)
        assert result is True
        assert len(store.snapshots["SNAP_TEST"]) == 1

    def test_reject_invalid_volume(self, store):
        """Reject snapshot with invalid volume."""
        snapshot = MetricSnapshot(
            asset="INVALID_VOL",
            timestamp=datetime.utcnow(),
            volume_7d=-100.0,  # Invalid
            volume_14d_prior=800.0,
            dau=5000,
            transaction_volume=50000,
            whale_activity_change=10.0,
            mentions_7d=100,
            mentions_14d_prior=50,
            sentiment_score=60,
            current_price=1.5,
            base_price=1.0,
            months_since_bottom=3,
        )

        result = store.add_snapshot(snapshot)
        assert result is False

    def test_get_history(self, store):
        """Retrieve historical snapshots."""
        now = datetime.utcnow()
        for i in range(5):
            snapshot = MetricSnapshot(
                asset="HISTORY_TEST",
                timestamp=now - timedelta(days=i),
                volume_7d=1000.0 + i * 100,
                volume_14d_prior=800.0,
                dau=5000 + i * 100,
                transaction_volume=50000,
                whale_activity_change=10.0,
                mentions_7d=100,
                mentions_14d_prior=50,
                sentiment_score=60,
                current_price=1.5,
                base_price=1.0,
                months_since_bottom=3,
            )
            store.add_snapshot(snapshot)

        history = store.get_history("HISTORY_TEST", days=90)
        assert len(history) == 5

    def test_baseline_metrics(self, store):
        """Calculate baseline metrics from history."""
        now = datetime.utcnow()
        for i in range(180):
            snapshot = MetricSnapshot(
                asset="BASELINE_TEST",
                timestamp=now - timedelta(days=i),
                volume_7d=1000.0,
                volume_14d_prior=900.0,
                dau=5000,
                transaction_volume=50000,
                whale_activity_change=0.0,
                mentions_7d=50,
                mentions_14d_prior=50,
                sentiment_score=50,
                current_price=1.0,
                base_price=1.0,
                months_since_bottom=12,
            )
            store.add_snapshot(snapshot)

        baseline = store.get_baseline_metrics("BASELINE_TEST")
        assert baseline is not None
        assert abs(baseline["avg_volume"] - 1000.0) < 50
        assert baseline["baseline_dau"] > 0


class TestFeatureEnricher:
    """Test feature enrichment."""

    @pytest.fixture
    def enricher(self):
        return FeatureEnricher()

    @pytest.fixture
    def sample_history(self):
        """Create sample snapshot history."""
        now = datetime.utcnow()
        snapshots = []
        for i in range(30):
            snapshot = MetricSnapshot(
                asset="ENRICH_TEST",
                timestamp=now - timedelta(days=i),
                volume_7d=500.0 + (30 - i) * 10,
                volume_14d_prior=450.0,
                dau=2000 + (30 - i) * 50,
                transaction_volume=20000 + (30 - i) * 100,
                whale_activity_change=5.0 + (30 - i) * 0.5,
                mentions_7d=20 + (30 - i),
                mentions_14d_prior=15,
                sentiment_score=50,
                current_price=1.0 + (30 - i) * 0.02,
                base_price=1.0,
                months_since_bottom=6,
            )
            snapshots.append(snapshot)
        return snapshots

    def test_enrich_with_acceleration(self, enricher, sample_history):
        """Enrich snapshot showing acceleration."""
        current = sample_history[0]
        features = enricher.enrich(current, sample_history[1:])

        assert features.volume_acceleration_7d > 0
        assert features.on_chain_acceleration > 0
        assert features.composite_signal > 30

    def test_feature_series(self, enricher, sample_history):
        """Get feature time series."""
        for snapshot in sample_history:
            enricher.enrich(snapshot, sample_history)

        series = enricher.get_feature_series("ENRICH_TEST", days=90)
        assert len(series) > 0


class TestStatisticalValidator:
    """Test walk-forward validation."""

    @pytest.fixture
    def validator(self):
        return RevivalValidator(accuracy_threshold=0.6)

    def test_record_prediction(self, validator):
        """Record revival prediction."""
        validator.record_prediction("VAL_TEST", predicted_score=75.0, predicted_stage="emerging", base_price=1.0)

        assert "VAL_TEST" in validator.prediction_history
        assert len(validator.prediction_history["VAL_TEST"]) == 1

    def test_validate_successful_prediction(self, validator):
        """Validate prediction that came true."""
        validator.record_prediction(
            "SUCCESS_TEST", predicted_score=75.0, predicted_stage="emerging", base_price=1.0
        )

        # Asset went 2x
        outcome = validator.validate_prediction(
            "SUCCESS_TEST", prediction_index=0, peak_price=2.0, peak_date=datetime.utcnow()
        )

        assert outcome is not None
        assert outcome.realized_gain == 100.0
        assert outcome.days_to_peak >= 0

    def test_validation_pass_criteria(self, validator):
        """Test validation pass/fail criteria."""
        base = 1.0
        for i in range(25):
            validator.record_prediction("MULTI_TEST", predicted_score=70.0 + i, predicted_stage="emerging", base_price=base)

        # Validate 20+ predictions
        for i in range(20):
            peak = base * (1.5 + (i % 3) * 0.5)  # 50-100% gains
            validator.validate_prediction("MULTI_TEST", prediction_index=i, peak_price=peak)

        validation = validator.validate_asset("MULTI_TEST")
        assert validation is not None
        assert validation.predictions_tested >= 20


class TestRRPFullPipeline:
    """Test complete RRP pipeline integration."""

    def test_full_revival_workflow(self):
        """Test complete workflow: detect -> store -> enrich -> validate."""
        detector = RevivalDetector()
        store = ImmutableSnapshotStore()
        enricher = FeatureEnricher()
        validator = RevivalValidator()

        asset = "FULL_PIPELINE"
        now = datetime.utcnow()

        # Simulate 90 days of metrics
        for day in range(90):
            # Gradual awakening
            accel = day / 90.0
            metrics = {
                "volume_7d": 100.0 * (1.0 + accel * 4),
                "dau": 1000 * int(1.0 + accel * 3),
                "transaction_volume": 5000 * (1.0 + accel * 3),
                "whale_activity_change": 5.0 * accel,
            }
            historical = {
                "avg_volume": 100.0,
                "baseline_dau": 1000,
                "baseline_tx": 5000,
                "dormancy_days": 180,
            }
            social = {
                "mentions_7d": int(10 * (1.0 + accel * 5)),
                "mentions_14d_prior": 10,
                "sentiment_score": 50 + int(30 * accel),
            }
            price = {
                "current_price": 1.0 * (1.0 + accel * 1),
                "base_price": 1.0,
                "months_since_bottom": 6,
                "formation_strength": "moderate",
            }

            # Detect
            analysis = detector.detect_revival(asset, metrics, historical, social, price)

            # Store
            snapshot = MetricSnapshot(
                asset=asset,
                timestamp=now - timedelta(days=day),
                volume_7d=metrics["volume_7d"],
                volume_14d_prior=metrics.get("volume_14d_prior", metrics["volume_7d"] * 0.9),
                dau=metrics["dau"],
                transaction_volume=metrics["transaction_volume"],
                whale_activity_change=metrics["whale_activity_change"],
                mentions_7d=social["mentions_7d"],
                mentions_14d_prior=social["mentions_14d_prior"],
                sentiment_score=social["sentiment_score"],
                current_price=price["current_price"],
                base_price=price["base_price"],
                months_since_bottom=price["months_since_bottom"],
            )
            store.add_snapshot(snapshot)

            # Enrich
            history = store.get_history(asset, days=90)
            if history:
                features = enricher.enrich(snapshot, history)

            # Validate
            validator.record_prediction(asset, analysis.overall_revival_score, analysis.revival_stage, price["base_price"])

        # Check results
        detector_result = detector.latest_signals[asset]
        assert detector_result.overall_revival_score > 50

        store_audit = store.audit_store(asset)
        assert store_audit["snapshots"] > 0

        enricher_audit = enricher.audit_enrichment(asset)
        assert enricher_audit["features_extracted"] > 0

        # Validate: need actual outcomes
        assert asset in validator.prediction_history


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
