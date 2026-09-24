from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator, field_validator


class OHLCVCandle(BaseModel):
    """OHLCV data point — must be closed candle."""
    symbol: str = Field(..., description="e.g., 'BTC/USDT'")
    source: str = Field(..., description="e.g., 'binance'")
    timeframe: str = Field(..., description="e.g., 'daily', '4h'")
    timestamp: datetime = Field(..., description="UTC candle open time")
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_ohlc_consistency(self):
        max_val = max(self.open, self.close, self.low)
        min_val = min(self.open, self.close, self.high)
        if self.high < max_val:
            raise ValueError(f"high ({self.high}) must be >= max(open, close, low) ({max_val})")
        if self.low > min_val:
            raise ValueError(f"low ({self.low}) must be <= min(open, close, high) ({min_val})")
        return self


class TokenMetadata(BaseModel):
    """Immutable token metadata from CoinGecko."""
    symbol: str
    name: str
    source: str = "coingecko"
    timestamp: datetime
    market_cap: Optional[float] = Field(None, ge=0, description="USD")
    fdv: Optional[float] = Field(None, ge=0, description="Fully diluted value in USD")
    circulating_supply: Optional[float] = Field(None, ge=0)
    total_supply: Optional[float] = Field(None, ge=0)
    volume_24h: Optional[float] = Field(None, ge=0, description="USD volume")
    rank: Optional[int] = Field(None, ge=1, description="Market cap rank")

    @field_validator("fdv", "market_cap", mode="before")
    @classmethod
    def handle_none_values(cls, v):
        return None if v is None or (isinstance(v, float) and v == 0) else v
