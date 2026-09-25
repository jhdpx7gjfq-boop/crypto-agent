"""Liquidation event schemas — Pydantic contracts for data validation.

Point-in-time compliance:
- Every event has exact timestamp (milliseconds precision minimum)
- No future peeking
- Source + lineage tracked
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LiquidationEvent(BaseModel):
    """Single liquidation event from exchange or on-chain.

    PIT Compliance:
    - timestamp: Exact event time (UTC, milliseconds)
    - symbol: Trading pair
    - side: Long or short liquidation
    - quantity: Liquidated amount
    - price: Liquidation price
    - source: Data origin (binance_websocket, coinglass, on_chain, etc.)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2026-09-25T18:31:08.532Z",
                "symbol": "BTCUSDT",
                "side": "long",
                "quantity": 1.5,
                "price": 65000.0,
                "source": "binance_websocket",
                "source_id": "evt_123456",
            }
        }
    )

    timestamp: datetime = Field(
        ..., description="UTC timestamp of liquidation event (PIT-compliant)"
    )
    symbol: str = Field(..., description="Trading pair (e.g., BTCUSDT)")
    side: Literal["long", "short"] = Field(..., description="Liquidation direction")
    quantity: float = Field(..., description="Liquidated quantity (base asset)")
    price: float = Field(..., description="Liquidation price (quote asset)")
    source: str = Field(..., description="Data source (binance_websocket, etc.)")
    source_id: str = Field(..., description="Unique source event ID")

    @property
    def usd_value(self) -> float:
        """USD value of liquidation event."""
        return self.quantity * self.price

    def dict_with_metadata(self) -> dict:
        """Export with computed metadata."""
        return {
            **self.model_dump(),
            "usd_value": self.usd_value,
            "timestamp_iso": self.timestamp.isoformat(),
        }


class LiquidationBatch(BaseModel):
    """Batch of liquidation events from a collection run.

    Used for:
    - Raw data validation
    - Deduplication checking
    - Source reliability scoring
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "batch_id": "batch_20260925_1803",
                "events": [
                    {
                        "timestamp": "2026-09-25T18:03:08.532Z",
                        "symbol": "BTCUSDT",
                        "side": "long",
                        "quantity": 1.5,
                        "price": 65000.0,
                        "source": "binance_websocket",
                        "source_id": "evt_123456",
                    }
                ],
                "batch_timestamp": "2026-09-25T18:03:10.000Z",
                "source": "binance_websocket",
                "total_usd_volume": 97500.0,
            }
        }
    )

    batch_id: str = Field(..., description="Unique batch identifier")
    events: list[LiquidationEvent] = Field(..., description="Events in batch")
    batch_timestamp: datetime = Field(..., description="When batch was collected")
    source: str = Field(..., description="Batch data source")
    total_usd_volume: float = Field(..., description="Total USD liquidated")

    @model_validator(mode="after")
    def validate_batch_consistency(self) -> "LiquidationBatch":
        """Validate batch consistency."""
        if not self.events:
            raise ValueError("Batch must contain at least one event")

        # Verify total_usd_volume matches events
        computed_volume = sum(e.usd_value for e in self.events)
        if abs(computed_volume - self.total_usd_volume) > 0.01:
            raise ValueError(
                f"Total USD volume mismatch: computed {computed_volume}, "
                f"provided {self.total_usd_volume}"
            )

        # Verify all events are from same source
        if not all(e.source == self.source for e in self.events):
            raise ValueError("All events must be from same source as batch")

        return self


class LiquidationQAReport(BaseModel):
    """Quality assurance report for liquidation dataset."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_events": 5000,
                "duplicates_found": 12,
                "outliers_flagged": 3,
                "gaps_identified": 0,
                "source_reliability_score": 0.98,
                "data_quality_score": 0.95,
                "timestamp": "2026-09-25T18:45:00.000Z",
            }
        }
    )

    total_events: int = Field(..., description="Total events processed")
    duplicates_found: int = Field(..., description="Exact duplicate events")
    outliers_flagged: int = Field(..., description="High-value outliers ($10M+)")
    gaps_identified: int = Field(..., description="Time windows with missing data")
    source_reliability_score: float = Field(
        ..., description="Source trust metric [0,1]"
    )
    data_quality_score: float = Field(..., description="Overall quality [0,1]")
    timestamp: datetime = Field(..., description="When QA was run")
