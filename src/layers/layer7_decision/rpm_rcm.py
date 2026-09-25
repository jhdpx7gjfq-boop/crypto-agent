"""RPM/RCM — Rotation Confirmation Model / Capital Flow Model."""

from typing import Dict, Tuple
import numpy as np


class RPMEngine:
    """RPM/RCM: Capital flow and rotation detection model."""

    def calculate_capital_flow(
        self,
        symbol: str,
        closes: list,
        volumes: list,
        timeframe_days: int = 20,
    ) -> float:
        """
        Calculate capital flow score (0-25).

        Measures inflow intensity and volume acceleration.

        Args:
            symbol: Asset symbol
            closes: Close prices
            volumes: Trading volumes
            timeframe_days: Lookback period

        Returns:
            Capital flow score 0-25
        """
        if len(closes) < timeframe_days or len(volumes) < timeframe_days:
            return 0.0

        closes_arr = np.array(closes[-timeframe_days:])
        volumes_arr = np.array(volumes[-timeframe_days:])

        # Price appreciation
        total_return = (closes_arr[-1] - closes_arr[0]) / closes_arr[0]
        price_flow = max(0.0, min(12.0, total_return * 100))

        # Volume strength (recent vs average)
        vol_recent = np.mean(volumes_arr[-5:])
        vol_average = np.mean(volumes_arr)
        vol_flow = 0.0
        if vol_average > 0:
            vol_flow = (vol_recent - vol_average) / vol_average
            vol_flow = max(0.0, min(13.0, vol_flow * 10))

        capital_flow = price_flow + vol_flow
        capital_flow = max(0.0, min(25.0, capital_flow))

        return float(capital_flow)

    def calculate_relative_strength(
        self,
        symbol: str,
        symbol_return: float,
        sector_return: float,
        market_return: float,
    ) -> float:
        """
        Calculate relative strength score (0-25).

        Measures outperformance vs sector and market.

        Args:
            symbol: Asset symbol
            symbol_return: Asset return %
            sector_return: Sector average return %
            market_return: Market (BTC) return %

        Returns:
            Relative strength score 0-25
        """
        # Outperformance vs sector
        vs_sector = 0.0
        if sector_return != 0:
            vs_sector = (symbol_return - sector_return) / abs(sector_return)
            vs_sector = max(0.0, min(12.0, vs_sector * 10))

        # Outperformance vs market
        vs_market = 0.0
        if market_return != 0:
            vs_market = (symbol_return - market_return) / abs(market_return)
            vs_market = max(0.0, min(13.0, vs_market * 10))

        relative_strength = vs_sector + vs_market
        relative_strength = max(0.0, min(25.0, relative_strength))

        return float(relative_strength)

    def detect_narrative_acceleration(
        self,
        symbol: str,
        social_volume: float,
        media_mentions: float,
        sentiment_change: float,
    ) -> float:
        """
        Detect narrative acceleration (0-20).

        Args:
            symbol: Asset symbol
            social_volume: Social conversation velocity 0-10
            media_mentions: Media coverage acceleration 0-7
            sentiment_change: Sentiment momentum 0-3

        Returns:
            Narrative acceleration score 0-20
        """
        social = max(0.0, min(10.0, social_volume))
        media = max(0.0, min(7.0, media_mentions))
        sentiment = max(0.0, min(3.0, sentiment_change))

        narrative_accel = social + media + sentiment
        narrative_accel = max(0.0, min(20.0, narrative_accel))

        return float(narrative_accel)

    def confirm_fundamentals(
        self,
        symbol: str,
        team_execution: float,
        revenue_growth: float,
        adoption_metrics: float,
    ) -> float:
        """
        Confirm fundamental change (0-20).

        Args:
            symbol: Asset symbol
            team_execution: Team delivery score 0-7
            revenue_growth: Revenue acceleration 0-7
            adoption_metrics: User/transaction growth 0-6

        Returns:
            Fundamental confirmation score 0-20
        """
        team = max(0.0, min(7.0, team_execution))
        revenue = max(0.0, min(7.0, revenue_growth))
        adoption = max(0.0, min(6.0, adoption_metrics))

        fundamental = team + revenue + adoption
        fundamental = max(0.0, min(20.0, fundamental))

        return float(fundamental)

    def analyze_derivatives_structure(
        self,
        symbol: str,
        liquidation_level: float,
        basis_level: float,
        funding_rate: float,
    ) -> float:
        """
        Analyze derivatives structure (0-10).

        Args:
            symbol: Asset symbol
            liquidation_level: Liquidation clustering 0-4
            basis_level: Futures premium/discount 0-3
            funding_rate: Positive funding signal 0-3

        Returns:
            Derivatives score 0-10
        """
        liquidations = max(0.0, min(4.0, liquidation_level))
        basis = max(0.0, min(3.0, basis_level))
        funding = max(0.0, min(3.0, funding_rate))

        derivatives = liquidations + basis + funding
        derivatives = max(0.0, min(10.0, derivatives))

        return float(derivatives)

    def calculate_rpm_score(
        self,
        capital_flow: float,
        relative_strength: float,
        narrative: float,
        fundamental: float,
        derivatives: float,
    ) -> float:
        """
        Calculate final RPM score (0-100).

        Weights:
        - Capital flow: 25%
        - Relative strength: 25%
        - Narrative: 20%
        - Fundamental: 20%
        - Derivatives: 10%

        Args:
            capital_flow: 0-25
            relative_strength: 0-25
            narrative: 0-20
            fundamental: 0-20
            derivatives: 0-10

        Returns:
            RPM score 0-100
        """
        weighted = (
            (capital_flow * 25.0 / 25.0)
            + (relative_strength * 25.0 / 25.0)
            + (narrative * 20.0 / 20.0)
            + (fundamental * 20.0 / 20.0)
            + (derivatives * 10.0 / 10.0)
        )

        rpm_score = max(0.0, min(100.0, weighted))
        return float(rpm_score)

    def validate_rpm_opportunity(self, rpm_score: float) -> bool:
        """
        Validate RPM opportunity threshold.

        RPM_SCORE >= 55 indicates rotation signal.

        Args:
            rpm_score: RPM score 0-100

        Returns:
            True if score >= 55, False otherwise
        """
        return rpm_score >= 55.0

    def analyze_rpm(
        self,
        symbol: str,
        closes: list,
        volumes: list,
        symbol_return: float,
        sector_return: float,
        market_return: float,
        social_volume: float,
        media_mentions: float,
        sentiment_change: float,
        team_execution: float,
        revenue_growth: float,
        adoption_metrics: float,
        liquidation_level: float,
        basis_level: float,
        funding_rate: float,
        timeframe_days: int = 20,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Complete RPM analysis pipeline.

        Args:
            symbol: Asset symbol
            closes: Close prices
            volumes: Trading volumes
            [Return metrics]
            symbol_return, sector_return, market_return
            [Narrative inputs]
            social_volume, media_mentions, sentiment_change
            [Fundamental inputs]
            team_execution, revenue_growth, adoption_metrics
            [Derivatives inputs]
            liquidation_level, basis_level, funding_rate
            timeframe_days: Lookback period

        Returns:
            (rpm_score 0-100, metrics_dict)
        """
        # Calculate component scores
        capital_flow = self.calculate_capital_flow(symbol, closes, volumes, timeframe_days)
        relative_strength = self.calculate_relative_strength(symbol, symbol_return, sector_return, market_return)
        narrative = self.detect_narrative_acceleration(symbol, social_volume, media_mentions, sentiment_change)
        fundamental = self.confirm_fundamentals(symbol, team_execution, revenue_growth, adoption_metrics)
        derivatives = self.analyze_derivatives_structure(symbol, liquidation_level, basis_level, funding_rate)

        # Calculate total
        rpm_score = self.calculate_rpm_score(capital_flow, relative_strength, narrative, fundamental, derivatives)

        # Validation
        is_rotation_signal = self.validate_rpm_opportunity(rpm_score)

        metrics = {
            "symbol": symbol,
            "capital_flow": capital_flow,
            "capital_flow_pct": (capital_flow / 25.0) * 100.0 if capital_flow > 0 else 0.0,
            "relative_strength": relative_strength,
            "relative_strength_pct": (relative_strength / 25.0) * 100.0 if relative_strength > 0 else 0.0,
            "narrative_acceleration": narrative,
            "narrative_pct": (narrative / 20.0) * 100.0 if narrative > 0 else 0.0,
            "fundamental_confirmation": fundamental,
            "fundamental_pct": (fundamental / 20.0) * 100.0 if fundamental > 0 else 0.0,
            "derivatives_structure": derivatives,
            "derivatives_pct": (derivatives / 10.0) * 100.0 if derivatives > 0 else 0.0,
            "rpm_score": rpm_score,
            "rotation_signal": is_rotation_signal,
        }

        return rpm_score, metrics

    def rank_rotations(self, opportunities: list) -> list:
        """
        Rank opportunities by RPM score.

        Args:
            opportunities: List of (symbol, rpm_score, metrics_dict) tuples

        Returns:
            Sorted list by rpm_score descending
        """
        return sorted(opportunities, key=lambda x: x[1], reverse=True)

    def filter_by_rotation_signal(self, opportunities: list, threshold: float = 55.0) -> list:
        """
        Filter opportunities showing rotation signals.

        Args:
            opportunities: List of (symbol, rpm_score, metrics_dict) tuples
            threshold: Minimum RPM score (default 55)

        Returns:
            Filtered list of rotation opportunities
        """
        return [opp for opp in opportunities if opp[1] >= threshold]
