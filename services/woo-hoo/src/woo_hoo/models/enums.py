"""Controlled vocabularies and enums for DIWOO metadata.

These enums correspond to the waardelijsten (value lists) from the DIWOO XSD schema
and TOOI (Thesaurus en Ontologie voor Officiële Informatievoorziening).
"""

from __future__ import annotations

from enum import Enum


class InformatieCategorie(str, Enum):
    """The 17 Woo information categories from Artikel 3.3 Wet open overheid.

    Each category maps to a TOOI URI at:
    https://identifier.overheid.nl/tooi/def/thes/kern/{value}
    """

    # Lid 1 - Verplicht actief openbaar te maken (geen uitzonderingen)
    WETTEN_AVV = "c_4191a648"  # 3.3.1a: wetten en algemeen verbindende voorschriften
    OVERIGE_BESLUITEN_AS = "c_237d1cf1"  # 3.3.1b: overige besluiten van algemene strekking
    ONTWERPEN_REGELGEVING = "c_fdee54ae"  # 3.3.1c: ontwerpen van regelgeving met adviesaanvraag
    ORGANISATIE_WERKWIJZE = "c_9f5cc14e"  # 3.3.1d: organisatie en werkwijze
    BEREIKBAARHEID = "c_e8bf4b9e"  # 3.3.1e: bereikbaarheidsgegevens

    # Lid 2 - Verplicht actief openbaar te maken (met uitzonderingen)
    INGEKOMEN_STUKKEN = "c_a3a6e5cf"  # 3.3.2a: bij vertegenwoordigende organen ingekomen stukken
    VERGADERSTUKKEN_SG = "c_7ebb6ba0"  # 3.3.2b: vergaderstukken Staten-Generaal
    VERGADERSTUKKEN_DECENTRAAL = "c_92a74153"  # 3.3.2c: vergaderstukken decentrale overheden
    AGENDAS_BESLUITENLIJSTEN = "c_5540d806"  # 3.3.2d: agenda's en besluitenlijsten bestuurscolleges
    ADVIEZEN = "c_5ba23c01"  # 3.3.2e: adviezen
    CONVENANTEN = "c_9fe65c9f"  # 3.3.2f: convenanten
    JAARPLANNEN_JAARVERSLAGEN = "c_9b4ab167"  # 3.3.2g: jaarplannen en jaarverslagen
    SUBSIDIES_ANDERS = "c_8ac47458"  # 3.3.2h: subsidieverplichtingen anders dan met beschikking
    WOO_VERZOEKEN = "c_4edc7ff0"  # 3.3.2i: Woo-verzoeken en -besluiten
    ONDERZOEKSRAPPORTEN = "c_28fb3d66"  # 3.3.2j: onderzoeksrapporten
    BESCHIKKINGEN = "c_0b6bd881"  # 3.3.2k: beschikkingen
    KLACHTOORDELEN = "c_b2f30ab9"  # 3.3.2l: klachtoordelen

    @property
    def label(self) -> str:
        """Human-readable Dutch label for this category."""
        return INFORMATIECATEGORIE_LABELS[self]

    @property
    def tooi_uri(self) -> str:
        """Full TOOI URI for this category."""
        return f"https://identifier.overheid.nl/tooi/def/thes/kern/{self.value}"

    @property
    def artikel(self) -> str:
        """Article reference in Woo (e.g., '3.3.1a')."""
        return INFORMATIECATEGORIE_ARTIKELEN[self]


