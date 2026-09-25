"""Configuration management with YAML + environment variable override."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class DataSourceConfig(BaseModel):
    """Configuration for a data source."""

    provider: str = Field(..., description="Provider name (e.g., 'coingecko')")
    enabled: bool = Field(default=True, description="Enable this source")
    timeout_seconds: int = Field(default=10, description="HTTP request timeout")
    retry_max: int = Field(default=3, description="Max retries on failure")


class AlertConfig(BaseModel):
    """Alert configuration."""

    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_chat_id: str = Field(..., description="Telegram chat ID")
    high_threshold: float = Field(default=70000, description="High price threshold (USD)")
    low_threshold: float = Field(default=55000, description="Low price threshold (USD)")


class PersistenceConfig(BaseModel):
    """Persistence configuration."""

    db_path: Path = Field(
        default_factory=lambda: Path("data/igwt.db"),
        description="DuckDB database path",
    )
    parquet_dir: Path = Field(
        default_factory=lambda: Path("data/parquet"),
        description="Directory for Parquet data files",
    )


class PollingConfig(BaseModel):
    """Polling configuration."""

    interval_seconds: int = Field(default=60, description="Polling interval in seconds")
    enabled: bool = Field(default=True, description="Enable polling")


class Config(BaseModel):
    """Root configuration."""

    data_sources: dict[str, DataSourceConfig] = Field(
        default_factory=dict, description="Data source configurations"
    )
    alerts: AlertConfig = Field(..., description="Alert configuration")
    persistence: PersistenceConfig = Field(
        default_factory=PersistenceConfig, description="Persistence configuration"
    )
    polling: PollingConfig = Field(
        default_factory=PollingConfig, description="Polling configuration"
    )

    @field_validator("persistence", mode="before")
    @classmethod
    def resolve_paths(cls, v: object) -> object:
        """Resolve relative paths to absolute."""
        if isinstance(v, dict):
            if "db_path" in v:
                v["db_path"] = Path(v["db_path"]).resolve()
            if "parquet_dir" in v:
                v["parquet_dir"] = Path(v["parquet_dir"]).resolve()
        return v


def load_config(config_path: str | None = None) -> Config:  # noqa: C901
    """Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to config.yaml. If None, uses default locations.

    Returns:
        Validated Config instance.

    Raises:
        FileNotFoundError: If no config file found.
        ValueError: If config is invalid.
    """
    # Determine config file path
    if config_path:
        cfg_file = Path(config_path)
    else:
        # Try default locations
        candidates = [
            Path("config.local.yaml"),  # Local override (gitignored)
            Path("config.yaml"),  # Shared config
        ]
        cfg_file = None
        for candidate in candidates:
            if candidate.exists():
                cfg_file = candidate
                break

    if not cfg_file:
        raise FileNotFoundError(
            "No config file found. Create config.yaml or config.local.yaml"
        )

    # Load YAML
    with open(cfg_file) as f:
        config_data = yaml.safe_load(f) or {}

    # Override with environment variables
    if bot_token := os.environ.get("BOT_TOKEN"):
        if "alerts" not in config_data:
            config_data["alerts"] = {}
        config_data["alerts"]["telegram_bot_token"] = bot_token

    if chat_id := os.environ.get("CHAT_ID"):
        if "alerts" not in config_data:
            config_data["alerts"] = {}
        config_data["alerts"]["telegram_chat_id"] = chat_id

    if high_thresh := os.environ.get("HIGH_THRESHOLD"):
        if "alerts" not in config_data:
            config_data["alerts"] = {}
        config_data["alerts"]["high_threshold"] = float(high_thresh)

    if low_thresh := os.environ.get("LOW_THRESHOLD"):
        if "alerts" not in config_data:
            config_data["alerts"] = {}
        config_data["alerts"]["low_threshold"] = float(low_thresh)

    if poll_sec := os.environ.get("POLL_SECONDS"):
        if "polling" not in config_data:
            config_data["polling"] = {}
        config_data["polling"]["interval_seconds"] = int(poll_sec)

    return Config(**config_data)
