"""Signal Aggregation & Risk Controls. Combines decision engines with risk filters."""

from typing import Dict, Tuple, List
from dataclasses import dataclass


@dataclass
class AggregatedSignal:
    """Complete signal with all engine scores and risk assessment."""
    symbol: str
    bce_score: float
    bce_signal: bool
    x20_score: float
    x20_signal: bool
    narm_p_score: float
    narm_p_signal: bool
    rpm_score: float
    rpm_signal: bool
    rrp_score: float
    rrp_signal: bool
    confluence_count: int
    final_signal: bool
    risk_level: str
    fomo_adjusted_score: float


class SignalAggregator:
    """Aggregates signals from all decision engines with risk controls."""

    def count_confluent_signals(
        self,
        bce_signal: bool,
        x20_signal: bool,
        narm_p_signal: bool,
        rpm_signal: bool,
        rrp_signal: bool,
    ) -> int:
        """
        Count number of confluent (positive) signals.

        Args:
            bce_signal: BCE signal >= 5/6
            x20_signal: X20 signal >= 50
            narm_p_signal: NARM-P+ signal >= 60
            rpm_signal: RPM signal >= 55
            rrp_signal: RRP signal >= 50

        Returns:
            Confluence count 0-5
        """
        signals = [bce_signal, x20_signal, narm_p_signal, rpm_signal, rrp_signal]
        return sum(int(s) for s in signals)

    def validate_multi_gate_confluence(
        self,
        confluence_count: int,
        min_confluent_gates: int = 2,
    ) -> bool:
        """
        Validate that sufficient gates are confluent.

        Args:
            confluence_count: Number of positive signals
            min_confluent_gates: Minimum required confluent gates (default 2)

        Returns:
            True if confluence_count >= min_confluent_gates
        """
        return confluence_count >= min_confluent_gates

    def detect_fomo_euphoria(
        self,
        price_change_pct: float,
        volume_spike: float,
        social_velocity: float,
        sentiment_extreme: float,
    ) -> Tuple[bool, float]:
        """
        Detect FOMO/euphoria conditions and return adjustment factor.

        Args:
            price_change_pct: Price change % in recent period (0-100)
            volume_spike: Volume increase ratio (0-10)
            social_velocity: Social conversation spike (0-10)
            sentiment_extreme: Sentiment extreme reading (0-10, where 10=max euphoria)

        Returns:
            (is_euphoria, adjustment_factor 0.5-1.0)
        """
        # Euphoria threshold: all 4 conditions show extreme behavior
        euphoria_score = 0.0

        if price_change_pct > 30.0:
            euphoria_score += 0.25
        if volume_spike > 3.0:
            euphoria_score += 0.25
        if social_velocity > 7.0:
            euphoria_score += 0.25
        if sentiment_extreme > 8.0:
            euphoria_score += 0.25

        is_euphoria = euphoria_score >= 0.75  # 3+ conditions triggered

        # Adjustment factor: 1.0 (no adjustment) down to 0.5 (50% reduction)
        adjustment_factor = max(0.5, 1.0 - euphoria_score)

        return is_euphoria, adjustment_factor

    def apply_regime_filter(
        self,
        confluence_count: int,
        market_regime: str,  # "bullish", "neutral", "bearish", "ranging"
    ) -> Tuple[bool, str]:
        """
        Apply regime-based filtering to gate thresholds.

        Args:
            confluence_count: Number of confluent signals
            market_regime: Market regime classification

        Returns:
            (is_valid, regime_note)
        """
        # Regime-specific minimum confluence requirements
        regime_rules = {
            "bullish": 1,      # Only 1 gate needed in bullish regime
            "neutral": 2,      # 2 gates needed in neutral
            "bearish": 3,      # 3 gates needed in bearish regime
            "ranging": 2,      # 2 gates needed in ranging market
        }

        min_required = regime_rules.get(market_regime, 2)
        is_valid = confluence_count >= min_required

        regime_note = f"Regime: {market_regime}, Min gates: {min_required}, Confluent: {confluence_count}"

        return is_valid, regime_note

    def calculate_risk_level(
        self,
        confluence_count: int,
        is_fomo: bool,
        bce_score: float,
    ) -> str:
        """
        Calculate risk level based on signals and FOMO conditions.

        Args:
            confluence_count: Number of positive signals
            is_fomo: Whether euphoria conditions detected
            bce_score: BCE score 0-6 (for accumulation strength)

        Returns:
            Risk level: "LOW", "MEDIUM", "HIGH", or "EXTREME"
        """
        risk_level = "MEDIUM"

        if is_fomo:
            risk_level = "EXTREME"
        elif confluence_count >= 4:
            risk_level = "LOW"
        elif confluence_count == 3:
            risk_level = "LOW" if bce_score >= 5.0 else "MEDIUM"
        elif confluence_count == 2:
            risk_level = "MEDIUM"
        elif confluence_count == 1:
            risk_level = "HIGH"
        elif confluence_count == 0:
            risk_level = "HIGH"

        return risk_level

    def aggregate_signals(
        self,
        symbol: str,
        bce_score: float,
        x20_score: float,
        narm_p_score: float,
        rpm_score: float,
        rrp_score: float,
        price_change_pct: float = 0.0,
        volume_spike: float = 1.0,
        social_velocity: float = 0.0,
        sentiment_extreme: float = 0.0,
        market_regime: str = "neutral",
        min_confluence: int = 2,
    ) -> AggregatedSignal:
        """
        Complete signal aggregation pipeline.

        Args:
            symbol: Asset symbol
            bce_score: BCE score 0-6
            x20_score: X20 score 0-100
            narm_p_score: NARM-P+ score 0-100
            rpm_score: RPM score 0-100
            rrp_score: RRP score 0-100
            price_change_pct: Price change % (for FOMO detection)
            volume_spike: Volume increase ratio (for FOMO detection)
            social_velocity: Social acceleration (for FOMO detection)
            sentiment_extreme: Sentiment extreme (for FOMO detection)
            market_regime: Market regime ("bullish", "neutral", "bearish", "ranging")
            min_confluence: Minimum confluent gates required (default 2)

        Returns:
            AggregatedSignal with complete analysis
        """
        # Determine individual gate signals
        bce_signal = bce_score >= 5.0
        x20_signal = x20_score >= 50.0
        narm_p_signal = narm_p_score >= 60.0
        rpm_signal = rpm_score >= 55.0
        rrp_signal = rrp_score >= 50.0

        # Count confluent signals
        confluence_count = self.count_confluent_signals(bce_signal, x20_signal, narm_p_signal, rpm_signal, rrp_signal)

        # Check multi-gate confluence
        confluence_valid = self.validate_multi_gate_confluence(confluence_count, min_confluence)

        # Detect FOMO/euphoria
        is_fomo, fomo_adjustment = self.detect_fomo_euphoria(price_change_pct, volume_spike, social_velocity, sentiment_extreme)

        # Apply regime filtering
        regime_valid, regime_note = self.apply_regime_filter(confluence_count, market_regime)

        # Calculate risk level
        risk_level = self.calculate_risk_level(confluence_count, is_fomo, bce_score)

        # Final signal: confluence + regime filter + not extreme euphoria
        final_signal = confluence_valid and regime_valid and not is_fomo

        # FOMO-adjusted score (average of all engine scores)
        avg_score = (bce_score / 6.0 * 100 + x20_score + narm_p_score + rpm_score + rrp_score) / 5.0
        fomo_adjusted_score = avg_score * fomo_adjustment

        return AggregatedSignal(
            symbol=symbol,
            bce_score=bce_score,
            bce_signal=bce_signal,
            x20_score=x20_score,
            x20_signal=x20_signal,
            narm_p_score=narm_p_score,
            narm_p_signal=narm_p_signal,
            rpm_score=rpm_score,
            rpm_signal=rpm_signal,
            rrp_score=rrp_score,
            rrp_signal=rrp_signal,
            confluence_count=confluence_count,
            final_signal=final_signal,
            risk_level=risk_level,
            fomo_adjusted_score=fomo_adjusted_score,
        )

    def rank_opportunities(self, signals: List[AggregatedSignal]) -> List[AggregatedSignal]:
        """
        Rank opportunities by FOMO-adjusted score.

        Args:
            signals: List of AggregatedSignal objects

        Returns:
            Sorted list by fomo_adjusted_score descending
        """
        return sorted(signals, key=lambda x: x.fomo_adjusted_score, reverse=True)

    def filter_valid_signals(self, signals: List[AggregatedSignal]) -> List[AggregatedSignal]:
        """
        Filter only valid signals (final_signal=True).

        Args:
            signals: List of AggregatedSignal objects

        Returns:
            Filtered list of valid signals
        """
        return [sig for sig in signals if sig.final_signal]

    def filter_by_risk_level(self, signals: List[AggregatedSignal], max_risk: str = "MEDIUM") -> List[AggregatedSignal]:
        """
        Filter signals by maximum risk level.

        Args:
            signals: List of AggregatedSignal objects
            max_risk: Maximum acceptable risk ("LOW", "MEDIUM", "HIGH", "EXTREME")

        Returns:
            Filtered list within risk threshold
        """
        risk_hierarchy = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "EXTREME": 3}
        max_risk_level = risk_hierarchy.get(max_risk, 1)

        return [sig for sig in signals if risk_hierarchy.get(sig.risk_level, 3) <= max_risk_level]

    def generate_summary(self, signal: AggregatedSignal) -> Dict[str, str]:
        """
        Generate human-readable summary of aggregated signal.

        Args:
            signal: AggregatedSignal object

        Returns:
            Summary dictionary
        """
        gates_summary = ", ".join([
            f"BCE:{signal.bce_score:.1f}{'✓' if signal.bce_signal else '✗'}",
            f"X20:{signal.x20_score:.1f}{'✓' if signal.x20_signal else '✗'}",
            f"NARM-P+:{signal.narm_p_score:.1f}{'✓' if signal.narm_p_signal else '✗'}",
            f"RPM:{signal.rpm_score:.1f}{'✓' if signal.rpm_signal else '✗'}",
            f"RRP:{signal.rrp_score:.1f}{'✓' if signal.rrp_signal else '✗'}",
        ])

        recommendation = "ACCEPT" if signal.final_signal else "REJECT"
        confidence = f"{signal.confluence_count}/5 gates"

        return {
            "symbol": signal.symbol,
            "recommendation": recommendation,
            "confidence": confidence,
            "risk_level": signal.risk_level,
            "adjusted_score": f"{signal.fomo_adjusted_score:.2f}",
            "gates": gates_summary,
        }
