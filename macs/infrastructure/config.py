"""Configuration management for MACS Infrastructure."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from macs.domain.interfaces import ISystemSettings


class SystemSettings(BaseSettings, ISystemSettings):
    """Postgres, Redis, and Docker environment configuration.

    Reasoning:
        Using distinct field names from the interface methods prevents
        Pydantic V2 shadowing warnings and attribute access errors.
    """

    db_url: str = Field(..., min_length=1, alias="DATABASE_URL")
    cache_url: str = Field(..., min_length=1, alias="REDIS_URL")
    base_image: str = Field(default="python:3.12-slim", alias="DOCKER_BASE_IMAGE")
    lvl: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_database_url(self) -> str:
        """Returns the PostgreSQL connection string."""
        return self.db_url

    def get_redis_url(self) -> str:
        """Returns the Redis connection string."""
        return self.cache_url

    def get_docker_base_image(self) -> str:
        """Returns the default Docker image for sibling containers."""
        return self.base_image

    def get_log_level(self) -> str:
        """Returns the configured logging level."""
        return self.lvl
