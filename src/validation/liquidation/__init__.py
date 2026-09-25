"""Liquidation research module — independent signal investigation.

Week 1 Implementation:
- BinanceLiquidationCollector: Real-time WebSocket data collection
- LiquidationEvent: Pydantic contract with PIT compliance
- LiquidationStore: DuckDB persistence (immutable raw store)

PIT Compliance:
- All events timestamped (UTC, millisecond precision)
- No future peeking
- Source tracking + deduplication
- Audit trail for all operations
"""

from src.validation.liquidation.collector import BinanceLiquidationCollector
from src.validation.liquidation.contracts import (
    LiquidationBatch,
    LiquidationEvent,
    LiquidationQAReport,
)
from src.validation.liquidation.persistence import LiquidationStore

__all__ = [
    "BinanceLiquidationCollector",
    "LiquidationEvent",
    "LiquidationBatch",
    "LiquidationQAReport",
    "LiquidationStore",
]
