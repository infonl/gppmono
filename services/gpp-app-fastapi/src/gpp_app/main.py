"""FastAPI application entry point."""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from gpp_app import __version__
from gpp_app.api import auth, documents, formats, metadata, publications, user_groups
from gpp_app.api.health import router as health_router
from gpp_app.config import get_settings
from gpp_app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

# Static files directory (Vue build output)
# In Docker: /app/src/gpp_app/main.py -> /app/static
# parent.parent.parent = /app/src/gpp_app -> /app/src -> /app
STATIC_DIR = Path(__file__).parent.parent.parent / "static"

# Regex for hashed assets (e.g., main-abc12345.js) - long cache
HASHED_ASSET_REGEX = re.compile(r"^[\w]+-[a-zA-Z0-9_-]{8}\.[\w]+$")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Sets up logging on startup and handles graceful shutdown.
    """
    setup_logging()
    logger.info("static_dir_check", path=str(STATIC_DIR), exists=STATIC_DIR.exists())
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    app = FastAPI(
        title="GPP App",
        description=(
            "FastAPI BFF for GPP - Generiek Publicatieplatform. "
            "Handles OIDC authentication and proxies to gpp-api backend."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add session middleware for OIDC
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        session_cookie=settings.session_cookie_name,
        max_age=86400,  # 24 hours
        same_site="lax",
        https_only=not settings.debug,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(health_router)
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    # User groups and formats mounted at /api (not /api/v1) to match frontend expectations
    app.include_router(user_groups.router, prefix="/api", tags=["user_groups"])
    app.include_router(formats.router, prefix="/api", tags=["formats"])
    app.include_router(publications.router, prefix="/api/v1", tags=["publications"])
    app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
    app.include_router(metadata.router, prefix="/api/v1", tags=["metadata"])

    # Mount static files (Vue.js build output) if directory exists
    if STATIC_DIR.exists():
        # Mount assets directory with cache headers
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # SPA fallback - serve index.html for all non-API routes
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(_request: Request, full_path: str) -> FileResponse | HTMLResponse:
            """Serve static files or fallback to index.html for SPA routing."""
            # Don't serve static files for API routes
            if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "health")):
                return HTMLResponse(status_code=404)

            # Try to serve the exact file
            file_path = STATIC_DIR / full_path
            if file_path.is_file():
                # Set cache headers based on whether file is hashed
                headers = {}
                if HASHED_ASSET_REGEX.match(file_path.name):
                    # Long cache for hashed assets (100 days)
                    headers["Cache-Control"] = "public, max-age=8640000"
                else:
                    # No cache for non-hashed files (index.html, etc.)
                    headers["Cache-Control"] = "no-cache"
                return FileResponse(str(file_path), headers=headers)

            # Fallback to index.html for SPA routing
            index_path = STATIC_DIR / "index.html"
            if index_path.is_file():
                return FileResponse(
                    str(index_path),
                    headers={"Cache-Control": "no-cache"},
                )

            return HTMLResponse(status_code=404)

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "gpp_app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
