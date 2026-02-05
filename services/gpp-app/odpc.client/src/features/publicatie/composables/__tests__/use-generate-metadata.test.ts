import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useGenerateMetadata } from "../use-generate-metadata";
import type { Publicatie, PublicatieDocument } from "../../types";

// Mock config to use empty base URL (like production) for cleaner test URLs
vi.mock("@/config", () => ({
	config: { odpcApiUrl: "" }
}));

// Mock useAppData — simulates the waardelijsten as they exist in the GPP-app
vi.mock("@/composables/use-app-data", () => ({
	useAppData: () => ({
		lijsten: {
			value: {
				organisaties: [
					{ uuid: "org-uuid-1", naam: "Gemeente Amsterdam" },
					{ uuid: "org-uuid-2", naam: "Gemeente Utrecht" }
				],
				informatiecategorieen: [
					{ uuid: "cat-uuid-1", naam: "Adviezen" },
					{ uuid: "cat-uuid-2", naam: "Convenanten" },
					{ uuid: "cat-uuid-3", naam: "Jaarplannen en jaarverslagen" }
				],
				onderwerpen: [
					{ uuid: "ond-uuid-1", naam: "Verkeer" },
					{ uuid: "ond-uuid-2", naam: "Onderwijs" }
				]
			}
		}
	})
}));

const mockToastAdd = vi.fn();
vi.mock("@/stores/toast", () => ({
	default: { add: (...args: unknown[]) => mockToastAdd(...args) }
}));

const createPublicatie = (overrides?: Partial<Publicatie>): Publicatie => ({
	publisher: "",
	verantwoordelijke: "",
	officieleTitel: "",
	verkorteTitel: "",
	omschrijving: "",
	eigenaarGroep: null,
	publicatiestatus: "concept",
	informatieCategorieen: [],
	onderwerpen: [],
	kenmerken: [],
	...overrides
});

const createDocument = (overrides?: Partial<PublicatieDocument>): PublicatieDocument => ({
	uuid: "550e8400-e29b-41d4-a716-446655440000",
	publicatie: "660e8400-e29b-41d4-a716-446655440000",
	officieleTitel: "Advies bestemmingsplan centrum",
	publicatiestatus: "concept",
	creatiedatum: "2024-01-01",
	bestandsnaam: "advies-bestemmingsplan-centrum.pdf",
	bestandsformaat: "application/pdf",
	bestandsomvang: 245760,
	kenmerken: [],
	...overrides
});

