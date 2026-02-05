"""Document text extraction utilities.

Extracts text content from various document formats (PDF, plain text)
for metadata generation.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from woo_hoo.utils.logging import get_logger

logger = get_logger(__name__)


class DocumentExtractionError(Exception):
    """Raised when document text extraction fails."""

    pass


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text content from a PDF file.

    Args:
        content: PDF file content as bytes

    Returns:
        Extracted text content

    Raises:
        DocumentExtractionError: If PDF extraction fails
    """
    try:
        reader = PdfReader(BytesIO(content))
        text_parts: list[str] = []

        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(
                    "Failed to extract text from PDF page",
                    page=page_num,
                    error=str(e),
                )

        if not text_parts:
            raise DocumentExtractionError("No text could be extracted from PDF")

        return "\n\n".join(text_parts)

    except DocumentExtractionError:
        raise
    except Exception as e:
        raise DocumentExtractionError(f"PDF extraction failed: {e}") from e


def extract_text_from_file(file_path: Path | str) -> str:
    """Extract text content from a file.

    Supports:
    - PDF files (.pdf)
    - Plain text files (.txt, .md, .rst)

    Args:
        file_path: Path to the file

    Returns:
        Extracted text content

    Raises:
        DocumentExtractionError: If extraction fails
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        content = path.read_bytes()
        return extract_text_from_pdf(content)

    if suffix in {".txt", ".md", ".rst", ".text"}:
        return path.read_text(encoding="utf-8")

    # Try to read as text for unknown extensions
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise DocumentExtractionError(f"Cannot read file as text: {e}") from e


def extract_text_from_bytes(content: bytes, filename: str | None = None) -> str:
    """Extract text content from raw bytes.

    Uses filename extension to determine file type if provided.

    Args:
        content: File content as bytes
        filename: Optional filename with extension

    Returns:
        Extracted text content

    Raises:
        DocumentExtractionError: If extraction fails
    """
    # Determine file type from filename or content
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return extract_text_from_pdf(content)

    # Check for PDF magic bytes
    if content[:4] == b"%PDF":
        return extract_text_from_pdf(content)

    # Try to decode as text
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise DocumentExtractionError("Could not decode file content as text")
