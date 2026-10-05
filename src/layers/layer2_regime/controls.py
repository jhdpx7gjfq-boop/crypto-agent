"""
Layer 2: Market Regime Engine — Control Implementations

Controls:
- C2.1: Bitcoin Dominance Regime
- C2.2: Liquidity Regime (Funding Rates)
- C2.3: Risk-On / Risk-Off Detection
- C2.4: Macro Conditions
- C2.5: ETF Flow Analysis
- C2.6: Open Interest Regime
- C2.7: Regime Composite Score

Status: Phase 1 (core engine)
PIT_STATUS: Always "UNVERIFIED" (until P0.1 empirical proof)
No Forward-Looking: All inputs must satisfy availability_time ≤ decision_time
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime


@dataclass
class RegimeSnapshot:
    """
    Immutable regime snapshot at decision_time.

    All inputs are historical (availability_time ≤ decision_time).
    No forward-looking data permitted.
    """
    timestamp: str

    # C2.1: Bitcoin Dominance
    btc_dom: float
    sma20_dom: float
    sma60_dom: float

    # C2.2: Liquidity (Funding Rates)
    funding_rate: float
    funding_avg: float
    oi_change: float

    # C2.3: Risk Appetite
    btc_spy_corr: float
    vtix: float
    eth_btc: float

    # C2.4: Macro
    dxy: float
    us10y: float
    cpi: float
    m2: float

    # C2.5: ETF Flows
    spy_flow: float
    gld_flow: float

    # C2.6: Open Interest
    oi_shorts: float

    def calculate_regime(self) -> Dict[str, Any]:
        """Calculate full regime snapshot with all controls."""
        btc_dom_regime = bitcoin_regime(self.btc_dom, self.sma20_dom, self.sma60_dom)
        liquidity = liquidity_regime(self.funding_rate, self.funding_avg, self.oi_change)
        risk_score = risk_appetite(self.btc_spy_corr, self.vtix, self.eth_btc)
        macro = macro_regime(self.dxy, self.us10y, self.cpi, self.m2)
        etf = etf_regime(self.spy_flow, self.gld_flow)
        oi = oi_regime(self.oi_change, self.oi_shorts)

        composite = composite_regime_score(
            btc_dom_regime=btc_dom_regime,
            liquidity=liquidity,
            risk_appetite=risk_score,
            macro=macro,
            etf_flows=etf,
            oi_regime=oi,
        )

        regime_state = _derive_regime_state(composite)

        return {
            "timestamp": self.timestamp,
            "btc_dominance_regime": btc_dom_regime,
            "liquidity_regime": liquidity,
            "risk_appetite": round(risk_score, 2),
            "macro_regime": macro,
            "etf_flows": etf,
            "oi_regime": oi,
            "composite_score": composite,
            "regime_state": regime_state,
            "pit_status": "UNVERIFIED",
        }


# ============================================================================
# C2.1: Bitcoin Dominance Regime
# ============================================================================

def bitcoin_regime(btc_dom: float, sma20: float, sma60: float) -> str:
    """
    Detect capital rotation between BTC and altcoins.

    Variables:
    - btc_dom: Current BTC dominance (%)
    - sma20: 20-day SMA
    - sma60: 60-day SMA

    Rules:
    - BTC_ACCUMULATION: BTC > SMA60 AND SMA60 > SMA20
    - ALT_ROTATION: BTC < SMA60 AND SMA60 < SMA20
    - BALANCED: Other conditions
    """
    if btc_dom > sma60 and sma60 > sma20:
        return "BTC_ACCUMULATION"
    elif btc_dom < sma60 and sma60 < sma20:
        return "ALT_ROTATION"
    else:
        return "BALANCED"


# ============================================================================
# C2.2: Liquidity Regime (Funding Rates)
# ============================================================================

def liquidity_regime(funding: float, funding_avg: float, oi_change: float) -> str:
    """
    Detect overleverage and liquidation risk.

    Variables:
    - funding: Current 8h funding rate (%)
    - funding_avg: 7-day moving average (%)
    - oi_change: 24h open interest change (%)

    Rules:
    - TIGHT: Funding > 0.10% AND funding > funding_avg (longs overleveraged)
    - ABUNDANT: Funding < -0.10% AND funding < funding_avg (shorts overleveraged)
    - NORMAL: Other conditions
    """
    if funding > 0.10 and funding > funding_avg:
        return "TIGHT"
    elif funding < -0.10 and funding < funding_avg:
        return "ABUNDANT"
    else:
        return "NORMAL"


# ============================================================================
# C2.3: Risk-On / Risk-Off Detection
# ============================================================================

def risk_appetite(btc_spy_corr: float, vtix: float, eth_btc: float) -> float:
    """
    Detect investor sentiment shift (equity/crypto correlation).

    Variables:
    - btc_spy_corr: BTC-SPY correlation (7-day)
    - vtix: Implied volatility (%)
    - eth_btc: ETH/BTC price ratio

    Returns:
    - Score [0, 1]
    - 0 = risk-off (negative corr, high VIX, low eth/btc)
    - 1 = risk-on (positive corr, low VIX, high eth/btc)

    Components (weights):
    - Correlation: 40% (normalized to [0,1])
    - Volatility: 30% (inverted, lower VIX = higher score)
    - ETH/BTC: 30% (normalized assuming 0.1 = max)
    """
    correlation_score = max(0, min(1, (btc_spy_corr + 1) / 2))
    volatility_score = max(0, 1 - (vtix / 100))
    eth_score = max(0, min(1, eth_btc / 0.1))

    score = (0.4 * correlation_score + 0.3 * volatility_score + 0.3 * eth_score)
    return max(0, min(1, score))


# ============================================================================
# C2.4: Macro Conditions
# ============================================================================

def macro_regime(dxy: float, us10y: float, cpi: float, m2: float) -> str:
    """
    Detect Fed policy regime: inflation, money supply growth.

    Variables:
    - dxy: US Dollar Index level
    - us10y: 10-year US Treasury yield (%)
    - cpi: CPI year-over-year (%)
    - m2: M2 growth year-over-year (%)

    Rules:
    - TIGHTENING: US10Y > 4.5% AND DXY > 105 (high rates, strong USD)
    - EASING_PRESSURE: CPI > 4% (still elevated, pressure to ease)
    - ACCOMMODATIVE: M2 growth > 5% (expansive money supply)
    - NEUTRAL: Default case
    """
    if us10y > 4.5 and dxy > 105:
        return "TIGHTENING"
    elif cpi > 4.0:
        return "EASING_PRESSURE"
    elif m2 > 5.0:
        return "ACCOMMODATIVE"
    else:
        return "NEUTRAL"


# ============================================================================
# C2.5: ETF Flow Analysis
# ============================================================================

def etf_regime(spy_flow: float, gld_flow: float) -> str:
    """
    Detect institutional capital rotation.

    Variables:
    - spy_flow: SPY daily net inflow (millions USD)
    - gld_flow: GLD daily net inflow (millions USD)

    Rules:
    - EQUITIES_INFLOW: SPY > 50M AND GLD < -20M
    - SAFE_HAVEN_INFLOW: SPY < -50M AND GLD > 20M
    - NEUTRAL_FLOWS: Other conditions
    """
    if spy_flow > 50 and gld_flow < -20:
        return "EQUITIES_INFLOW"
    elif spy_flow < -50 and gld_flow > 20:
        return "SAFE_HAVEN_INFLOW"
    else:
        return "NEUTRAL_FLOWS"


# ============================================================================
# C2.6: Open Interest Regime
# ============================================================================

def oi_regime(oi_change: float, shorts_ratio: float) -> str:
    """
    Detect positioning changes in futures markets.

    Variables:
    - oi_change: 24h open interest change (%)
    - shorts_ratio: Shorts / Total OI ratio

    Rules:
    - SHORT_ACCUMULATION: OI change > 10% AND shorts_ratio > 0.6
    - LONG_ACCUMULATION: OI change > 10% AND shorts_ratio < 0.4
    - LIQUIDATION_CYCLE: OI change < -10%
    - STABLE_OI: Other conditions
    """
    if oi_change > 10 and shorts_ratio > 0.6:
        return "SHORT_ACCUMULATION"
    elif oi_change > 10 and shorts_ratio < 0.4:
        return "LONG_ACCUMULATION"
    elif oi_change < -10:
        return "LIQUIDATION_CYCLE"
    else:
        return "STABLE_OI"


# ============================================================================
# C2.7: Regime Composite Score
# ============================================================================

def composite_regime_score(
    btc_dom_regime: str,
    liquidity: str,
    risk_appetite: float,
    macro: str,
    etf_flows: str,
    oi_regime: str,
) -> int:
    """
    Unified regime signal combining all controls.

    Returns:
    - Composite score [0, 100]
    - 0 = extreme bear regime
    - 50 = neutral
    - 100 = extreme bull regime

    Weights:
    - BTC Dominance: 20%
    - Liquidity: 15%
    - Risk Appetite: 25% (highest weight)
    - Macro: 20%
    - ETF Flows: 10%
    - OI Regime: 10%
    """
    scores = {
        # BTC Dominance
        "BTC_ACCUMULATION": 70,
        "ALT_ROTATION": 30,
        "BALANCED": 50,

        # Liquidity
        "TIGHT": 20,
        "ABUNDANT": 70,
        "NORMAL": 50,

        # Macro
        "TIGHTENING": 20,
        "EASING_PRESSURE": 30,
        "ACCOMMODATIVE": 70,
        "NEUTRAL": 50,

        # ETF Flows
        "EQUITIES_INFLOW": 70,
        "SAFE_HAVEN_INFLOW": 30,
        "NEUTRAL_FLOWS": 50,

        # OI Regime
        "SHORT_ACCUMULATION": 30,
        "LONG_ACCUMULATION": 70,
        "LIQUIDATION_CYCLE": 40,
        "STABLE_OI": 50,
    }

    btc_dom_score = scores.get(btc_dom_regime, 50)
    liquidity_score = scores.get(liquidity, 50)
    macro_score = scores.get(macro, 50)
    etf_score = scores.get(etf_flows, 50)
    oi_score = scores.get(oi_regime, 50)
    risk_score = int(risk_appetite * 100)

    composite = (
        0.20 * btc_dom_score +
        0.15 * liquidity_score +
        0.25 * risk_score +
        0.20 * macro_score +
        0.10 * etf_score +
        0.10 * oi_score
    )

    return int(round(composite))


# ============================================================================
# Helper: Derive Regime State from Composite Score
# ============================================================================

def _derive_regime_state(composite_score: int) -> str:
    """
    Map composite score to regime state label.

    Ranges:
    - BULL: > 70
    - SIDEWAYS: 40-60
    - BEAR: < 30
    - TRANSITION: 30-40 or 60-70
    """
    if composite_score > 70:
        return "BULL"
    elif composite_score < 30:
        return "BEAR"
    elif 40 <= composite_score <= 60:
        return "SIDEWAYS"
    else:
        return "TRANSITION"