const createWooHooResponse = (metadataOverrides = {}) => ({
	success: true,
	request_id: "req_550e8400-e29b-41d4-a716-446655440000",
	suggestion: {
		metadata: {
			identifiers: ["ZAAK-2024-001234"],
			publisher: {
				resource: "https://identifier.overheid.nl/tooi/id/gemeente/gm0363",
				label: "Gemeente Amsterdam"
			},
			titelcollectie: {
				officieleTitel: "Advies inzake wijziging bestemmingsplan centrum",
				verkorteTitels: ["Advies bestemmingsplan centrum"],
				alternatieveTitels: null
			},
			omschrijvingen: [
				"Advies van de commissie ruimtelijke ordening over de voorgenomen wijziging van het bestemmingsplan voor het centrumgebied, met betrekking tot horecabestemmingen."
			],
			classificatiecollectie: {
				informatiecategorieen: [
					{
						categorie: "ADVIEZEN",
						resource: "https://identifier.overheid.nl/tooi/def/thes/kern/c_5ba23c01",
						label: "Adviezen"
					}
				],
				documentsoorten: [
					{
						soort: "ADVIES",
						resource: "https://identifier.overheid.nl/tooi/def/thes/kern/c_advies",
						label: "advies"
					}
				],
				themas: [
					{
						resource: "https://identifier.overheid.nl/tooi/def/thes/kern/c_verkeer",
						label: "Verkeer"
					}
				],
				trefwoorden: ["bestemmingsplan", "horeca", "centrum"]
			},
			creatiedatum: "2024-03-15",
			geldigheid: {
				begindatum: "2024-03-15T00:00:00",
				einddatum: "2025-03-15"
			},
			language: {
				taal: "NL",
				resource: "https://identifier.overheid.nl/tooi/def/thes/kern/c_nl",
				label: "Nederlands"
			},
			format: {
				resource: "https://identifier.overheid.nl/tooi/def/thes/kern/c_pdf",
				label: "PDF"
			},
			documenthandelingen: [
				{
					soortHandeling: {
						handeling: "ONDERTEKENING",
						resource: "https://identifier.overheid.nl/tooi/def/thes/kern/c_ondertekening",
						label: "ondertekening"
					},
					atTime: "2024-03-14T10:00:00Z",
					wasAssociatedWith: {
						resource: "https://identifier.overheid.nl/tooi/id/gemeente/gm0363",
						label: "Gemeente Amsterdam"
					}
				},
				{
					soortHandeling: {
						handeling: "ONTVANGST",
						resource: "https://identifier.overheid.nl/tooi/def/thes/kern/c_ontvangst",
						label: "ontvangst"
					},
					atTime: "2024-03-13T09:30:00Z",
					wasAssociatedWith: {
						resource: "https://identifier.overheid.nl/tooi/id/gemeente/gm0363",
						label: "Gemeente Amsterdam"
					}
				}
			],
			verantwoordelijke: null,
			medeverantwoordelijken: null,
			opsteller: null,
			naamOpsteller: null,
			aggregatiekenmerk: null,
			isPartOf: null,
			hasParts: null,
			documentrelaties: null,
			redenVerwijderingVervanging: null,
			...metadataOverrides
		},
		confidence: {
			overall: 0.85,
			fields: []
		},
		model_used: "mistralai/mistral-large-2411",
		processing_time_ms: 2847
	},
	error: null
});

const DOC_UUID = "550e8400-e29b-41d4-a716-446655440000";

