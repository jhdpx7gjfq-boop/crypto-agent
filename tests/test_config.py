"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import AlertConfig, DataSourceConfig, PersistenceConfig, load_config


class TestDataSourceConfig:
    """Tests for DataSourceConfig schema."""

    def test_defaults(self):
        """Test DataSourceConfig default values."""
        cfg = DataSourceConfig(provider="coingecko")
        assert cfg.provider == "coingecko"
        assert cfg.enabled is True
        assert cfg.timeout_seconds == 10
        assert cfg.retry_max == 3

    def test_custom_values(self):
        """Test DataSourceConfig with custom values."""
        cfg = DataSourceConfig(
            provider="binance",
            enabled=False,
            timeout_seconds=20,
            retry_max=5,
        )
        assert cfg.provider == "binance"
        assert cfg.enabled is False
        assert cfg.timeout_seconds == 20
        assert cfg.retry_max == 5


class TestAlertConfig:
    """Tests for AlertConfig schema."""

    def test_required_fields(self):
        """Test AlertConfig requires token and chat_id."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AlertConfig(telegram_bot_token="tok123")

    def test_with_thresholds(self):
        """Test AlertConfig with custom thresholds."""
        cfg = AlertConfig(
            telegram_bot_token="tok123",
            telegram_chat_id="chat123",
            high_threshold=80000,
            low_threshold=50000,
        )
        assert cfg.high_threshold == 80000
        assert cfg.low_threshold == 50000


class TestPersistenceConfig:
    """Tests for PersistenceConfig schema."""

    def test_defaults(self):
        """Test PersistenceConfig default paths."""
        cfg = PersistenceConfig()
        assert "igwt.db" in str(cfg.db_path)
        assert "parquet" in str(cfg.parquet_dir)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_from_yaml(self):
        """Test loading config from YAML file."""
        config_data = {
            "alerts": {
                "telegram_bot_token": "test_token",
                "telegram_chat_id": "test_chat",
                "high_threshold": 75000,
            },
            "polling": {
                "interval_seconds": 30,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            config = load_config(str(config_file))
            assert config.alerts.telegram_bot_token == "test_token"
            assert config.alerts.telegram_chat_id == "test_chat"
            assert config.alerts.high_threshold == 75000
            assert config.polling.interval_seconds == 30

    def test_load_config_env_override(self):
        """Test environment variables override YAML."""
        config_data = {
            "alerts": {
                "telegram_bot_token": "yaml_token",
                "telegram_chat_id": "yaml_chat",
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            # Set env vars
            os.environ["BOT_TOKEN"] = "env_token"
            os.environ["CHAT_ID"] = "env_chat"

            try:
                config = load_config(str(config_file))
                assert config.alerts.telegram_bot_token == "env_token"
                assert config.alerts.telegram_chat_id == "env_chat"
            finally:
                # Cleanup env vars
                del os.environ["BOT_TOKEN"]
                del os.environ["CHAT_ID"]

    def test_load_config_file_not_found(self):
        """Test FileNotFoundError when no config exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)  # Change to empty directory
            with pytest.raises(FileNotFoundError):
                load_config()

    def test_load_config_resolves_paths(self):
        """Test that relative paths are resolved to absolute."""
        config_data = {
            "alerts": {
                "telegram_bot_token": "test",
                "telegram_chat_id": "test",
            },
            "persistence": {
                "db_path": "/tmp/igwt.db",
                "parquet_dir": "/tmp/parquet",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            config = load_config(str(config_file))
            # Verify they're Path objects
            assert isinstance(config.persistence.db_path, Path)
            assert isinstance(config.persistence.parquet_dir, Path)
