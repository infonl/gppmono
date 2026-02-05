#!/usr/bin/env python3
"""End-to-end test script for metadata generation with real OpenRouter API.

This script tests the full flow:
1. Extract text from PDF
2. Generate metadata via LLM
3. Validate the response matches DIWOO schema
4. Output results as JSON

Prerequisites:
    OPENROUTER_API_KEY must be set in .env

Usage:
    uv run python scripts/test_e2e.py
    uv run python scripts/test_e2e.py --file data/samples/woo_besluit_landsadvocaat_stikstof.pdf
    uv run python scripts/test_e2e.py --all --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import structlog

from woo_hoo.config import get_settings
from woo_hoo.models.requests import DocumentContent, MetadataGenerationRequest
from woo_hoo.services.document_extractor import extract_text_from_file
from woo_hoo.services.metadata_generator import MetadataGenerator
from woo_hoo.services.prompt_templates import OutputMode, get_system_prompt

logger = structlog.get_logger(__name__)

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"


@dataclass
class TestResult:
    """Result of a single e2e test."""

    filename: str
    success: bool
    extracted_chars: int
    processing_time_ms: int | None
    category: str | None
    title: str | None
    error: str | None
    raw_response: dict | None


async def test_single_file(
    filepath: Path,
    verbose: bool = False,
    output_mode: OutputMode = OutputMode.JSON,
) -> TestResult:
    """Run e2e test on a single file.

    Args:
        filepath: Path to the PDF file
        verbose: Whether to print detailed output
        output_mode: Whether to use JSON or XML output from LLM

    Returns:
        TestResult with test outcome
    """
    settings = get_settings()

    # Check API key
    if not settings.openrouter_api_key:
        return TestResult(
            filename=filepath.name,
            success=False,
            extracted_chars=0,
            processing_time_ms=None,
            category=None,
            title=None,
            error="OPENROUTER_API_KEY not configured",
            raw_response=None,
        )

    # Extract text
    try:
        text = extract_text_from_file(filepath)
        # Truncate to max allowed length
        max_length = 50000  # Leave room for metadata
        if len(text) > max_length:
            text = text[:max_length]
            if verbose:
                logger.info("Text extracted (truncated)", chars=len(text))
        elif verbose:
            logger.info("Text extracted", chars=len(text))
    except Exception as e:
        return TestResult(
            filename=filepath.name,
            success=False,
            extracted_chars=0,
            processing_time_ms=None,
            category=None,
            title=None,
            error=f"Text extraction failed: {e}",
            raw_response=None,
        )

    # Generate metadata
    request = MetadataGenerationRequest(
        document=DocumentContent(text=text, filename=filepath.name),
        include_confidence=True,
    )

    generator = MetadataGenerator()
    try:
        response = await generator.generate(request, output_mode=output_mode)
    finally:
        await generator.close()

    if not response.success:
        return TestResult(
            filename=filepath.name,
            success=False,
            extracted_chars=len(text),
            processing_time_ms=None,
            category=None,
            title=None,
            error=response.error,
            raw_response=None,
        )

    suggestion = response.suggestion
    metadata = suggestion.metadata

    # Extract primary category
    primary_category = None
    if metadata.classificatiecollectie.informatiecategorieen:
        primary_category = metadata.classificatiecollectie.informatiecategorieen[0].categorie.name

    return TestResult(
        filename=filepath.name,
        success=True,
        extracted_chars=len(text),
        processing_time_ms=suggestion.processing_time_ms,
        category=primary_category,
        title=metadata.titelcollectie.officiele_titel[:80] + "..."
        if len(metadata.titelcollectie.officiele_titel) > 80
        else metadata.titelcollectie.officiele_titel,
        error=None,
        raw_response=metadata.model_dump(mode="json", by_alias=True),
    )


async def run_all_tests(
    verbose: bool = False,
    output_mode: OutputMode = OutputMode.JSON,
) -> list[TestResult]:
    """Run e2e tests on all sample files.

    Args:
        verbose: Whether to print detailed output
        output_mode: Whether to use JSON or XML output from LLM

    Returns:
        List of test results
    """
    if not SAMPLES_DIR.exists():
        logger.error(
            "Samples directory not found",
            path=str(SAMPLES_DIR),
            hint="Run: make download-samples",
        )
        return []

    pdf_files = sorted(SAMPLES_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.error(
            "No PDF files found",
            path=str(SAMPLES_DIR),
            hint="Run: make download-samples",
        )
        return []

    results = []
    for pdf_file in pdf_files:
        logger.info("Testing", filename=pdf_file.name)
        result = await test_single_file(pdf_file, verbose, output_mode)
        results.append(result)

        if result.success:
            logger.info(
                "Test passed",
                processing_time_ms=result.processing_time_ms,
                category=result.category,
                title=result.title,
            )
            # Output full metadata JSON for inspection
            logger.info("Generated metadata", filename=pdf_file.name)
            sys.stdout.write(json.dumps(result.raw_response, indent=2, ensure_ascii=False))
            sys.stdout.write("\n")
        else:
            logger.error("Test failed", error=result.error)

    return results


def log_summary(results: list[TestResult]) -> None:
    """Log test summary."""
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed

    logger.info(
        "Test summary",
        total=len(results),
        passed=passed,
        failed=failed,
    )

    if failed > 0:
        for r in results:
            if not r.success:
                logger.warning("Failed test", filename=r.filename, error=r.error)

    # Performance stats
    times = [r.processing_time_ms for r in results if r.processing_time_ms]
    if times:
        logger.info(
            "Processing times",
            average_ms=f"{sum(times) / len(times):.0f}",
            min_ms=min(times),
            max_ms=max(times),
        )


def show_prompt_preview(output_mode: OutputMode = OutputMode.XML) -> None:
    """Show a preview of the system prompt with schema."""
    prompt = get_system_prompt(include_schema=True, output_mode=output_mode)
    logger.info(
        "System prompt preview",
        output_mode=output_mode.value.upper(),
        length=len(prompt),
    )
    # Write first 2000 chars to stdout for inspection
    sys.stdout.write("\n--- First 2000 characters ---\n")
    sys.stdout.write(prompt[:2000])
    sys.stdout.write("\n")
    if len(prompt) > 2000:
        sys.stdout.write(f"... ({len(prompt) - 2000} more characters)\n")


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="E2E test for DIWOO metadata generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/test_e2e.py                    # Test all samples (XML mode - default)
  uv run python scripts/test_e2e.py --json             # Test all samples (JSON mode)
  uv run python scripts/test_e2e.py --file doc.pdf    # Test single file
  uv run python scripts/test_e2e.py --show-prompt     # Show system prompt
  uv run python scripts/test_e2e.py --all --verbose   # Verbose output
        """,
    )
    parser.add_argument("--file", "-f", type=Path, help="Specific file to test")
    parser.add_argument("--all", "-a", action="store_true", help="Test all samples")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Use JSON output mode instead of XML (default)")
    parser.add_argument("--show-prompt", action="store_true", help="Show system prompt and exit")
    parser.add_argument("--output", "-o", type=Path, help="Save results to JSON file")

    args = parser.parse_args()

    # Determine output mode (XML is default, --json overrides)
    output_mode = OutputMode.JSON if args.json else OutputMode.XML

    # Show prompt preview
    if args.show_prompt:
        show_prompt_preview(output_mode)
        return 0

    # Check API key
    settings = get_settings()
    if not settings.openrouter_api_key:
        logger.error(
            "API key not configured",
            hint="Copy .env.example to .env and add your OPENROUTER_API_KEY",
        )
        return 1

    logger.info(
        "DIWOO E2E Test",
        model=settings.default_model,
        output_mode=output_mode.value.upper(),
    )

    # Run tests
    if args.file:
        if not args.file.exists():
            logger.error("File not found", path=str(args.file))
            return 1
        result = await test_single_file(args.file, args.verbose, output_mode)
        results = [result]

        if result.success:
            logger.info("Generated metadata")
            sys.stdout.write(json.dumps(result.raw_response, indent=2, ensure_ascii=False))
            sys.stdout.write("\n")
    else:
        results = await run_all_tests(args.verbose, output_mode)

    # Print summary
    log_summary(results)

    # Save results
    if args.output:
        output_data = {
            "model": settings.default_model,
            "results": [
                {
                    "filename": r.filename,
                    "success": r.success,
                    "extracted_chars": r.extracted_chars,
                    "processing_time_ms": r.processing_time_ms,
                    "category": r.category,
                    "title": r.title,
                    "error": r.error,
                }
                for r in results
            ],
        }
        args.output.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
        logger.info("Results saved", filepath=str(args.output))

    # Return exit code
    failed = sum(1 for r in results if not r.success)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
