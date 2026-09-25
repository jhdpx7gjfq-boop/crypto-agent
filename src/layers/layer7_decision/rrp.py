"""RRP — Revival Radar Pipeline. Detects token resurrection patterns."""

from typing import Dict, Tuple, List
import numpy as np


class RRPEngine:
    """Revival Radar Pipeline: Identifies dead coins with renewed activity."""

    def detect_momentum_from_lows(
        self,
        symbol: str,
        closes: list,
        lookback_days: int = 90,
    ) -> float:
        """
        Detect momentum acceleration from recent lows (0-30).

        Measures if price is rising from local lows after prolonged weakness.

        Args:
            symbol: Asset symbol
            closes: Close prices (historical)
            lookback_days: Period to detect lows

        Returns:
            Momentum from lows score 0-30
        """
        if len(closes) < lookback_days:
            return 0.0

        closes_arr = np.array(closes[-lookback_days:])

        # Find recent low
        recent_low = np.min(closes_arr)
        current_price = closes_arr[-1]

        # Calculate recovery percentage from low
        if recent_low <= 0:
            return 0.0

        recovery_pct = (current_price - recent_low) / recent_low
        recovery_score = max(0.0, min(15.0, recovery_pct * 100))

        # Momentum: accelerating uptrend
        returns = np.diff(closes_arr) / closes_arr[:-1]
        recent_returns = np.mean(returns[-20:]) if len(returns) >= 20 else np.mean(returns)
        momentum_score = max(0.0, min(15.0, recent_returns * 100))

        total_score = recovery_score + momentum_score
        total_score = max(0.0, min(30.0, total_score))

        return float(total_score)

    def detect_volume_confirmation(
        self,
        symbol: str,
        volumes: list,
        lookback_days: int = 90,
    ) -> float:
        """
        Detect volume confirmation of resurrection (0-25).

        Measures if volume is rising alongside price recovery.

        Args:
            symbol: Asset symbol
            volumes: Trading volumes (historical)
            lookback_days: Period to analyze

        Returns:
            Volume confirmation score 0-25
        """
        if len(volumes) < lookback_days:
            return 0.0

        volumes_arr = np.array(volumes[-lookback_days:])

        # Volume trend
        early_vol = np.mean(volumes_arr[:20]) if len(volumes_arr) >= 20 else np.mean(volumes_arr)
        recent_vol = np.mean(volumes_arr[-20:]) if len(volumes_arr) >= 20 else np.mean(volumes_arr)

        if early_vol <= 0:
            return 0.0

        vol_acceleration = (recent_vol - early_vol) / early_vol
        vol_score = max(0.0, min(15.0, vol_acceleration * 10))

        # Volume consistency (no spike-out)
        vol_std = np.std(volumes_arr)
        vol_mean = np.mean(volumes_arr)
        vol_consistency = 0.0
        if vol_mean > 0:
            vol_cv = vol_std / vol_mean
            vol_consistency = max(0.0, min(10.0, (1.0 - vol_cv) * 10))

        total_score = vol_score + vol_consistency
        total_score = max(0.0, min(25.0, total_score))

        return float(total_score)

    def detect_adoption_acceleration(
        self,
        symbol: str,
        user_growth: float,
        transaction_growth: float,
        address_growth: float,
    ) -> float:
        """
        Detect on-chain adoption acceleration (0-20).

        Measures if usage metrics show meaningful growth.

        Args:
            symbol: Asset symbol
            user_growth: User/wallet growth rate 0-10
            transaction_growth: Transaction volume growth 0-7
            address_growth: New address creation 0-3

        Returns:
            Adoption acceleration score 0-20
        """
        users = max(0.0, min(10.0, user_growth))
        txns = max(0.0, min(7.0, transaction_growth))
        addrs = max(0.0, min(3.0, address_growth))

        adoption_score = users + txns + addrs
        adoption_score = max(0.0, min(20.0, adoption_score))

        return float(adoption_score)

    def detect_narrative_revival(
        self,
        symbol: str,
        social_velocity: float,
        media_mentions: float,
        sentiment_shift: float,
    ) -> float:
        """
        Detect narrative revival and renewed attention (0-15).

        Measures if narrative is awakening after dormancy.

        Args:
            symbol: Asset symbol
            social_velocity: Social conversation acceleration 0-7
            media_mentions: Media coverage spike 0-5
            sentiment_shift: Sentiment improvement 0-3

        Returns:
            Narrative revival score 0-15
        """
        social = max(0.0, min(7.0, social_velocity))
        media = max(0.0, min(5.0, media_mentions))
        sentiment = max(0.0, min(3.0, sentiment_shift))

        narrative_score = social + media + sentiment
        narrative_score = max(0.0, min(15.0, narrative_score))

        return float(narrative_score)

    def detect_bce_confluence(
        self,
        symbol: str,
        bce_score: float,
    ) -> float:
        """
        Detect BCE (Bottom Confirmation Engine) confluence (0-10).

        High BCE score indicates strong accumulation pattern.

        Args:
            symbol: Asset symbol
            bce_score: BCE score 0-6

        Returns:
            BCE confluence score 0-10
        """
        # Normalize BCE to 0-10 scale (6 → 10)
        bce_normalized = max(0.0, min(10.0, (bce_score / 6.0) * 10.0))

        return float(bce_normalized)

    def calculate_rrp_score(
        self,
        momentum: float,
        volume: float,
        adoption: float,
        narrative: float,
        bce: float,
    ) -> float:
        """
        Calculate final RRP score (0-100).

        Weights:
        - Momentum from lows: 30%
        - Volume confirmation: 25%
        - Adoption acceleration: 20%
        - Narrative revival: 15%
        - BCE confluence: 10%

        Args:
            momentum: 0-30
            volume: 0-25
            adoption: 0-20
            narrative: 0-15
            bce: 0-10

        Returns:
            RRP score 0-100
        """
        weighted = (
            (momentum * 30.0 / 30.0)
            + (volume * 25.0 / 25.0)
            + (adoption * 20.0 / 20.0)
            + (narrative * 15.0 / 15.0)
            + (bce * 10.0 / 10.0)
        )

        rrp_score = max(0.0, min(100.0, weighted))
        return float(rrp_score)

    def validate_rrp_revival(self, rrp_score: float) -> bool:
        """
        Validate RRP revival signal.

        RRP_SCORE >= 50 indicates strong revival pattern.

        Args:
            rrp_score: RRP score 0-100

        Returns:
            True if score >= 50, False otherwise
        """
        return rrp_score >= 50.0

    def analyze_rrp(
        self,
        symbol: str,
        closes: list,
        volumes: list,
        bce_score: float,
        user_growth: float,
        transaction_growth: float,
        address_growth: float,
        social_velocity: float,
        media_mentions: float,
        sentiment_shift: float,
        lookback_days: int = 90,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Complete RRP analysis pipeline.

        Args:
            symbol: Asset symbol
            closes: Close prices
            volumes: Trading volumes
            bce_score: BCE score 0-6 (from BCE engine)
            user_growth: User growth rate 0-10
            transaction_growth: Transaction growth 0-7
            address_growth: Address creation 0-3
            social_velocity: Social acceleration 0-7
            media_mentions: Media spike 0-5
            sentiment_shift: Sentiment improvement 0-3
            lookback_days: Historical lookback period

        Returns:
            (rrp_score 0-100, metrics_dict)
        """
        # Calculate component scores
        momentum = self.detect_momentum_from_lows(symbol, closes, lookback_days)
        volume = self.detect_volume_confirmation(symbol, volumes, lookback_days)
        adoption = self.detect_adoption_acceleration(symbol, user_growth, transaction_growth, address_growth)
        narrative = self.detect_narrative_revival(symbol, social_velocity, media_mentions, sentiment_shift)
        bce = self.detect_bce_confluence(symbol, bce_score)

        # Calculate total
        rrp_score = self.calculate_rrp_score(momentum, volume, adoption, narrative, bce)

        # Validation
        is_revival_signal = self.validate_rrp_revival(rrp_score)

        metrics = {
            "symbol": symbol,
            "momentum_from_lows": momentum,
            "momentum_pct": (momentum / 30.0) * 100.0 if momentum > 0 else 0.0,
            "volume_confirmation": volume,
            "volume_pct": (volume / 25.0) * 100.0 if volume > 0 else 0.0,
            "adoption_acceleration": adoption,
            "adoption_pct": (adoption / 20.0) * 100.0 if adoption > 0 else 0.0,
            "narrative_revival": narrative,
            "narrative_pct": (narrative / 15.0) * 100.0 if narrative > 0 else 0.0,
            "bce_confluence": bce,
            "bce_pct": (bce / 10.0) * 100.0 if bce > 0 else 0.0,
            "rrp_score": rrp_score,
            "revival_signal": is_revival_signal,
        }

        return rrp_score, metrics

    def rank_revivals(self, opportunities: list) -> list:
        """
        Rank revival opportunities by RRP score.

        Args:
            opportunities: List of (symbol, rrp_score, metrics_dict) tuples

        Returns:
            Sorted list by rrp_score descending
        """
        return sorted(opportunities, key=lambda x: x[1], reverse=True)

    def filter_by_revival_signal(self, opportunities: list, threshold: float = 50.0) -> list:
        """
        Filter opportunities showing revival signals.

        Args:
            opportunities: List of (symbol, rrp_score, metrics_dict) tuples
            threshold: Minimum RRP score (default 50)

        Returns:
            Filtered list of revival opportunities
        """
        return [opp for opp in opportunities if opp[1] >= threshold]
