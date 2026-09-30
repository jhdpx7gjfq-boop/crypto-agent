"""
Feature Store Schema Definitions - All 7 Layers
Version: 2.0.0

Defines DuckDB table schemas for Layer 1-7 features and backtest results.
"""

import logging

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "2.0.0"

# Layer 1: Data Intelligence (OHLCV)
LAYER1_SCHEMA = """
CREATE TABLE IF NOT EXISTS features_layer1 (
  timestamp BIGINT NOT NULL,
  asset VARCHAR NOT NULL,
  open DOUBLE NOT NULL,
  high DOUBLE NOT NULL,
  low DOUBLE NOT NULL,
  close DOUBLE NOT NULL,
  volume DOUBLE NOT NULL,
  PRIMARY KEY (timestamp, asset)
)
"""

# Layer 3: Wyckoff BCE (Bottom Confirmation Engine)
LAYER3_SCHEMA = """
CREATE TABLE IF NOT EXISTS features_layer3 (
  timestamp BIGINT NOT NULL,
  asset VARCHAR NOT NULL,
  bce_score DOUBLE NOT NULL,
  wyckoff_structure DOUBLE,
  volume_analysis DOUBLE,
  selling_exhaustion DOUBLE,
  smart_money_accumulation DOUBLE,
  market_structure DOUBLE,
  momentum_confirmation DOUBLE,
  valid BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (timestamp, asset)
)
"""

# Layer 4: X20 Opportunity Scanner
LAYER4_SCHEMA = """
CREATE TABLE IF NOT EXISTS features_layer4 (
  timestamp BIGINT NOT NULL,
  asset VARCHAR NOT NULL,
  x20_score DOUBLE NOT NULL,
  fundamental DOUBLE,
  narrative DOUBLE,
  quantitative DOUBLE,
  momentum DOUBLE,
  volatility DOUBLE,
  relative_strength DOUBLE,
  liquidity DOUBLE,
  valid BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (timestamp, asset)
)
"""

# Layer 5: NARM-P+ (Narrative + Adoption + Rotation)
LAYER5_SCHEMA = """
CREATE TABLE IF NOT EXISTS features_layer5 (
  timestamp BIGINT NOT NULL,
  asset VARCHAR NOT NULL,
  narm_score DOUBLE NOT NULL,
  narrative_strength DOUBLE,
  adoption DOUBLE,
  capital_rotation DOUBLE,
  fundamentals DOUBLE,
  market_timing DOUBLE,
  valid BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (timestamp, asset)
)
"""

# Layer 6: RCM/RPM (Rotation Confirmation Model)
LAYER6_SCHEMA = """
CREATE TABLE IF NOT EXISTS features_layer6 (
  timestamp BIGINT NOT NULL,
  asset VARCHAR NOT NULL,
  rcm_score DOUBLE NOT NULL,
  capital_flow DOUBLE,
  relative_strength DOUBLE,
  narrative_acceleration DOUBLE,
  fundamental_confirmation DOUBLE,
  derivatives_structure DOUBLE,
  valid BOOLEAN DEFAULT FALSE,
  walk_forward_pass BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (timestamp, asset)
)
"""

# Layer 7: RRP (Revival Radar Pipeline)
LAYER7_SCHEMA = """
CREATE TABLE IF NOT EXISTS features_layer7 (
  timestamp BIGINT NOT NULL,
  asset VARCHAR NOT NULL,
  rrp_score DOUBLE NOT NULL,
  dormancy_stage VARCHAR,
  revival_probability DOUBLE,
  snapshot_status VARCHAR,
  feature_enrichment DOUBLE,
  performance_tracked BOOLEAN DEFAULT FALSE,
  valid BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (timestamp, asset)
)
"""

