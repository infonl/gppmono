"""Client for proxying requests to gpp-api backend."""

from __future__ import annotations

import unicodedata
from typing import Any

import httpx

from gpp_app.auth.oidc import OdpcUser
from gpp_app.config import get_settings
from gpp_app.utils.logging import get_logger

logger = get_logger(__name__)


def normalize_to_ascii(value: str | None) -> str:
    """Normalize a string to ASCII for HTTP headers.

    Removes diacritics and non-ASCII characters.

    Args:
        value: String to normalize

    Returns:
        ASCII-safe string
    """
    if not value:
        return ""

    # Normalize to NFD form (decomposed)
    normalized = unicodedata.normalize("NFD", value)

    # Remove combining characters (diacritics)
    ascii_str = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    # Encode to ASCII, ignoring errors
    return ascii_str.encode("ascii", errors="ignore").decode("ascii")


class GppApiClient:
    """Client for gpp-api backend with audit header injection."""

    def __init__(
        self,
        user: OdpcUser,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            user: Current user for audit headers
            client: Optional httpx client (for testing)
        """
        self.user = user
        self._external_client = client
        self._internal_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._external_client:
            return self._external_client

        if self._internal_client is None:
            settings = get_settings()
            self._internal_client = httpx.AsyncClient(
                base_url=settings.gpp_api_base_url,
                timeout=60.0,
            )
        return self._internal_client

    async def close(self) -> None:
        """Close the internal HTTP client."""
        if self._internal_client:
            await self._internal_client.aclose()
            self._internal_client = None

    def _get_headers(self, action: str | None = None) -> dict[str, str]:
        """Get headers including audit context.

        Args:
            action: Description of the action being performed

        Returns:
            Headers dict
        """
        settings = get_settings()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if settings.gpp_api_token:
            headers["Authorization"] = f"Token {settings.gpp_api_token}"

        # Add audit headers
        if self.user.id:
            headers["Audit-User-ID"] = normalize_to_ascii(self.user.id)
        if self.user.full_name:
            headers["Audit-User-Representation"] = normalize_to_ascii(self.user.full_name)
        if action:
            headers["Audit-Remarks"] = normalize_to_ascii(action)

        return headers

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        action: str | None = None,
    ) -> httpx.Response:
        """Make a GET request to gpp-api.

        Args:
            path: API path
            params: Query parameters
            action: Audit action description

        Returns:
            HTTP response
        """
        client = await self._get_client()
        response = await client.get(
            path,
            params=params,
            headers=self._get_headers(action),
        )

        logger.debug(
            "gpp_api_get",
            path=path,
            status=response.status_code,
            user_id=self.user.id,
        )

        return response

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: Any = None,
        action: str | None = None,
    ) -> httpx.Response:
        """Make a POST request to gpp-api.

        Args:
            path: API path
            json: JSON body
            data: Form data
            action: Audit action description

        Returns:
            HTTP response
        """
        client = await self._get_client()
        response = await client.post(
            path,
            json=json,
            data=data,
            headers=self._get_headers(action),
        )

        logger.debug(
            "gpp_api_post",
            path=path,
            status=response.status_code,
            user_id=self.user.id,
        )

        return response

    async def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        action: str | None = None,
    ) -> httpx.Response:
        """Make a PUT request to gpp-api.

        Args:
            path: API path
            json: JSON body
            action: Audit action description

        Returns:
            HTTP response
        """
        client = await self._get_client()
        response = await client.put(
            path,
            json=json,
            headers=self._get_headers(action),
        )

        logger.debug(
            "gpp_api_put",
            path=path,
            status=response.status_code,
            user_id=self.user.id,
        )

        return response

    async def delete(
        self,
        path: str,
        action: str | None = None,
    ) -> httpx.Response:
        """Make a DELETE request to gpp-api.

        Args:
            path: API path
            action: Audit action description

        Returns:
            HTTP response
        """
        client = await self._get_client()
        response = await client.delete(
            path,
            headers=self._get_headers(action),
        )

        logger.debug(
            "gpp_api_delete",
            path=path,
            status=response.status_code,
            user_id=self.user.id,
        )

        return response


def get_gpp_api_client(user: OdpcUser) -> GppApiClient:
    """Create a GppApiClient for a user.

    Args:
        user: Current user

    Returns:
        Configured client
    """
    return GppApiClient(user)
