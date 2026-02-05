#!/usr/bin/env python3
"""Test metadata generation with real documents and OpenRouter API.

Prerequisites:
1. Set OPENROUTER_API_KEY in your .env file
2. Run: uv run python scripts/download_samples.py

Usage:
    uv run python scripts/test_generation.py
    uv run python scripts/test_generation.py --file data/samples/cybersecuritybeeld_nederland_2024.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import structlog

from woo_hoo.config import get_settings
from woo_hoo.models.requests import DocumentContent, MetadataGenerationRequest, PublisherHint
from woo_hoo.services.document_extractor import extract_text_from_file
from woo_hoo.services.metadata_generator import MetadataGenerator

logger = structlog.get_logger(__name__)

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"


async def test_single_file(filepath: Path, publisher: str | None = None) -> None:
    """Test metadata generation for a single file."""
    logger.info("Testing file", filename=filepath.name)

    # Check API key
    settings = get_settings()
    if not settings.openrouter_api_key:
        logger.error(
            "API key not configured",
            hint="Copy .env.example to .env and add your OPENROUTER_API_KEY",
        )
        return

    # Extract text
    logger.info("Extracting text from document")
    try:
        text = extract_text_from_file(filepath)
        logger.info(
            "Text extracted",
            chars=len(text),
            preview=text[:200] + "...",
        )
    except Exception as e:
        logger.error("Text extraction failed", error=str(e))
        return

    # Build request
    logger.info("Building metadata generation request")
    publisher_hint = PublisherHint(name=publisher) if publisher else None
    request = MetadataGenerationRequest(
        document=DocumentContent(text=text, filename=filepath.name),
        publisher_hint=publisher_hint,
        include_confidence=True,
    )

    # Generate metadata
    logger.info("Generating metadata", model=settings.default_model)
    generator = MetadataGenerator()
    try:
        response = await generator.generate(request)
    finally:
        await generator.close()

    # Show results
    if response.success and response.suggestion:
        suggestion = response.suggestion
        metadata = suggestion.metadata

        logger.info(
            "Generation successful",
            model=suggestion.model_used,
            processing_time_ms=suggestion.processing_time_ms,
            confidence=f"{suggestion.confidence.overall:.2f}",
        )

        logger.info("Title", title=metadata.titelcollectie.officiele_titel)

        for cat in metadata.classificatiecollectie.informatiecategorieen:
            logger.info("Category", name=cat.categorie.name, label=cat.categorie.label)

        if metadata.classificatiecollectie.trefwoorden:
            logger.info("Keywords", keywords=metadata.classificatiecollectie.trefwoorden)

        if metadata.omschrijvingen:
            logger.info("Description", text=metadata.omschrijvingen[0][:200] + "...")

        # Save full output
        output_file = filepath.with_suffix(".metadata.json")
        output_data = {
            "source_file": str(filepath),
            "success": response.success,
            "request_id": response.request_id,
            "suggestion": {
                "metadata": metadata.model_dump(mode="json", by_alias=True),
                "confidence": suggestion.confidence.model_dump(),
                "model_used": suggestion.model_used,
                "processing_time_ms": suggestion.processing_time_ms,
            },
        }
        output_file.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
        logger.info("Output saved", filepath=str(output_file))

    else:
        logger.error("Generation failed", error=response.error)


async def test_all_samples() -> None:
    """Test metadata generation for all sample documents."""
    if not SAMPLES_DIR.exists():
        logger.error(
            "Samples directory not found",
            path=str(SAMPLES_DIR),
            hint="Run: uv run python scripts/download_samples.py",
        )
        return

    pdf_files = list(SAMPLES_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.error(
            "No PDF files found",
            path=str(SAMPLES_DIR),
            hint="Run: uv run python scripts/download_samples.py",
        )
        return

    logger.info("Found sample documents", count=len(pdf_files))

    for pdf_file in pdf_files:
        await test_single_file(pdf_file)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test metadata generation")
    parser.add_argument("--file", "-f", type=Path, help="Specific file to test")
    parser.add_argument("--publisher", "-p", help="Publisher name hint")
    args = parser.parse_args()

    if args.file:
        if not args.file.exists():
            logger.error("File not found", path=str(args.file))
            return
        asyncio.run(test_single_file(args.file, args.publisher))
    else:
        asyncio.run(test_all_samples())


if __name__ == "__main__":
    main()