# Backtest Results
BACKTEST_SCHEMA = """
CREATE TABLE IF NOT EXISTS backtest_results (
  test_id VARCHAR PRIMARY KEY,
  asset VARCHAR NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  total_trades BIGINT,
  winning_trades BIGINT,
  losing_trades BIGINT,
  profit_factor DOUBLE,
  max_drawdown DOUBLE,
  sharpe_ratio DOUBLE,
  win_rate DOUBLE,
  wfv_pass BOOLEAN DEFAULT FALSE,
  validation_status VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Schema metadata
SCHEMAS = {
    "layer1": {
        "name": "features_layer1",
        "definition": LAYER1_SCHEMA,
        "layer": 1,
        "description": "Data Intelligence - OHLCV candles",
        "indexed_by": ["timestamp", "asset"],
    },
    "layer3": {
        "name": "features_layer3",
        "definition": LAYER3_SCHEMA,
        "layer": 3,
        "description": "Wyckoff Intelligence - Bottom Confirmation Engine",
        "indexed_by": ["timestamp", "asset", "bce_score"],
    },
    "layer4": {
        "name": "features_layer4",
        "definition": LAYER4_SCHEMA,
        "layer": 4,
        "description": "X20 Engine - Asymmetric opportunity detection",
        "indexed_by": ["timestamp", "asset", "x20_score"],
    },
    "layer5": {
        "name": "features_layer5",
        "definition": LAYER5_SCHEMA,
        "layer": 5,
        "description": "NARM-P+ - Narrative + Adoption + Rotation Model",
        "indexed_by": ["timestamp", "asset", "narm_score"],
    },
    "layer6": {
        "name": "features_layer6",
        "definition": LAYER6_SCHEMA,
        "layer": 6,
        "description": "RCM/RPM - Rotation Confirmation Model",
        "indexed_by": ["timestamp", "asset", "rcm_score"],
    },
    "layer7": {
        "name": "features_layer7",
        "definition": LAYER7_SCHEMA,
        "layer": 7,
        "description": "RRP - Revival Radar Pipeline",
        "indexed_by": ["timestamp", "asset", "rrp_score"],
    },
    "backtest": {
        "name": "backtest_results",
        "definition": BACKTEST_SCHEMA,
        "layer": "backtest",
        "description": "Backtest results with walk-forward validation",
        "indexed_by": ["asset", "start_date", "wfv_pass"],
    },
}

# Validation constraints per layer
CONSTRAINTS = {
    "layer1": {
        "required_fields": ["timestamp", "asset", "open", "high", "low", "close", "volume"],
        "type_checks": {
            "timestamp": int,
            "asset": str,
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float,
        },
        "value_checks": {
            "high": (">=", "max(open, close)"),
            "low": ("<=", "min(open, close)"),
            "volume": (">=", 0),
            "prices": (">", 0),
        },
    },
    "layer3": {
        "required_fields": ["timestamp", "asset", "bce_score"],
        "valid_range": {"bce_score": (0, 6)},
        "threshold": 5.0,  # Valid signal >= 5/6
    },
    "layer4": {
        "required_fields": ["timestamp", "asset", "x20_score"],
        "valid_range": {"x20_score": (0, 100)},
    },
    "layer5": {
        "required_fields": ["timestamp", "asset", "narm_score"],
        "valid_range": {"narm_score": (0, 100)},
    },
    "layer6": {
        "required_fields": ["timestamp", "asset", "rcm_score"],
        "valid_range": {"rcm_score": (0, 100)},
        "walk_forward_required": True,
    },
    "layer7": {
        "required_fields": ["timestamp", "asset", "rrp_score"],
        "valid_range": {"rrp_score": (0, 100)},
    },
    "backtest": {
        "required_fields": ["test_id", "asset", "start_date", "end_date"],
        "validation": {
            "min_trades": 200,
            "profit_factor": (">", 1.3),
            "max_drawdown": ("<", 0.25),
        },
        "wfv_mandatory": True,
    },
}


def get_schema(layer: str) -> dict:
    """Get schema definition for a layer."""
    if layer not in SCHEMAS:
        raise ValueError(f"Unknown layer: {layer}. Available: {list(SCHEMAS.keys())}")
    return SCHEMAS[layer]


def get_all_schemas() -> dict:
    """Get all schema definitions."""
    return SCHEMAS


def get_constraints(layer: str) -> dict:
    """Get validation constraints for a layer."""
    if layer not in CONSTRAINTS:
        return {}
    return CONSTRAINTS[layer]


def validate_layer_data(layer: str, data: dict) -> tuple[bool, list[str]]:
    """
    Validate data row against layer constraints.

    Returns: (is_valid, error_messages)
    """
    errors = []
    constraints = get_constraints(layer)

    if not constraints:
        return True, []

    # Check required fields
    if "required_fields" in constraints:
        for field in constraints["required_fields"]:
            if field not in data:
                errors.append(f"Missing required field: {field}")

    # Check value ranges
    if "valid_range" in constraints:
        for field, (min_val, max_val) in constraints["valid_range"].items():
            if field in data and data[field] is not None:
                val = data[field]
                if not (min_val <= val <= max_val):
                    errors.append(
                        f"Field {field} out of range [{min_val}, {max_val}]: {val}"
                    )

    return len(errors) == 0, errors
