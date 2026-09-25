"""RRP Engine — Revival Radar Pipeline (Layer 7)."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.core.models import OHLCV, RRPSignal
from src.core.config import Config

logger = logging.getLogger(__name__)


class RRPEngine:
    """Revival Radar Pipeline — Detects dormant tokens showing renaissance signs."""

    def __init__(self):
        self.config = Config

    def scan(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        snapshot_data: Optional[Dict[str, Any]] = None,
        community_data: Optional[Dict[str, Any]] = None,
    ) -> RRPSignal:
        """Quick RRP scan for token revival detection."""

        if not ohlcv_data or len(ohlcv_data) < 20:
            return RRPSignal(
                timestamp=datetime.utcnow(),
                asset=asset,
                revival_probability=0.0,
                snapshot_health=0.0,
                volume_signature=0.0,
                community_activity=0.0,
                technical_confirmation=0.0,
                stage="dead",
            )

        snapshot = self._score_snapshot_health(snapshot_data or {})
        volume = self._score_volume_signature(ohlcv_data)
        community = self._score_community_activity(community_data or {})
        technical = self._score_technical_confirmation(ohlcv_data)

        # Weighted: 30% snapshot, 25% volume, 25% community, 20% technical
        revival = (snapshot * 0.30 + volume * 0.25 + community * 0.25 + technical * 0.20)

        # Stage detection
        if revival >= 70:
            stage = "momentum"
        elif revival >= 55:
            stage = "revival"
        elif revival >= 35:
            stage = "awakening"
        else:
            stage = "dead"

        return RRPSignal(
            timestamp=datetime.utcnow(),
            asset=asset,
            revival_probability=min(100.0, revival),
            snapshot_health=snapshot,
            volume_signature=volume,
            community_activity=community,
            technical_confirmation=technical,
            stage=stage,
        )

    def _score_snapshot_health(self, data: Dict[str, Any]) -> float:
        """Score token health snapshot (on-chain metrics)."""
        # Holder distribution: 0-30
        holders = min(30.0, data.get("holder_concentration", 50) / 100 * 30)

        # Large holder accumulation: 0-30
        whale_score = min(30.0, data.get("whale_accumulation", 50) / 100 * 30)

        # Address activity: 0-25
        active = min(25.0, data.get("active_addresses", 50) / 100 * 25)

        # Exchange inflow: 0-15
        inflow = min(15.0, data.get("exchange_inflow_score", 50) / 100 * 15)

        factors = {"holders": holders, "whales": whale_score, "activity": active, "inflow": inflow}
        return sum(factors.values()) / len(factors) if factors else 50.0

    def _score_volume_signature(self, ohlcv: List[OHLCV]) -> float:
        """Score volume signature for unusual activity."""
        if len(ohlcv) < 20:
            return 50.0

        # Recent volume vs historical
        recent_vol = sum(c.volume for c in ohlcv[-5:]) / 5
        hist_vol = sum(c.volume for c in ohlcv[-30:-5]) / 25 if len(ohlcv) >= 30 else recent_vol

        if hist_vol == 0:
            vol_ratio = 1.0
        else:
            vol_ratio = recent_vol / hist_vol

        # Volume spike detection (2x or more = awakening)
        if vol_ratio >= 2.0:
            vol_score = 85.0
        elif vol_ratio >= 1.5:
            vol_score = 70.0
        elif vol_ratio >= 1.0:
            vol_score = 50.0
        else:
            vol_score = 30.0

        return vol_score

    def _score_community_activity(self, data: Dict[str, Any]) -> float:
        """Score community engagement and sentiment."""
        # Social mentions: 0-30
        social = min(30.0, data.get("social_mentions", 20) / 100 * 30)

        # Developer activity: 0-30
        dev = min(30.0, data.get("dev_activity", 20) / 100 * 30)

        # Sentiment: 0-25
        sentiment = min(25.0, data.get("community_sentiment", 50) / 100 * 25)

        # Institutional interest: 0-15
        inst = min(15.0, data.get("institutional_interest", 20) / 100 * 15)

        factors = {"social": social, "dev": dev, "sentiment": sentiment, "inst": inst}
        return sum(factors.values()) / len(factors) if factors else 30.0

    def _score_technical_confirmation(self, ohlcv: List[OHLCV]) -> float:
        """Score technical price action confirmation."""
        if len(ohlcv) < 20:
            return 50.0

        # Price breakout
        recent_high = max(c.high for c in ohlcv[-10:])
        hist_high = max(c.high for c in ohlcv[-40:-10]) if len(ohlcv) >= 40 else 0

        if hist_high > 0:
            breakout_score = 50.0 if recent_high > hist_high else 20.0
        else:
            breakout_score = 35.0

        # Volatility expansion
        closes = [c.close for c in ohlcv[-20:]]
        avg = sum(closes) / len(closes)
        variance = sum((c - avg) ** 2 for c in closes) / len(closes)
        volatility = (variance ** 0.5) / avg * 100

        # Rising volatility = price discovery
        vol_score = min(30.0, volatility / 2)

        # Positive momentum
        price_change = (ohlcv[-1].close - ohlcv[-20].close) / ohlcv[-20].close
        momentum_score = min(20.0, max(0.0, price_change * 100))

        return breakout_score + vol_score + momentum_score