INFORMATIECATEGORIE_LABELS: dict[InformatieCategorie, str] = {
    InformatieCategorie.WETTEN_AVV: "Wetten en algemeen verbindende voorschriften",
    InformatieCategorie.OVERIGE_BESLUITEN_AS: "Overige besluiten van algemene strekking",
    InformatieCategorie.ONTWERPEN_REGELGEVING: "Ontwerpen van regelgeving met adviesaanvraag",
    InformatieCategorie.ORGANISATIE_WERKWIJZE: "Organisatie en werkwijze",
    InformatieCategorie.BEREIKBAARHEID: "Bereikbaarheidsgegevens",
    InformatieCategorie.INGEKOMEN_STUKKEN: "Bij vertegenwoordigende organen ingekomen stukken",
    InformatieCategorie.VERGADERSTUKKEN_SG: "Vergaderstukken Staten-Generaal",
    InformatieCategorie.VERGADERSTUKKEN_DECENTRAAL: "Vergaderstukken decentrale overheden",
    InformatieCategorie.AGENDAS_BESLUITENLIJSTEN: "Agenda's en besluitenlijsten bestuurscolleges",
    InformatieCategorie.ADVIEZEN: "Adviezen",
    InformatieCategorie.CONVENANTEN: "Convenanten",
    InformatieCategorie.JAARPLANNEN_JAARVERSLAGEN: "Jaarplannen en jaarverslagen",
    InformatieCategorie.SUBSIDIES_ANDERS: "Subsidieverplichtingen anders dan met beschikking",
    InformatieCategorie.WOO_VERZOEKEN: "Woo-verzoeken en -besluiten",
    InformatieCategorie.ONDERZOEKSRAPPORTEN: "Onderzoeksrapporten",
    InformatieCategorie.BESCHIKKINGEN: "Beschikkingen",
    InformatieCategorie.KLACHTOORDELEN: "Klachtoordelen",
}

INFORMATIECATEGORIE_ARTIKELEN: dict[InformatieCategorie, str] = {
    InformatieCategorie.WETTEN_AVV: "3.3.1a",
    InformatieCategorie.OVERIGE_BESLUITEN_AS: "3.3.1b",
    InformatieCategorie.ONTWERPEN_REGELGEVING: "3.3.1c",
    InformatieCategorie.ORGANISATIE_WERKWIJZE: "3.3.1d",
    InformatieCategorie.BEREIKBAARHEID: "3.3.1e",
    InformatieCategorie.INGEKOMEN_STUKKEN: "3.3.2a",
    InformatieCategorie.VERGADERSTUKKEN_SG: "3.3.2b",
    InformatieCategorie.VERGADERSTUKKEN_DECENTRAAL: "3.3.2c",
    InformatieCategorie.AGENDAS_BESLUITENLIJSTEN: "3.3.2d",
    InformatieCategorie.ADVIEZEN: "3.3.2e",
    InformatieCategorie.CONVENANTEN: "3.3.2f",
    InformatieCategorie.JAARPLANNEN_JAARVERSLAGEN: "3.3.2g",
    InformatieCategorie.SUBSIDIES_ANDERS: "3.3.2h",
    InformatieCategorie.WOO_VERZOEKEN: "3.3.2i",
    InformatieCategorie.ONDERZOEKSRAPPORTEN: "3.3.2j",
    InformatieCategorie.BESCHIKKINGEN: "3.3.2k",
    InformatieCategorie.KLACHTOORDELEN: "3.3.2l",
}


class DocumentSoort(str, Enum):
    """Document types from TOOI documentsoortlijst."""

    BRIEF = "c_brief"
    NOTA = "c_nota"
    RAPPORT = "c_rapport"
    BESLUIT = "c_besluit"
    ADVIES = "c_advies"
    NOTULEN = "c_notulen"
    AGENDA = "c_agenda"
    VERSLAG = "c_verslag"
    CONVENANT = "c_convenant"
    OVEREENKOMST = "c_overeenkomst"
    BELEIDSREGEL = "c_beleidsregel"
    CIRCULAIRE = "c_circulaire"
    BESCHIKKING = "c_beschikking"
    WOO_BESLUIT = "c_woo_besluit"
    ONDERZOEKSRAPPORT = "c_onderzoeksrapport"
    JAARVERSLAG = "c_jaarverslag"
    JAARPLAN = "c_jaarplan"
    KLACHTOORDEEL = "c_klachtoordeel"
    MEMORIE_VAN_TOELICHTING = "c_memorie_van_toelichting"
    AMENDEMENT = "c_amendement"
    MOTIE = "c_motie"

    @property
    def label(self) -> str:
        """Human-readable Dutch label."""
        return DOCUMENTSOORT_LABELS.get(self, self.name.lower().replace("_", " "))

    @property
    def tooi_uri(self) -> str:
        """Full TOOI URI."""
        return f"https://identifier.overheid.nl/tooi/def/thes/kern/{self.value}"


