"""
Unit tests for RCM Engine (narrative, fundamental, derivatives metrics)
"""

import pytest
from rcm_engine import (
    RCMEngine,
    NarrativeAccelerationMetric,
    FundamentalConfirmationMetric,
    DerivativesStructureMetric,
)


@pytest.fixture
def engine():
    return RCMEngine()


def test_narrative_acceleration_growth(engine):
    """Test narrative_acceleration with positive growth."""
    narrative_data = {
        "current_mentions": 1000,
        "prior_mentions": 500,
        "timestamp": 1000,
    }

    metric = engine.calculate_narrative_acceleration(narrative_data, "SOL")

    assert isinstance(metric, NarrativeAccelerationMetric)
    assert -1.0 <= metric.value <= 1.0
    assert metric.growth_rate > 0  # 100% growth
    assert metric.value > 0  # Positive signal


def test_narrative_acceleration_decay(engine):
    """Test narrative_acceleration with negative growth."""
    narrative_data = {
        "current_mentions": 250,
        "prior_mentions": 500,
        "timestamp": 1000,
    }

    metric = engine.calculate_narrative_acceleration(narrative_data, "SOL")

    assert metric.growth_rate < 0  # -50% decay
    assert metric.value < 0  # Negative signal


def test_narrative_acceleration_zero_prior(engine):
    """Test narrative_acceleration with zero prior mentions."""
    narrative_data = {
        "current_mentions": 100,
        "prior_mentions": 0,
        "timestamp": 1000,
    }

    metric = engine.calculate_narrative_acceleration(narrative_data, "SOL")
    assert metric.value == 0.0


def test_fundamental_confirmation_positive(engine):
    """Test fundamental_confirmation with positive metrics."""
    on_chain_metrics = {
        "market_cap_growth": 0.5,  # 50% growth
        "active_addresses_growth": 0.3,  # 30% growth
        "revenue_multiple": 25,  # P/E of 25
        "developer_activity": 0.2,  # 20% commit growth
        "timestamp": 1000,
    }

    metric = engine.calculate_fundamental_confirmation(on_chain_metrics, "AVAX")

    assert isinstance(metric, FundamentalConfirmationMetric)
    assert -1.0 <= metric.value <= 1.0
    assert len(metric.components) == 4


def test_fundamental_confirmation_components(engine):
    """Test that fundamental_confirmation computes all components."""
    on_chain_metrics = {
        "market_cap_growth": 0.5,
        "active_addresses_growth": 0.3,
        "revenue_multiple": 25,
        "developer_activity": 0.2,
        "timestamp": 1000,
    }

    metric = engine.calculate_fundamental_confirmation(on_chain_metrics, "AVAX")

    assert "market_cap_growth" in metric.components
    assert "active_addresses" in metric.components
    assert "revenue_multiple" in metric.components
    assert "developer_activity" in metric.components

    for value in metric.components.values():
        assert -1.0 <= value <= 1.0


def test_derivatives_structure_long_bias(engine):
    """Test derivatives_structure with long bias."""
    derivatives_data = {
        "funding_rate": 0.00015,  # Positive (longs paying)
        "oi_change": 0.1,  # 10% OI increase
        "ls_ratio": 1.3,  # More longs
        "timestamp": 1000,
    }

    metric = engine.calculate_derivatives_structure(derivatives_data, "BTC")

    assert isinstance(metric, DerivativesStructureMetric)
    assert -1.0 <= metric.value <= 1.0
    assert metric.funding_rate > 0
    assert metric.ls_ratio > 0


def test_derivatives_structure_short_bias(engine):
    """Test derivatives_structure with short bias."""
    derivatives_data = {
        "funding_rate": -0.00015,  # Negative (shorts paying)
        "oi_change": -0.1,  # 10% OI decrease
        "ls_ratio": 0.7,  # More shorts
        "timestamp": 1000,
    }

    metric = engine.calculate_derivatives_structure(derivatives_data, "BTC")

    assert metric.funding_rate < 0
    assert metric.oi_change < 0
    assert metric.ls_ratio < 0


def test_score_rcm_full_calculation(engine):
    """Test full RPM/RCM score calculation with all 5 components."""
    score_dict = engine.score_rcm_full(
        capital_flow=0.5,
        relative_strength=0.3,
        narrative_accel=0.2,
        fundamental_confirm=0.4,
        derivatives_struct=0.1,
    )

    # Expected: 0.25*0.5 + 0.25*0.3 + 0.20*0.2 + 0.20*0.4 + 0.10*0.1
    #         = 0.125 + 0.075 + 0.04 + 0.08 + 0.01 = 0.33
    expected = 0.125 + 0.075 + 0.04 + 0.08 + 0.01

    assert "rpm_score" in score_dict
    assert abs(score_dict["rpm_score"] - expected) < 0.01

    # Verify all components present
    assert score_dict["capital_flow"] == 0.5
    assert score_dict["relative_strength"] == 0.3
    assert score_dict["narrative_acceleration"] == 0.2
    assert score_dict["fundamental_confirmation"] == 0.4
    assert score_dict["derivatives_structure"] == 0.1


def test_score_rcm_full_range(engine):
    """Test RPM score stays in [-1, 1] range."""
    # Test extreme case: all negative
    score_dict = engine.score_rcm_full(
        capital_flow=-1.0,
        relative_strength=-1.0,
        narrative_accel=-1.0,
        fundamental_confirm=-1.0,
        derivatives_struct=-1.0,
    )
    assert -1.0 <= score_dict["rpm_score"] <= 1.0

    # Test extreme case: all positive
    score_dict = engine.score_rcm_full(
        capital_flow=1.0,
        relative_strength=1.0,
        narrative_accel=1.0,
        fundamental_confirm=1.0,
        derivatives_struct=1.0,
    )
    assert -1.0 <= score_dict["rpm_score"] <= 1.0
    assert abs(score_dict["rpm_score"] - 1.0) < 0.001
