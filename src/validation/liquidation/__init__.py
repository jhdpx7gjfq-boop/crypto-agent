"""Liquidation research module — independent signal investigation.

Week 1 Implementation:
- BinanceLiquidationCollector: Real-time WebSocket data collection
- LiquidationEvent: Pydantic contract with PIT compliance
- LiquidationStore: DuckDB persistence (immutable raw store)

Week 2 Implementation:
- LiquidationQA: Quality assurance pipeline (duplicates, outliers, gaps)
- LiquidationQAReport: QA findings schema

Week 3 Implementation:
- LiquidationFeatureEngine: F001-F006 feature computation (4-hour rolling window)

Week 4 Implementation:
- LiquidationLabelEngine: Target computation (RETURN[T→T+1m])
- Label computation with PIT compliance (future prices not at T)

PIT Compliance:
- All events timestamped (UTC, millisecond precision)
- No future peeking
- Source tracking + deduplication
- Audit trail for all operations
- Feature computation strictly before observation time
- Label computation separates observation time from label availability
"""

from src.validation.liquidation.collector import BinanceLiquidationCollector
from src.validation.liquidation.contracts import (
    LiquidationBatch,
    LiquidationEvent,
    LiquidationQAReport,
)
from src.validation.liquidation.features import LiquidationFeatureEngine
from src.validation.liquidation.labels import LiquidationLabelEngine
from src.validation.liquidation.persistence import LiquidationStore
from src.validation.liquidation.qa import LiquidationQA

__all__ = [
    "BinanceLiquidationCollector",
    "LiquidationEvent",
    "LiquidationBatch",
    "LiquidationQAReport",
    "LiquidationStore",
    "LiquidationQA",
    "LiquidationFeatureEngine",
    "LiquidationLabelEngine",
]
