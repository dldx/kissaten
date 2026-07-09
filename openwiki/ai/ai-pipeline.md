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
- `tasting_notes_search` — flavor-specific search with wildcard/boolean syntax (e.g., `*chocolate*&!bitter`)

Wildcard syntax supported on: region, producer, farm, roast_level, roast_profile, process, variety.

Integrates `AISearchCache` for caching query translations.

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
| Search Agent | Gemini (text + image) | PydanticAI Agent |
| Region Selector | Gemini 2.5 Flash Lite | PydanticAI Agent |
| Podcast Tagger | Gemini 3.5 Flash (×2 stages) | PydanticAI + google.genai |
