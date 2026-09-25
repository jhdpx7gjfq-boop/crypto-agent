"""Path A: Liquidation Independent Alpha — Research Framework.

This module contains data collection, feature engineering, and validation
for liquidation-based alpha research (non-integrated, governance-approved
research track).

Structure:
  - liquidation_pipeline.py: Core data collection + feature engineering
  - data_sources_config.py: Data source registry + collection plan
  - (future) liquidation_analysis.ipynb: Statistical analysis

Governance:
  - Research-only (no training/optimization)
  - Walk-forward validation required
  - Real data required before any backtest claims
  - Independent from Layers 1-7 (no integration until validated)
"""

from .liquidation_pipeline import (
    LiquidationSignal,
    LiquidationFeatures,
    LiquidationDataCollector,
    LiquidationFeatureEngineer,
    LiquidationValidationPipeline,
    LiquidationAlphaResearchFramework,
)
from .data_sources_config import (
    DataSourceStatus,
    DataSourceInfo,
    DataSourceRegistry,
    DataCollectionPlan,
)

__all__ = [
    "LiquidationSignal",
    "LiquidationFeatures",
    "LiquidationDataCollector",
    "LiquidationFeatureEngineer",
    "LiquidationValidationPipeline",
    "LiquidationAlphaResearchFramework",
    "DataSourceStatus",
    "DataSourceInfo",
    "DataSourceRegistry",
    "DataCollectionPlan",
]
