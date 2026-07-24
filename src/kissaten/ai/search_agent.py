"""AI-powered search query translation using Gemini and PydanticAI."""

import logging
import os
import re
import time
from urllib.parse import urlencode

import duckdb
import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.gemini import GeminiModelSettings

from ..cache.ai_search_cache import AISearchCache
from ..schemas.ai_search import AISearchResponse, BasicSearchParameters, Country, SearchContext, SearchParameters

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()


class AISearchAgent:
    """AI agent for translating natural language queries to structured search parameters."""

    def __init__(
        self,
        database_connection: duckdb.DuckDBPyConnection,
        api_key: str | None = None,
        cache_db_path: str | None = None,
    ):
        """Initialize the AI search agent.

        Args:
            database_connection: DuckDB connection for querying available data
            api_key: Google API key. If None, will try to get from environment.
            cache_db_path: Path to cache database. If None, uses default location.
        """
        self.conn = database_connection
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )

        # Initialize cache
        cache_path = cache_db_path or "data/ai_search_cache.duckdb"
        self.cache = AISearchCache(cache_path)
        logger.info(f"AI search agent initialized with cache at {cache_path}")

    def _get_system_prompt(self, is_image_based: bool = False) -> str:
        """Get the system prompt for search query translation."""
        text_based_prompt = """
You are an expert coffee search assistant. Your task is to translate natural language queries
about coffee beans into structured search parameters.

You will receive:
1. A natural language query from a user
2. Filtered context data from the coffee database (only items matching query keywords)

Your job is to analyze the query and generate appropriate search parameters that will help find relevant coffee beans.
"""
        image_based_prompt = self._get_image_analysis_prompt()

        return (
            (image_based_prompt if is_image_based else text_based_prompt)
            + """
SEARCH BACKEND BEHAVIOR (critical for correct parameter choice):
- `variety` is matched against BOTH raw scraped names AND a canonical name array.
  Canonical mappings handle accent/spacing variants automatically
  (e.g., "Sudanrume" and "Sudán Rumé" both map to canonical "Sudan Rume").
  → When the context lists a canonical varietal name, use it directly WITHOUT wildcards.
  → Only use wildcards for partial/spelling-variant matching (e.g., "Ge*sha" for Geisha/Gesha).
  → Do NOT manually enumerate accent variants (e.g., NOT "Sudanrume|Sudán Rumé" — just use "Sudan Rume").
- Countries are NOT regions. Use `origin` for countries (Panama → origin: ["PA"], Colombia → origin: ["CO"]).
  Use `region` for sub-national areas (Huila, Yirgacheffe, Nariño).
- `process` is matched against `process_common_name` (a canonical processing method).

WILDCARD SYNTAX (supported by: tasting_notes_search, region, producer,
farm, roast_level, roast_profile, process, variety):
- `*` matches multiple characters (e.g., "Ge*sha" matches "Geisha", "Gesha")
- `?` matches single character
- `|` OR operator (e.g., "Light|Medium")
- `&` AND operator (e.g., "Natural&Honey" means both terms must be present)
- `!` NOT operator (e.g., "Washed&!Decaf" means Washed but not Decaf)
- `()` grouping (e.g., "Colombian&(Huila|Nariño)")
- A bare term without wildcards matches as a substring (case-insensitive).
  Use `*` explicitly when you need prefix/suffix-only matching (e.g., "*Dark" matches "Medium-Dark" but not "Darkness").

USE WILDCARDS WHEN:
- User mentions spelling variations (e.g., "geisha or gesha" → variety: "Ge*sha")
- User wants a range (e.g., "light to medium roast" → roast_level: "Light|Medium-Light|Medium")
- User excludes characteristics (e.g., "natural but not anaerobic" → process: "Natural&!Anaerobic")
DO NOT add wildcards when the canonical name from the context list matches directly.

PARAMETER GUIDELINES:

1. DUAL SEARCH:
   - `search_text`: For general terms (bean names, descriptions) — avoid if more specific fields apply.
   - `tasting_notes_search`: For flavor/taste searches using wildcard syntax.
   - Both can be used simultaneously.
   - "pina colada flavor" → tasting_notes_search: "pineapple&coconut"
   - "chocolate but not bitter" → tasting_notes_search: "chocolate&!bitter"

2. VARIETIES: Match from available varietals list. Use canonical names directly.
   - "pink bourbon" → variety: "Pink Bourbon" (exact canonical, no wildcard)
   - "geisha or gesha" → variety: "Ge*sha" (spelling variation)
   - NOT: variety: "Panama Geisha" — use origin: ["PA"] + variety: "Ge*sha"

3. ROASTERS: Match from available roasters list.
   - "cartwheel coffee" → roaster: ["Cartwheel Coffee"]

4. ROASTER LOCATIONS: Two-letter codes from available locations list.
   - "uk roasters" → roaster_location: ["GB"]
   - "european roasters" → roaster_location: ["XE"]
   - "scandinavian roasters" → roaster_location: ["SE"]

5. PROCESSES: Match from available processes list.
   - "washed or honey" → process: "Washed|Honey"
   - "natural but not anaerobic" → process: "Natural&!Anaerobic"

6. ROAST LEVELS: Light, Medium-Light, Medium, Medium-Dark, Dark, Extra-Light
   - "light to medium" → roast_level: "Light|Medium-Light|Medium"

7. ORIGIN COUNTRIES: Two-letter codes.
   - "colombian coffee" → origin: ["CO"]
   - "kenyan or rwandan" → origin: ["KE", "RW"]

8. REGIONS, PRODUCERS, FARMS: Sub-national areas, producer/farm names.
   - "Huila region" → region: "Huila"
   - "any Finca farm" → farm: "Finca*"

9. PRICE: "under £20" → max_price: 20.0

10. ELEVATION: "above 1800m" → min_elevation: 1800; "high altitude" → min_elevation: 1500

11. BOOLEANS: is_single_origin, in_stock_only, is_decaf

12. SORTING: Use `sort_by` and `sort_order` to control result ordering.
    - Valid `sort_by` fields: "date_added" (default), "price", "price_large", "name",
      "cupping_score", "relevance"
    - Valid `sort_order` values: "asc" (ascending), "desc" (descending)
    - "cheapest first" → sort_by: "price", sort_order: "asc"
    - "best rated first" → sort_by: "cupping_score", sort_order: "desc"
    - "newest first" → sort_by: "date_added", sort_order: "desc" (default)
    - "bulk cheapest first" → sort_by: "price_large", sort_order: "asc"
    - "largest bags first" → sort_by: "price_large", sort_order: "desc"
      (shows highest bulk prices, implying larger sizes)

13. LARGE BAG / BULK OPTIONS: Use `min_large_weight` to filter coffees that have a large bag option available.
    - "1kg bags" or "1kg+" → min_large_weight: 1000
    - "large bags" or "bulk" → min_large_weight: 500 (500g+)
    - "2kg" or "2kg+" → min_large_weight: 2000
    - Combine with sorting: "cheapest 1kg bags" → min_large_weight: 1000, sort_by: "price_large", sort_order: "asc"
    - "best value bulk" → min_large_weight: 1000, sort_by: "price_large", sort_order: "asc"

GENERAL RULES:
- Be conservative — only set parameters you're confident about.
- Prefer specific fields over search_text.
- Set confidence based on query clarity.
- Provide clear reasoning for your parameter choices.
- If query is ambiguous, prefer broader searches.
"""
        )

    def _get_image_analysis_prompt(self) -> str:
        """Get specialized prompt for image-based coffee search."""
        return """
You are an expert coffee search assistant specialized in analyzing coffee packaging images.

When provided with an image of coffee packaging, extract the following information:

1. **ROASTER NAME**: Look for brand/roaster logo or text
2. **COFFEE NAME**: The specific coffee blend or single origin name
3. **ORIGIN**: Country or region of origin (look for flags, maps, or country names)
4. **PROCESSING METHOD**: Natural, Washed, Honey, Anaerobic, etc.
5. **TASTING NOTES**: Flavor descriptions, often listed as bullet points or icons
6. **VARIETY/CULTIVAR**: Bourbon, Geisha, Typica, etc.
7. **ALTITUDE/ELEVATION**: Often shown as "MASL" or meters
8. **PRODUCER/FARM**: Farm or cooperative name

VISUAL CUES TO LOOK FOR:
- Text in different languages (origin indicator)
- Icons representing flavors (fruit, chocolate, nuts, etc.)
- QR codes or batch numbers (ignore these)

IMPORTANT:
- Extract ONLY information visible in the image
- If text is partially obscured or unclear, make reasonable inferences
- Prioritize clearly visible text over assumptions
- For tasting notes, convert visual representations to text (e.g., cherry icon = "cherry")
- If multiple languages are present, prioritize English
- Be conservative - only extract what you can clearly see or reasonably infer

After analyzing the image, generate search parameters that would find this coffee or similar coffees.
"""

    async def get_search_context(self) -> SearchContext:
        """Get current database context for search parameters."""
        try:
            # Get available tasting notes
            tasting_notes_query = """
                SELECT DISTINCT unnest(tasting_notes) as note
                FROM coffee_beans
                WHERE tasting_notes IS NOT NULL AND array_length(tasting_notes) > 0
                ORDER BY note
            """
            tasting_notes_result = self.conn.execute(tasting_notes_query).fetchall()
            tasting_notes = [row[0] for row in tasting_notes_result if row[0]]

            # Get available varietals (canonical names from the mapping table)
            varietals_query = """
                SELECT DISTINCT c
                FROM origins, UNNEST(variety_canonical) AS t(c)
                WHERE c IS NOT NULL AND c != ''
                ORDER BY c
            """
            varietals_result = self.conn.execute(varietals_query).fetchall()
            varietals = [row[0] for row in varietals_result if row[0]]

            # Get available roasters
            roasters_query = """
                SELECT DISTINCT roaster
                FROM coffee_beans
                WHERE roaster IS NOT NULL AND roaster != ''
                ORDER BY roaster
            """
            roasters_result = self.conn.execute(roasters_query).fetchall()
            roasters = [row[0] for row in roasters_result if row[0]]

            # Get available processes
            processes_query = """
                SELECT DISTINCT process_common_name
                FROM origins
                WHERE process_common_name IS NOT NULL AND process_common_name != ''
                ORDER BY process_common_name
            """
            processes_result = self.conn.execute(processes_query).fetchall()
            processes = [row[0] for row in processes_result if row[0]]

            # Get available roast levels
            roast_levels_query = """
                SELECT DISTINCT roast_level
                FROM coffee_beans
                WHERE roast_level IS NOT NULL AND roast_level != ''
                ORDER BY roast_level
            """
            roast_levels_result = self.conn.execute(roast_levels_query).fetchall()
            roast_levels = [row[0] for row in roast_levels_result if row[0]]

            # Get available countries with both codes and names
            countries_query = """
                SELECT DISTINCT
                    o.country as country_code,
                    cc.name as country_name
                FROM origins o
                LEFT JOIN country_codes cc ON o.country = cc.alpha_2
                WHERE o.country IS NOT NULL AND o.country != ''
                ORDER BY cc.name, o.country
            """
            countries_result = self.conn.execute(countries_query).fetchall()

            # Create list with both codes and names for AI context
            countries = []
            for row in countries_result:
                country_code, country_name = row
                if country_name:
                    countries.append(Country(country_full_name=country_name, country_code=country_code))
                else:
                    countries.append(Country(country_full_name=country_code, country_code=country_code))

            # Get available roaster location codes
            roaster_locations_query = """
                SELECT rlc.code, rlc.location, rlc.region
                FROM roaster_location_codes rlc
                ORDER BY rlc.location
            """
            roaster_locations_result = self.conn.execute(roaster_locations_query).fetchall()
            roaster_locations = []
            for row in roaster_locations_result:
                code, location, region = row
                roaster_locations.append(f"{code} ({location})")  # Display code with description

            # Get available farms, producers, and regions
            farms_query = """
                SELECT DISTINCT farm FROM origins
                WHERE farm IS NOT NULL AND farm != ''
                ORDER BY farm
            """
            farms = [r[0] for r in self.conn.execute(farms_query).fetchall() if r[0]]

            producers_query = """
                SELECT DISTINCT producer FROM origins
                WHERE producer IS NOT NULL AND producer != ''
                ORDER BY producer
            """
            producers = [r[0] for r in self.conn.execute(producers_query).fetchall() if r[0]]

            regions_query = """
                SELECT DISTINCT region FROM origins
                WHERE region IS NOT NULL AND region != ''
                ORDER BY region
            """
            regions = [r[0] for r in self.conn.execute(regions_query).fetchall() if r[0]]

            return SearchContext(
                available_tasting_notes=tasting_notes,
                available_varietals=varietals,
                available_roasters=roasters,
                available_processes=processes,
                available_roast_levels=roast_levels,
                available_countries=countries,
                available_roaster_locations=roaster_locations,
                available_farms=farms,
                available_producers=producers,
                available_regions=regions,
            )

        except Exception as e:
            logger.error(f"Error getting search context: {e}")
            # Return empty context if database query fails
            return SearchContext(
                available_tasting_notes=[],
                available_varietals=[],
                available_roasters=[],
                available_processes=[],
                available_roast_levels=[],
                available_countries=[],
                available_roaster_locations=[],
            )

    # Common words that are too generic to be useful for context filtering.
    _STOPWORDS = frozenset(
        {
            "coffee",
            "beans",
            "bean",
            "with",
            "from",
            "that",
            "this",
            "like",
            "notes",
            "flavor",
            "flavors",
            "taste",
            "tasting",
            "find",
            "show",
            "any",
            "some",
            "for",
            "the",
            "and",
            "but",
            "not",
            "or",
            "want",
            "looking",
            "need",
            "please",
            "help",
            "me",
            "you",
            "are",
            "was",
        }
    )

    def _generate_query_ngrams(self, query: str) -> list[str]:
        """Generate n-grams from a query string for context filtering.

        Produces single words (>= 4 chars, non-stopword) and multi-word
        phrases. Longer n-grams are listed first so they rank higher when
        sorting context matches.
        """
        words = re.findall(r"[a-zà-ÿ]+", query.lower())
        # Single words: filter stopwords and short tokens
        single_grams = [w for w in words if len(w) >= 4 and w not in self._STOPWORDS]
        ngrams: list[str] = []
        # Multi-word n-grams first (longer = more specific)
        for n in range(min(len(words), 4), 1, -1):
            for i in range(len(words) - n + 1):
                ngrams.append(" ".join(words[i : i + n]))
        # Single words last
        ngrams.extend(single_grams)
        return ngrams

    def _filter_context_by_query(
        self, query: str, context: SearchContext, limit_per_list: int = 20
    ) -> dict[str, list[str]]:
        """Filter context lists to only items relevant to the query keywords.

        Uses n-gram substring matching (case-insensitive) to find relevant
        items in large lists. Small lists (roast levels, countries, roaster
        locations) are always returned in full since they're needed for
        disambiguation and are cheap to include.
        """
        ngrams = self._generate_query_ngrams(query)

        def filter_list(items: list[str]) -> list[str]:
            if not items or not ngrams:
                return []
            matches: list[tuple[int, str]] = []
            for item in items:
                item_lower = item.lower()
                best_len = 0
                for ngram in ngrams:
                    if ngram in item_lower:
                        best_len = max(best_len, len(ngram))
                if best_len > 0:
                    matches.append((best_len, item))
            matches.sort(key=lambda x: (-x[0], x[1]))
            return [item for _, item in matches[:limit_per_list]]

        return {
            "tasting_notes": filter_list(context.available_tasting_notes),
            "varietals": filter_list(context.available_varietals),
            "roasters": filter_list(context.available_roasters),
            "processes": filter_list(context.available_processes),
            "farms": filter_list(context.available_farms),
            "producers": filter_list(context.available_producers),
            "regions": filter_list(context.available_regions),
            # Small lists: always include in full
            "roast_levels": context.available_roast_levels,
            "countries": [f"{c.country_full_name} ({c.country_code})" for c in context.available_countries],
            "roaster_locations": context.available_roaster_locations,
        }

    def extract_image_data(self, base64_url: str) -> tuple[bytes, str]:
        """Extract binary data and MIME type from base64 data URL.

        Args:
            base64_url: Data URL like "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."

        Returns:
            Tuple of (binary_data, mime_type)
        """
        import base64

        # Parse the data URL
        header, b64data = base64_url.split(",", 1)

        # MIME type (before any ';' like ';base64')
        mime_type = header[5:].split(";")[0] or "application/octet-stream"

        # Clean and normalize base64
        b64data = b64data.strip().replace("\n", "").replace("\r", "")
        b64data = b64data.replace("-", "+").replace("_", "/")  # URL-safe → standard
        b64data += "=" * (-len(b64data) % 4)  # add missing padding

        binary_content = base64.b64decode(b64data)

        return binary_content, mime_type

    async def translate_query(self, query: str | None = None, image_data: bytes | None = None) -> AISearchResponse:
        """Translate a natural language query to structured search parameters.

        Args:
            query: Natural language search query or base64 encoded image data

        Returns:
            AISearchResponse with generated parameters or error
        """
        start_time = time.time()
        if query is None and image_data is not None:
            is_image_based = True
        else:
            is_image_based = False

        # Compute base query hash upfront
        if query:
            _ = self.cache._hash_text_query(query)
        else:
            _ = self.cache._hash_image_query(image_data)  # type: ignore

        # Check cache first
        negative_feedback_threshold = int(os.getenv("AI_NEGATIVE_FEEDBACK_THRESHOLD", "3"))
        cache_hit = self.cache.get_cached_query(query=query, image_data=image_data)
        negatively_rated_bypass = False
        if cache_hit:
            if self.cache.is_negatively_rated(cache_hit.entry_id, negative_feedback_threshold):
                logger.warning(
                    f"Cache entry {cache_hit.entry_id[:8]}... has too many downvotes "
                    f"(threshold={negative_feedback_threshold}). "
                    "Bypassing cache and saving result as a new version."
                )
                negatively_rated_bypass = True
            else:
                search_url = self._generate_search_url(cache_hit.search_params)
                processing_time = (time.time() - start_time) * 1000
                logger.info(f"Returning cached AI search result (processing time: {processing_time:.2f}ms)")
                return AISearchResponse(
                    success=True,
                    search_params=cache_hit.search_params,
                    search_url=search_url,
                    error_message=None,
                    processing_time_ms=processing_time,
                    query_hash=cache_hit.entry_id,
                )

        # Cache miss — check global rate limit before calling the AI
        rate_limit_max_requests = int(os.getenv("AI_RATE_LIMIT_MAX_REQUESTS", "10"))
        rate_limit_window_hours = int(os.getenv("AI_RATE_LIMIT_WINDOW_HOURS", "24"))
        rate_limit = self.cache.check_rate_limit(
            window_hours=rate_limit_window_hours, max_requests=rate_limit_max_requests
        )
        if not rate_limit["allowed"]:
            processing_time = (time.time() - start_time) * 1000
            reset_at = rate_limit.get("reset_at")
            reset_at_str = reset_at.isoformat() if reset_at else None
            logger.warning(
                f"Rate limit exceeded: {rate_limit['current_count']}/{rate_limit['limit']} "
                f"fresh AI requests in {rate_limit['window_hours']}h window"
            )
            return AISearchResponse(
                success=False,
                search_params=None,
                search_url=None,
                error_message="AI search rate limit exceeded. Please try again later.",
                processing_time_ms=processing_time,
                rate_limited=True,
                rate_limit_remaining=0,
                rate_limit_reset_at=reset_at_str,
                rate_limit_limit=rate_limit["limit"],
            )

        try:
            if is_image_based:
                logger.debug("Translating AI image search query")
            else:
                logger.debug(f"Translating AI search query: {query}")

            # Get current database context
            context = await self.get_search_context()

            example_queries = """
EXAMPLES:

Query: "Find me coffee beans that taste like a pina colada"
→ tasting_notes_search: "pineapple&coconut", use_tasting_notes_only: true, confidence: 0.9

Query: "light roast pink bourbon"
→ roast_level: "Light", variety: ["Pink Bourbon"], use_tasting_notes_only: false, confidence: 0.95

Query: "fruity Ethiopian coffee under £25"
→ tasting_notes_search: "fruit*|berry*", origin: ["ET"], max_price: 25.0, use_tasting_notes_only: true, confidence: 0.85

Query: "cartwheel natural process with chocolate notes"
→ roaster: ["Cartwheel Coffee"], process: "Natural",
   tasting_notes_search: "chocolate", use_tasting_notes_only: true, confidence: 0.7

Query: "chocolate coffee that's not bitter"
→ tasting_notes_search: "chocolate&!bitter", use_tasting_notes_only: true, confidence: 0.8

Query: "high altitude Colombian coffee with citrus flavors above 1800m"
→ search_text: "Colombian",
   tasting_notes_search: "citrus*|lemon*|orange*|tangerine*|lime*",
   origin: ["CO"], min_elevation: 1800, use_tasting_notes_only: false, confidence: 0.95

Query: "coffee from uk roasters"
→ roaster_location: ["GB"], use_tasting_notes_only: false, confidence: 0.9

Query: "light roast from european roasters with berry notes"
→ tasting_notes_search: "berry*", roast_level: "Light",
   roaster_location: ["XE"], use_tasting_notes_only: false, confidence: 0.85

Query: "Kenyan AA with wine-like acidity"
→ search_text: "AA", tasting_notes_search: "wine*|acidic*",
   origin: ["KE"], use_tasting_notes_only: false, confidence: 0.9

Query: "Colombian coffee from Huila or Nariño regions, natural or honey process"
→ origin: ["CO"], region: "Huila|Nariño", process: "Natural|Honey", use_tasting_notes_only: false, confidence: 0.95

Query: "any geisha variety with light to medium roast"
→ variety: "Ge*sha", roast_level: "Light|Medium-Light|Medium", use_tasting_notes_only: false, confidence: 0.9

Query: "Indonesian coffee that is not chocolatey"
→ origin: ["ID"], tasting_notes_search: "!chocolate&!cocoa", use_tasting_notes_only: true, confidence: 0.85

Query: "coffees from south america"
→ origin: ["CO", "PE", "PA", "GT", "CR", "NI", "SV", "HN",
   "DO", "BR", "EC", "BO", "AR", "CL", "UY", "PY", "VE", "GY", "SR"],
   use_tasting_notes_only: false, confidence: 0.9

Query: "coffees from asia"
→ origin: ["IN", "ID", "VN", "TH", "MY", "PH",
   "CN", "TW", "JP", "KR", "LK", "PG"],
   use_tasting_notes_only: false, confidence: 0.9

Query: "cheapest bulk options"
→ sort_by: "price_large", sort_order: "asc",
   min_large_weight: 1000, use_tasting_notes_only: false, confidence: 0.95

Query: "1kg bags sorted by price"
→ min_large_weight: 1000, sort_by: "price_large", sort_order: "asc",
   use_tasting_notes_only: false, confidence: 0.95

Query: "large bag options under £30"
→ min_large_weight: 500, max_price: 30.0,
   sort_by: "price_large", sort_order: "asc",
   use_tasting_notes_only: false, confidence: 0.9

Query: "best value large bags"
→ min_large_weight: 1000, sort_by: "price_large", sort_order: "asc", use_tasting_notes_only: false, confidence: 0.9

NEGATIVE EXAMPLES (what NOT to do):

Query: "panama geisha"
✓ origin: ["PA"], variety: "Ge*sha"
✗ variety: "Panama Geisha" — Panama is a country, not part of the variety name

Query: "sudan rume"
✓ variety: "Sudan Rume" (canonical name — backend handles "Sudanrume" and "Sudán Rumé" automatically)
✗ variety: "Sudan Rume*" — suffix wildcard won't match compound words like "Sudanrume"
✗ variety: "Sudanrume|Sudán Rumé" — unnecessary; canonical matching handles accent variants

Query: "killbean panama geisha"
✓ roaster: ["KillBean"], origin: ["PA"], variety: "Ge*sha"
✗ region: "Panama" — Panama is a country, use origin: ["PA"]
"""

            # Filter context to only items relevant to the query keywords
            if not is_image_based and query:
                filtered = self._filter_context_by_query(query, context)
            else:
                # For image-based search: send only small lists (no query to filter by)
                filtered = {
                    "tasting_notes": [],
                    "varietals": [],
                    "roasters": [],
                    "processes": [],
                    "farms": [],
                    "producers": [],
                    "regions": [],
                    "roast_levels": context.available_roast_levels,
                    "countries": [f"{c.country_full_name} ({c.country_code})" for c in context.available_countries],
                    "roaster_locations": context.available_roaster_locations,
                }

            # Build context sections — only include non-empty lists
            context_sections = []

            for label, key in [
                ("MATCHED TASTING NOTES", "tasting_notes"),
                ("MATCHED VARIETALS (canonical names — use these directly)", "varietals"),
                ("MATCHED ROASTERS", "roasters"),
                ("MATCHED PROCESSES", "processes"),
                ("MATCHED FARMS", "farms"),
                ("MATCHED PRODUCERS", "producers"),
                ("MATCHED REGIONS", "regions"),
                ("ROAST LEVELS", "roast_levels"),
                ("COFFEE ORIGIN COUNTRIES", "countries"),
                ("ROASTER LOCATIONS", "roaster_locations"),
            ]:
                items = filtered[key]
                if items:
                    context_sections.append(f"{label}:\n{', '.join(items)}")

            context_body = (
                "\n\n".join(context_sections)
                if context_sections
                else (
                    "No matching database entries found for query keywords. "
                    "Use your coffee knowledge to generate appropriate search parameters."
                )
            )

            # Prepare the context message for the AI
            context_message = f"""
{example_queries if not is_image_based else ""}
{f"User Query: {query}" if not is_image_based else "User Query: An image of coffee packaging"}

{context_body}

Please analyze the user query and generate appropriate search parameters.
"""

            content = [
                context_message,
            ]
            if is_image_based:
                content.append(BinaryContent(data=image_data, media_type="image/png"))
            # Create the PydanticAI agent
            self.agent = Agent(
                "gemini-2.5-flash-lite",
                output_type=SearchParameters if not is_image_based else BasicSearchParameters,
                system_prompt=self._get_system_prompt(is_image_based),
                model_settings=GeminiModelSettings(),
            )

            # Run the AI agent
            result = await self.agent.run(content)
            search_params = result.output

            if is_image_based:
                # Convert basic search parameters to search parameters so
                # that we can use the same code for both text and image based searches
                search_params = SearchParameters(**search_params.model_dump())

            # Fix country codes if they are not two letter codes
            if search_params.origin:
                for i, country in enumerate(search_params.origin or []):
                    if len(country) != 2:
                        search_params.origin[i] = dict(
                            [list(country.model_dump().values()) for country in context.available_countries]
                        ).get(country, country)
                    # check that the code exists in the available countries
                    if search_params.origin[i] not in [c.country_code for c in context.available_countries]:
                        search_params.origin[i] = None
                # Remove any None values
                search_params.origin = [c for c in search_params.origin if c]
                if not search_params.origin:
                    search_params.origin = None

            # Generate search URL
            search_url = self._generate_search_url(search_params)

            processing_time = (time.time() - start_time) * 1000

            logger.info(f"AI search translation successful: {query} → confidence: {search_params.confidence}")

            # Cache the result — create a new version when bypassing a negatively-rated entry
            # so the old entry (and its vote history) is preserved intact.
            new_entry_id = self.cache.cache_query(
                search_params=search_params,
                query=query,
                image_data=image_data,
                force_new_version=negatively_rated_bypass,
            )

            # Log this as a fresh (non-cached) request for rate limiting
            self.cache.log_fresh_request(query_type="image" if is_image_based else "text")

            return AISearchResponse(
                success=True,
                search_params=search_params,
                search_url=search_url,
                error_message=None,
                processing_time_ms=processing_time,
                query_hash=new_entry_id,
            )

        except Exception as e:
            import traceback

            processing_time = (time.time() - start_time) * 1000
            error_msg = f"AI search translation failed: {str(e)}"
            traceback.print_exc()
            logger.error(error_msg)

            return AISearchResponse(
                success=False,
                search_params=None,
                search_url=None,
                error_message=error_msg,
                processing_time_ms=processing_time,
            )

    def _generate_search_url(self, params: SearchParameters) -> str:
        """Generate a search URL from the structured parameters."""
        url_params = {}

        # Add search text and tasting notes search (can be used simultaneously)
        if params.search_text:
            url_params["q"] = params.search_text

        if params.tasting_notes_search:
            url_params["tasting_notes_query"] = params.tasting_notes_search

        # Add filters
        if params.roaster:
            for roaster in params.roaster:
                if isinstance(url_params.get("roaster"), list):
                    url_params.setdefault("roaster", []).append(roaster)
                else:
                    url_params.update({"roaster": roaster})

        if params.roaster_location:
            for location in params.roaster_location:
                if "roaster_location" not in url_params:
                    url_params["roaster_location"] = []
                url_params["roaster_location"].append(location)

        if params.variety:
            url_params["variety"] = params.variety

        if params.process:
            url_params["process"] = params.process

        if params.origin:
            for origin in params.origin:
                if "origin" not in url_params:
                    url_params["origin"] = []
                url_params["origin"].append(origin)

        # Add wildcard-enabled filters
        if params.region:
            url_params["region"] = params.region
        if params.producer:
            url_params["producer"] = params.producer
        if params.farm:
            url_params["farm"] = params.farm

        # Add single-value filters
        if params.roast_level:
            url_params["roast_level"] = params.roast_level
        if params.roast_profile:
            url_params["roast_profile"] = params.roast_profile

        # Add range parameters
        if params.min_price is not None:
            url_params["min_price"] = str(params.min_price)
        if params.max_price is not None:
            url_params["max_price"] = str(params.max_price)
        if params.min_weight is not None:
            url_params["min_weight"] = str(params.min_weight)
        if params.min_large_weight is not None:
            url_params["min_large_weight"] = str(params.min_large_weight)
        if params.max_weight is not None:
            url_params["max_weight"] = str(params.max_weight)
        if params.min_elevation is not None:
            url_params["min_elevation"] = str(params.min_elevation)
        if params.max_elevation is not None:
            url_params["max_elevation"] = str(params.max_elevation)

        # Add boolean parameters
        if params.in_stock_only:
            url_params["in_stock_only"] = "true"
        if params.is_decaf is not None:
            url_params["is_decaf"] = "true" if params.is_decaf else "false"
        if params.is_single_origin is not None:
            url_params["is_single_origin"] = "true" if params.is_single_origin else "false"

        # Add sorting
        if params.sort_by != "name":
            url_params["sort_by"] = params.sort_by
        if params.sort_order != "asc":
            url_params["sort_order"] = params.sort_order

        # Handle multiple values properly
        query_parts = []
        for key, value in url_params.items():
            if isinstance(value, list):
                for v in value:
                    query_parts.append(f"{key}={urlencode({'': v})[1:]}")
            else:
                query_parts.append(f"{key}={urlencode({'': value})[1:]}")

        return f"/search?{'&'.join(query_parts)}" if query_parts else "/search"
