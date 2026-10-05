"""
Layer 2: Market Regime Engine

Objective:
Identify global market context to detect regime shifts, liquidity conditions,
and risk appetite changes. Enables dynamic parameter optimization and
opportunistic signal filtering in downstream layers.

Principle: "Understand the market before entering a position."

Architecture:
- C2.1: Bitcoin Dominance Regime
- C2.2: Liquidity Regime (Funding Rates)
- C2.3: Risk-On / Risk-Off Detection
- C2.4: Macro Conditions
- C2.5: ETF Flow Analysis
- C2.6: Open Interest Regime
- C2.7: Regime Composite Score

Status: Phase 1 (core engine)
PIT_STATUS: Always "UNVERIFIED" (until P0.1 empirical proof)
"""

from .controls import (
    RegimeSnapshot,
    bitcoin_regime,
    liquidity_regime,
    risk_appetite,
    macro_regime,
    etf_regime,
    oi_regime,
    composite_regime_score,
)

__all__ = [
    "RegimeSnapshot",
    "bitcoin_regime",
    "liquidity_regime",
    "risk_appetite",
    "macro_regime",
    "etf_regime",
    "oi_regime",
    "composite_regime_score",
]
