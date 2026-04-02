"""Configuration management for MACS Infrastructure."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from macs.domain.interfaces import ISystemSettings


class SystemSettings(BaseSettings, ISystemSettings):
    """Postgres, Redis, and Docker environment configuration.

    Reasoning:
        Pydantic V2 automatically reads from environment variables.
        The field aliases ensure we match the expected deployment environment.
    """

    db_url: str = Field(..., alias="DATABASE_URL")
    cache_url: str = Field(..., alias="REDIS_URL")
    base_image: str = Field(default="python:3.12-slim", alias="DOCKER_BASE_IMAGE")
    lvl: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_database_url(self) -> str:
        """Returns the PostgreSQL connection string.

        Returns:
            str: The database URL from the environment configuration.
        """
        return self.db_url

    def get_redis_url(self) -> str:
        """Returns the Redis connection string.

        Returns:
            str: The cache URL from the environment configuration.
        """
        return self.cache_url

    def get_docker_base_image(self) -> str:
        """Returns the default Docker image for sibling containers.

        Returns:
            str: The configured Docker base image.
        """
        return self.base_image

    def get_log_level(self) -> str:
        """Returns the configured logging level.

        Returns:
            str: The logging level (e.g., INFO, DEBUG).
        """
        return self.lvl