DOCUMENTSOORT_LABELS: dict[DocumentSoort, str] = {
    DocumentSoort.BRIEF: "Brief",
    DocumentSoort.NOTA: "Nota",
    DocumentSoort.RAPPORT: "Rapport",
    DocumentSoort.BESLUIT: "Besluit",
    DocumentSoort.ADVIES: "Advies",
    DocumentSoort.NOTULEN: "Notulen",
    DocumentSoort.AGENDA: "Agenda",
    DocumentSoort.VERSLAG: "Verslag",
    DocumentSoort.CONVENANT: "Convenant",
    DocumentSoort.OVEREENKOMST: "Overeenkomst",
    DocumentSoort.BELEIDSREGEL: "Beleidsregel",
    DocumentSoort.CIRCULAIRE: "Circulaire",
    DocumentSoort.BESCHIKKING: "Beschikking",
    DocumentSoort.WOO_BESLUIT: "Woo-besluit",
    DocumentSoort.ONDERZOEKSRAPPORT: "Onderzoeksrapport",
    DocumentSoort.JAARVERSLAG: "Jaarverslag",
    DocumentSoort.JAARPLAN: "Jaarplan",
    DocumentSoort.KLACHTOORDEEL: "Klachtoordeel",
    DocumentSoort.MEMORIE_VAN_TOELICHTING: "Memorie van toelichting",
    DocumentSoort.AMENDEMENT: "Amendement",
    DocumentSoort.MOTIE: "Motie",
}


class SoortHandeling(str, Enum):
    """Document handling types from TOOI soorthandelinglijst."""

    ONTVANGST = "c_ontvangst"
    VASTSTELLING = "c_vaststelling"
    ONDERTEKENING = "c_ondertekening"
    PUBLICATIE = "c_publicatie"
    INWERKINGTREDING = "c_inwerkingtreding"
    WIJZIGING = "c_wijziging"
    INTREKKING = "c_intrekking"
    REGISTRATIE = "c_registratie"

    @property
    def label(self) -> str:
        """Human-readable Dutch label."""
        return SOORTHANDELING_LABELS.get(self, self.name.lower())

    @property
    def tooi_uri(self) -> str:
        """Full TOOI URI."""
        return f"https://identifier.overheid.nl/tooi/def/thes/kern/{self.value}"


SOORTHANDELING_LABELS: dict[SoortHandeling, str] = {
    SoortHandeling.ONTVANGST: "Ontvangst",
    SoortHandeling.VASTSTELLING: "Vaststelling",
    SoortHandeling.ONDERTEKENING: "Ondertekening",
    SoortHandeling.PUBLICATIE: "Publicatie",
    SoortHandeling.INWERKINGTREDING: "Inwerkingtreding",
    SoortHandeling.WIJZIGING: "Wijziging",
    SoortHandeling.INTREKKING: "Intrekking",
    SoortHandeling.REGISTRATIE: "Registratie",
}


class Taal(str, Enum):
    """Language codes from TOOI taallijst (ISO 639-1)."""

    NL = "c_nl"  # Nederlands
    EN = "c_en"  # Engels
    DE = "c_de"  # Duits
    FR = "c_fr"  # Frans
    FY = "c_fy"  # Fries
    PAP = "c_pap"  # Papiaments

    @property
    def label(self) -> str:
        """Human-readable Dutch label."""
        return TAAL_LABELS.get(self, self.name)

    @property
    def tooi_uri(self) -> str:
        """Full TOOI URI."""
        return f"https://identifier.overheid.nl/tooi/def/thes/kern/{self.value}"


