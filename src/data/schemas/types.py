"""
Data type definitions and provenance tracking.

Phase 1: Core types for datasource ingestion and normalization.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Provenance:
    """Track data lineage and audit trail."""

    source: str  # "coingecko", "binance", "glassnode", etc.
    provider: str  # Vendor name
    endpoint: str  # API path or feed name
    retrieval_timestamp: datetime  # When we fetched it
    event_timestamp: datetime  # When the event occurred (bar close, etc.)
    symbol: str  # BTC, ETH, etc.
    timeframe: str  # 1h, 1d, 4h, etc.
    schema_version: str  # "1.0"
    data_version: str  # YYYY-MM-DD
    availability_timestamp: Optional[datetime] = None  # When data became available (PIT reconstruction)
    caveats: Optional[str] = None  # Known issues, data gaps

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in asdict(self).items()
        }


@dataclass
class OHLCV:
    """Normalized OHLCV candle."""

    timestamp: datetime  # Bar close time
    open: float
    high: float
    low: float
    close: float
    volume: float  # In base currency
    provenance: Provenance

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "provenance": self.provenance.to_dict(),
        }


@dataclass
class FeatureDefinition:
    """Feature metadata for versioning and validation."""

    name: str  # e.g., "rsi_14"
    version: str  # "1.0"
    source: str  # "layer1.coingecko_adapter"
    timestamp_semantics: str  # "point-in-time" or "bar-close"
    lookback: int  # Number of bars
    calculation: str  # Human-readable description
    missing_data_policy: str  # "forward_fill", "interpolate", "null"
    validation_status: str  # "ready", "experimental", "deprecated"
    dependencies: list[str] = None  # List of feature dependencies

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """Validation test result."""

    test_name: str
    status: str  # "PASS", "FAIL", "WARN"
    timestamp: datetime
    message: str
    component: str  # "layer1", "layer2", etc.
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat(),
        }
