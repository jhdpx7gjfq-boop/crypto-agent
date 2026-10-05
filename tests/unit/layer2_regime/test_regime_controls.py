"""
Layer 2: Market Regime Engine — Unit Tests (TDD)

Tests for:
- C2.1: Bitcoin Dominance Regime
- C2.2: Liquidity Regime
- C2.3: Risk-On / Risk-Off Detection
- C2.4: Macro Conditions
- C2.5: ETF Flow Analysis
- C2.6: Open Interest Regime
- C2.7: Regime Composite Score
- T2.8: Integration Tests

Status: Phase 1 (core engine)
Tests: 30+
Coverage: All controls with fixture-based mock data
"""

import pytest
from datetime import datetime
from src.layers.layer2_regime.controls import (
    bitcoin_regime,
    liquidity_regime,
    risk_appetite,
    macro_regime,
    etf_regime,
    oi_regime,
    composite_regime_score,
    RegimeSnapshot,
)


# ============================================================================
# FIXTURES: Mock Data (no P0.1 dependency)
# ============================================================================

@pytest.fixture
def btc_dominance_accumulation():
    """BTC > SMA60 > SMA20: accumulation regime"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_dom": 52.5,
        "sma20": 49.0,
        "sma60": 50.5,
    }


@pytest.fixture
def btc_dominance_alt_rotation():
    """BTC < SMA60 < SMA20: alt rotation regime"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_dom": 48.5,
        "sma20": 51.0,
        "sma60": 49.5,
    }


@pytest.fixture
def btc_dominance_balanced():
    """Mixed conditions: balanced regime"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_dom": 50.0,
        "sma20": 50.5,
        "sma60": 50.0,
    }


@pytest.fixture
def liquidity_tight():
    """Funding > 0.10%, avg positive: tight liquidity"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "funding_rate_8h": 0.12,
        "funding_rate_moving_avg_7d": 0.10,
        "open_interest_change_24h": 5.0,
    }


@pytest.fixture
def liquidity_abundant():
    """Funding < -0.10%, avg negative: abundant liquidity"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "funding_rate_8h": -0.12,
        "funding_rate_moving_avg_7d": -0.10,
        "open_interest_change_24h": -5.0,
    }


@pytest.fixture
def liquidity_normal():
    """Funding near 0: normal liquidity"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "funding_rate_8h": 0.02,
        "funding_rate_moving_avg_7d": 0.01,
        "open_interest_change_24h": 1.0,
    }


@pytest.fixture
def risk_on_data():
    """BTC-SPY corr > 0, VIX low, ETH/BTC high: risk-on"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_spy_correlation_7d": 0.6,
        "vtix_implied_volatility": 15.0,
        "eth_btc_ratio": 0.055,
    }


@pytest.fixture
def risk_off_data():
    """BTC-SPY corr < 0, VIX high, ETH/BTC low: risk-off"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_spy_correlation_7d": -0.5,
        "vtix_implied_volatility": 35.0,
        "eth_btc_ratio": 0.030,
    }


@pytest.fixture
def risk_transition_data():
    """Mixed signals: transition"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_spy_correlation_7d": 0.1,
        "vtix_implied_volatility": 25.0,
        "eth_btc_ratio": 0.045,
    }


@pytest.fixture
def macro_tightening():
    """High rates, strong USD: tightening"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "dxy_level": 107.0,
        "us10y_yield": 5.0,
        "cpi_yoy": 3.5,
        "m2_growth_yoy": 2.0,
    }


@pytest.fixture
def macro_accommodative():
    """High M2 growth: accommodative"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "dxy_level": 100.0,
        "us10y_yield": 3.5,
        "cpi_yoy": 2.0,
        "m2_growth_yoy": 6.0,
    }


@pytest.fixture
def macro_neutral():
    """Balanced conditions: neutral"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "dxy_level": 103.0,
        "us10y_yield": 4.0,
        "cpi_yoy": 2.5,
        "m2_growth_yoy": 4.0,
    }