describe("useGenerateMetadata", () => {
	let fetchSpy: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		fetchSpy = vi.fn();
		vi.stubGlobal("fetch", fetchSpy);
		vi.spyOn(console, "error").mockImplementation(() => {});
		vi.spyOn(console, "warn").mockImplementation(() => {});
		mockToastAdd.mockClear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
	});

	describe("generateMetadataPreview", () => {
		it("sets isGenerating to true during request and false after", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { isGenerating, generateMetadataPreview } = useGenerateMetadata();

			expect(isGenerating.value).toBe(false);
			const promise = generateMetadataPreview(createPublicatie(), [createDocument()]);
			expect(isGenerating.value).toBe(true);
			await promise;
			expect(isGenerating.value).toBe(false);
		});

		it("calls the correct backend endpoint", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			await generateMetadataPreview(createPublicatie(), [createDocument()]);

			expect(fetchSpy).toHaveBeenCalledWith(`/api/v1/metadata/generate/${DOC_UUID}`, {
				method: "POST"
			});
		});

		it("returns publication suggestions with correct field mappings", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), [createDocument()]);

			expect(preview).not.toBeNull();
			expect(preview!.publicationSuggestions).toContainEqual(
				expect.objectContaining({
					field: "officieleTitel",
					suggestedValue: "Advies inzake wijziging bestemmingsplan centrum"
				})
			);
			expect(preview!.publicationSuggestions).toContainEqual(
				expect.objectContaining({
					field: "verkorteTitel",
					suggestedValue: "Advies bestemmingsplan centrum"
				})
			);
		});

		it("returns document suggestions with correct field mappings", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), [createDocument()]);

			expect(preview!.documentSuggestions).toHaveLength(1);
			expect(preview!.documentSuggestions[0].documentUuid).toBe(DOC_UUID);
			expect(preview!.documentSuggestions[0].fields).toContainEqual(
				expect.objectContaining({
					field: "creatiedatum",
					suggestedValue: "2024-03-15"
				})
			);
		});

		it("pre-selects suggestions when current value is empty", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(
				createPublicatie({ officieleTitel: "" }),
				[createDocument()]
			);

			const titleSuggestion = preview!.publicationSuggestions.find(
				(s) => s.field === "officieleTitel"
			);
			expect(titleSuggestion?.selected).toBe(true);
		});

		it("does not pre-select suggestions when current value exists", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(
				createPublicatie({ officieleTitel: "Existing title" }),
				[createDocument()]
			);

			const titleSuggestion = preview!.publicationSuggestions.find(
				(s) => s.field === "officieleTitel"
			);
			expect(titleSuggestion?.selected).toBe(false);
		});

		it("matches informatiecategorieen by label to waardelijst UUIDs", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), [createDocument()]);

			const catSuggestion = preview!.publicationSuggestions.find(
				(s) => s.field === "informatieCategorieen"
			);
			expect(catSuggestion?.suggestedValue).toEqual(["cat-uuid-1"]);
		});

		it("matches themas to onderwerpen waardelijst UUIDs", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), [createDocument()]);

			const themaSuggestion = preview!.publicationSuggestions.find(
				(s) => s.field === "onderwerpen"
			);
			expect(themaSuggestion?.suggestedValue).toEqual(["ond-uuid-1"]);
		});

		it("maps trefwoorden to kenmerken with bron 'woo-hoo'", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), [createDocument()]);

			const kenmerkSuggestion = preview!.publicationSuggestions.find(
				(s) => s.field === "kenmerken"
			);
			expect(kenmerkSuggestion?.suggestedValue).toEqual([
				{ kenmerk: "bestemmingsplan", bron: "woo-hoo" },
				{ kenmerk: "horeca", bron: "woo-hoo" },
				{ kenmerk: "centrum", bron: "woo-hoo" }
			]);
		});

		it("extracts documenthandelingen dates correctly", async () => {
			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(createWooHooResponse())
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), [createDocument()]);

			const docFields = preview!.documentSuggestions[0].fields;
			expect(docFields).toContainEqual(
				expect.objectContaining({
					field: "datumOndertekend",
					suggestedValue: "2024-03-14T10:00:00Z"
				})
			);
			expect(docFields).toContainEqual(
				expect.objectContaining({
					field: "ontvangstdatum",
					suggestedValue: "2024-03-13T09:30:00Z"
				})
			);
		});

		it("returns null and shows error toast when fetch fails", async () => {
			fetchSpy.mockResolvedValue({
				ok: false,
				status: 502,
				text: () => Promise.resolve("")
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), [createDocument()]);

			expect(preview).toBeNull();
			expect(mockToastAdd).toHaveBeenCalledWith({
				text: "Metadata generatie mislukt: Geen metadata suggesties gevonden in de documenten",
				type: "error"
			});
		});

		it("returns null when no documents provided", async () => {
			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), []);

			expect(preview).toBeNull();
		});

		it("handles datetime-to-date conversion for geldigheid fields", async () => {
			const response = createWooHooResponse({
				geldigheid: {
					begindatum: "2024-06-01T12:30:00Z",
					einddatum: "2025-06-01"
				}
			});

			fetchSpy.mockResolvedValue({
				ok: true,
				json: () => Promise.resolve(response)
			});

			const { generateMetadataPreview } = useGenerateMetadata();
			const preview = await generateMetadataPreview(createPublicatie(), [createDocument()]);

			expect(preview!.publicationSuggestions).toContainEqual(
				expect.objectContaining({
					field: "datumBeginGeldigheid",
					suggestedValue: "2024-06-01"
				})
			);
		});
	});

	describe("applyMetadataSuggestions", () => {
		it("applies only selected publication suggestions", () => {
			const { applyMetadataSuggestions } = useGenerateMetadata();

			const result = applyMetadataSuggestions({
				publicationSuggestions: [
					{
						field: "officieleTitel",
						label: "Titel",
						currentValue: "",
						suggestedValue: "New Title",
						selected: true
					},
					{
						field: "omschrijving",
						label: "Omschrijving",
						currentValue: "",
						suggestedValue: "New Description",
						selected: false
					}
				],
				documentSuggestions: [],
				mainDocumentName: "test.pdf"
			});

			expect(result.publicatie.officieleTitel).toBe("New Title");
			expect(result.publicatie.omschrijving).toBeUndefined();
		});

		it("applies only selected document suggestions", () => {
			const { applyMetadataSuggestions } = useGenerateMetadata();

			const result = applyMetadataSuggestions({
				publicationSuggestions: [],
				documentSuggestions: [
					{
						documentUuid: DOC_UUID,
						documentName: "test.pdf",
						fields: [
							{
								field: "officieleTitel",
								label: "Titel",
								currentValue: "",
								suggestedValue: "Doc Title",
								selected: true
							},
							{
								field: "creatiedatum",
								label: "Datum",
								currentValue: "",
								suggestedValue: "2024-01-01",
								selected: false
							}
						]
					}
				],
				mainDocumentName: "test.pdf"
			});

			const docUpdate = result.documents.get(DOC_UUID);
			expect(docUpdate?.officieleTitel).toBe("Doc Title");
			expect(docUpdate?.creatiedatum).toBeUndefined();
		});

		it("returns empty updates when nothing is selected", () => {
			const { applyMetadataSuggestions } = useGenerateMetadata();

			const result = applyMetadataSuggestions({
				publicationSuggestions: [
					{
						field: "officieleTitel",
						label: "Titel",
						currentValue: "Existing",
						suggestedValue: "New",
						selected: false
					}
				],
				documentSuggestions: [],
				mainDocumentName: "test.pdf"
			});

			expect(Object.keys(result.publicatie)).toHaveLength(0);
		});

		it("handles multiple documents", () => {
			const { applyMetadataSuggestions } = useGenerateMetadata();

			const result = applyMetadataSuggestions({
				publicationSuggestions: [],
				documentSuggestions: [
					{
						documentUuid: "doc-1",
						documentName: "doc1.pdf",
						fields: [
							{
								field: "officieleTitel",
								label: "Titel",
								currentValue: "",
								suggestedValue: "Title 1",
								selected: true
							}
						]
					},
					{
						documentUuid: "doc-2",
						documentName: "doc2.pdf",
						fields: [
							{
								field: "officieleTitel",
								label: "Titel",
								currentValue: "",
								suggestedValue: "Title 2",
								selected: true
							}
						]
					}
				],
				mainDocumentName: "doc1.pdf"
			});

			expect(result.documents.get("doc-1")?.officieleTitel).toBe("Title 1");
			expect(result.documents.get("doc-2")?.officieleTitel).toBe("Title 2");
		});
	});

	describe("checkAvailability", () => {
		it("sets isAvailable to true when health endpoint returns ok", async () => {
			fetchSpy.mockResolvedValue({ ok: true });

			const { isAvailable, checkAvailability } = useGenerateMetadata();

			expect(isAvailable.value).toBe(false);
			await checkAvailability();
			expect(isAvailable.value).toBe(true);
			expect(fetchSpy).toHaveBeenCalledWith("/api/v1/metadata/health");
		});

		it("sets isAvailable to false when health endpoint returns non-ok", async () => {
			fetchSpy.mockResolvedValue({ ok: false, status: 503 });

			const { isAvailable, checkAvailability } = useGenerateMetadata();
			await checkAvailability();

			expect(isAvailable.value).toBe(false);
		});

		it("sets isAvailable to false on network error", async () => {
			fetchSpy.mockRejectedValue(new TypeError("Failed to fetch"));

			const { isAvailable, checkAvailability } = useGenerateMetadata();
			await checkAvailability();

			expect(isAvailable.value).toBe(false);
		});
	});
});
