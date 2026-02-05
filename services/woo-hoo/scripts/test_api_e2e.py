#!/usr/bin/env python3
"""Full end-to-end API test.

This script:
1. Starts the woo_hoo FastAPI app on localhost:8000
2. Makes real HTTP requests using httpx
3. Tests both /generate (text) and /generate-from-file (upload) endpoints
4. Gets metadata from OpenRouter
5. Shuts down the server

Usage:
    uv run python scripts/test_api_e2e.py                           # Test with default sample (both routes)
    uv run python scripts/test_api_e2e.py --file path/to/doc.pdf    # Test specific file
    uv run python scripts/test_api_e2e.py --list-models             # List available models
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import httpx
import structlog
import uvicorn

from woo_hoo.main import app
from woo_hoo.services.document_extractor import extract_text_from_file

logger = structlog.get_logger(__name__)

BASE_URL = "http://localhost:8000"
SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"
DEFAULT_SAMPLE = SAMPLES_DIR / "woo_besluit_landsadvocaat_stikstof.pdf"


def start_server() -> uvicorn.Server:
    """Start the FastAPI server in a background thread."""
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to be ready
    for _ in range(50):
        try:
            response = httpx.get(f"{BASE_URL}/health", timeout=0.5)
            if response.status_code == 200:
                logger.info("Server started", url=BASE_URL)
                return server
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(0.1)

    raise RuntimeError("Server failed to start")


def stop_server(server: uvicorn.Server) -> None:
    """Stop the server."""
    server.should_exit = True
    logger.info("Server stopped")


def test_health() -> bool:
    """Test health endpoint."""
    logger.info("Testing health endpoint")
    response = httpx.get(f"{BASE_URL}/health")

    if response.status_code == 200:
        data = response.json()
        logger.info("Health check passed", service=data.get("service"), version=data.get("version"))
        return True

    logger.error("Health check failed", status_code=response.status_code)
    return False


def list_models() -> None:
    """List available models."""
    logger.info("Fetching models")
    response = httpx.get(f"{BASE_URL}/api/v1/metadata/models")

    if response.status_code != 200:
        logger.error("Failed", status_code=response.status_code)
        return

    data = response.json()
    logger.info("Models", default=data["default_model"], total=len(data["recommended_models"]))

    for model in data["recommended_models"]:
        eu = "EU" if model["is_eu_based"] else "non-EU"
        default = " [DEFAULT]" if model["is_default"] else ""
        logger.info(f"  {model['id']} ({eu}){default}")


def generate_from_text(text: str, filename: str, model: str | None = None) -> dict | None:
    """Generate metadata via POST /generate with document text."""
    logger.info("Testing /generate endpoint", text_length=len(text), filename=filename)

    payload = {
        "document": {"text": text, "filename": filename},
        "include_confidence": True,
    }
    if model:
        payload["model"] = model

    response = httpx.post(
        f"{BASE_URL}/api/v1/metadata/generate",
        json=payload,
        timeout=120.0,
    )

    if response.status_code != 200:
        logger.error("/generate failed", status_code=response.status_code, detail=response.text)
        return None

    return response.json()


def generate_from_file(filepath: Path, model: str | None = None) -> dict | None:
    """Generate metadata via POST /generate-from-file with file upload."""
    logger.info("Testing /generate-from-file endpoint", file=filepath.name, size=filepath.stat().st_size)

    with open(filepath, "rb") as f:
        files = {"file": (filepath.name, f, "application/pdf")}
        data = {"model": model} if model else {}
        response = httpx.post(
            f"{BASE_URL}/api/v1/metadata/generate-from-file",
            files=files,
            data=data,
            timeout=120.0,
        )

    if response.status_code != 200:
        logger.error("/generate-from-file failed", status_code=response.status_code, detail=response.text)
        return None

    return response.json()


def log_result(result: dict, endpoint: str) -> None:
    """Log the result."""
    if not result.get("success"):
        logger.error("Generation failed", endpoint=endpoint, error=result.get("error"))
        return

    suggestion = result.get("suggestion", {})
    metadata = suggestion.get("metadata", {})

    logger.info(
        "Generation successful",
        endpoint=endpoint,
        model=suggestion.get("model_used"),
        time_ms=suggestion.get("processing_time_ms"),
        confidence=suggestion.get("confidence", {}).get("overall"),
    )

    title = metadata.get("titelcollectie", {}).get("officieleTitel", "N/A")
    logger.info("Title", title=title[:80] + "..." if len(title) > 80 else title)

    # Log full metadata JSON
    logger.info("Full metadata JSON", metadata=json.dumps(metadata, indent=2, ensure_ascii=False))


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="E2E API test for woo-hoo")
    parser.add_argument("--file", "-f", type=Path, help="PDF file to test")
    parser.add_argument("--model", "-m", type=str, help="LLM model to use")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--text-only", action="store_true", help="Only test /generate endpoint")
    parser.add_argument("--file-only", action="store_true", help="Only test /generate-from-file endpoint")
    args = parser.parse_args()

    # Start server
    server = start_server()

    try:
        if not test_health():
            return 1

        if args.list_models:
            list_models()
            return 0

        filepath = args.file or DEFAULT_SAMPLE
        if not filepath.exists():
            logger.error("File not found", path=str(filepath), hint="Run: make download-samples")
            return 1

        success = True

        # Test /generate-from-file (file upload)
        if not args.text_only:
            logger.info("=" * 50)
            result = generate_from_file(filepath, model=args.model)
            if result:
                log_result(result, "/generate-from-file")
                if not result.get("success"):
                    success = False
            else:
                success = False

        # Test /generate (text input)
        if not args.file_only:
            logger.info("=" * 50)
            text = extract_text_from_file(filepath)
            result = generate_from_text(text, filepath.name, model=args.model)
            if result:
                log_result(result, "/generate")
                if not result.get("success"):
                    success = False
            else:
                success = False

        return 0 if success else 1

    finally:
        stop_server(server)


if __name__ == "__main__":
    sys.exit(main())
