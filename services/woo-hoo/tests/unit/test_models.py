"""Unit tests for Pydantic models."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from woo_hoo.models.diwoo import (
    ClassificatieCollectie,
    DiWooMetadata,
    DocumentHandeling,
    InformatieCategorieMeta,
    Organisatie,
    SoortHandelingMeta,
    TitelCollectie,
)
from woo_hoo.models.enums import InformatieCategorie, SoortHandeling


class TestInformatieCategorie:
    """Tests for InformatieCategorie enum."""

    def test_has_17_categories(self):
        """There should be exactly 17 Woo categories."""
        assert len(InformatieCategorie) == 17

    def test_all_categories_have_labels(self):
        """All categories should have Dutch labels."""
        for cat in InformatieCategorie:
            assert cat.label, f"{cat.name} missing label"
            assert len(cat.label) > 0

    def test_all_categories_have_artikel(self):
        """All categories should have Woo article reference."""
        for cat in InformatieCategorie:
            assert cat.artikel, f"{cat.name} missing artikel"
            assert cat.artikel.startswith("3.3")

    def test_all_categories_have_tooi_uri(self):
        """All categories should have valid TOOI URIs."""
        for cat in InformatieCategorie:
            assert cat.tooi_uri.startswith("https://identifier.overheid.nl/tooi/")

    @pytest.mark.parametrize(
        "cat,expected_label",
        [
            (InformatieCategorie.ADVIEZEN, "Adviezen"),
            (InformatieCategorie.CONVENANTEN, "Convenanten"),
            (InformatieCategorie.WOO_VERZOEKEN, "Woo-verzoeken en -besluiten"),
        ],
    )
    def test_specific_category_labels(self, cat: InformatieCategorie, expected_label: str):
        """Test specific category labels."""
        assert cat.label == expected_label


class TestTitelCollectie:
    """Tests for TitelCollectie model."""

    def test_valid_minimal(self):
        """Minimal valid title collection."""
        tc = TitelCollectie(officiele_titel="Test Document")
        assert tc.officiele_titel == "Test Document"
        assert tc.verkorte_titels is None

    def test_with_short_title(self):
        """Title collection with short title."""
        tc = TitelCollectie(
            officiele_titel="Long Official Title Here",
            verkorte_titels=["Short Title"],
        )
        assert tc.verkorte_titels == ["Short Title"]

    def test_empty_title_invalid(self):
        """Empty official title should be invalid."""
        with pytest.raises(ValidationError):
            TitelCollectie(officiele_titel="")

    def test_max_length_enforced(self):
        """Title should not exceed max length."""
        with pytest.raises(ValidationError):
            TitelCollectie(officiele_titel="x" * 2001)


class TestClassificatieCollectie:
    """Tests for ClassificatieCollectie model."""

    def test_valid_minimal(self):
        """Minimal valid classification with one category."""
        cc = ClassificatieCollectie(
            informatiecategorieen=[InformatieCategorieMeta(categorie=InformatieCategorie.ADVIEZEN)]
        )
        assert len(cc.informatiecategorieen) == 1

    def test_requires_at_least_one_category(self):
        """At least one informatiecategorie is required."""
        with pytest.raises(ValidationError):
            ClassificatieCollectie(informatiecategorieen=[])

    def test_multiple_categories_allowed(self):
        """Multiple categories should be allowed."""
        cc = ClassificatieCollectie(
            informatiecategorieen=[
                InformatieCategorieMeta(categorie=InformatieCategorie.ADVIEZEN),
                InformatieCategorieMeta(categorie=InformatieCategorie.ONDERZOEKSRAPPORTEN),
            ]
        )
        assert len(cc.informatiecategorieen) == 2


class TestDocumentHandeling:
    """Tests for DocumentHandeling model."""

    def test_valid_minimal(self):
        """Minimal valid document handling."""
        dh = DocumentHandeling(
            soort_handeling=SoortHandelingMeta(handeling=SoortHandeling.REGISTRATIE),
            at_time=datetime(2024, 1, 15, 10, 0, 0),
        )
        assert dh.soort_handeling.handeling == SoortHandeling.REGISTRATIE

    def test_with_organization(self):
        """Document handling with associated organization."""
        dh = DocumentHandeling(
            soort_handeling=SoortHandelingMeta(handeling=SoortHandeling.VASTSTELLING),
            at_time=datetime(2024, 1, 15, 10, 0, 0),
            was_associated_with=Organisatie(
                resource="https://identifier.overheid.nl/tooi/id/gemeente/gm0363",
                label="Gemeente Amsterdam",
            ),
        )
        assert dh.was_associated_with is not None
        assert dh.was_associated_with.label == "Gemeente Amsterdam"


class TestDiWooMetadata:
    """Tests for the main DiWooMetadata model."""

    def test_valid_minimal(self, minimal_valid_metadata: dict):
        """Minimal valid DIWOO metadata."""
        metadata = DiWooMetadata.model_validate(minimal_valid_metadata)
        assert metadata.publisher.label == "Gemeente Amsterdam"
        assert metadata.titelcollectie.officiele_titel == "Test Document"

    def test_requires_publisher(self, minimal_valid_metadata: dict):
        """Publisher is required."""
        del minimal_valid_metadata["publisher"]
        with pytest.raises(ValidationError):
            DiWooMetadata.model_validate(minimal_valid_metadata)

    def test_requires_titelcollectie(self, minimal_valid_metadata: dict):
        """Titelcollectie is required."""
        del minimal_valid_metadata["titelcollectie"]
        with pytest.raises(ValidationError):
            DiWooMetadata.model_validate(minimal_valid_metadata)

    def test_requires_classificatiecollectie(self, minimal_valid_metadata: dict):
        """Classificatiecollectie is required."""
        del minimal_valid_metadata["classificatiecollectie"]
        with pytest.raises(ValidationError):
            DiWooMetadata.model_validate(minimal_valid_metadata)

    def test_requires_documenthandelingen(self, minimal_valid_metadata: dict):
        """At least one documenthandeling is required."""
        del minimal_valid_metadata["documenthandelingen"]
        with pytest.raises(ValidationError):
            DiWooMetadata.model_validate(minimal_valid_metadata)

    def test_optional_fields(self, minimal_valid_metadata: dict):
        """Optional fields should be settable."""
        minimal_valid_metadata["omschrijvingen"] = ["Test description"]
        minimal_valid_metadata["creatiedatum"] = "2024-01-15"
        minimal_valid_metadata["trefwoorden"] = ["test", "document"]

        metadata = DiWooMetadata.model_validate(minimal_valid_metadata)
        assert metadata.omschrijvingen == ["Test description"]
        assert metadata.creatiedatum == date(2024, 1, 15)

    def test_json_serialization(self, minimal_valid_metadata: dict):
        """Metadata should serialize to JSON."""
        metadata = DiWooMetadata.model_validate(minimal_valid_metadata)
        json_data = metadata.model_dump(mode="json", by_alias=True)

        assert "publisher" in json_data
        assert "titelcollectie" in json_data
        assert "officieleTitel" in json_data["titelcollectie"]  # alias used
