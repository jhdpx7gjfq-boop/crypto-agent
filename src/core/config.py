"""Configuration management for IGWT-PF26."""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Central configuration object."""

    # Project
    PROJECT_NAME = "IGWT-PF26"
    VERSION = "0.1.0"
    PHASE = "Phase 1 — Data Layer"

    # Paths
    ROOT_DIR = Path(__file__).parent.parent.parent
    SRC_DIR = ROOT_DIR / "src"
    DATA_DIR = ROOT_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    VALIDATION_REPORTS_DIR = DATA_DIR / "validation_reports"
    DOCS_DIR = ROOT_DIR / "docs"
    NOTEBOOKS_DIR = ROOT_DIR / "notebooks"

    # Create dirs if missing
    for d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, VALIDATION_REPORTS_DIR, DOCS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # API Keys (from environment)
    COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    GLASSNODE_API_KEY = os.getenv("GLASSNODE_API_KEY", "")
    CRYPTOQUANT_API_KEY = os.getenv("CRYPTOQUANT_API_KEY", "")
    NANSEN_API_KEY = os.getenv("NANSEN_API_KEY", "")
    ARKHAM_API_KEY = os.getenv("ARKHAM_API_KEY", "")

    # Data collection
    DATA_POLL_INTERVAL_SECONDS = int(os.getenv("DATA_POLL_INTERVAL", "3600"))
    BINANCE_FETCH_LIMIT = 1000
    LOOKBACK_DAYS = 365  # 1 year default

    # Validation thresholds
    BCE_THRESHOLD = 5.0  # Minimum score for entry signal
    X20_THRESHOLD = 70.0
    NARM_THRESHOLD = 60.0
    RCM_THRESHOLD = 70.0
    RRP_THRESHOLD = 60.0

    # Backtest settings
    MIN_TRADES_BACKTEST = 200
    MIN_PROFIT_FACTOR = 1.3
    MAX_DRAWDOWN_PCT = 25.0
    WALK_FORWARD_PERIODS = 5

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Database (DuckDB)
    DUCKDB_PATH = str(PROCESSED_DATA_DIR / "igwt.duckdb")

    # Feature store (Parquet)
    FEATURE_STORE_PATH = str(PROCESSED_DATA_DIR / "features.parquet")

    # Supported assets for analysis
    TRACKED_ASSETS = [
        "bitcoin", "ethereum", "solana", "polkadot",
        "chainlink", "uniswap", "aave", "curve",
        "avax", "arbitrum", "optimism",
    ]

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get config value by key, with fallback to env var."""
        return getattr(cls, key, default)

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production."""
        return os.getenv("ENVIRONMENT") == "production"

    @classmethod
    def is_test(cls) -> bool:
        """Check if running in test mode."""
        return os.getenv("PYTEST_CURRENT_TEST") is not None or \
               os.getenv("ENVIRONMENT") == "test"
