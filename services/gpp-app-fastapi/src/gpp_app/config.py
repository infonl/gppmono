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
        "postgresql+asyncpg://postgres:localdev@localhost:5432/gpp_app",
        description="PostgreSQL connection URL (async)",
    )
    db_echo: bool = Field(False, description="Echo SQL statements for debugging")

    # GPP API Backend
    gpp_api_base_url: str = Field(
        "http://gpp-api:8000",
        description="GPP API backend base URL",
    )
    gpp_api_token: str = Field(
        "",
        description="API token for GPP API authentication",
    )

    # woo-hoo Integration
    woo_hoo_base_url: str = Field(
        "http://woo-hoo:8000",
        description="woo-hoo service base URL for metadata generation",
    )
    woo_hoo_health_timeout_seconds: int = Field(
        30,
        description="Timeout for woo-hoo health checks",
    )
    woo_hoo_generate_timeout_seconds: int = Field(
        120,
        description="Timeout for woo-hoo metadata generation",
    )

    # OIDC Configuration
    oidc_authority: str = Field(
        "",
        description="OIDC authority URL (empty for dev auto-login)",
    )
    oidc_client_id: str = Field(
        "",
        description="OIDC client ID",
    )
    oidc_client_secret: str = Field(
        "",
        description="OIDC client secret",
    )
    oidc_admin_role: str = Field(
        "odpc-admin",
        description="Role claim value for admin users",
    )
    oidc_name_claim_type: str = Field(
        "name",
        description="Claim type for user's display name",
    )
    oidc_role_claim_type: str = Field(
        "roles",
        description="Claim type for user's roles",
    )
    oidc_id_claim_type: str = Field(
        "preferred_username",
        description="Claim type for user's ID",
    )

    # Session
    session_secret_key: str = Field(
        "dev-secret-key-change-in-production-minimum-32-chars",
        description="Secret key for session encryption",
    )
    session_cookie_name: str = Field(
        "gpp_session",
        description="Session cookie name",
    )

    # Application
    app_name: str = Field("gpp-app", description="Application name")
    app_url: str = Field(
        "http://localhost:8000",
        description="Application URL (for OIDC callbacks)",
    )
    debug: bool = Field(False, description="Debug mode")

    # Logging
    log_level: str = Field("INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field("json", description="Log format (json or console)")

    @property
    def is_dev_mode(self) -> bool:
        """Check if running in dev mode (no OIDC configured)."""
        return not self.oidc_authority


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
