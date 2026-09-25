"""Decision pipeline orchestration for IGWT-PF26."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from .models import (
    DecisionSignal, SignalType, OHLCV, MarketRegime,
    WyckoffSignal, X20Opportunity, NARMSignal, RCMSignal, RRPSignal
)
from .config import Config


logger = logging.getLogger(__name__)


class DecisionPipeline:
    """
    Decision orchestration pipeline.

    Flow:
    1. Load market data (Layer 1)
    2. Detect regime (Layer 2)
    3. Compute BCE (Layer 3 — Wyckoff)
    4. Compute X20 (Layer 4)
    5. Compute NARM (Layer 5)
    6. Compute RCM (Layer 6)
    7. Compute RRP (Layer 7)
    8. Validate against rules
    9. Generate alert signal
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = Config

    def process_asset(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        market_regime: MarketRegime,
        wyckoff_signal: Optional[WyckoffSignal] = None,
        x20_signal: Optional[X20Opportunity] = None,
        narm_signal: Optional[NARMSignal] = None,
        rcm_signal: Optional[RCMSignal] = None,
        rrp_signal: Optional[RRPSignal] = None,
    ) -> DecisionSignal:
        """
        Process asset through complete decision pipeline.

        Returns: Final decision signal (LONG / SHORT / NEUTRAL / HOLD)
        """

        timestamp = datetime.utcnow()
        components = {}
        confidence = 0.0
        signal_type = SignalType.NEUTRAL
        reason = ""

        # Rule 1: BCE validation
        bce_valid = False
        if wyckoff_signal and wyckoff_signal.valid:
            bce_valid = True
            components["bce"] = asdict(wyckoff_signal)
            self.logger.info(f"{asset}: BCE score {wyckoff_signal.bce_score:.2f} ✓")
        else:
            self.logger.info(f"{asset}: BCE < {self.config.BCE_THRESHOLD} — no entry")
            reason = "BCE validation failed"

        # Rule 2: FOMO circuit breaker (anti-euphoria check)
        if bce_valid and market_regime:
            if self._is_in_fomo_zone(market_regime, ohlcv_data):
                self.logger.warning(f"{asset}: FOMO detected, reducing confidence")
                confidence -= 20
                reason += " (FOMO detected)"

        # Rule 3: X20 opportunity confirmation
        if bce_valid and x20_signal:
            if x20_signal.combined_score >= self.config.X20_THRESHOLD:
                components["x20"] = asdict(x20_signal)
                confidence += 15
                self.logger.info(f"{asset}: X20 opportunity confirmed ({x20_signal.combined_score:.1f})")
            else:
                self.logger.info(f"{asset}: X20 below threshold")

        # Rule 4: NARM narrative validation
        if bce_valid and narm_signal:
            if narm_signal.total_score >= self.config.NARM_THRESHOLD:
                components["narm"] = asdict(narm_signal)
                confidence += 10
                self.logger.info(f"{asset}: NARM narrative confirms ({narm_signal.total_score:.1f})")
            else:
                self.logger.info(f"{asset}: NARM narrative weak")

        # Rule 5: RCM rotation confirmation (capital flows)
        if rcm_signal and rcm_signal.valid:
            components["rcm"] = asdict(rcm_signal)
            confidence += 15
            self.logger.info(f"{asset}: RCM rotation detected ({rcm_signal.combined_score:.1f})")

        # Rule 6: RRP revival detection (bonus for dead tokens)
        if rrp_signal and rrp_signal.revival_probability >= self.config.RRP_THRESHOLD:
            components["rrp"] = asdict(rrp_signal)
            confidence += 10
            self.logger.info(f"{asset}: RRP revival probability {rrp_signal.revival_probability:.1f}%")

        # Final decision logic
        if bce_valid and confidence >= 50:
            signal_type = SignalType.LONG
            reason = f"Multi-confirmation: {', '.join(components.keys())}"
        elif bce_valid and confidence >= 30:
            signal_type = SignalType.HOLD
            reason = "BCE valid but weak confirmation"
        else:
            signal_type = SignalType.NEUTRAL
            reason = reason or "No valid signal"

        # Risk assessment
        risk_level = self._assess_risk(market_regime, wyckoff_signal, confidence)

        decision = DecisionSignal(
            timestamp=timestamp,
            asset=asset,
            signal_type=signal_type,
            confidence=max(0, min(100, confidence)),
            components=components,
            bce_score=wyckoff_signal.bce_score if wyckoff_signal else None,
            x20_score=x20_signal.combined_score if x20_signal else None,
            narm_score=narm_signal.total_score if narm_signal else None,
            rcm_score=rcm_signal.combined_score if rcm_signal else None,
            rrp_score=rrp_signal.revival_probability if rrp_signal else None,
            regime=market_regime.regime if market_regime else None,
            reason=reason,
            risk_level=risk_level,
        )

        return decision

    @staticmethod
    def _is_in_fomo_zone(
        regime: MarketRegime,
        ohlcv: List[OHLCV],
        window: int = 20
    ) -> bool:
        """
        Detect FOMO conditions:
        - Extreme euphoria (BTC dom spike)
        - Price discovery (new ATH + extended move)
        """

        if len(ohlcv) < window:
            return False

        recent = ohlcv[-window:]
        latest_close = recent[-1].close
        highest_high = max(c.high for c in recent)
        lowest_low = min(c.low for c in recent)

        price_range_pct = ((highest_high - lowest_low) / lowest_low) * 100
        extension = ((latest_close - lowest_low) / lowest_low) * 100

        fomo_indicators = [
            regime.btc_dominance > 70,  # BTC dominance spike
            price_range_pct > 20,        # Extreme volatility
            extension > 15,              # Extended move from low
        ]

        return sum(fomo_indicators) >= 2

    @staticmethod
    def _assess_risk(
        regime: Optional[MarketRegime],
        wyckoff: Optional[WyckoffSignal],
        confidence: float
    ) -> str:
        """Assess risk level: low / medium / high."""

        risk_points = 0

        if regime:
            if regime.funding_rate > 0.1:
                risk_points += 1
            if regime.open_interest_change > 30:
                risk_points += 1

        if wyckoff and wyckoff.bce_score < 5.5:
            risk_points += 1

        if confidence < 40:
            risk_points += 1

        if risk_points >= 3:
            return "high"
        elif risk_points >= 1:
            return "medium"
        else:
            return "low"


class PipelineValidator:
    """Validate pipeline integrity and data quality."""

    @staticmethod
    def validate_ohlcv_integrity(data: List[OHLCV]) -> bool:
        """Check OHLCV data is valid."""
        if not data:
            return False

        for candle in data:
            try:
                # __post_init__ raises on invalid data
                _ = OHLCV(
                    timestamp=candle.timestamp,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                )
            except ValueError:
                return False

        return True

    @staticmethod
    def check_lookahead_bias(
        feature_timestamp: datetime,
        signal_timestamp: datetime,
        max_lag_seconds: int = 3600
    ) -> bool:
        """
        Ensure signal uses only data known at that time.
        Returns True if no lookahead bias detected.
        """
        lag = (signal_timestamp - feature_timestamp).total_seconds()
        return 0 <= lag <= max_lag_seconds
