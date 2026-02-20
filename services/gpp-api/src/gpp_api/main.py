"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gpp_api import __version__
from gpp_api.api.routers import health, publications, documents, organisations, categories, topics
from gpp_api.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Sets up logging on startup and handles graceful shutdown.
    """
    setup_logging()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="GPP API",
        description=(
            "FastAPI backend for GPP - Generiek Publicatieplatform. "
            "Manages publications, documents, and metadata for Dutch government Woo compliance."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(publications.router, prefix="/api/v2", tags=["publications"])
    app.include_router(documents.router, prefix="/api/v2", tags=["documents"])
    app.include_router(organisations.router, prefix="/api/v2", tags=["organisations"])
    app.include_router(categories.router, prefix="/api/v2", tags=["categories"])
    app.include_router(topics.router, prefix="/api/v2", tags=["topics"])

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "gpp_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
