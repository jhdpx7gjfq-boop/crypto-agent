"""Real-time BCE (Bottom Confirmation Engine) consumer for Layer 2 regime feed.

Receives regime updates from RealtimeRegimePipeline and runs Wyckoff analysis.
"""

import logging
from collections import deque
from typing import Callable, Optional, List
from datetime import datetime

from src.core.models import OHLCV, MarketRegime, WyckoffSignal
from src.layers.layer3_wyckoff.bce_engine import BottomConfirmationEngine


logger = logging.getLogger(__name__)


class RealtimeBCEConsumer:
    """
    Real-time Bottom Confirmation Engine consumer.

    Receives regime updates from Layer 2, maintains OHLCV history,
    and analyzes Wyckoff signals when regime changes.
    """

    def __init__(
        self,
        asset: str = "BTC",
        max_history: int = 100,
        signal_callback: Optional[Callable[[WyckoffSignal], None]] = None
    ):
        """
        Initialize BCE consumer.

        Args:
            asset: Asset to analyze (default 'BTC')
            max_history: Max candles to keep in memory
            signal_callback: Function to call when BCE ≥5/6
        """
        self.asset = asset
        self.max_history = max_history
        self.signal_callback = signal_callback
        self.engine = BottomConfirmationEngine()
        self.ohlcv_history = deque(maxlen=max_history)
        self.last_bce_signal = None
        self.last_regime = None

    def on_regime_update(self, regime: MarketRegime):
        """
        Handle regime update from Layer 2.

        Stores regime, analyzes Wyckoff if >= 20 candles available.

        Args:
            regime: MarketRegime object from Layer 2
        """
        try:
            self.last_regime = regime

            # Only analyze if we have sufficient history
            if len(self.ohlcv_history) < 20:
                logger.debug(
                    f"BCE consumer: Insufficient history ({len(self.ohlcv_history)}/20)"
                )
                return

            # Run Wyckoff analysis
            ohlcv_list = list(self.ohlcv_history)
            signal = self.engine.analyze(self.asset, ohlcv_list)
            self.last_bce_signal = signal

            # Log if significant
            if signal.valid:
                logger.warning(
                    f"🔔 BCE SIGNAL: {self.asset} @ {signal.timestamp.isoformat()} "
                    f"Score={signal.bce_score:.1f}/6 (Regime: {regime.regime.value})"
                )

                # Fire callback if registered
                if self.signal_callback:
                    try:
                        self.signal_callback(signal)
                    except Exception as e:
                        logger.error(f"BCE callback error: {e}")

        except Exception as e:
            logger.error(f"BCE consumer error: {e}")

    def add_candle(self, candle: OHLCV):
        """
        Add OHLCV candle to history.

        Called by Layer 1 to keep BCE history synchronized.

        Args:
            candle: OHLCV candle from Layer 1
        """
        self.ohlcv_history.append(candle)
        logger.debug(
            f"BCE history: {len(self.ohlcv_history)} candles "
            f"(latest: ${candle.close:.2f})"
        )

    def get_current_signal(self) -> Optional[WyckoffSignal]:
        """Get last computed BCE signal."""
        return self.last_bce_signal

    def get_current_regime(self) -> Optional[MarketRegime]:
        """Get last received regime."""
        return self.last_regime

    def reset_history(self):
        """Clear OHLCV history."""
        self.ohlcv_history.clear()
        logger.info("BCE history cleared")
