"""X20 Engine — Asymmetric opportunity detection (10-20x potential)."""

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np


@dataclass
class X20Score:
    """X20 opportunity scoring structure."""

    fundamental: float  # 0-30
    narrative: float  # 0-30
    quantitative: float  # 0-40
    total: float  # 0-100


class X20Engine:
    """X20 Engine: Detects asymmetric opportunities with 10-20x potential."""

    def score_fundamentals(
        self,
        symbol: str,
        team_quality: float,
        investor_quality: float,
        tokenomics_health: float,
        unlock_risk: float,
        revenue_adoption: float,
        competitive_advantage: float,
    ) -> float:
        """
        Score fundamental factors (0-30).

        Args:
            symbol: Asset symbol
            team_quality: 0-5 (founder track record, execution ability)
            investor_quality: 0-5 (tier-1 backers, ecosystem support)
            tokenomics_health: 0-5 (supply schedule, inflation, incentives)
            unlock_risk: 0-5 (inverse of unlock risk; high unlock risk = low score)
            revenue_adoption: 0-5 (monetization, user growth, network effects)
            competitive_advantage: 0-5 (moat, differentiation, market positioning)

        Returns:
            Fundamental score 0-30
        """
        scores = [
            team_quality,
            investor_quality,
            tokenomics_health,
            unlock_risk,
            revenue_adoption,
            competitive_advantage,
        ]

        # Clamp all inputs to 0-5
        scores = [max(0.0, min(5.0, s)) for s in scores]

        # Sum of max 6 * 5 = 30
        fundamental_score = sum(scores)
        fundamental_score = max(0.0, min(30.0, fundamental_score))

        return float(fundamental_score)

    def score_narrative(
        self,
        symbol: str,
        sector_strength: float,
        capital_rotation: float,
        attention_growth: float,
        adoption_narrative: float,
    ) -> float:
        """
        Score narrative and adoption factors (0-30).

        Args:
            symbol: Asset symbol
            sector_strength: 0-10 (DeFi, Layer 1, infrastructure, etc.)
            capital_rotation: 0-10 (inflow relative to sector size)
            attention_growth: 0-5 (social sentiment, search volume acceleration)
            adoption_narrative: 0-5 (AI, RWA, payments, etc. thematic strength)

        Returns:
            Narrative score 0-30
        """
        sector = max(0.0, min(10.0, sector_strength))
        rotation = max(0.0, min(10.0, capital_rotation))
        attention = max(0.0, min(5.0, attention_growth))
        adoption = max(0.0, min(5.0, adoption_narrative))

        # Sum of max (10 + 10 + 5 + 5) = 30
        narrative_score = sector + rotation + attention + adoption
        narrative_score = max(0.0, min(30.0, narrative_score))

        return float(narrative_score)

    def score_quantitative(
        self,
        momentum: float,
        relative_strength: float,
        volatility_regime: float,
        liquidity: float,
    ) -> float:
        """
        Score quantitative factors (0-40).

        Args:
            momentum: 0-15 (price momentum, MACD slope, rate of change)
            relative_strength: 0-15 (vs sector, vs market, outperformance)
            volatility_regime: 0-5 (expansion, contraction, opportunity zones)
            liquidity: 0-5 (trading volume, bid-ask spread, slippage potential)

        Returns:
            Quantitative score 0-40
        """
        mom = max(0.0, min(15.0, momentum))
        rs = max(0.0, min(15.0, relative_strength))
        vol = max(0.0, min(5.0, volatility_regime))
        liq = max(0.0, min(5.0, liquidity))

        # Sum of max (15 + 15 + 5 + 5) = 40
        quantitative_score = mom + rs + vol + liq
        quantitative_score = max(0.0, min(40.0, quantitative_score))

        return float(quantitative_score)

    def calculate_x20_score(
        self,
        fundamental_score: float,
        narrative_score: float,
        quantitative_score: float,
    ) -> float:
        """
        Calculate final X20 score (0-100).

        X20 Total = Fundamental (0-30) + Narrative (0-30) + Quantitative (0-40)

        Args:
            fundamental_score: 0-30
            narrative_score: 0-30
            quantitative_score: 0-40

        Returns:
            X20 score 0-100
        """
        total = fundamental_score + narrative_score + quantitative_score
        total = max(0.0, min(100.0, total))
        return float(total)

    def validate_x20_opportunity(self, x20_score: float) -> bool:
        """
        Validate X20 opportunity threshold.

        Opportunities with X20_SCORE >= 50 are considered viable.

        Args:
            x20_score: X20 score 0-100

        Returns:
            True if score >= 50, False otherwise
        """
        return x20_score >= 50.0

    def detect_x20_opportunities(
        self,
        symbol: str,
        team_quality: float,
        investor_quality: float,
        tokenomics_health: float,
        unlock_risk: float,
        revenue_adoption: float,
        competitive_advantage: float,
        sector_strength: float,
        capital_rotation: float,
        attention_growth: float,
        adoption_narrative: float,
        momentum: float,
        relative_strength: float,
        volatility_regime: float,
        liquidity: float,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Detect X20 opportunities using comprehensive analysis.

        Args:
            symbol: Asset symbol
            [Fundamental factors]
            team_quality, investor_quality, tokenomics_health, unlock_risk,
            revenue_adoption, competitive_advantage
            [Narrative factors]
            sector_strength, capital_rotation, attention_growth, adoption_narrative
            [Quantitative factors]
            momentum, relative_strength, volatility_regime, liquidity

        Returns:
            (x20_score 0-100, metrics_dict)
        """
        # Calculate component scores
        fundamental = self.score_fundamentals(
            symbol,
            team_quality,
            investor_quality,
            tokenomics_health,
            unlock_risk,
            revenue_adoption,
            competitive_advantage,
        )

        narrative = self.score_narrative(
            symbol, sector_strength, capital_rotation, attention_growth, adoption_narrative
        )

        quantitative = self.score_quantitative(
            momentum, relative_strength, volatility_regime, liquidity
        )

        # Calculate total
        x20_score = self.calculate_x20_score(fundamental, narrative, quantitative)

        # Validation
        is_viable = self.validate_x20_opportunity(x20_score)

        metrics = {
            "symbol": symbol,
            "fundamental": fundamental,
            "fundamental_pct": (fundamental / 30.0) * 100.0 if fundamental > 0 else 0.0,
            "narrative": narrative,
            "narrative_pct": (narrative / 30.0) * 100.0 if narrative > 0 else 0.0,
            "quantitative": quantitative,
            "quantitative_pct": (quantitative / 40.0) * 100.0 if quantitative > 0 else 0.0,
            "x20_score": x20_score,
            "viable_opportunity": is_viable,
        }

        return x20_score, metrics

    def rank_opportunities(
        self, opportunities: list
    ) -> list:
        """
        Rank X20 opportunities by score.

        Args:
            opportunities: List of (symbol, x20_score, metrics_dict) tuples

        Returns:
            Sorted list by x20_score descending
        """
        return sorted(
            opportunities, key=lambda x: x[1], reverse=True
        )

    def filter_by_threshold(
        self, opportunities: list, threshold: float = 50.0
    ) -> list:
        """
        Filter opportunities by minimum threshold.

        Args:
            opportunities: List of (symbol, x20_score, metrics_dict) tuples
            threshold: Minimum X20 score (default 50)

        Returns:
            Filtered list of viable opportunities
        """
        return [opp for opp in opportunities if opp[1] >= threshold]
