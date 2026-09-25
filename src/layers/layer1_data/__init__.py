"""Layer 1 — Data Intelligence.

Raw data collection, validation, and feature engineering.
Responsible for clean, validated OHLCV feeds and derived features.
"""

from .collector import DataCollector
from .validator import DataValidator

__all__ = ["DataCollector", "DataValidator"]