TAAL_LABELS: dict[Taal, str] = {
    Taal.NL: "Nederlands",
    Taal.EN: "Engels",
    Taal.DE: "Duits",
    Taal.FR: "Frans",
    Taal.FY: "Fries",
    Taal.PAP: "Papiaments",
}


class DocumentRelatie(str, Enum):
    """Document relationship types from TOOI documentrelatielijst."""

    VERVANGT = "c_vervangt"
    WORDT_VERVANGEN_DOOR = "c_wordt_vervangen_door"
    WIJZIGT = "c_wijzigt"
    WORDT_GEWIJZIGD_DOOR = "c_wordt_gewijzigd_door"
    INTREKT = "c_intrekt"
    WORDT_INGETROKKEN_DOOR = "c_wordt_ingetrokken_door"
    HEEFT_BIJLAGE = "c_heeft_bijlage"
    IS_BIJLAGE_VAN = "c_is_bijlage_van"

    @property
    def label(self) -> str:
        """Human-readable Dutch label."""
        return self.name.lower().replace("_", " ")

    @property
    def tooi_uri(self) -> str:
        """Full TOOI URI."""
        return f"https://identifier.overheid.nl/tooi/def/thes/kern/{self.value}"


class RedenVerwijderingVervanging(str, Enum):
    """Reasons for document removal/replacement from TOOI."""

    ONJUISTE_INFORMATIE = "c_onjuiste_informatie"
    PRIVACYGEVOELIGE_INFORMATIE = "c_privacygevoelige_informatie"
    TECHNISCHE_FOUT = "c_technische_fout"
    VERVANGING_DOOR_NIEUWE_VERSIE = "c_vervanging_door_nieuwe_versie"

    @property
    def label(self) -> str:
        """Human-readable Dutch label."""
        return self.name.lower().replace("_", " ")

    @property
    def tooi_uri(self) -> str:
        """Full TOOI URI."""
        return f"https://identifier.overheid.nl/tooi/def/thes/kern/{self.value}"


