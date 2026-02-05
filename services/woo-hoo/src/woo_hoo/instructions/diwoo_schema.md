# DIWOO Metadata Schema (JSON Output Format)

You are extracting metadata from Dutch government documents according to the DIWOO (Digitale Informatiehuishouding Wet open overheid) standard.

## Required Output Format

Return a JSON object with ALL these fields (use null for fields you cannot determine):

```json
{
  "identifiers": ["Reference numbers like kenmerk, zaaknummer, etc."],
  "publisher": {
    "name": "Organization name from letterhead/signature",
    "type": "ministerie|gemeente|provincie|waterschap|other"
  },
  "verantwoordelijke": {
    "name": "Responsible organization if different from publisher",
    "type": "ministerie|gemeente|provincie|waterschap|other"
  },
  "opsteller": {
    "name": "Drafting organization if mentioned",
    "type": "ministerie|gemeente|provincie|waterschap|other"
  },
  "naamOpsteller": "Name of document author/signatory if present",
  "titelcollectie": {
    "officieleTitel": "Full official title including reference numbers",
    "verkorteTitels": ["Short title"],
    "alternatieveTitels": ["Alternative titles if any"]
  },
  "omschrijvingen": ["Clear description of document content and purpose"],
  "classificatiecollectie": {
    "informatiecategorieen": [
      {
        "categorie": "CATEGORY_CODE",
        "confidence": 0.95,
        "reasoning": "Why this category applies"
      }
    ],
    "documentsoorten": ["DOCUMENT_TYPE"],
    "trefwoorden": ["keyword1", "keyword2", "keyword3"]
  },
  "creatiedatum": "YYYY-MM-DD",
  "geldigheid": {
    "begindatum": "YYYY-MM-DD or null",
    "einddatum": "YYYY-MM-DD or null"
  },
  "taal": "NL",
  "aggregatiekenmerk": "Group identifier if document is part of a series",
  "documentrelaties": [
    {
      "type": "BIJLAGE|VERWIJZING|REACTIE_OP",
      "label": "Description of related document"
    }
  ],
  "confidence_scores": {
    "overall": 0.95,
    "titel": 0.98,
    "publisher": 0.90,
    "informatiecategorie": 0.95,
    "creatiedatum": 0.99
  }
}
```

## Informatiecategorieen (Article 3.3 Woo)

Use EXACTLY these category codes:

| Code | Label | Article | When to use |
|------|-------|---------|-------------|
| `WETTEN_AVV` | Wetten en algemeen verbindende voorschriften | 3.3.1a | Laws, regulations |
| `OVERIGE_BESLUITEN_AS` | Overige besluiten van algemene strekking | 3.3.1b | Policy rules |
| `ONTWERPEN_REGELGEVING` | Ontwerpen van regelgeving met adviesaanvraag | 3.3.1c | Draft legislation |
| `ORGANISATIE_WERKWIJZE` | Organisatie en werkwijze | 3.3.1d | Organizational info |
| `BEREIKBAARHEID` | Bereikbaarheidsgegevens | 3.3.1e | Contact info |
| `INGEKOMEN_STUKKEN` | Bij vertegenwoordigende organen ingekomen stukken | 3.3.2a | Incoming documents to parliament |
| `VERGADERSTUKKEN_SG` | Vergaderstukken Staten-Generaal | 3.3.2b | Parliamentary documents |
| `VERGADERSTUKKEN_DECENTRAAL` | Vergaderstukken decentrale overheden | 3.3.2c | Local council documents |
| `AGENDAS_BESLUITENLIJSTEN` | Agenda's en besluitenlijsten bestuurscolleges | 3.3.2d | Agendas, decision lists |
| `ADVIEZEN` | Adviezen | 3.3.2e | Advisory documents |
| `CONVENANTEN` | Convenanten | 3.3.2f | Agreements, covenants |
| `JAARPLANNEN_JAARVERSLAGEN` | Jaarplannen en jaarverslagen | 3.3.2g | Annual plans/reports |
| `SUBSIDIES_ANDERS` | Subsidieverplichtingen anders dan met beschikking | 3.3.2h | Non-beschikking subsidies |
| `WOO_VERZOEKEN` | Woo-verzoeken en -besluiten | 3.3.2i | Woo requests and decisions |
| `ONDERZOEKSRAPPORTEN` | Onderzoeksrapporten | 3.3.2j | Research reports |
| `BESCHIKKINGEN` | Beschikkingen | 3.3.2k | Administrative decisions |
| `KLACHTOORDELEN` | Klachtoordelen | 3.3.2l | Complaint rulings |

