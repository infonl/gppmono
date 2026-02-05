"""Command-line interface for woo-hoo.

Provides CLI commands for standalone testing and development.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from woo_hoo import __version__
from woo_hoo.models.enums import InformatieCategorie
from woo_hoo.models.requests import DocumentContent, MetadataGenerationRequest, PublisherHint
from woo_hoo.services.document_extractor import extract_text_from_file
from woo_hoo.services.metadata_generator import MetadataGenerator
from woo_hoo.utils.logging import setup_logging

app = typer.Typer(
    name="woo-hoo",
    help="LLM-powered DIWOO metadata generation for Dutch government documents.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"woo-hoo version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """woo-hoo: LLM-powered DIWOO metadata generation."""
    pass


@app.command()
def generate(
    file: Annotated[
        Path,
        typer.Argument(
            help="Path to document file (PDF or text)",
            exists=True,
            readable=True,
        ),
    ],
    publisher: Annotated[
        str | None,
        typer.Option(
            "--publisher",
            "-p",
            help="Publisher organization name",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (JSON)",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="LLM model to use (defaults to Mistral Large)",
        ),
    ] = None,
) -> None:
    """Generate DIWOO metadata for a document.

    Extracts text from the document and uses an LLM to generate
    DIWOO-compliant metadata.
    """
    setup_logging()

    typer.echo(f"Extracting text from: {file}")

    try:
        text = extract_text_from_file(file)
    except Exception as e:
        typer.echo(f"Error extracting text: {e}", err=True)
        raise typer.Exit(1) from None

    typer.echo(f"Extracted {len(text)} characters")

    # Build request
    publisher_hint = PublisherHint(name=publisher) if publisher else None
    request = MetadataGenerationRequest(
        document=DocumentContent(text=text, filename=file.name),
        publisher_hint=publisher_hint,
        preferred_model=model,
    )

    typer.echo("Generating metadata...")

    # Run async generation
    async def _generate():
        generator = MetadataGenerator()
        try:
            return await generator.generate(request)
        finally:
            await generator.close()

    response = asyncio.run(_generate())

    if not response.success:
        typer.echo(f"Error: {response.error}", err=True)
        raise typer.Exit(1)

    # Output result
    result = response.suggestion.metadata.model_dump(mode="json", by_alias=True, exclude_none=True)

    if output:
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        typer.echo(f"Metadata written to: {output}")
    else:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    typer.echo(f"\nConfidence: {response.suggestion.confidence.overall:.2f}")
    typer.echo(f"Model: {response.suggestion.model_used}")
    typer.echo(f"Processing time: {response.suggestion.processing_time_ms}ms")


@app.command()
def categories() -> None:
    """List all 17 Woo information categories."""
    typer.echo("Woo Information Categories (Artikel 3.3):\n")

    for cat in InformatieCategorie:
        typer.echo(f"  {cat.name}")
        typer.echo(f"    Label: {cat.label}")
        typer.echo(f"    Artikel: {cat.artikel}")
        typer.echo(f"    URI: {cat.tooi_uri}")
        typer.echo()


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option(
            "--host",
            "-h",
            help="Host to bind to",
        ),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        typer.Option(
            "--port",
            "-p",
            help="Port to bind to",
        ),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option(
            "--reload",
            "-r",
            help="Enable auto-reload for development",
        ),
    ] = False,
) -> None:
    """Start the FastAPI development server."""
    import uvicorn

    typer.echo(f"Starting woo-hoo server at http://{host}:{port}")
    typer.echo("API docs: http://{host}:{port}/docs")

    uvicorn.run(
        "woo_hoo.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def validate(
    file: Annotated[
        Path,
        typer.Argument(
            help="Path to JSON metadata file",
            exists=True,
            readable=True,
        ),
    ],
) -> None:
    """Validate a JSON metadata file against DIWOO schema."""
    from woo_hoo.models.diwoo import DiWooMetadata

    typer.echo(f"Validating: {file}")

    try:
        content = json.loads(file.read_text())
        DiWooMetadata.model_validate(content)
        typer.echo("Validation successful!")
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid JSON: {e}", err=True)
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"Validation failed: {e}", err=True)
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
