#!/usr/bin/env python3
"""Download sample documents from open.overheid.nl for testing.

Run with: uv run python scripts/download_samples.py
"""

from __future__ import annotations

from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger(__name__)

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"

# Sample documents from open.overheid.nl
# These are real Woo documents from the Dutch government
SAMPLE_URLS = [
    # Cybersecuritybeeld Nederland 2024 - onderzoeksrapport
    {
        "url": "https://open.overheid.nl/documenten/dpc-ba5f9fedb13653bca9ad8633f765ba720f422c4b/pdf",
        "filename": "cybersecuritybeeld_nederland_2024.pdf",
        "category": "ONDERZOEKSRAPPORTEN",
        "description": "Cybersecuritybeeld Nederland 2024 - jaarlijks onderzoeksrapport NCSC",
    },
    # Advies Raad van State - Het belang van het kind in meeroudergezinnen
    {
        "url": "https://open.overheid.nl/documenten/dpc-ca4ae3f026683a68b93a1fbfdaa14aeadee5b3b8/pdf",
        "filename": "advies_belang_kind_meeroudergezinnen_2024.pdf",
        "category": "ADVIEZEN",
        "description": "Advies over het belang van het kind in meeroudergezinnen",
    },
    # Jaarplan Belastingdienst 2024
    {
        "url": "https://open.overheid.nl/documenten/045b37ec-14e1-481c-8394-d437338eee50/file",
        "filename": "jaarplan_belastingdienst_2024.pdf",
        "category": "JAARPLANNEN_JAARVERSLAGEN",
        "description": "Jaarplan 2024 Belastingdienst",
    },
    # Besluit Woo-verzoek Landsadvocaat stikstof
    {
        "url": "https://open.overheid.nl/documenten/4916ff44-20f2-4ce9-a69d-71ad2de53805/file",
        "filename": "woo_besluit_landsadvocaat_stikstof.pdf",
        "category": "WOO_VERZOEKEN",
        "description": "Besluit op Woo-verzoek advies Landsadvocaat over stikstof",
    },
]


def download_samples() -> None:
    """Download sample documents for testing."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading samples", target_dir=str(SAMPLES_DIR))

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for sample in SAMPLE_URLS:
            filepath = SAMPLES_DIR / sample["filename"]

            if filepath.exists():
                logger.info("Skipping (exists)", filename=sample["filename"])
                continue

            logger.info("Downloading", filename=sample["filename"])
            try:
                response = client.get(sample["url"])
                response.raise_for_status()

                filepath.write_bytes(response.content)
                logger.info(
                    "Saved",
                    filepath=str(filepath),
                    size_kb=f"{len(response.content) / 1024:.1f}",
                )

            except httpx.HTTPError as e:
                logger.error("Download failed", filename=sample["filename"], error=str(e))

    # Create a metadata file describing the samples
    metadata_file = SAMPLES_DIR / "README.md"
    metadata_file.write_text(
        "# Sample Documents\n\n"
        "These are real documents from [open.overheid.nl](https://open.overheid.nl) "
        "for testing the woo-hoo metadata generation.\n\n"
        "| File | Category | Description |\n"
        "|------|----------|-------------|\n"
        + "\n".join(
            f"| {s['filename']} | {s['category']} | {s['description']} |" for s in SAMPLE_URLS
        )
        + "\n"
    )
    logger.info("Created metadata file", filepath=str(metadata_file))


if __name__ == "__main__":
    download_samples()
