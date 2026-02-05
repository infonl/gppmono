"""Application configuration using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables can be set directly or via a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenRouter API
    openrouter_api_key: str = Field(
        "",
        description="OpenRouter API key for LLM access (required for generation)",
    )
    default_model: str = Field(
        "mistralai/mistral-large-2512",
        description="Default LLM model (EU-based Mistral preferred for Dutch govt data sovereignty)",
    )
    fallback_model: str = Field(
        "mistralai/mistral-small-3.2-24b-instruct-2506",
        description="Fallback model if primary fails (also EU-based)",
    )

    # Application
    app_name: str = Field("woo-hoo", description="Application name")
    app_url: str = Field(
        "http://localhost:8000",
        description="Application URL (used for OpenRouter attribution)",
    )
    debug: bool = Field(False, description="Debug mode")

    # Logging
    log_level: str = Field("INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field("json", description="Log format (json or console)")

    # LLM settings
    max_text_length: int = Field(
        15000,
        description="Maximum document text length to send to LLM",
    )
    llm_temperature: float = Field(
        0.1,
        ge=0.0,
        le=1.0,
        description="LLM temperature (low for structured extraction)",
    )
    llm_timeout_seconds: int = Field(
        60,
        description="LLM request timeout in seconds",
    )
    llm_max_retries: int = Field(
        3,
        description="Maximum retry attempts for LLM requests",
    )

    # Optional GPP integration
    gpp_publicatiebank_url: str | None = Field(
        None,
        description="GPP-publicatiebank API URL (optional for integration)",
    )
    gpp_api_token: str | None = Field(
        None,
        description="GPP API token for authentication",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