class LLMModel(str, Enum):
    """Recommended LLM models for metadata extraction via OpenRouter.

    These models have been tested for Dutch government document analysis.
    Any valid OpenRouter model ID can be used, but these are recommended.

    IMPORTANT: For Dutch government documents, EU-based models are strongly
    recommended for data sovereignty compliance. Mistral AI models are hosted
    in the EU (France). Non-EU models may transfer data to US servers.

    Default is Mistral Large (EU-based) for data sovereignty compliance.
    """

    # =========================================================================
    # EU-BASED MODELS (Recommended for Dutch Government)
    # Mistral AI - French company, servers hosted in EU
    # =========================================================================

    # Mistral Large - Best quality, recommended default
    MISTRAL_LARGE_2512 = "mistralai/mistral-large-2512"  # Latest, 675B MoE
    MISTRAL_LARGE_2411 = "mistralai/mistral-large-2411"  # Previous stable
    MISTRAL_LARGE_2407 = "mistralai/mistral-large-2407"  # Legacy

    # Mistral Medium - Good balance of quality and cost
    MISTRAL_MEDIUM_3_1 = "mistralai/mistral-medium-3.1"
    MISTRAL_MEDIUM_3 = "mistralai/mistral-medium-3"

    # Mistral Small - Fast and cost-effective
    MISTRAL_SMALL_3_2 = "mistralai/mistral-small-3.2-24b-instruct-2506"
    MISTRAL_SMALL_3_1 = "mistralai/mistral-small-3.1-24b-instruct-2503"
    MISTRAL_SMALL_2501 = "mistralai/mistral-small-24b-instruct-2501"

    # Mistral Nemo - Lightweight, fast
    MISTRAL_NEMO = "mistralai/mistral-nemo"

    # Ministral - Compact models
    MINISTRAL_14B = "mistralai/ministral-14b-2512"
    MINISTRAL_8B = "mistralai/ministral-8b-2512"
    MINISTRAL_3B = "mistralai/ministral-3b"

    # Mixtral - Open-source MoE
    MIXTRAL_8X7B = "mistralai/mixtral-8x7b-instruct"

    # Mistral 7B - Lightweight open model
    MISTRAL_7B = "mistralai/mistral-7b-instruct-v0.3"

    # =========================================================================
    # NON-EU MODELS (Warning: Data may be processed outside EU)
    # Use only if EU data sovereignty is not a requirement
    # =========================================================================

    # Anthropic Claude (US-based)
    CLAUDE_4_5_SONNET = "anthropic/claude-4.5-sonnet-20250929"  # WARNING: Non-EU
    CLAUDE_4_5_OPUS = "anthropic/claude-4.5-opus-20251124"  # WARNING: Non-EU
    CLAUDE_4_SONNET = "anthropic/claude-4-sonnet-20250522"  # WARNING: Non-EU
    CLAUDE_4_5_HAIKU = "anthropic/claude-4.5-haiku-20251001"  # WARNING: Non-EU
    CLAUDE_3_5_SONNET = "anthropic/claude-3.5-sonnet"  # WARNING: Non-EU
    CLAUDE_3_5_HAIKU = "anthropic/claude-3-5-haiku"  # WARNING: Non-EU

    # OpenAI (US-based)
    GPT_5_1 = "openai/gpt-5.1-20251113"  # WARNING: Non-EU
    GPT_5 = "openai/gpt-5-2025-08-07"  # WARNING: Non-EU
    GPT_5_MINI = "openai/gpt-5-mini-2025-08-07"  # WARNING: Non-EU
    GPT_4_1 = "openai/gpt-4.1-2025-04-14"  # WARNING: Non-EU
    GPT_4_1_MINI = "openai/gpt-4.1-mini-2025-04-14"  # WARNING: Non-EU
    GPT_4O = "openai/gpt-4o"  # WARNING: Non-EU
    GPT_4O_MINI = "openai/gpt-4o-mini"  # WARNING: Non-EU

    # Google (US-based)
    GEMINI_2_5_PRO = "google/gemini-2.5-pro"  # WARNING: Non-EU
    GEMINI_2_5_FLASH = "google/gemini-2.5-flash"  # WARNING: Non-EU
    GEMINI_2_5_FLASH_LITE = "google/gemini-2.5-flash-lite"  # WARNING: Non-EU

    @classmethod
    def default(cls) -> LLMModel:
        """Get the default model (Mistral Large for EU compliance)."""
        return cls.MISTRAL_LARGE_2512

    @classmethod
    def eu_models(cls) -> set[LLMModel]:
        """Get all EU-based models (Mistral AI)."""
        return {
            cls.MISTRAL_LARGE_2512,
            cls.MISTRAL_LARGE_2411,
            cls.MISTRAL_LARGE_2407,
            cls.MISTRAL_MEDIUM_3_1,
            cls.MISTRAL_MEDIUM_3,
            cls.MISTRAL_SMALL_3_2,
            cls.MISTRAL_SMALL_3_1,
            cls.MISTRAL_SMALL_2501,
            cls.MISTRAL_NEMO,
            cls.MINISTRAL_14B,
            cls.MINISTRAL_8B,
            cls.MINISTRAL_3B,
            cls.MIXTRAL_8X7B,
            cls.MISTRAL_7B,
        }

    @classmethod
    def is_eu_based(cls, model_id: str) -> bool:
        """Check if a model is EU-based (data sovereignty compliant).

        Mistral AI models are hosted in the EU (France).
        """
        return model_id.startswith("mistralai/")

    @classmethod
    def is_valid_openrouter_model(cls, model_id: str) -> bool:
        """Check if a model ID looks like a valid OpenRouter model.

        This is a basic format check - actual validation happens at OpenRouter.
        Valid format: provider/model-name
        """
        if not model_id or "/" not in model_id:
            return False
        parts = model_id.split("/")
        return len(parts) == 2 and all(part.strip() for part in parts)


# Default model for metadata extraction (EU-based for data sovereignty)
DEFAULT_LLM_MODEL = LLMModel.MISTRAL_LARGE_2512.value
