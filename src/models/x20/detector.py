"""X20 Engine: Asymmetric opportunity detection — Layer 4 implementation."""

from typing import Literal

import numpy as np

from src.utils.logging import get_logger

from .base import (
    FundamentalScore,
    NarrativeScore,
    QuantitativeScore,
    X20Score,
    X20Signal,
)

logger = get_logger(__name__)


class X20Engine:
    """Detect asymmetric opportunities (X10-X20 potential) across three dimensions."""

    # Thresholds for potential classification
    LOW_THRESHOLD = 0.3
    MEDIUM_THRESHOLD = 0.5
    HIGH_THRESHOLD = 0.7

    def __init__(self) -> None:
        """Initialize X20 engine."""
        self.history: list[X20Score] = []

    def evaluate(self, signal: X20Signal) -> X20Score:
        """Evaluate X20 opportunity potential.

        Args:
            signal: X20Signal with asset fundamentals, narrative, and quant data

        Returns:
            X20Score with composite assessment and reasoning
        """
        # Score each dimension
        fund_score = self._score_fundamentals(signal)
        narr_score = self._score_narrative(signal)
        quant_score = self._score_quantitative(signal)

        # Calculate composite X20 score
        fundamental_composite = fund_score.composite_score()
        narrative_composite = narr_score.composite_score()
        quantitative_composite = quant_score.composite_score()

        x20_score = X20Score(
            timestamp=signal.timestamp,
            asset_id=signal.asset_id,
            fundamental_score=fundamental_composite,
            narrative_score=narrative_composite,
            quantitative_score=quantitative_composite,
            components={
                "fundamental": {
                    "team_quality": fund_score.team_quality,
                    "investor_quality": fund_score.investor_quality,
                    "tokenomics": fund_score.tokenomics,
                    "revenue_potential": fund_score.revenue_potential,
                    "competitive_advantage": fund_score.competitive_advantage,
                    "adoption_trajectory": fund_score.adoption_trajectory,
                },
                "narrative": {
                    "sector_strength": narr_score.sector_strength,
                    "narrative_rotation": narr_score.narrative_rotation,
                    "attention_growth": narr_score.attention_growth,
                    "theme_relevance": narr_score.theme_relevance,
                    "adoption_catalyst": narr_score.adoption_catalyst,
                },
                "quantitative": {
                    "momentum": quant_score.momentum,
                    "relative_strength": quant_score.relative_strength,
                    "volatility_regime": quant_score.volatility_regime,
                    "liquidity": quant_score.liquidity,
                    "risk_reward_ratio": quant_score.risk_reward_ratio,
                },
            },
            confidence=self._calculate_confidence(
                fundamental_composite, narrative_composite, quantitative_composite
            ),
            x20_potential=self._classify_potential(
                fundamental_composite, narrative_composite, quantitative_composite
            ),
            reasoning=self._generate_reasoning(
                signal, fund_score, narr_score, quant_score
            ),
            metadata={
                "composite_score": fundamental_composite * 0.35
                + narrative_composite * 0.35
                + quantitative_composite * 0.30,
            },
        )

        self.history.append(x20_score)
        logger.info(
            f"X20 opportunity evaluated: {signal.asset_id}",
            extra={
                "extra_fields": {
                    "asset_id": signal.asset_id,
                    "potential": x20_score.x20_potential,
                    "confidence": x20_score.confidence,
                }
            },
        )

        return x20_score

    @staticmethod
    def _score_fundamentals(signal: X20Signal) -> FundamentalScore:
        """Score fundamental strength (team, investors, tokenomics, etc)."""
        team_quality = 0.6
        investor_quality = 0.55
        tokenomics = 0.5
        revenue_potential = 0.6
        competitive_advantage = 0.55
        adoption_trajectory = min(1.0, max(0.0, signal.adoption_growth / 50.0))

        return FundamentalScore(
            team_quality=team_quality,
            investor_quality=investor_quality,
            tokenomics=tokenomics,
            revenue_potential=revenue_potential,
            competitive_advantage=competitive_advantage,
            adoption_trajectory=adoption_trajectory,
        )

    @staticmethod
    def _score_narrative(signal: X20Signal) -> NarrativeScore:
        """Score narrative strength and adoption potential."""
        sector_strength = signal.narrative_relevance
        narrative_rotation = signal.narrative_relevance * 0.9
        attention_growth = min(
            1.0, max(0.0, signal.adoption_growth / 30.0)
        )
        theme_relevance = signal.narrative_relevance
        adoption_catalyst = signal.adoption_growth / 100.0 if signal.adoption_growth > 0 else 0.3

        return NarrativeScore(
            sector_strength=float(sector_strength),
            narrative_rotation=float(narrative_rotation),
            attention_growth=float(attention_growth),
            theme_relevance=float(theme_relevance),
            adoption_catalyst=float(min(1.0, adoption_catalyst)),
        )

    @staticmethod
    def _score_quantitative(signal: X20Signal) -> QuantitativeScore:
        """Score quantitative strength (momentum, volatility, liquidity)."""
        momentum = (signal.rsi_14 / 100.0) * 0.5 + (signal.momentum_score + 1) / 2 * 0.5
        relative_strength = (signal.momentum_score + 1) / 2
        volatility_regime = min(1.0, signal.volatility_30d * 1.5)
        liquidity = min(1.0, (signal.volume_24h / (signal.market_cap + 1e-8)) * 10)
        risk_reward_ratio = (
            momentum * (1 - signal.volatility_30d / 2) if signal.volatility_30d > 0 else 0.5
        )

        return QuantitativeScore(
            momentum=float(np.clip(momentum, 0, 1)),
            relative_strength=float(np.clip(relative_strength, 0, 1)),
            volatility_regime=float(np.clip(volatility_regime, 0, 1)),
            liquidity=float(np.clip(liquidity, 0, 1)),
            risk_reward_ratio=float(np.clip(risk_reward_ratio, 0, 1)),
        )

    @staticmethod
    def _calculate_confidence(
        fund: float, narr: float, quant: float
    ) -> float:
        """Calculate overall confidence in the X20 assessment."""
        consistency = 1.0 - np.std([fund, narr, quant])
        avg_score = (fund + narr + quant) / 3.0
        confidence = consistency * 0.5 + avg_score * 0.5
        return float(np.clip(confidence, 0, 1))

    @staticmethod
    def _classify_potential(
        fund: float, narr: float, quant: float
    ) -> Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]:
        """Classify X20 potential based on composite scores."""
        composite = fund * 0.35 + narr * 0.35 + quant * 0.30

        if composite >= X20Engine.HIGH_THRESHOLD:
            return "VERY_HIGH"
        elif composite >= X20Engine.MEDIUM_THRESHOLD:
            return "HIGH"
        elif composite >= X20Engine.LOW_THRESHOLD:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def _generate_reasoning(
        signal: X20Signal,
        fund: FundamentalScore,
        narr: NarrativeScore,
        quant: QuantitativeScore,
    ) -> list[str]:
        """Generate human-readable reasoning for the X20 score."""
        reasoning = []

        if fund.composite_score() > 0.6:
            reasoning.append(
                "Strong fundamentals: team + investors + competitive advantage"
            )
        if fund.adoption_trajectory > 0.6:
            reasoning.append(f"High adoption growth: {signal.adoption_growth:.1f}%/month")

        if narr.composite_score() > 0.6:
            reasoning.append("Strong narrative: sector rotation + attention growth")
        if narr.theme_relevance > 0.7:
            reasoning.append("High theme relevance: aligned with current narratives")

        if quant.momentum > 0.6:
            reasoning.append(
                f"Strong momentum: RSI={signal.rsi_14:.0f}, momentum={signal.momentum_score:.2f}"
            )
        if quant.liquidity > 0.6:
            reasoning.append("Good liquidity: volume-to-cap ratio favorable")

        if not reasoning:
            reasoning.append("Moderate opportunity: balanced across dimensions")

        return reasoning
