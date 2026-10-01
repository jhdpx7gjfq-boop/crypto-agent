"""Component 4: Smart Money Accumulation (Institutional Flows)."""

import logging
from typing import Dict, List, Optional

from src.core.models import OHLCV

logger = logging.getLogger(__name__)


class SmartMoney:
    """
    Detect institutional/large buyer activity.

    Tier 1 (required):
    - Large exchange outflows (>1000 BTC, >10K ETH)
    - Whale wallet accumulation
    - Funding rates (negative = shorts squeezed)

    Score 1.0: 2+ tier1 signals + whale inflow
    Score 0.6: 1 tier1 signal OR negative funding rate
    Score 0.3: Mixed signals
    Score 0.0: Otherwise
    """

    def compute(
        self,
        ohlcv_data: List[OHLCV],
        smart_money_data: Optional[Dict] = None
    ) -> float:
        """
        Compute smart money accumulation score.

        Args:
            ohlcv_data: Time-series OHLCV data
            smart_money_data: Dict with keys like 'exchange_outflow', 'whale_inflow', 'funding_rate'

        Returns:
            float: Score 0–1
        """
        if not smart_money_data:
            logger.warning("No smart money data provided (SE = 0)")
            return 0.0

        # Parse tier 1 signals
        tier1_signals = 0

        # Exchange outflows
        outflow = smart_money_data.get('exchange_outflow', 0)
        asset = ohlcv_data[0].__class__.__name__ if ohlcv_data else ""

        # Thresholds depend on asset (simplified)
        outflow_threshold = 1000 if "BTC" in str(ohlcv_data[-1]) else (10000 if "ETH" in str(ohlcv_data[-1]) else 100000)

        if outflow > outflow_threshold:
            tier1_signals += 1
            logger.debug(f"SM: Exchange outflow signal detected ({outflow})")

        # Whale accumulation
        whale_inflow = smart_money_data.get('whale_inflow', 0)
        if whale_inflow > 0:
            tier1_signals += 1
            logger.debug(f"SM: Whale accumulation signal detected ({whale_inflow})")

        # Funding rate
        funding_rate = smart_money_data.get('funding_rate', 0)
        if funding_rate < -0.05:
            tier1_signals += 1
            logger.debug(f"SM: Funding rate signal detected ({funding_rate})")

        # Scoring
        if tier1_signals >= 2 and whale_inflow > 0:
            score = 1.0
        elif tier1_signals >= 1 or funding_rate < -0.05:
            score = 0.6
        elif tier1_signals > 0:
            score = 0.3
        else:
            score = 0.0

        # Data freshness check
        data_age = smart_money_data.get('data_age_days', 0)
        if data_age > 7:
            logger.warning(f"Smart money data is stale ({data_age} days old)")
            score *= 0.5

        logger.debug(f"SM: score={score:.2f}, tier1_signals={tier1_signals}, whale_inflow={whale_inflow}")

        return max(0.0, min(1.0, score))
