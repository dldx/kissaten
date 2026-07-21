---
type: "Reference"
title: "AI Pipeline"
description: "AI modules for extraction, categorization, search, validation, and region selection using PydanticAI and Google Gemini, including the keyword-based context filtering search architecture."
---

# AI Pipeline

## Overview

All AI modules live under `src/kissaten/ai/` and share a common stack:
- **PydanticAI** `Agent` framework with structured Pydantic `output_type` models
- **Google Gemini** models via `GOOGLE_API_KEY`
- **`thinking_budget=0`** on all agents to minimize cost/latency
- **Logfire** instrumentation for observability

## Modules

### Coffee Data Extractor (`ai/extractor.py`)

**Purpose**: Extract structured `CoffeeBean` data from roaster product pages (HTML and/or screenshots).

**Class**: `CoffeeDataExtractor` with three PydanticAI agents:
- `agent_lite` — Gemini 2.5 Flash Lite (fast/cheap extraction)
- `agent_full` — Gemini 2.5 Flash (higher-quality extraction)
- `agent_translator` — Gemini 2.5 Flash (translates foreign-language pages to English)

Accepts `BinaryContent` (screenshots) alongside text for multimodal extraction. The system prompt covers required fields (name, roaster, url), origin details (country code, region, farm, elevation, lat/lon), processing (process, variety, harvest date, prices), product info (roast level, roast profile, price options, currency, decaf, cupping score), and flavour profile.

Used by `BaseScraper` during the scraping pipeline.

### Processing Method Categorizer (`ai/processing_method_categorizer.py`)

**Purpose**: Standardize raw processing method strings (e.g., "Anaerobic Natural 72h") into canonical names.

**Class**: `ProcessCategorizer` with three agents:
- Main categorization agent (outputs `ProcessingMethodBatch`)
- Merge agent — merges near-duplicate canonical names
- Conflict resolution agent — resolves cases where different originals map to the same canonical

**Output**: `database/processing_methods_mappings.json` (159K of mappings)

Runs via Typer CLI with Rich progress bars for batch processing.

### Varietal Categorizer (`ai/varietal_categorizer.py`)

**Purpose**: Clean and standardize coffee varietal names, splitting compound strings (e.g., "Caturra, Typica" → ["Caturra", "Typica"]).

**Key logic**: A `model_validator` (`ensure_compound_split`) auto-splits LLM output if a separator was detected but the LLM returned a single name containing the separator.

**Reference data**: `database/coffee_varietals.json` (canonical names)
**Output**: `database/varietal_mappings.json` (271K of mappings)

### Tasting Note Categorizer (`ai/tasting_note_categorizer.py`)

**Purpose**: Categorize tasting notes into a three-tier hierarchy (primary → secondary → tertiary) and maintain a taste lexicon.

**Pydantic models**:
- `TastingNoteCategory` — tasting_note, primary/secondary/tertiary category, confidence. Enforces hierarchy: tertiary requires secondary.
- `CanonicalName` / `CanonicalNameBatch` — resolve raw note to a single canonical flavor word
- `NonFlavourCheck` — detects non-flavour entries (product names, marketing phrases)

**Outputs**:
- `database/tasting_notes_categorized.csv` (190K)
- `database/taste_lexicon.json` (three-tier flavor taxonomy)

Model: Gemini Flash 2.5 via PydanticAI.

### Tasting Note Splitter (`ai/tasting_note_splitter.py`)

**Purpose**: Split long descriptive tasting note strings into individual concise notes.

**Class**: `TastingNoteSplitter` using Gemini 3.1 Flash Lite.
- Short input guard: strings < 10 chars returned as-is (title-cased)
- Fallback: returns `[text.strip().title()]` on API failure

### Validation Gate (`ai/validation_gate.py`)

**Purpose**: Pre/post-flight validation for varietal and processing method mapping files, ensuring one canonical mapping per `original_name`.

Distinguishes **conflicting** duplicates (same original → different canonical) from **redundant** duplicates (same original → same canonical, case-variant). Uses Rich console for issue reporting. Raises `MappingValidationError` or warns depending on `raise_on_error` flag.

### AI Search Agent (`ai/search_agent.py`)

**Purpose**: Translate natural language coffee queries (text or image) into structured search parameters.

**Class**: `AISearchAgent` with dual search capability:
- `search_text` — general natural language search
- `tasting_notes_search` — flavour-specific search with wildcard/boolean syntax (e.g., `*chocolate*&!bitter`)

Wildcard syntax supported on: tasting_notes_search, region, producer, farm, roast_level, roast_profile, process, variety.

Integrates `AISearchCache` for caching query translations.

#### Search Architecture (v2)

The search agent was redesigned to address quality issues caused by an oversized prompt (~34K tokens of inline context data sent to `gemini-2.5-flash-lite`). The new architecture uses **keyword-based context filtering** to send only relevant database entries, reducing prompt size to ~1-3K tokens while improving accuracy.

**How it works**:

1. **Query n-gram generation** (`_generate_query_ngrams`): Extracts all contiguous word n-grams (1-4 words) from the query, filtering stopwords and short tokens. Longer n-grams rank higher for relevance scoring.

2. **Context filtering** (`_filter_context_by_query`): For each database list, finds items where any n-gram is a substring (case-insensitive). Returns up to 20 matches per list, sorted by match length (longest first). Small lists (roast levels, countries, roaster locations) are always sent in full for disambiguation.

