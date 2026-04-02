"""Unit tests for MACS Configuration Management."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from macs.infrastructure.config import SystemSettings


class TestSystemSettings:
    """Test suite for environment variable parsing and validation.

    Reasoning:
        Config validation is the first line of defense. These tests ensure the
        system refuses to start if required infrastructure handles are missing.
    """

    def test_settings_load_from_env_success(self) -> None:
        """Verifies that settings correctly map from environment variables."""
        mock_env = {
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "REDIS_URL": "redis://localhost:6379/0",
            "DOCKER_BASE_IMAGE": "macs-custom:latest",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, mock_env):
            settings = SystemSettings()
            assert settings.get_database_url() == mock_env["DATABASE_URL"]
            assert settings.get_redis_url() == mock_env["REDIS_URL"]
            assert settings.get_docker_base_image() == mock_env["DOCKER_BASE_IMAGE"]
            assert settings.get_log_level() == "DEBUG"

    def test_settings_missing_required_throws_error(self) -> None:
        """Verifies that missing required fields raise a ValidationError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                SystemSettings()

            # Ensure the specific missing fields are mentioned in the error
            errors = str(exc_info.value)
            assert "DATABASE_URL" in errors
            assert "REDIS_URL" in errors

    def test_settings_defaults_work(self) -> None:
        """Verifies that optional settings fallback to their defaults."""
        mock_env = {
            "DATABASE_URL": "mock://db",
            "REDIS_URL": "mock://redis",
        }

        with patch.dict(os.environ, mock_env):
            settings = SystemSettings()
            # Defaults defined in the class
            assert settings.get_docker_base_image() == "python:3.12-slim"
            assert settings.get_log_level() == "INFO"
