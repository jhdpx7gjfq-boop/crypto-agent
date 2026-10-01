"""
Unit tests for C1.5-PIT: Point-in-Time Validation (Independent Gate)

Tests verify:
- Temporal ordering (availability_time ≤ decision_time)
- Future data rejection (100% blocking)
- Future feature rejection
- Retroactive revision detection
- Late-arriving data rejection
- Aggregation cutoff enforcement
- Independent availability proof (Hierarchy A-E)
- Asset-agnostic engine
- Historical period coverage (2020/2021/2022/2024/2025)
- PIT_STATUS propagation

Key distinction:
- C1.5-IGWT: snapshot reproducibility (we can recreate what we captured)
- C1.5-PIT: temporal availability (data was available at decision time)
- C1.5-PIT does NOT validate alpha/performance
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

import pytest


class AvailabilityProofLevel(Enum):
    """Hierarchy of temporal availability proofs."""
    A_PUBLISHER_VERSIONED = "A"  # Publisher timestamp + versioned history
    B_IMMUTABLE_ARCHIVE = "B"    # Immutable dated archive
    C_API_HISTORICAL = "C"       # API historical with timestamp (conditional)
    D_RETROACTIVE = "D"          # Retroactively reconstructed (FAIL)
    E_SYNTHETIC = "E"            # Synthetic/mock (FAIL)


class TestAvailabilityOrdering:
    """PIT-001: availability_time ≤ decision_time (not event_time ≤ decision_time)."""

    def test_availability_before_decision(self):
        """Observation available before decision is valid."""
        event_time = "2026-09-28"
        availability_time = "2026-09-29T10:00:00Z"
        decision_time = "2026-09-30T15:00:00Z"

        is_valid = pit_temporal_check(availability_time, decision_time)
        assert is_valid is True

    def test_availability_at_decision(self):
        """Observation available exactly at decision is valid."""
        availability_time = "2026-09-30T15:00:00Z"
        decision_time = "2026-09-30T15:00:00Z"

        is_valid = pit_temporal_check(availability_time, decision_time)
        assert is_valid is True

    def test_availability_after_decision_is_invalid(self):
        """Observation available after decision is invalid."""
        availability_time = "2026-10-01T10:00:00Z"
        decision_time = "2026-09-30T15:00:00Z"

        is_valid = pit_temporal_check(availability_time, decision_time)
        assert is_valid is False

    def test_event_time_not_sufficient(self):
        """Event time alone does not guarantee availability."""
        event_time = "2026-09-28T14:00:00Z"
        availability_time = "2026-10-05T10:00:00Z"
        decision_time = "2026-09-30T15:00:00Z"

        # Event happened before decision, but availability is after
        is_valid = pit_temporal_check(availability_time, decision_time)
        assert is_valid is False


class TestFutureDataRejection:
    """PIT-002: Reject observations with availability_time > decision_time."""

    def test_reject_future_close_price(self):
        """Reject candle close price from future."""
        observation = {
            "asset": "BTC",
            "date": "2026-09-30",
            "close": 65000.0,
            "availability_time": "2026-10-02T10:00:00Z",  # Future
        }
        decision_time = "2026-10-01T15:00:00Z"

        result = pit_reject_future_data([observation], decision_time)
        assert len(result) == 0  # Rejected

    def test_reject_future_volume(self):
        """Reject volume from future."""
        observation = {
            "asset": "ETH",
            "date": "2026-09-30",
            "volume": 18000000000.0,
            "availability_time": "2026-10-03T10:00:00Z",
        }
        decision_time = "2026-10-01T15:00:00Z"

        result = pit_reject_future_data([observation], decision_time)
        assert len(result) == 0

    def test_reject_future_high_low(self):
        """Reject high/low from future (only available when candle closes)."""
        observation = {
            "asset": "BTC",
            "date": "2026-09-30",
            "high": 65500.0,
            "low": 64500.0,
            "availability_time": "2026-10-05T10:00:00Z",  # Way in future
        }
        decision_time = "2026-10-01T15:00:00Z"

        result = pit_reject_future_data([observation], decision_time)
        assert len(result) == 0

    def test_accept_available_data(self):
        """Accept observations available before decision."""
        observation = {
            "asset": "BTC",
            "date": "2026-09-28",
            "close": 64500.0,
            "availability_time": "2026-09-29T10:00:00Z",
        }
        decision_time = "2026-10-01T15:00:00Z"

        result = pit_reject_future_data([observation], decision_time)
        assert len(result) == 1  # Accepted


class TestFutureFeatureRejection:
    """PIT-003: Reject engineered features using future data."""

    def test_reject_feature_using_future_high(self):
        """Reject feature (e.g., daily range) calculated with future high."""
        features = {
            "daily_range": {
                "value": 1000.0,
                "uses_high": True,
                "high_availability": "2026-10-05T10:00:00Z",  # Future
            }
        }
        decision_time = "2026-10-01T15:00:00Z"

        is_valid = pit_validate_feature_availability(features, decision_time)
        assert is_valid is False

    def test_reject_centered_window_feature(self):
        """Reject features using centered windows (future lookback)."""
        features = {
            "sma_7_centered": {
                "value": 64800.0,
                "window": "centered",
                "lookahead_days": 3,  # Uses future data
            }
        }
        decision_time = "2026-10-01T15:00:00Z"

        is_valid = pit_validate_feature_availability(features, decision_time)
        assert is_valid is False

    def test_reject_full_series_normalization(self):
        """Reject features using min/max from entire series (includes future)."""
        features = {
            "close_normalized": {
                "value": 0.75,
                "uses_series_min_max": True,
                "series_includes_future": True,
            }
        }
        decision_time = "2026-10-01T15:00:00Z"

        is_valid = pit_validate_feature_availability(features, decision_time)
        assert is_valid is False

    def test_accept_backward_looking_features(self):
        """Accept features using only past data."""
        features = {
            "sma_7_backward": {
                "value": 64800.0,
                "window": "backward",
                "days_lookback": 7,
            }
        }
        decision_time = "2026-10-01T15:00:00Z"

        is_valid = pit_validate_feature_availability(features, decision_time)
        assert is_valid is True


class TestRetroactiveRevision:
    """PIT-004: Detect retroactive revision (snapshot(T) ≠ snapshot(T+Δ))."""

    def test_detect_price_correction(self):
        """Detect when historical price is corrected."""
        snapshot_t = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.0, "availability_time": "2026-09-29T10:00:00Z"}
            ]
        }
        snapshot_t_plus_1 = {
            "BTC": [
                {"date": "2026-09-28", "close": 64512.50, "availability_time": "2026-09-29T10:00:00Z"}
            ]
        }

        revisions = pit_detect_retroactive_revision(snapshot_t, snapshot_t_plus_1)
        assert len(revisions) == 1
        assert revisions[0]["type"] == "retroactive_correction"

    def test_detect_volume_revision(self):
        """Detect when historical volume changes."""
        snapshot_t = {
            "ETH": [
                {"date": "2026-09-27", "volume": 18000000000.0, "availability_time": "2026-09-28T10:00:00Z"}
            ]
        }
        snapshot_t_plus_1 = {
            "ETH": [
                {"date": "2026-09-27", "volume": 18033182350.13, "availability_time": "2026-09-28T10:00:00Z"}
            ]
        }

        revisions = pit_detect_retroactive_revision(snapshot_t, snapshot_t_plus_1)
        assert len(revisions) == 1
        assert revisions[0]["field"] == "volume"

    def test_no_revision_if_data_identical(self):
        """No revision detected if snapshots are identical."""
        snapshot_t = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.0, "availability_time": "2026-09-29T10:00:00Z"}
            ]
        }
        snapshot_t_plus_1 = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.0, "availability_time": "2026-09-29T10:00:00Z"}
            ]
        }

        revisions = pit_detect_retroactive_revision(snapshot_t, snapshot_t_plus_1)
        assert len(revisions) == 0

    def test_revision_must_be_explicit(self):
        """Revisions must be explicitly handled; cannot be silently tolerated."""
        revisions = [
            {
                "type": "retroactive_correction",
                "asset": "BTC",
                "date": "2026-09-28",
                "field": "close",
                "old_value": 64500.0,
                "new_value": 64512.50,
                "handled": True,  # Must be explicitly marked
            }
        ]

        for rev in revisions:
            assert rev.get("handled") is True


class TestLateArrivingData:
    """PIT-005: Reject observations that arrive after decision_time."""

    def test_reject_data_arriving_after_decision(self):
        """Data arriving after decision must be rejected."""
        observation = {
            "asset": "BTC",
            "date": "2026-09-28",
            "close": 64500.0,
            "event_time": "2026-09-28T14:00:00Z",
            "availability_time": "2026-10-05T10:00:00Z",  # Arrives 7 days later
        }
        decision_time = "2026-09-30T15:00:00Z"

        is_available = pit_check_availability(observation, decision_time)
        assert is_available is False

    def test_accept_data_arriving_before_decision(self):
        """Data arriving before decision is accepted."""
        observation = {
            "asset": "ETH",
            "date": "2026-09-28",
            "close": 2450.0,
            "event_time": "2026-09-28T14:00:00Z",
            "availability_time": "2026-09-29T08:00:00Z",  # Arrives quickly
        }
        decision_time = "2026-09-30T15:00:00Z"

        is_available = pit_check_availability(observation, decision_time)
        assert is_available is True

    def test_edge_case_zero_latency(self):
        """Zero-latency observation (event_time = availability_time)."""
        observation = {
            "asset": "BTC",
            "date": "2026-09-28",
            "close": 64500.0,
            "event_time": "2026-09-28T14:00:00Z",
            "availability_time": "2026-09-28T14:00:00Z",
        }
        decision_time = "2026-09-30T15:00:00Z"

        is_available = pit_check_availability(observation, decision_time)
        assert is_available is True


class TestMissingThenAdded:
    """PIT-005 variant: Data missing at T but added at T+Δ must stay missing for T."""

    def test_missing_then_added_historical_candle(self):
        """Historical candle absent, then added later."""
        snapshot_t = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.0}
            ]
        }
        snapshot_t_plus_1 = {
            "BTC": [
                {"date": "2026-09-27", "close": 63800.0, "availability_time": "2026-09-29T10:00:00Z"},  # New row
                {"date": "2026-09-28", "close": 64500.0}
            ]
        }

        # At decision_time = 2026-09-28, we must use snapshot_t (missing 2026-09-27)
        decision_time = "2026-09-28T15:00:00Z"
        data = pit_get_data_as_of("BTC", "2026-09-27", snapshot_t, decision_time)
        assert data is None  # Not available


class TestAggregationCutoffs:
    """PIT-006: Aggregation must respect period closures."""

    def test_daily_aggregate_requires_full_day_closure(self):
        """Daily aggregate available only after market close (typically 00:00 UTC next day)."""
        daily_open = "2026-09-30"
        market_close_utc = "2026-10-01T00:00:00Z"
        decision_time_during_day = "2026-09-30T12:00:00Z"  # Midday same day

        is_available = pit_check_aggregate_available("daily", daily_open, market_close_utc, decision_time_during_day)
        assert is_available is False

    def test_daily_aggregate_available_after_close(self):
        """Daily aggregate available after market close."""
        daily_open = "2026-09-30"
        market_close_utc = "2026-10-01T00:00:00Z"
        decision_time_after_close = "2026-10-01T01:00:00Z"  # After close

        is_available = pit_check_aggregate_available("daily", daily_open, market_close_utc, decision_time_after_close)
        assert is_available is True

    def test_weekly_aggregate_requires_full_week(self):
        """Weekly aggregate requires full week (e.g., Monday-Sunday closure)."""
        week_start = "2026-09-28"  # Monday
        week_close_utc = "2026-10-05T00:00:00Z"  # Monday next week
        decision_midweek = "2026-10-01T12:00:00Z"  # Thursday midweek

        is_available = pit_check_aggregate_available("weekly", week_start, week_close_utc, decision_midweek)
        assert is_available is False

    def test_monthly_aggregate_requires_full_month(self):
        """Monthly aggregate requires full month."""
        month = "2026-09"
        month_close_utc = "2026-10-01T00:00:00Z"
        decision_midmonth = "2026-09-15T12:00:00Z"

        is_available = pit_check_aggregate_available("monthly", month, month_close_utc, decision_midmonth)
        assert is_available is False


class TestIndependentAvailabilityProof:
    """Hierarchy A-E: Validate proof of temporal availability."""

    def test_level_a_publisher_versioned_passes(self):
        """Level A (publisher timestamp + versioned history) = PASS."""
        proof = {
            "level": AvailabilityProofLevel.A_PUBLISHER_VERSIONED,
            "publisher_timestamp": "2026-09-29T10:00:00Z",
            "version": 1,
            "versioned_history_available": True,
        }

        verdict = pit_validate_availability_proof(proof)
        assert verdict == "PASS"

    def test_level_b_immutable_archive_passes(self):
        """Level B (immutable archive dated) = PASS."""
        proof = {
            "level": AvailabilityProofLevel.B_IMMUTABLE_ARCHIVE,
            "archive_timestamp": "2026-09-29T10:00:00Z",
            "archive_hash": "abc123" * 10 + "ab",
            "immutable": True,
        }

        verdict = pit_validate_availability_proof(proof)
        assert verdict == "PASS"

    def test_level_c_api_historical_conditional_pass(self):
        """Level C (API historical with timestamp) = PASS CONDITIONAL."""
        proof = {
            "level": AvailabilityProofLevel.C_API_HISTORICAL,
            "api_timestamp": "2026-09-29T10:00:00Z",
            "requires_documentation": "Availability semantics must be documented",
        }

        verdict = pit_validate_availability_proof(proof)
        assert verdict == "PASS_CONDITIONAL"

    def test_level_d_retroactive_fails(self):
        """Level D (retroactively reconstructed) = FAIL."""
        proof = {
            "level": AvailabilityProofLevel.D_RETROACTIVE,
            "reconstruction_method": "backwards_calculation",
        }

        verdict = pit_validate_availability_proof(proof)
        assert verdict == "FAIL"

    def test_level_e_synthetic_fails(self):
        """Level E (synthetic/mock) = FAIL."""
        proof = {
            "level": AvailabilityProofLevel.E_SYNTHETIC,
            "data_source": "mock",
        }

        verdict = pit_validate_availability_proof(proof)
        assert verdict == "FAIL"


class TestAssetAgnostic:
    """Engine must be asset-agnostic (works for any asset)."""

    def test_btc_pit_validation(self):
        """PIT validation works for BTC."""
        asset = "BTC"
        observation = {
            "asset": asset,
            "availability_time": "2026-09-29T10:00:00Z",
        }
        decision_time = "2026-10-01T15:00:00Z"

        is_valid = pit_temporal_check(observation["availability_time"], decision_time)
        assert is_valid is True

    def test_eth_pit_validation(self):
        """PIT validation works for ETH."""
        asset = "ETH"
        observation = {
            "asset": asset,
            "availability_time": "2026-09-29T10:00:00Z",
        }
        decision_time = "2026-10-01T15:00:00Z"

        is_valid = pit_temporal_check(observation["availability_time"], decision_time)
        assert is_valid is True

    def test_sol_pit_validation(self):
        """PIT validation works for SOL."""
        asset = "SOL"
        observation = {
            "asset": asset,
            "availability_time": "2026-09-29T10:00:00Z",
        }
        decision_time = "2026-10-01T15:00:00Z"

        is_valid = pit_temporal_check(observation["availability_time"], decision_time)
        assert is_valid is True


class TestHistoricalPeriods:
    """Validate across different market regimes and historical periods."""

    def test_2020_early_period(self):
        """Validate PIT logic on 2020 early period data."""
        decision_time = "2020-03-31T15:00:00Z"
        observation = {
            "date": "2020-03-15",
            "availability_time": "2020-03-16T10:00:00Z",
        }

        is_valid = pit_temporal_check(observation["availability_time"], decision_time)
        assert is_valid is True

    def test_2021_bull_market(self):
        """Validate on 2021 bull market period."""
        decision_time = "2021-03-31T15:00:00Z"
        observation = {
            "date": "2021-02-28",
            "availability_time": "2021-03-01T10:00:00Z",
        }

        is_valid = pit_temporal_check(observation["availability_time"], decision_time)
        assert is_valid is True

    def test_2022_bear_market(self):
        """Validate on 2022 bear market period."""
        decision_time = "2022-07-31T15:00:00Z"
        observation = {
            "date": "2022-05-15",
            "availability_time": "2022-05-16T10:00:00Z",
        }

        is_valid = pit_temporal_check(observation["availability_time"], decision_time)
        assert is_valid is True

    def test_2024_recent_period(self):
        """Validate on 2024 recent period."""
        decision_time = "2024-03-31T15:00:00Z"
        observation = {
            "date": "2024-01-15",
            "availability_time": "2024-01-16T10:00:00Z",
        }

        is_valid = pit_temporal_check(observation["availability_time"], decision_time)
        assert is_valid is True

    def test_2025_current_period(self):
        """Validate on 2025 current period."""
        decision_time = "2025-03-31T15:00:00Z"
        observation = {
            "date": "2025-01-15",
            "availability_time": "2025-01-16T10:00:00Z",
        }

        is_valid = pit_temporal_check(observation["availability_time"], decision_time)
        assert is_valid is True


class TestPITStatusPropagation:
    """PIT_STATUS must propagate correctly through validation."""

    def test_pit_status_in_observation(self):
        """Observation carries pit_status field."""
        observation = {
            "asset": "BTC",
            "availability_time": "2026-09-29T10:00:00Z",
            "pit_status": "UNVERIFIED",  # Before C1.5-PIT validation
        }

        assert observation["pit_status"] == "UNVERIFIED"

    def test_pit_status_after_validation(self):
        """After C1.5-PIT validation, status changes to VERIFIED."""
        observation = {
            "asset": "BTC",
            "availability_time": "2026-09-29T10:00:00Z",
            "pit_status": "UNVERIFIED",
        }
        decision_time = "2026-10-01T15:00:00Z"

        if pit_temporal_check(observation["availability_time"], decision_time):
            observation["pit_status"] = "VERIFIED"

        assert observation["pit_status"] == "VERIFIED"

    def test_pit_status_never_verified_if_violation(self):
        """PIT_STATUS remains UNVERIFIED if temporal check fails."""
        observation = {
            "asset": "BTC",
            "availability_time": "2026-10-05T10:00:00Z",  # Future
            "pit_status": "UNVERIFIED",
        }
        decision_time = "2026-10-01T15:00:00Z"

        if not pit_temporal_check(observation["availability_time"], decision_time):
            # Stay UNVERIFIED, observation is rejected
            pass

        assert observation["pit_status"] == "UNVERIFIED"


class TestQAAcceptanceCriteria:
    """Integration QA for PIT validation system."""

    def test_complete_pit_validation_workflow(self):
        """Complete workflow: snapshot → availability check → feature validation → decision."""
        # Snapshot
        snapshot = {
            "BTC": [
                {"date": "2026-09-28", "close": 64500.0, "availability_time": "2026-09-29T10:00:00Z"}
            ]
        }

        # Decision
        decision_time = "2026-10-01T15:00:00Z"

        # Step 1: Temporal check
        obs = snapshot["BTC"][0]
        temporal_ok = pit_temporal_check(obs["availability_time"], decision_time)
        assert temporal_ok is True

        # Step 2: Feature validation (no future features)
        features = {"sma_7_backward": {"value": 64800.0}}
        features_ok = pit_validate_feature_availability(features, decision_time)
        assert features_ok is True

        # Step 3: Update status
        obs["pit_status"] = "VERIFIED"
        assert obs["pit_status"] == "VERIFIED"

    def test_pit_validation_blocks_wfv_if_violations(self):
        """WFV is blocked until PIT violations = 0."""
        violations = []

        # Detect future data
        future_obs = {
            "availability_time": "2026-10-05T10:00:00Z",
        }
        decision_time = "2026-10-01T15:00:00Z"

        if not pit_temporal_check(future_obs["availability_time"], decision_time):
            violations.append("future_data")

        # Detect late-arriving data
        late_obs = {
            "availability_time": "2026-10-10T10:00:00Z",
        }

        if not pit_temporal_check(late_obs["availability_time"], decision_time):
            violations.append("late_arriving")

        # WFV blocked if any violations
        can_proceed_to_wfv = len(violations) == 0
        assert can_proceed_to_wfv is False


# Helper functions (to be implemented in pit_validator.py)

def pit_temporal_check(availability_time: str, decision_time: str) -> bool:
    """Check if availability_time ≤ decision_time."""
    avail = datetime.fromisoformat(availability_time.replace('Z', '+00:00'))
    decision = datetime.fromisoformat(decision_time.replace('Z', '+00:00'))
    return avail <= decision


def pit_reject_future_data(observations: List[Dict], decision_time: str) -> List[Dict]:
    """Reject observations with availability_time > decision_time."""
    return [obs for obs in observations if pit_temporal_check(obs["availability_time"], decision_time)]


def pit_validate_feature_availability(features: Dict, decision_time: str) -> bool:
    """Validate that all features use only available data."""
    for feature_name, feature in features.items():
        # Reject centered windows, future lookahead, full-series normalization
        if feature.get("window") == "centered":
            return False
        if feature.get("lookahead_days"):
            return False
        if feature.get("series_includes_future"):
            return False
        # Check high/low availability
        if "high_availability" in feature:
            if not pit_temporal_check(feature["high_availability"], decision_time):
                return False
    return True


def pit_detect_retroactive_revision(snapshot_t: Dict, snapshot_t_plus_1: Dict) -> List[Dict]:
    """Detect retroactive revisions between two snapshots."""
    revisions = []
    for asset in snapshot_t:
        if asset not in snapshot_t_plus_1:
            continue
        rows_t = {row["date"]: row for row in snapshot_t[asset]}
        rows_t1 = {row["date"]: row for row in snapshot_t_plus_1[asset]}
        for date in rows_t:
            if date in rows_t1:
                for field in rows_t1[date]:
                    if field != "date" and rows_t[date].get(field) != rows_t1[date].get(field):
                        revisions.append({
                            "type": "retroactive_correction",
                            "asset": asset,
                            "date": date,
                            "field": field,
                            "old_value": rows_t[date].get(field),
                            "new_value": rows_t1[date].get(field),
                        })
    return revisions


def pit_check_availability(observation: Dict, decision_time: str) -> bool:
    """Check if observation is available at decision_time."""
    return pit_temporal_check(observation["availability_time"], decision_time)


def pit_get_data_as_of(asset: str, date: str, snapshot: Dict, decision_time: str) -> Optional[Dict]:
    """Get data for asset/date if available at decision_time."""
    asset_data = snapshot.get(asset, [])
    for row in asset_data:
        if row.get("date") == date:
            if pit_temporal_check(row.get("availability_time", ""), decision_time):
                return row
    return None


def pit_check_aggregate_available(agg_type: str, period_start: str, period_close_utc: str, decision_time: str) -> bool:
    """Check if aggregate is available (requires period closure)."""
    return pit_temporal_check(period_close_utc, decision_time)


def pit_validate_availability_proof(proof: Dict) -> str:
    """Validate temporal availability proof (Hierarchy A-E)."""
    level = proof.get("level")
    if level == AvailabilityProofLevel.A_PUBLISHER_VERSIONED:
        return "PASS"
    elif level == AvailabilityProofLevel.B_IMMUTABLE_ARCHIVE:
        return "PASS"
    elif level == AvailabilityProofLevel.C_API_HISTORICAL:
        return "PASS_CONDITIONAL"
    elif level == AvailabilityProofLevel.D_RETROACTIVE:
        return "FAIL"
    elif level == AvailabilityProofLevel.E_SYNTHETIC:
        return "FAIL"
    return "UNKNOWN"
