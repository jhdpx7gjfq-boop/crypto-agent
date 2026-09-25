"""Common types and Pydantic base models."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AlertZone(str, Enum):
    """Alert zone classification."""

    HIGH = "high"
    LOW = "low"
    NEUTRAL = None


class PriceAlert(BaseModel):
    """Price alert notification."""

    zone: AlertZone = Field(..., description="Alert zone (high, low, or None)")
    price: float = Field(..., description="Price that triggered alert")
    asset: str = Field(default="BTC", description="Asset")
    message: str = Field(..., description="Alert message")

    model_config = ConfigDict(use_enum_values=True)
