"""File format endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Format(BaseModel):
    """File format model."""

    identifier: str
    name: str
    mimeType: str
    extension: str | None = None


# Static list of supported formats (matching C# FormatsMock)
FORMATS: list[Format] = [
    Format(identifier="a81129a3-ec70-40f3-8eb6-fc94e97ef865", name="7z", mimeType="application/x-7z-compressed", extension=".7z"),
    Format(identifier="a81129a3-ec70-40f3-8eb6-fc94e97ef865", name="7z Win v1", mimeType="application/x-compressed", extension=".7z"),
    Format(identifier="a81129a3-ec70-40f3-8eb6-fc94e97ef865", name="7z Win v2", mimeType="application/octet-stream", extension=".7z"),
    Format(identifier="6bdd2631-b5d5-472a-b336-9cc643822f0a", name="CSV", mimeType="text/csv"),
    Format(identifier="822928f7-73f0-45d3-b1a0-4f3a3dbc361a", name="Excel XLS", mimeType="application/vnd.ms-excel"),
    Format(identifier="fd16ded8-f013-4ca7-ba21-ee3ca36a6054", name="Excel XLSX", mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    Format(identifier="bf16a8af-f40b-4e36-96e3-0bdd5d6f5316", name="HTML", mimeType="text/html"),
    Format(identifier="26a3df9c-290c-40a4-98cb-387842816698", name="ODF", mimeType="application/vnd.oasis.opendocument.formula"),
    Format(identifier="8b31aa20-d284-4540-aca4-222e1394c1d5", name="ODP", mimeType="application/vnd.oasis.opendocument.presentation"),
    Format(identifier="837abc18-616f-4e82-945b-fe78ab939860", name="ODS", mimeType="application/vnd.oasis.opendocument.spreadsheet"),
    Format(identifier="53b7d662-4413-4901-a3a4-6c129fcb93c1", name="ODT", mimeType="application/vnd.oasis.opendocument.text"),
    Format(identifier="a8836b30-8b25-4af6-9b35-e68e4f644c59", name="PDF", mimeType="application/pdf"),
    Format(identifier="549c6a31-6274-4b51-8528-fa9de141681e", name="TXT", mimeType="text/plain"),
    Format(identifier="ff7cf4ad-372f-4996-b6af-5bf8c5b178d8", name="PPSX", mimeType="application/vnd.openxmlformats-officedocument.presentationml.slideshow"),
    Format(identifier="580e3592-c5b2-40d0-ab7a-0c626c8e171a", name="PPT", mimeType="application/vnd.ms-powerpoint"),
    Format(identifier="fc188a40-f0bf-415f-a339-fd7520b531f8", name="PPTX", mimeType="application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    Format(identifier="65298a3a-346d-4614-9fee-028f532ed8bc", name="PPS", mimeType="application/vnd.ms-powerpoint.slideshow.macroEnabled.12"),
    Format(identifier="63026476-5d40-424e-a113-b02ed7fba760", name="RTF", mimeType="application/rtf"),
    Format(identifier="26ccc5e3-acf2-4251-9618-46321e2b9d36", name="DOC", mimeType="application/msword"),
    Format(identifier="ae0ea877-3207-4a97-b5df-bf552bc9b895", name="DOCX", mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    Format(identifier="f879f55e-a9c2-4779-96b2-288d6359d86b", name="ZIP", mimeType="application/zip", extension=".zip"),
    Format(identifier="f879f55e-a9c2-4779-96b2-288d6359d86b", name="ZIP Win v1", mimeType="application/zip-compressed", extension=".zip"),
    Format(identifier="f879f55e-a9c2-4779-96b2-288d6359d86b", name="ZIP Win v2", mimeType="application/x-zip-compressed", extension=".zip"),
    Format(identifier="f879f55e-a9c2-4779-96b2-288d6359d86b", name="ZIP Win v3", mimeType="application/octet-stream", extension=".zip"),
]


@router.get("/formats", response_model=list[Format])
async def list_formats() -> list[Format]:
    """List supported file formats.

    Returns:
        List of supported file formats sorted by name
    """
    return sorted(FORMATS, key=lambda f: f.name)
