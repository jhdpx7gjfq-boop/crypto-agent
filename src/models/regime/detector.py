"""Market Regime Detector — Layer 2 implementation."""

from typing import Literal

import numpy as np

from src.utils.logging import get_logger

from .base import RegimeContext, RegimeScores, RegimeSignal

logger = get_logger(__name__)


class MarketRegimeDetector:
    """Detect market regime (risk-on vs risk-off) from macro signals."""

    def __init__(self) -> None:
        """Initialize detector."""
        self.history: list[RegimeContext] = []

    def detect(self, signal: RegimeSignal) -> RegimeContext:
        """Detect current market regime.

        Args:
            signal: RegimeSignal with macro indicators

        Returns:
            RegimeContext with regime, score, and confidence
        """
        scores = self._calculate_scores(signal)
        regime, regime_score, confidence = self._classify_regime(scores)

        context = RegimeContext(
            timestamp=signal.timestamp,
            regime=regime,
            regime_score=regime_score,
            confidence=confidence,
            scores=scores,
            metadata={
                "dxy": float(signal.dxy),
                "us10y": float(signal.us10y),
                "btc_price": float(signal.btc_price),
                "lookback_days": signal.lookback_days,
            },
        )

        self.history.append(context)
        logger.info(
            f"Regime detected: {regime}",
            extra={
                "extra_fields": {
                    "regime": regime,
                    "score": regime_score,
                    "confidence": confidence,
                }
            },
        )

        return context

    def _calculate_scores(self, signal: RegimeSignal) -> RegimeScores:
        """Calculate individual regime indicator scores.

        Args:
            signal: Market signal

        Returns:
            RegimeScores with normalized [0, 1] or [-1, 1] values
        """
        btc_trend = self._calculate_btc_trend(signal.btc_price)
        dxy_strength = self._normalize_dxy(signal.dxy)
        rates_regime = self._normalize_rates(signal.us10y)
        liquidity_regime = self._normalize_liquidity(signal.open_interest)
        crypto_momentum = self._normalize_momentum(signal.funding_rate)
        inflation_pressure = self._normalize_inflation(signal.cpi_yoy)

        return RegimeScores(
            btc_trend=btc_trend,
            dxy_strength=dxy_strength,
            rates_regime=rates_regime,
            liquidity_regime=liquidity_regime,
            crypto_momentum=crypto_momentum,
            inflation_pressure=inflation_pressure,
        )

    @staticmethod
    def _calculate_btc_trend(_btc_price: float) -> float:
        """Calculate BTC trend signal (placeholder: returns 0)."""
        return 0.0

    @staticmethod
    def _normalize_dxy(dxy: float) -> float:
        """Normalize DXY to [0, 1]. Higher DXY = risk-off (1)."""
        dxy_min, dxy_max = 90.0, 110.0
        norm_dxy = (dxy - dxy_min) / (dxy_max - dxy_min)
        return float(np.clip(norm_dxy, 0, 1))

    @staticmethod
    def _normalize_rates(us10y: float) -> float:
        """Normalize rates to [0, 1]. Higher rates = risk-off (1)."""
        rates_min, rates_max = 0.5, 5.0
        norm_rates = (us10y - rates_min) / (rates_max - rates_min)
        return float(np.clip(norm_rates, 0, 1))

    @staticmethod
    def _normalize_liquidity(open_interest: float) -> float:
        """Normalize OI to [0, 1]. Already normalized input."""
        return float(np.clip(1.0 - open_interest, 0, 1))

    @staticmethod
    def _normalize_momentum(funding_rate: float) -> float:
        """Normalize funding rate to [0, 1]. High funding = risk-on (1)."""
        fr_min, fr_max = -0.05, 0.05
        norm_fr = (funding_rate - fr_min) / (fr_max - fr_min)
        return float(np.clip(norm_fr, 0, 1))

    @staticmethod
    def _normalize_inflation(cpi_yoy: float) -> float:
        """Normalize inflation to [0, 1]. High inflation = risk-off (1)."""
        cpi_min, cpi_max = -2.0, 8.0
        norm_cpi = (cpi_yoy - cpi_min) / (cpi_max - cpi_min)
        return float(np.clip(norm_cpi, 0, 1))

    @staticmethod
    def _classify_regime(
        scores: RegimeScores,
    ) -> tuple[Literal["RISK_ON", "RISK_OFF", "TRANSITIONAL"], float, float]:
        """Classify regime and calculate confidence.

        Args:
            scores: RegimeScores with individual components

        Returns:
            (regime, regime_score, confidence)
        """
        risk_off_weight = (
            scores.dxy_strength * 0.25
            + scores.rates_regime * 0.25
            + scores.inflation_pressure * 0.20
            + scores.liquidity_regime * 0.15
        )

        risk_on_weight = (
            scores.crypto_momentum * 0.25
            + (1.0 - scores.dxy_strength) * 0.25
            + (1.0 - scores.rates_regime) * 0.20
            + (1.0 - scores.inflation_pressure) * 0.15
        )

        regime_score = float(risk_on_weight - risk_off_weight)

        regime: Literal["RISK_ON", "RISK_OFF", "TRANSITIONAL"]
        if regime_score > 0.3:
            regime = "RISK_ON"
            confidence = min(regime_score, 1.0)
        elif regime_score < -0.3:
            regime = "RISK_OFF"
            confidence = min(abs(regime_score), 1.0)
        else:
            regime = "TRANSITIONAL"
            confidence = 1.0 - abs(regime_score)

        return regime, regime_score, confidence