## Documentsoorten

Use these document types:
- `BRIEF` - Letter/correspondence
- `ADVIES` - Advisory document
- `RAPPORT` - Report
- `BESLUIT` - Decision
- `VERSLAG` - Minutes/report
- `NOTA` - Memo/note
- `CONVENANT` - Agreement/covenant
- `BESCHIKKING` - Administrative decision (beschikking)
- `JAARVERSLAG` - Annual report
- `JAARPLAN` - Annual plan
- `WOO_BESLUIT` - Woo decision specifically
- `ONDERZOEKSRAPPORT` - Research report

## Publisher/Organization Extraction

Extract organization info from:
1. **Letterhead** - Logo, header text
2. **Signature block** - "Namens de minister", "De Secretaris-Generaal"
3. **Return address** - "Retouradres Postbus..."
4. **Department** - "Ministerie van...", "Gemeente...", "Directoraat-Generaal..."

Common organization types:
- Ministeries: "Ministerie van Infrastructuur en Waterstaat", "Ministerie van Financiën"
- Gemeenten: "Gemeente Amsterdam", "Gemeente Rotterdam"
- Provincies: "Provincie Noord-Holland"
- Waterschappen: "Hoogheemraadschap"

## Identifier Extraction

Look for:
- **Kenmerk**: "kenmerk 2025-54", "Uw kenmerk", "Ons kenmerk"
- **Zaaknummer**: Case numbers
- **Reference**: Document reference numbers
- **ECLI**: Court decision identifiers

## Date Extraction

Look for dates in these formats:
- "Datum 9 december 2025"
- "d.d. 15-01-2024"
- "15 januari 2024"
- Date in letterhead

Use ISO 8601: `YYYY-MM-DD`

## Extraction Rules

1. **Never use placeholders** - If you can identify the publisher, use it
2. **Extract all identifiers** - Kenmerk, zaaknummer, reference numbers
3. **Look for signatories** - Names in signature blocks → naamOpsteller
4. **Check for related documents** - References to attachments, previous correspondence
5. **Multiple categories** - A document can have multiple categories if applicable
6. **Confidence** - Rate each field 0.0-1.0 based on clarity in document

## Example: Woo Decision

```json
{
  "identifiers": ["2025-54", "MCEN/IWR-2025/..."],
  "publisher": {
    "name": "Ministerie van Infrastructuur en Waterstaat",
    "type": "ministerie"
  },
  "verantwoordelijke": null,
  "opsteller": {
    "name": "Directoraat-Generaal Mobiliteit",
    "type": "ministerie"
  },
  "naamOpsteller": null,
  "titelcollectie": {
    "officieleTitel": "Besluit op Woo-verzoek over advies stikstof Landsadvocaat, kenmerk 2025-54",
    "verkorteTitels": ["Woo-besluit stikstof Landsadvocaat"],
    "alternatieveTitels": null
  },
  "omschrijvingen": [
    "Besluit op een verzoek onder de Wet open overheid betreffende documenten over het advies van de Landsadvocaat inzake stikstofbeleid."
  ],
  "classificatiecollectie": {
    "informatiecategorieen": [
      {
        "categorie": "WOO_VERZOEKEN",
        "confidence": 0.98,
        "reasoning": "Document is explicitly a Woo decision (Besluit op Woo-verzoek)"
      }
    ],
    "documentsoorten": ["WOO_BESLUIT", "BESLUIT"],
    "trefwoorden": ["Woo-verzoek", "stikstof", "Landsadvocaat", "openbaarmaking", "MCEN"]
  },
  "creatiedatum": "2025-12-09",
  "geldigheid": null,
  "taal": "NL",
  "aggregatiekenmerk": null,
  "documentrelaties": [
    {
      "type": "BIJLAGE",
      "label": "Inventarislijst"
    }
  ],
  "confidence_scores": {
    "overall": 0.95,
    "titel": 0.98,
    "publisher": 0.85,
    "informatiecategorie": 0.98,
    "creatiedatum": 0.99
  }
}
```