3. **Canonical varietal querying**: The varietals query now reads from `variety_canonical` (the canonical name array) instead of the raw `variety` column. This gives the AI clean canonical names like "Sudan Rume" instead of compound scraped strings like "Caturra, Rume Sudan, H1". The AI can then use these names directly without wildcards, since the search backend already matches against the canonical array.

4. **Farm/producer/region context**: `SearchContext` (`schemas/ai_search.py`) includes `available_farms`, `available_producers`, and `available_regions` lists (2K-3.5K items each, each with `default_factory=list`). These are filtered by query keywords and sent to the AI so it can match farm names (e.g., "Finca Milan"), producer names, and regions that aren't countries.

**Example**: Query `"tanat finca milan"` filters the context to:
- `MATCHED ROASTERS: Tanat Coffee`
- `MATCHED FARMS: Finca Milan, Finca Milan Uba, Milan Estate`

The AI then generates `roaster: ["Tanat Coffee"]`, `farm: "Finca Milan"`.

#### System Prompt Design

The prompt was restructured to address specific failure patterns identified from cache feedback data (20 downvotes vs 3 upvotes across 229 cached entries):

- **Search backend behaviour explanation**: Explains that `variety` is matched against both raw scraped names AND a canonical name array, so the AI should use canonical names directly without wildcards or accent-variant enumeration.
- **Country vs region disambiguation**: Explicitly explains that countries use `origin` (Panama → `origin: ["PA"]`) while sub-national areas use `region` (Huila, Yirgacheffe).
- **Consolidated wildcard syntax**: The 6 repeated wildcard-syntax sections (one per field) were merged into a single section listing supported fields.
- **Negative examples**: The downvoted failure cases (e.g., `variety: "Panama Geisha"` instead of `origin: ["PA"]` + `variety: "Ge*sha"`) were added as explicit "what NOT to do" examples.
- **No duplicated prompt**: The system prompt is set once via `Agent(system_prompt=...)` and is no longer re-injected into the context message (previously doubled the prompt size).
- **Inline guidelines removed**: The full `SEARCH PARAMETER GUIDELINES` block (wildcard syntax, varietal matching rules, etc.) was removed from the system prompt because the keyword-filtered context data is self-describing — the AI sees only relevant canonical names and does not need wildcard enumeration guidance.

#### Frontend Integration

The frontend API client (`frontend/src/lib/api.ts`) converts `SmartSearchParameters` from the AI into `SearchParams` for the search endpoint. Both `smartSearchParameters` and `smartImageSearchParameters` methods map all fields including `farm`, `producer`, `region`, `variety`, `process`, `roaster`, `roaster_location`, `origin`, `tasting_notes_query`, and `search_text`.

### Region Selector (`ai/region_selector.py`)

**Purpose**: AI agent that selects the best geocoding result from OpenCage API responses for coffee-growing regions.

**Class**: `RegionSelector` using Gemini 2.5 Flash Lite.
Selection criteria (priority order): administrative level granularity, elevation match (coffee regions 800–2500m), OpenCage confidence score, component completeness, geographical accuracy, name clarity, coffee-growing relevance.

Outputs `RegionSelection` with `selected_index`, `canonical_state`, `confidence`, `reasoning`, `metadata`.

### Podcast Tagger (`ai/podcast_tagger.py`)

**Purpose**: Segment podcast transcripts and extract coffee-related entities using a two-stage LLM pipeline.

**Class**: `PodcastTagger` using Google GenAI client directly (for context caching) with Gemini 3.5 Flash:
1. **Segmenter** — splits transcript into topical segments with titles, summaries, timestamps, entities, key takeaways
2. **Extractor** — extracts typed coffee entities (variety/farm/process/origin/producer) from each segment, resolving canonical IDs from the Kissaten database

Sets up a Gemini context cache for entity resolution. Also handles blog/video media types.

## Caching

### AI Search Cache (`cache/ai_search_cache.py`)
**Class**: `AISearchCache` — DuckDB-backed persistent cache for AI search query translations.
- Table: `ai_query_cache` with versioning, TTL, hit counting, and thumbs-up/down feedback
- `_safe_connect()` — recovers from corrupted WAL files by deleting and reconnecting

### Media Insights Cache (`cache/media_insights_cache.py`)
**Class**: `MediaInsightsCache` — DuckDB-backed cache for podcast/blog search results and AI reranking.
- TTL: 7 days
- Cache key: query hash + results hash
- Uses Pydantic `TypeAdapter` for serialization

## AI Model Reference

| Module | Model | Framework |
|---|---|---|
| Extractor | Gemini 2.5 Flash Lite + Flash | PydanticAI Agent |
| Processing Method Categorizer | Gemini (via PydanticAI) | PydanticAI Agent |
| Varietal Categorizer | Gemini (via PydanticAI) | PydanticAI Agent |
| Tasting Note Categorizer | Gemini Flash 2.5 | PydanticAI Agent |
| Tasting Note Splitter | Gemini 3.1 Flash Lite | PydanticAI Agent |
| Validation Gate | None (deterministic) | Pure Python |
| Search Agent | Gemini 2.5 Flash Lite (text + image) | PydanticAI Agent |
| Region Selector | Gemini 2.5 Flash Lite | PydanticAI Agent |
| Podcast Tagger | Gemini 3.5 Flash (×2 stages) | PydanticAI + google.genai |
