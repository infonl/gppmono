"""Application configuration using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        "postgresql+asyncpg://postgres:localdev@localhost:5432/gpp_api",
        description="PostgreSQL connection URL (async)",
    )
    db_echo: bool = Field(False, description="Echo SQL statements for debugging")

    # Redis
    redis_url: str = Field(
        "redis://localhost:6379/3",
        description="Redis connection URL for task queue",
    )

    # OpenZaak Integration
    openzaak_documents_api_url: str = Field(
        "http://openzaak:8000/documenten/api/v1",
        description="OpenZaak Documents API base URL",
    )
    openzaak_catalogi_api_url: str = Field(
        "http://openzaak:8000/catalogi/api/v1",
        description="OpenZaak Catalogi API base URL (for informatieobjecttype URLs)",
    )
    openzaak_client_id: str = Field(
        "",
        description="OpenZaak API client ID",
    )
    openzaak_secret: str = Field(
        "",
        description="OpenZaak API secret",
    )

    # GPP Zoeken (Search) Integration
    gpp_zoeken_url: str = Field(
        "",
        description="GPP Zoeken API URL for indexing",
    )
    gpp_zoeken_api_key: str = Field(
        "",
        description="GPP Zoeken API key",
    )

    # Application
    app_name: str = Field("gpp-api", description="Application name")
    app_url: str = Field(
        "http://localhost:8000",
        description="Application URL",
    )
    debug: bool = Field(False, description="Debug mode")

    # Logging
    log_level: str = Field("INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field("json", description="Log format (json or console)")

    # API Keys
    api_keys: str = Field(
        "",
        description="Comma-separated list of valid API keys for authentication",
    )

    @property
    def api_key_list(self) -> list[str]:
        """Get list of valid API keys."""
        if not self.api_keys:
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
