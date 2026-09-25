"""NARM-P+ — Narrative Adoption Rotation Model Plus."""

from typing import Dict, Tuple
import numpy as np


class NARMPPlus:
    """NARM-P+: Narrative Adoption Rotation Model for narrative-driven markets."""

    def score_narrative_strength(
        self,
        symbol: str,
        sector: str,
        sentiment_score: float,
        media_mentions: float,
        social_volume: float,
    ) -> float:
        """
        Score narrative strength and market attention (0-25).

        Args:
            symbol: Asset symbol
            sector: Market sector/category (DeFi, Layer1, AI, RWA, etc.)
            sentiment_score: 0-10 (sentiment from news/social, 0=bearish, 10=bullish)
            media_mentions: 0-10 (normalized count of media coverage)
            social_volume: 0-5 (social conversation volume spike)

        Returns:
            Narrative strength score 0-25
        """
        sentiment = max(0.0, min(10.0, sentiment_score))
        media = max(0.0, min(10.0, media_mentions))
        social = max(0.0, min(5.0, social_volume))

        # Sum of max (10 + 10 + 5) = 25
        narrative_score = sentiment + media + social
        narrative_score = max(0.0, min(25.0, narrative_score))

        return float(narrative_score)

    def score_adoption(
        self,
        symbol: str,
        user_growth: float,
        transaction_volume: float,
        network_effect: float,
    ) -> float:
        """
        Score adoption metrics (0-20).

        Args:
            symbol: Asset symbol
            user_growth: 0-10 (QoQ user acceleration, new addresses)
            transaction_volume: 0-7 (on-chain transaction velocity)
            network_effect: 0-3 (lock-in, switching cost, ecosystem growth)

        Returns:
            Adoption score 0-20
        """
        users = max(0.0, min(10.0, user_growth))
        txn = max(0.0, min(7.0, transaction_volume))
        network = max(0.0, min(3.0, network_effect))

        # Sum of max (10 + 7 + 3) = 20
        adoption_score = users + txn + network
        adoption_score = max(0.0, min(20.0, adoption_score))

        return float(adoption_score)

    def score_capital_rotation(
        self,
        symbol: str,
        closes: list,
        volumes: list,
        timeframe_days: int = 20,
    ) -> float:
        """
        Score capital rotation and momentum acceleration (0-25).

        Args:
            symbol: Asset symbol
            closes: Close prices
            volumes: Trading volumes
            timeframe_days: Lookback period for rotation detection

        Returns:
            Capital rotation score 0-25
        """
        if len(closes) < timeframe_days or len(volumes) < timeframe_days:
            return 0.0

        closes_arr = np.array(closes[-timeframe_days:])
        volumes_arr = np.array(volumes[-timeframe_days:])

        # Price momentum
        returns = np.diff(closes_arr) / closes_arr[:-1]
        momentum = np.mean(returns[returns > 0])  # Average positive return
        momentum = max(0.0, min(15.0, momentum * 100))  # Scale to 0-15

        # Volume acceleration
        vol_recent = np.mean(volumes_arr[-5:])
        vol_prior = np.mean(volumes_arr[:-5])
        vol_accel = 0.0
        if vol_prior > 0:
            vol_accel = (vol_recent - vol_prior) / vol_prior
            vol_accel = max(0.0, min(10.0, vol_accel * 10))

        rotation_score = momentum + vol_accel
        rotation_score = max(0.0, min(25.0, rotation_score))

        return float(rotation_score)

    def score_fundamentals(
        self,
        symbol: str,
        team_strength: float,
        revenue_model: float,
        market_traction: float,
    ) -> float:
        """
        Score fundamental verification (0-15).

        Args:
            symbol: Asset symbol
            team_strength: 0-5 (team quality, execution)
            revenue_model: 0-5 (sustainable monetization)
            market_traction: 0-5 (product-market fit signals)

        Returns:
            Fundamental score 0-15
        """
        team = max(0.0, min(5.0, team_strength))
        revenue = max(0.0, min(5.0, revenue_model))
        traction = max(0.0, min(5.0, market_traction))

        fundamental_score = team + revenue + traction
        fundamental_score = max(0.0, min(15.0, fundamental_score))

        return float(fundamental_score)

    def score_market_timing(
        self,
        symbol: str,
        btc_dominance: float,
        volatility_regime: float,
        macro_environment: float,
    ) -> float:
        """
        Score market timing and regime fitness (0-15).

        Args:
            symbol: Asset symbol
            btc_dominance: 0-5 (low dominance = alt season, high = bitcoin dominance)
            volatility_regime: 0-5 (expansion phase opportunity)
            macro_environment: 0-5 (risk-on vs risk-off, macro conditions)

        Returns:
            Market timing score 0-15
        """
        btc_dom = max(0.0, min(5.0, btc_dominance))
        volatility = max(0.0, min(5.0, volatility_regime))
        macro = max(0.0, min(5.0, macro_environment))

        timing_score = btc_dom + volatility + macro
        timing_score = max(0.0, min(15.0, timing_score))

        return float(timing_score)

    def calculate_narm_p_score(
        self,
        narrative: float,
        adoption: float,
        rotation: float,
        fundamental: float,
        timing: float,
    ) -> float:
        """
        Calculate final NARM-P+ score (0-100).

        NARM-P+ = Narrative (0-25) + Adoption (0-20) + Rotation (0-25)
                + Fundamental (0-15) + Timing (0-15)

        Args:
            narrative: 0-25
            adoption: 0-20
            rotation: 0-25
            fundamental: 0-15
            timing: 0-15

        Returns:
            NARM-P+ score 0-100
        """
        total = narrative + adoption + rotation + fundamental + timing
        total = max(0.0, min(100.0, total))
        return float(total)

    def validate_narm_p_opportunity(self, narm_p_score: float) -> bool:
        """
        Validate NARM-P+ opportunity threshold.

        Opportunities with NARM_P_SCORE >= 60 are considered high-conviction.

        Args:
            narm_p_score: NARM-P+ score 0-100

        Returns:
            True if score >= 60, False otherwise
        """
        return narm_p_score >= 60.0

    def analyze_narm_p(
        self,
        symbol: str,
        sentiment_score: float,
        media_mentions: float,
        social_volume: float,
        user_growth: float,
        transaction_volume: float,
        network_effect: float,
        closes: list,
        volumes: list,
        team_strength: float,
        revenue_model: float,
        market_traction: float,
        btc_dominance: float,
        volatility_regime: float,
        macro_environment: float,
        timeframe_days: int = 20,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Complete NARM-P+ analysis.

        Args:
            symbol: Asset symbol
            [Narrative inputs]
            sentiment_score, media_mentions, social_volume
            [Adoption inputs]
            user_growth, transaction_volume, network_effect
            [Capital rotation inputs]
            closes, volumes, timeframe_days
            [Fundamental inputs]
            team_strength, revenue_model, market_traction
            [Market timing inputs]
            btc_dominance, volatility_regime, macro_environment

        Returns:
            (narm_p_score 0-100, metrics_dict)
        """
        # Calculate component scores
        narrative = self.score_narrative_strength(
            symbol, "", sentiment_score, media_mentions, social_volume
        )

        adoption = self.score_adoption(
            symbol, user_growth, transaction_volume, network_effect
        )

        rotation = self.score_capital_rotation(symbol, closes, volumes, timeframe_days)

        fundamental = self.score_fundamentals(
            symbol, team_strength, revenue_model, market_traction
        )

        timing = self.score_market_timing(symbol, btc_dominance, volatility_regime, macro_environment)

        # Calculate total
        narm_p_score = self.calculate_narm_p_score(narrative, adoption, rotation, fundamental, timing)

        # Validation
        is_high_conviction = self.validate_narm_p_opportunity(narm_p_score)

        metrics = {
            "symbol": symbol,
            "narrative_strength": narrative,
            "narrative_pct": (narrative / 25.0) * 100.0 if narrative > 0 else 0.0,
            "adoption": adoption,
            "adoption_pct": (adoption / 20.0) * 100.0 if adoption > 0 else 0.0,
            "capital_rotation": rotation,
            "rotation_pct": (rotation / 25.0) * 100.0 if rotation > 0 else 0.0,
            "fundamental": fundamental,
            "fundamental_pct": (fundamental / 15.0) * 100.0 if fundamental > 0 else 0.0,
            "market_timing": timing,
            "timing_pct": (timing / 15.0) * 100.0 if timing > 0 else 0.0,
            "narm_p_score": narm_p_score,
            "high_conviction": is_high_conviction,
        }

        return narm_p_score, metrics

    def rank_narratives(self, opportunities: list) -> list:
        """
        Rank narrative opportunities by NARM-P+ score.

        Args:
            opportunities: List of (symbol, narm_p_score, metrics_dict) tuples

        Returns:
            Sorted list by narm_p_score descending
        """
        return sorted(opportunities, key=lambda x: x[1], reverse=True)

    def filter_by_conviction(self, opportunities: list, threshold: float = 60.0) -> list:
        """
        Filter opportunities by conviction threshold.

        Args:
            opportunities: List of (symbol, narm_p_score, metrics_dict) tuples
            threshold: Minimum NARM-P+ score (default 60)

        Returns:
            Filtered list of high-conviction opportunities
        """
        return [opp for opp in opportunities if opp[1] >= threshold]
