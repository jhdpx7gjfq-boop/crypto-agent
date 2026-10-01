"""Bottom Confirmation Engine (BCE) - Layer 3 Wyckoff Intelligence."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.core.models import OHLCV

logger = logging.getLogger(__name__)


@dataclass
class BCEComponentScores:
    """Per-component scores (0–1 each)."""
    wyckoff_structure: float = 0.0
    volume_analysis: float = 0.0
    selling_exhaustion: float = 0.0
    smart_money: float = 0.0
    market_structure: float = 0.0
    momentum_confirmation: float = 0.0

    @property
    def total(self) -> float:
        """Aggregate BCE score (0–6)."""
        return sum([
            self.wyckoff_structure,
            self.volume_analysis,
            self.selling_exhaustion,
            self.smart_money,
            self.market_structure,
            self.momentum_confirmation
        ])

    def to_dict(self) -> Dict[str, float]:
        """Export as dict."""
        return {
            'wyckoff_structure': self.wyckoff_structure,
            'volume_analysis': self.volume_analysis,
            'selling_exhaustion': self.selling_exhaustion,
            'smart_money': self.smart_money,
            'market_structure': self.market_structure,
            'momentum_confirmation': self.momentum_confirmation,
            'total': self.total,
        }


@dataclass
class BCEResult:
    """Complete BCE analysis result."""
    asset: str
    timestamp: str
    bce_score: float
    components: BCEComponentScores
    signal: str  # "HIGH_CONFIDENCE", "MEDIUM", "LOW", "VERY_LOW"
    confidence_level: float  # 0.0–1.0
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BottomConfirmationEngine:
    """
    BCE: Multi-dimensional accumulation zone detector.

    Combines 6 Wyckoff-based components to identify low-risk entry zones.
    Score range: 0–6. Gate: BCE ≥ 5.0 for entry signals.
    """

    def __init__(self, asset: str):
        self.asset = asset
        self.logger = logger

    def compute_bce_score(
        self,
        ohlcv_data: List[OHLCV],
        smart_money_data: Optional[Dict] = None,
    ) -> BCEResult:
        """
        Compute BCE score for current market state.

        Args:
            ohlcv_data: Time-series of OHLCV candles (≥200 days for MA calc)
            smart_money_data: Optional dict with on-chain metrics

        Returns:
            BCEResult with score and component breakdown

        Raises:
            ValueError: If data insufficient or invalid
        """
        # Validation
        if not ohlcv_data:
            raise ValueError("OHLCV data is empty")
        if len(ohlcv_data) < 50:
            raise ValueError(f"Insufficient data: {len(ohlcv_data)} candles (min 50)")

        self.logger.info(f"Computing BCE for {self.asset} ({len(ohlcv_data)} candles)")

        # Import components dynamically to avoid circular imports
        from src.layers.layer3_wyckoff.components.wyckoff_structure import WyckoffStructure
        from src.layers.layer3_wyckoff.components.volume_analysis import VolumeAnalysis
        from src.layers.layer3_wyckoff.components.selling_exhaustion import SellingExhaustion
        from src.layers.layer3_wyckoff.components.smart_money import SmartMoney
        from src.layers.layer3_wyckoff.components.market_structure import MarketStructure
        from src.layers.layer3_wyckoff.components.momentum_confirmation import MomentumConfirmation

        # Compute each component
        ws_score = WyckoffStructure().compute(ohlcv_data)
        va_score = VolumeAnalysis().compute(ohlcv_data)
        se_score = SellingExhaustion().compute(ohlcv_data)
        sma_score = SmartMoney().compute(ohlcv_data, smart_money_data or {})
        ms_score = MarketStructure().compute(ohlcv_data)
        mc_score = MomentumConfirmation().compute(ohlcv_data)

        # Aggregate
        components = BCEComponentScores(
            wyckoff_structure=ws_score,
            volume_analysis=va_score,
            selling_exhaustion=se_score,
            smart_money=sma_score,
            market_structure=ms_score,
            momentum_confirmation=mc_score,
        )

        bce_score = components.total

        # Determine signal
        if bce_score >= 5.0:
            signal = "HIGH_CONFIDENCE"
            confidence = 0.9 + (min(bce_score - 5.0, 1.0) * 0.1)
        elif bce_score >= 4.0:
            signal = "MEDIUM"
            confidence = 0.7
        elif bce_score >= 3.0:
            signal = "LOW"
            confidence = 0.4
        else:
            signal = "VERY_LOW"
            confidence = 0.1

        # Build result
        result = BCEResult(
            asset=self.asset,
            timestamp=ohlcv_data[-1].open_time.isoformat() if hasattr(ohlcv_data[-1].open_time, 'isoformat') else str(ohlcv_data[-1].open_time),
            bce_score=bce_score,
            components=components,
            signal=signal,
            confidence_level=confidence,
        )

        self.logger.info(
            f"BCE {self.asset}: score={bce_score:.2f}, signal={signal}, "
            f"WS={ws_score:.2f} VA={va_score:.2f} SE={se_score:.2f} "
            f"SMA={sma_score:.2f} MS={ms_score:.2f} MC={mc_score:.2f}"
        )

        return result

    def get_component_breakdown(self, result: BCEResult) -> Dict[str, float]:
        """Return per-component scores for debugging."""
        return result.components.to_dict()
