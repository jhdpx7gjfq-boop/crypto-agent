"""Real-time X20 Engine consumer for Layer 2 regime feed.

Receives regime updates from RealtimeRegimePipeline and evaluates opportunities.
"""

import logging
from collections import deque
from typing import Callable, Optional, Dict, Any
from datetime import datetime

from src.core.models import OHLCV, MarketRegime, X20Opportunity
from src.layers.layer4_x20.x20_engine import X20Scanner


logger = logging.getLogger(__name__)


class RealtimeX20Consumer:
    """
    Real-time X20 Opportunity Scanner consumer.

    Receives regime updates from Layer 2, maintains OHLCV history,
    and scans for asymmetric opportunities.
    """

    def __init__(
        self,
        asset: str = "BTC",
        max_history: int = 100,
        opportunity_callback: Optional[Callable[[X20Opportunity], None]] = None
    ):
        """
        Initialize X20 consumer.

        Args:
            asset: Asset to scan (default 'BTC')
            max_history: Max candles to keep in memory
            opportunity_callback: Function to call when score >= 70
        """
        self.asset = asset
        self.max_history = max_history
        self.opportunity_callback = opportunity_callback
        self.scanner = X20Scanner()
        self.ohlcv_history = deque(maxlen=max_history)
        self.last_opportunity = None
        self.last_regime = None

    def on_regime_update(self, regime: MarketRegime):
        """
        Handle regime update from Layer 2.

        Stores regime, evaluates X20 score if >= 20 candles available.

        Args:
            regime: MarketRegime object from Layer 2
        """
        try:
            self.last_regime = regime

            # Only analyze if we have sufficient history
            if len(self.ohlcv_history) < 20:
                logger.debug(
                    f"X20 consumer: Insufficient history ({len(self.ohlcv_history)}/20)"
                )
                return

            # Run X20 scan
            ohlcv_list = list(self.ohlcv_history)
            opportunity = self.scanner.scan(
                asset=self.asset,
                ohlcv_data=ohlcv_list,
            )
            self.last_opportunity = opportunity

            # Log if significant opportunity detected
            if opportunity.combined_score >= 70:
                logger.warning(
                    f"🚀 X20 OPPORTUNITY: {self.asset} @ {opportunity.timestamp.isoformat()} "
                    f"Score={opportunity.combined_score:.1f}/100 (Regime: {regime.regime.value})"
                )

                # Fire callback if registered
                if self.opportunity_callback:
                    try:
                        self.opportunity_callback(opportunity)
                    except Exception as e:
                        logger.error(f"X20 callback error: {e}")
            else:
                logger.debug(
                    f"X20 scan: {self.asset} score={opportunity.combined_score:.1f} "
                    f"(Regime: {regime.regime.value})"
                )

        except Exception as e:
            logger.error(f"X20 consumer error: {e}")

    def add_candle(self, candle: OHLCV):
        """
        Add OHLCV candle to history.

        Called by Layer 1 to keep X20 history synchronized.

        Args:
            candle: OHLCV candle from Layer 1
        """
        self.ohlcv_history.append(candle)
        logger.debug(
            f"X20 history: {len(self.ohlcv_history)} candles "
            f"(latest: ${candle.close:.2f})"
        )

    def get_current_opportunity(self) -> Optional[X20Opportunity]:
        """Get last computed opportunity score."""
        return self.last_opportunity

    def get_current_regime(self) -> Optional[MarketRegime]:
        """Get last received regime."""
        return self.last_regime

    def reset_history(self):
        """Clear OHLCV history."""
        self.ohlcv_history.clear()
        logger.info("X20 history cleared")