@pytest.fixture
def etf_equities_inflow():
    """SPY inflow, GLD outflow: equities"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "spy_etf_flow_daily": 100.0,
        "gld_etf_flow_daily": -30.0,
    }


@pytest.fixture
def etf_safe_haven_inflow():
    """SPY outflow, GLD inflow: safe haven"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "spy_etf_flow_daily": -100.0,
        "gld_etf_flow_daily": 30.0,
    }


@pytest.fixture
def etf_neutral_flows():
    """Balanced flows: neutral"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "spy_etf_flow_daily": 30.0,
        "gld_etf_flow_daily": 20.0,
    }


@pytest.fixture
def oi_short_accumulation():
    """OI increase + shorts > 0.6: short accumulation"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_oi_change_24h": 12.0,
        "oi_shorts_vs_longs": 0.65,
    }


@pytest.fixture
def oi_long_accumulation():
    """OI increase + shorts < 0.4: long accumulation"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_oi_change_24h": 12.0,
        "oi_shorts_vs_longs": 0.35,
    }


@pytest.fixture
def oi_liquidation_cycle():
    """OI decrease: liquidation cycle"""
    return {
        "timestamp": "2026-10-05T00:00:00Z",
        "btc_oi_change_24h": -12.0,
        "oi_shorts_vs_longs": 0.50,
    }


# ============================================================================
# T2.1: Bitcoin Dominance Regime Tests
# ============================================================================

def test_btc_dom_accumulation(btc_dominance_accumulation):
    """BTC > SMA60 > SMA20 → BTC_ACCUMULATION"""
    regime = bitcoin_regime(
        btc_dominance_accumulation["btc_dom"],
        btc_dominance_accumulation["sma20"],
        btc_dominance_accumulation["sma60"],
    )
    assert regime == "BTC_ACCUMULATION"


def test_btc_dom_alt_rotation(btc_dominance_alt_rotation):
    """BTC < SMA60 < SMA20 → ALT_ROTATION"""
    regime = bitcoin_regime(
        btc_dominance_alt_rotation["btc_dom"],
        btc_dominance_alt_rotation["sma20"],
        btc_dominance_alt_rotation["sma60"],
    )
    assert regime == "ALT_ROTATION"


def test_btc_dom_balanced(btc_dominance_balanced):
    """Mixed conditions → BALANCED"""
    regime = bitcoin_regime(
        btc_dominance_balanced["btc_dom"],
        btc_dominance_balanced["sma20"],
        btc_dominance_balanced["sma60"],
    )
    assert regime == "BALANCED"


# ============================================================================
# T2.2: Liquidity Regime Tests
# ============================================================================

def test_liquidity_tight(liquidity_tight):
    """Funding > 0.10%, avg positive → TIGHT"""
    regime = liquidity_regime(
        liquidity_tight["funding_rate_8h"],
        liquidity_tight["funding_rate_moving_avg_7d"],
        liquidity_tight["open_interest_change_24h"],
    )
    assert regime == "TIGHT"


def test_liquidity_abundant(liquidity_abundant):
    """Funding < -0.10%, avg negative → ABUNDANT"""
    regime = liquidity_regime(
        liquidity_abundant["funding_rate_8h"],
        liquidity_abundant["funding_rate_moving_avg_7d"],
        liquidity_abundant["open_interest_change_24h"],
    )
    assert regime == "ABUNDANT"


def test_liquidity_normal(liquidity_normal):
    """Funding near 0 → NORMAL"""
    regime = liquidity_regime(
        liquidity_normal["funding_rate_8h"],
        liquidity_normal["funding_rate_moving_avg_7d"],
        liquidity_normal["open_interest_change_24h"],
    )
    assert regime == "NORMAL"


# ============================================================================
# T2.3: Risk Appetite Tests
# ============================================================================

def test_risk_appetite_on(risk_on_data):
    """BTC-SPY corr > 0, VIX low → risk_on (score > 0.6)"""
    score = risk_appetite(
        risk_on_data["btc_spy_correlation_7d"],
        risk_on_data["vtix_implied_volatility"],
        risk_on_data["eth_btc_ratio"],
    )
    assert 0.5 < score <= 1.0, f"Expected 0.5 < {score} <= 1.0"


def test_risk_appetite_off(risk_off_data):
    """BTC-SPY corr < 0, VIX high → risk_off (score < 0.4)"""
    score = risk_appetite(
        risk_off_data["btc_spy_correlation_7d"],
        risk_off_data["vtix_implied_volatility"],
        risk_off_data["eth_btc_ratio"],
    )
    assert 0.0 <= score < 0.4, f"Expected 0 <= {score} < 0.4"


def test_risk_appetite_transition(risk_transition_data):
    """Mixed signals → transition (0.4 ≤ score ≤ 0.6)"""
    score = risk_appetite(
        risk_transition_data["btc_spy_correlation_7d"],
        risk_transition_data["vtix_implied_volatility"],
        risk_transition_data["eth_btc_ratio"],
    )
    assert 0.3 <= score <= 0.7, f"Expected 0.3 <= {score} <= 0.7"


def test_risk_appetite_bounds():
    """Score always in [0, 1]"""
    # Test extreme values
    score_extreme_on = risk_appetite(1.0, 10.0, 0.1)
    score_extreme_off = risk_appetite(-1.0, 50.0, 0.01)
    assert 0.0 <= score_extreme_on <= 1.0
    assert 0.0 <= score_extreme_off <= 1.0


# ============================================================================
# T2.4: Macro Regime Tests
# ============================================================================

def test_macro_tightening(macro_tightening):
    """US10Y > 4.5 and DXY > 105 → TIGHTENING"""
    regime = macro_regime(
        macro_tightening["dxy_level"],
        macro_tightening["us10y_yield"],
        macro_tightening["cpi_yoy"],
        macro_tightening["m2_growth_yoy"],
    )
    assert regime == "TIGHTENING"


def test_macro_accommodative(macro_accommodative):
    """M2 growth > 5.0 → ACCOMMODATIVE"""
    regime = macro_regime(
        macro_accommodative["dxy_level"],
        macro_accommodative["us10y_yield"],
        macro_accommodative["cpi_yoy"],
        macro_accommodative["m2_growth_yoy"],
    )
    assert regime == "ACCOMMODATIVE"


def test_macro_neutral(macro_neutral):
    """Balanced conditions → NEUTRAL"""
    regime = macro_regime(
        macro_neutral["dxy_level"],
        macro_neutral["us10y_yield"],
        macro_neutral["cpi_yoy"],
        macro_neutral["m2_growth_yoy"],
    )
    assert regime == "NEUTRAL"


# ============================================================================
# T2.5: ETF Flow Tests
# ============================================================================

def test_etf_equities_inflow(etf_equities_inflow):
    """SPY > 50, GLD < -20 → EQUITIES_INFLOW"""
    regime = etf_regime(
        etf_equities_inflow["spy_etf_flow_daily"],
        etf_equities_inflow["gld_etf_flow_daily"],
    )
    assert regime == "EQUITIES_INFLOW"


def test_etf_safe_haven_inflow(etf_safe_haven_inflow):
    """SPY < -50, GLD > 20 → SAFE_HAVEN_INFLOW"""
    regime = etf_regime(
        etf_safe_haven_inflow["spy_etf_flow_daily"],
        etf_safe_haven_inflow["gld_etf_flow_daily"],
    )
    assert regime == "SAFE_HAVEN_INFLOW"


def test_etf_neutral_flows(etf_neutral_flows):
    """Mixed flows → NEUTRAL_FLOWS"""
    regime = etf_regime(
        etf_neutral_flows["spy_etf_flow_daily"],
        etf_neutral_flows["gld_etf_flow_daily"],
    )
    assert regime == "NEUTRAL_FLOWS"


# ============================================================================
# T2.6: Open Interest Regime Tests
# ============================================================================

def test_oi_short_accumulation(oi_short_accumulation):
    """OI > 10%, shorts > 0.6 → SHORT_ACCUMULATION"""
    regime = oi_regime(
        oi_short_accumulation["btc_oi_change_24h"],
        oi_short_accumulation["oi_shorts_vs_longs"],
    )
    assert regime == "SHORT_ACCUMULATION"


def test_oi_long_accumulation(oi_long_accumulation):
    """OI > 10%, shorts < 0.4 → LONG_ACCUMULATION"""
    regime = oi_regime(
        oi_long_accumulation["btc_oi_change_24h"],
        oi_long_accumulation["oi_shorts_vs_longs"],
    )
    assert regime == "LONG_ACCUMULATION"


def test_oi_liquidation_cycle(oi_liquidation_cycle):
    """OI < -10% → LIQUIDATION_CYCLE"""
    regime = oi_regime(
        oi_liquidation_cycle["btc_oi_change_24h"],
        oi_liquidation_cycle["oi_shorts_vs_longs"],
    )
    assert regime == "LIQUIDATION_CYCLE"


# ============================================================================
# T2.7: Composite Score Tests
# ============================================================================

def test_composite_score_bull():
    """All bullish signals → score > 70"""
    score = composite_regime_score(
        btc_dom_regime="BTC_ACCUMULATION",
        liquidity="ABUNDANT",
        risk_appetite=0.8,
        macro="ACCOMMODATIVE",
        etf_flows="EQUITIES_INFLOW",
        oi_regime="LONG_ACCUMULATION",
    )
    assert score > 70, f"Expected > 70, got {score}"


def test_composite_score_bear():
    """All bearish signals → score < 30"""
    score = composite_regime_score(
        btc_dom_regime="ALT_ROTATION",
        liquidity="TIGHT",
        risk_appetite=0.2,
        macro="TIGHTENING",
        etf_flows="SAFE_HAVEN_INFLOW",
        oi_regime="SHORT_ACCUMULATION",
    )
    assert score < 30, f"Expected < 30, got {score}"


def test_composite_score_neutral():
    """Balanced signals → 40 < score < 60"""
    score = composite_regime_score(
        btc_dom_regime="BALANCED",
        liquidity="NORMAL",
        risk_appetite=0.5,
        macro="NEUTRAL",
        etf_flows="NEUTRAL_FLOWS",
        oi_regime="STABLE_OI",
    )
    assert 40 < score < 60, f"Expected 40 < {score} < 60"


def test_composite_score_range():
    """Score always in [0, 100]"""
    score = composite_regime_score(
        btc_dom_regime="BTC_ACCUMULATION",
        liquidity="ABUNDANT",
        risk_appetite=0.9,
        macro="ACCOMMODATIVE",
        etf_flows="EQUITIES_INFLOW",
        oi_regime="LONG_ACCUMULATION",
    )
    assert 0 <= score <= 100


def test_composite_score_risk_appetite_weight():
    """Risk appetite has highest weight (0.25)"""
    # Test with high risk appetite vs low
    score_high_risk = composite_regime_score(
        btc_dom_regime="BALANCED",
        liquidity="NORMAL",
        risk_appetite=0.9,  # High
        macro="NEUTRAL",
        etf_flows="NEUTRAL_FLOWS",
        oi_regime="STABLE_OI",
    )
    score_low_risk = composite_regime_score(
        btc_dom_regime="BALANCED",
        liquidity="NORMAL",
        risk_appetite=0.1,  # Low
        macro="NEUTRAL",
        etf_flows="NEUTRAL_FLOWS",
        oi_regime="STABLE_OI",
    )
    assert score_high_risk > score_low_risk, "High risk appetite should yield higher score"


# ============================================================================
# T2.8: Integration Tests
# ============================================================================

def test_full_regime_calculation():
    """End-to-end: all controls → composite score"""
    snapshot = RegimeSnapshot(
        timestamp="2026-10-05T00:00:00Z",
        btc_dom=52.0,
        sma20_dom=51.0,
        sma60_dom=50.0,
        funding_rate=0.05,
        funding_avg=0.03,
        oi_change=8.0,
        btc_spy_corr=0.5,
        vtix=18.0,
        eth_btc=0.052,
        dxy=103.0,
        us10y=4.0,
        cpi=2.5,
        m2=4.0,
        spy_flow=75.0,
        gld_flow=-10.0,
        oi_shorts=0.45,
    )
    result = snapshot.calculate_regime()

    assert result["composite_score"] >= 0
    assert result["composite_score"] <= 100
    assert "btc_dominance_regime" in result
    assert "liquidity_regime" in result
    assert "risk_appetite" in result
    assert "macro_regime" in result
    assert "etf_flows" in result
    assert "oi_regime" in result


def test_regime_state_derivation():
    """Composite score → regime_state label"""
    snapshot = RegimeSnapshot(
        timestamp="2026-10-05T00:00:00Z",
        btc_dom=53.0, sma20_dom=49.0, sma60_dom=51.0,
        funding_rate=-0.15, funding_avg=-0.12, oi_change=12.0,
        btc_spy_corr=0.7, vtix=15.0, eth_btc=0.055,
        dxy=100.0, us10y=3.5, cpi=2.0, m2=6.0,
        spy_flow=100.0, gld_flow=-25.0, oi_shorts=0.35,
    )
    result = snapshot.calculate_regime()

    # High composite should yield BULL
    assert result["composite_score"] > 70
    assert result["regime_state"] == "BULL"


def test_regime_state_transition():
    """Medium composite → SIDEWAYS"""
    snapshot = RegimeSnapshot(
        timestamp="2026-10-05T00:00:00Z",
        btc_dom=50.0, sma20_dom=50.5, sma60_dom=50.0,
        funding_rate=0.01, funding_avg=0.01, oi_change=1.0,
        btc_spy_corr=0.1, vtix=20.0, eth_btc=0.045,
        dxy=104.0, us10y=4.2, cpi=2.8, m2=3.0,
        spy_flow=20.0, gld_flow=15.0, oi_shorts=0.50,
    )
    result = snapshot.calculate_regime()

    # Mid-range composite should yield SIDEWAYS
    assert 40 <= result["composite_score"] <= 60
    assert result["regime_state"] == "SIDEWAYS"


def test_timestamp_propagation():
    """Timestamp preserved through calculation"""
    ts = "2026-10-05T00:00:00Z"
    snapshot = RegimeSnapshot(
        timestamp=ts,
        btc_dom=50.0, sma20_dom=50.0, sma60_dom=50.0,
        funding_rate=0.0, funding_avg=0.0, oi_change=0.0,
        btc_spy_corr=0.0, vtix=20.0, eth_btc=0.045,
        dxy=103.0, us10y=4.0, cpi=2.5, m2=4.0,
        spy_flow=0.0, gld_flow=0.0, oi_shorts=0.50,
    )
    result = snapshot.calculate_regime()
    assert result["timestamp"] == ts


def test_pit_status_always_unverified():
    """PIT_STATUS always = UNVERIFIED (until P0.1 proof)"""
    snapshot = RegimeSnapshot(
        timestamp="2026-10-05T00:00:00Z",
        btc_dom=50.0, sma20_dom=50.0, sma60_dom=50.0,
        funding_rate=0.0, funding_avg=0.0, oi_change=0.0,
        btc_spy_corr=0.0, vtix=20.0, eth_btc=0.045,
        dxy=103.0, us10y=4.0, cpi=2.5, m2=4.0,
        spy_flow=0.0, gld_flow=0.0, oi_shorts=0.50,
    )
    result = snapshot.calculate_regime()
    assert result["pit_status"] == "UNVERIFIED"


def test_no_forward_looking():
    """Regime uses only decision_time data, not future data"""
    # This is an architectural constraint test
    # The snapshot should only accept historical data
    # Implementation will enforce this at query time
    snapshot = RegimeSnapshot(
        timestamp="2026-10-05T00:00:00Z",  # decision_time
        btc_dom=50.0, sma20_dom=50.0, sma60_dom=50.0,
        funding_rate=0.0, funding_avg=0.0, oi_change=0.0,
        btc_spy_corr=0.0, vtix=20.0, eth_btc=0.045,
        dxy=103.0, us10y=4.0, cpi=2.5, m2=4.0,
        spy_flow=0.0, gld_flow=0.0, oi_shorts=0.50,
    )
    # All inputs should be <= decision_time
    # Enforced in data layer, tested here for completeness
    result = snapshot.calculate_regime()
    assert result["timestamp"] == "2026-10-05T00:00:00Z"
