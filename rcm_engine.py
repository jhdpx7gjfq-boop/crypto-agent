"""
RCM (Rotation Confirmation Model) - Narrative, Fundamental, Derivatives Sub-metrics

Implements the remaining 3 components for B-004 validation:
- narrative_acceleration (20% weight)
- fundamental_confirmation (20% weight)
- derivatives_structure (10% weight)

Locked specification: All metrics normalized to [-1, 1] range.
No lookahead bias. Used in 19-window walk-forward validation.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class NarrativeAccelerationMetric:
    """Narrative growth signal: trending adoption/narrative strength."""
    value: float
    mentions_current: float
    mentions_prior: float
    growth_rate: float
    timestamp: int
    lookback_days: int = 7


@dataclass
class FundamentalConfirmationMetric:
    """On-chain and valuation support for rotation."""
    value: float
    components: Dict[str, float]
    timestamp: int
    lookback_days: int = 30


@dataclass
class DerivativesStructureMetric:
    """Leverage and positioning alignment."""
    value: float
    funding_rate: float
    oi_change: float
    ls_ratio: float
    timestamp: int
    lookback_days: int = 7


class RCMEngine:
    """RCM calculation engine (Phase 6 implementation)."""

    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ["BTC", "ETH", "SOL", "AVAX"]

    def calculate_narrative_acceleration(
        self,
        narrative_data: Dict[str, Any],
        symbol: str,
        verbose: bool = False,
    ) -> NarrativeAccelerationMetric:
        """
        Calculate narrative acceleration: trending adoption growth.

        Formula:
          narrative_score = (mentions_t - mentions_[t-7]) / mentions_[t-7]
          Normalized = tanh(narrative_score / threshold)

        Args:
            narrative_data: Dict with 'current_mentions' and 'prior_mentions'
            symbol: Crypto symbol (for logging)
            verbose: Enable debug logging

        Returns:
            NarrativeAccelerationMetric with normalized value [-1, 1]
        """
        current_mentions = narrative_data.get("current_mentions", 0)
        prior_mentions = narrative_data.get("prior_mentions", 1)

        if prior_mentions < 1:
            return NarrativeAccelerationMetric(
                value=0.0,
                mentions_current=current_mentions,
                mentions_prior=prior_mentions,
                growth_rate=0.0,
                timestamp=narrative_data.get("timestamp", 0),
            )

        growth_rate = (current_mentions - prior_mentions) / prior_mentions
        threshold = 0.5  # 50% growth threshold
        normalized = float(np.tanh(growth_rate / (threshold + 1e-8)))

        if verbose:
            logger.info(
                f"{symbol} narrative_acceleration: "
                f"current={current_mentions}, prior={prior_mentions}, "
                f"growth={growth_rate:.4f}, normalized={normalized:.4f}"
            )

        return NarrativeAccelerationMetric(
            value=normalized,
            mentions_current=float(current_mentions),
            mentions_prior=float(prior_mentions),
            growth_rate=float(growth_rate),
            timestamp=narrative_data.get("timestamp", 0),
        )

    def calculate_fundamental_confirmation(
        self,
        on_chain_metrics: Dict[str, float],
        symbol: str,
        verbose: bool = False,
    ) -> FundamentalConfirmationMetric:
        """
        Calculate fundamental confirmation: on-chain + valuation support.

        Metrics:
        - market_cap_growth: YoY market cap change
        - active_addresses: On-chain active addresses growth
        - revenue_multiple: P/E or revenue multiple (normalized)
        - developer_activity: GitHub commits growth

        Formula:
          fundamental_score = mean([
            normalized_market_cap_growth,
            normalized_active_addresses,
            normalized_revenue_multiple,
            normalized_developer_activity
          ])
          Normalized = tanh(fundamental_score / 2)

        Args:
            on_chain_metrics: Dict with metric values
            symbol: Crypto symbol (for logging)
            verbose: Enable debug logging

        Returns:
            FundamentalConfirmationMetric with normalized value [-1, 1]
        """
        components = {}

        # Market cap growth (normalized to [-1, 1] range via tanh)
        market_cap_growth = on_chain_metrics.get("market_cap_growth", 0.0)
        components["market_cap_growth"] = float(np.tanh(market_cap_growth / (0.5 + 1e-8)))

        # Active addresses growth
        active_addresses_growth = on_chain_metrics.get("active_addresses_growth", 0.0)
        components["active_addresses"] = float(np.tanh(active_addresses_growth / (0.3 + 1e-8)))

        # Revenue multiple (P/E normalized)
        revenue_multiple = on_chain_metrics.get("revenue_multiple", 0.0)
        normalized_pe = min(1.0, max(-1.0, (revenue_multiple - 20) / 20))
        components["revenue_multiple"] = float(normalized_pe)

        # Developer activity (GitHub commits growth)
        dev_activity = on_chain_metrics.get("developer_activity", 0.0)
        components["developer_activity"] = float(np.tanh(dev_activity / (0.2 + 1e-8)))

        # Average all components
        avg_score = float(np.mean(list(components.values())))
        normalized = float(np.tanh(avg_score / (2.0 + 1e-8)))

        if verbose:
            logger.info(
                f"{symbol} fundamental_confirmation: "
                f"components={components}, avg={avg_score:.4f}, normalized={normalized:.4f}"
            )

        return FundamentalConfirmationMetric(
            value=normalized,
            components=components,
            timestamp=on_chain_metrics.get("timestamp", 0),
        )

    def calculate_derivatives_structure(
        self,
        derivatives_data: Dict[str, float],
        symbol: str,
        verbose: bool = False,
    ) -> DerivativesStructureMetric:
        """
        Calculate derivatives structure: leverage and positioning alignment.

        Formula:
          derivatives_score = mean([
            normalized_funding_rate,
            normalized_oi_change,
            normalized_ls_ratio
          ])
          Normalized = tanh(derivatives_score / 1.5)

        Args:
            derivatives_data: Dict with funding_rate, oi_change, ls_ratio
            symbol: Crypto symbol (for logging)
            verbose: Enable debug logging

        Returns:
            DerivativesStructureMetric with normalized value [-1, 1]
        """
        # Funding rate (-1 = excessive shorts, 0 = neutral, +1 = excessive longs)
        funding_rate = derivatives_data.get("funding_rate", 0.0)
        normalized_funding = float(np.tanh(funding_rate / (0.001 + 1e-8)))

        # OI change (-1 = sharp decrease, 0 = stable, +1 = sharp increase)
        oi_change = derivatives_data.get("oi_change", 0.0)
        normalized_oi = float(np.tanh(oi_change / (0.1 + 1e-8)))

        # Long/Short ratio (>1 = more longs, <1 = more shorts)
        ls_ratio = derivatives_data.get("ls_ratio", 1.0)
        normalized_ls = float(np.tanh((ls_ratio - 1.0) / (0.5 + 1e-8)))

        components_avg = np.mean([normalized_funding, normalized_oi, normalized_ls])
        normalized = float(np.tanh(components_avg / (1.5 + 1e-8)))

        if verbose:
            logger.info(
                f"{symbol} derivatives_structure: "
                f"funding={normalized_funding:.4f}, oi={normalized_oi:.4f}, "
                f"ls={normalized_ls:.4f}, normalized={normalized:.4f}"
            )

        return DerivativesStructureMetric(
            value=normalized,
            funding_rate=float(normalized_funding),
            oi_change=float(normalized_oi),
            ls_ratio=float(normalized_ls),
            timestamp=derivatives_data.get("timestamp", 0),
        )

    def score_rcm_full(
        self,
        capital_flow: float,
        relative_strength: float,
        narrative_accel: float,
        fundamental_confirm: float,
        derivatives_struct: float,
    ) -> Dict[str, float]:
        """
        Calculate full RPM/RCM score with all 5 components (locked weights).

        Weights:
        - capital_flow: 25%
        - relative_strength: 25%
        - narrative_acceleration: 20%
        - fundamental_confirmation: 20%
        - derivatives_structure: 10%

        Args:
            capital_flow, relative_strength, narrative_accel, fundamental_confirm, derivatives_struct:
                Normalized component scores [-1, 1]

        Returns:
            Dict with component scores and final RPM score
        """
        rpm_score = (
            0.25 * capital_flow
            + 0.25 * relative_strength
            + 0.20 * narrative_accel
            + 0.20 * fundamental_confirm
            + 0.10 * derivatives_struct
        )

        return {
            "capital_flow": float(capital_flow),
            "relative_strength": float(relative_strength),
            "narrative_acceleration": float(narrative_accel),
            "fundamental_confirmation": float(fundamental_confirm),
            "derivatives_structure": float(derivatives_struct),
            "rpm_score": float(rpm_score),
        }
