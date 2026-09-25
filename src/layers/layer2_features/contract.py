"""
Feature contract definitions with versioning and validation.

Layer 2: Feature Store
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional


@dataclass
class FeatureContract:
    """Versioned contract for a reproducible feature."""

    name: str
    version: str
    source: str
    timestamp_semantics: str
    lookback_bars: int
    parameters: Dict[str, Any]
    dtype: str
    valid_range: Tuple[float, float]
    missing_policy: str
    calculation: str
    caveats: Optional[str] = None

    def validate_value(self, value: float) -> bool:
        if value is None or (isinstance(value, float) and value != value):
            return self.missing_policy != "drop"
        return self.valid_range[0] <= value <= self.valid_range[1]

    def validate_series(self, values: list) -> Tuple[bool, list]:
        invalid = []
        for i, val in enumerate(values):
            if not self.validate_value(val):
                invalid.append(i)
        return len(invalid) == 0, invalid


# Standard feature contracts
RSI_14 = FeatureContract(
    name="rsi_14", version="1.0", source="layer2.technical",
    timestamp_semantics="bar-close", lookback_bars=14,
    parameters={"period": 14}, dtype="float", valid_range=(0.0, 100.0),
    missing_policy="forward_fill",
    calculation="Wilder's RSI: 100 - (100 / (1 + RS))",
    caveats="First value at bar 14",
)

SMA_20 = FeatureContract(
    name="sma_20", version="1.0", source="layer2.technical",
    timestamp_semantics="bar-close", lookback_bars=20,
    parameters={"period": 20}, dtype="float", valid_range=(0.0, float("inf")),
    missing_policy="forward_fill", calculation="SMA(20)",
    caveats="First value at bar 20",
)

EMA_12 = FeatureContract(
    name="ema_12", version="1.0", source="layer2.technical",
    timestamp_semantics="bar-close", lookback_bars=12,
    parameters={"period": 12}, dtype="float", valid_range=(0.0, float("inf")),
    missing_policy="forward_fill", calculation="EMA(12)",
    caveats="First value at bar 12",
)

MACD_LINE = FeatureContract(
    name="macd_line", version="1.0", source="layer2.technical",
    timestamp_semantics="bar-close", lookback_bars=26,
    parameters={"fast": 12, "slow": 26}, dtype="float",
    valid_range=(float("-inf"), float("inf")),
    missing_policy="forward_fill", calculation="EMA(12) - EMA(26)",
    caveats="First value at bar 26",
)

BB_WIDTH = FeatureContract(
    name="bb_width", version="1.0", source="layer2.technical",
    timestamp_semantics="bar-close", lookback_bars=20,
    parameters={"period": 20, "std_dev": 2.0}, dtype="float",
    valid_range=(0.0, float("inf")), missing_policy="forward_fill",
    calculation="Bollinger Band width", caveats="First value at bar 20",
)

VOLATILITY_HV = FeatureContract(
    name="volatility_hv", version="1.0", source="layer2.technical",
    timestamp_semantics="bar-close", lookback_bars=20,
    parameters={"period": 20}, dtype="float", valid_range=(0.0, float("inf")),
    missing_policy="forward_fill", calculation="Historical volatility",
    caveats="Annualized std dev; first value at bar 20",
)
