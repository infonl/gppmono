"""FastAPI dependency injection utilities."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from woo_hoo.config import Settings, get_settings
from woo_hoo.services.metadata_generator import MetadataGenerator
from woo_hoo.services.openrouter import OpenRouterClient


async def get_openrouter_client() -> AsyncGenerator[OpenRouterClient, None]:
    """Dependency that provides an OpenRouter client.

    Yields:
        OpenRouter client instance
    """
    client = OpenRouterClient()
    try:
        yield client
    finally:
        await client.close()


async def get_metadata_generator() -> AsyncGenerator[MetadataGenerator, None]:
    """Dependency that provides a MetadataGenerator.

    Yields:
        MetadataGenerator instance
    """
    generator = MetadataGenerator()
    try:
        yield generator
    finally:
        await generator.close()


def get_app_settings() -> Settings:
    """Dependency that provides application settings.

    Returns:
        Application settings
    """
    return get_settings()
