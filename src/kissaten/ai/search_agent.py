"""AI-powered search query translation using Gemini and PydanticAI."""

import logging
import os
import time
from urllib.parse import urlencode

import duckdb
import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModelSettings

from ..schemas.ai_search import AISearchResponse, Country, SearchContext, SearchParameters

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()


class AISearchAgent:
    """AI agent for translating natural language queries to structured search parameters."""

    def __init__(self, database_connection: duckdb.DuckDBPyConnection, api_key: str | None = None):
        """Initialize the AI search agent.

        Args:
            database_connection: DuckDB connection for querying available data
            api_key: Google API key. If None, will try to get from environment.
        """
        self.conn = database_connection
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )

        # Create the PydanticAI agent
        self.agent = Agent(
            "gemini-2.5-flash-lite",
            output_type=SearchParameters,
            system_prompt=self._get_system_prompt(),
            model_settings=GeminiModelSettings(),
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for search query translation."""
        return """
You are an expert coffee search assistant. Your task is to translate natural language queries
about coffee beans into structured search parameters.

You will receive:
1. A natural language query from a user
2. Context about available data in the coffee database (tasting notes, varietals, roasters, etc.)

Your job is to analyze the query and generate appropriate search parameters that will help find relevant coffee beans.

SEARCH PARAMETER GUIDELINES:

1. DUAL SEARCH CAPABILITY:
   - You can use BOTH `search_text` AND `tasting_notes_search` simultaneously
   - `search_text`: For general searches (bean names, descriptions)
   - `tasting_notes_search`: For specific flavor/taste searches with boolean operators

   TASTING NOTES SEARCH:
   - Use `tasting_notes_search` for specific flavors, tastes, or tasting notes
   - Supports advanced wildcard syntax with boolean operators
   - Examples:
     * "Ethiopian coffee with chocolate notes" → search_text: "Ethiopian", tasting_notes_search: "chocolate"
     * "pina colada flavor" → tasting_notes_search: "pineapple&coconut"
     * "chocolate but not bitter" → tasting_notes_search: "chocolate&!bitter"
     * "fruity Brazilian coffee" → search_text: "Brazilian", tasting_notes_search: "fruit*|berry*|cherry*"

2. WILDCARD SEARCH SYNTAX:
   The following fields support advanced wildcard and boolean search syntax:
   - `tasting_notes_search` (already explained above)
   - `region` - coffee growing regions
   - `producer` - coffee producer names
   - `farm` - farm names
   - `roast_level` - roasting levels
   - `roast_profile` - roasting profiles (Espresso/Filter/Omni)
   - `process` - processing methods
   - `variety` - coffee varieties/varietals

   WILDCARD OPERATORS:
   - `*` - matches multiple characters (e.g., "Huar*" matches "Huarango", "Huaraz")
   - `?` - matches single character (e.g., "Ge?sha" matches "Geisha", "Gesha")
   - `|` - OR operator (e.g., "Light|Medium" matches either "Light" or "Medium")
   - `&` - AND operator (e.g., "Natural&Honey" matches items with both "Natural" and "Honey")
   - `!` - NOT operator (e.g., "Washed&!Decaf" matches "Washed" but excludes "Decaf")
   - `()` - grouping (e.g., "Colombian&(Huila|Nariño)" matches Colombian from either Huila or Nariño)

   WILDCARD EXAMPLES:
   - Region: "Huila|Nariño" → region: "Huila|Nariño" (Colombian regions)
   - Producer: "Finca*" → producer: "Finca*" (farms starting with "Finca")
   - Process: "Natural|Honey" → process: "Natural|Honey" (either natural or honey process)
   - Variety: "Bourbon*" → variety: "Bourbon*" (any Bourbon variant)
   - Roast Level: "Light|Medium-Light" → roast_level: "Light|Medium-Light"
   - Farm: "*Vista" → farm: "*Vista" (farms ending with "Vista")

   USE WILDCARDS WHEN:
   - User mentions partial names or variations (e.g., "Geisha or Gesha" → variety: "Ge*sha")
   - User wants multiple similar options (e.g., "light to medium roast" → roast_level: "Light|Medium-Light|Medium")
   - User excludes certain characteristics (e.g., "natural process but not anaerobic" → process: "Natural&!Anaerobic")
   - User mentions regional variations (e.g., "Ethiopian regions" → region: "*" with origin: ["ET"])

3. VARIETALS/VARIETIES:
   - Match coffee variety names from available varietals
   - Now supports wildcard syntax (see section 2 above)
   - Common varieties: Bourbon, Typica, Geisha, Caturra, Catuai, SL28, SL34, etc.
   - Examples:
     * "pink bourbon" → variety: "Pink Bourbon"
     * "any bourbon variety" → variety: "Bourbon*"
     * "geisha or gesha" → variety: "Ge*sha"

4. ROASTERS:
   - Match roaster names from available roasters list
   - Examples: "cartwheel coffee" → roaster: ["Cartwheel Coffee"]

5. ROASTER LOCATIONS:
   - Use two-letter location codes from available roaster locations list
   - Handle regional groupings (XE for continental Europe, EU for European Union)
   - Examples:
     * "coffee from uk roasters" → roaster_location: ["GB"]
     * "italian roasters" → roaster_location: ["IT"]
     * "european coffee roasters" → roaster_location: ["XE"]
     * "spanish coffee" → roaster_location: ["ES"]
     * "scandinavian roasters" → roaster_location: ["SE"]

6. PROCESSING METHODS:
   - Common processes: Natural, Washed, Honey, Anaerobic, etc.
   - Now supports wildcard syntax (see section 2 above)
   - Examples:
     * "natural process" → process: "Natural"
     * "washed or honey" → process: "Washed|Honey"
     * "natural but not anaerobic" → process: "Natural&!Anaerobic"

7. ROAST LEVELS:
   - Valid levels: Light, Medium-Light, Medium, Medium-Dark, Dark
   - Now supports wildcard syntax (see section 2 above)
   - Examples:
     * "light roast" → roast_level: "Light"
     * "light to medium" → roast_level: "Light|Medium-Light|Medium"
     * "any dark roast" → roast_level: "*Dark"

8. COFFEE ORIGIN COUNTRIES:
   - Use country two letter codes, not full names for better matching
   - Examples: "colombian coffee" → origin: ["CO"]
   - "ethiopian beans" → origin: ["ET"]
   - "kenyan or rwandan" → origin: ["KE", "RW"]

9. REGIONS, PRODUCERS, AND FARMS:
   - Now support wildcard syntax (see section 2 above)
   - Examples:
     * "Huila region" → region: "Huila"
     * "Huila or Nariño" → region: "Huila|Nariño"
     * "any Finca farm" → farm: "Finca*"
     * "producers ending in family" → producer: "*Family"

10. PRICE RANGES:
   - Extract price information if mentioned
   - Examples: "under £20" → max_price: 20.0

11. ELEVATION RANGES:
   - Extract elevation information if mentioned (in meters above sea level)
   - Examples: "high altitude coffee" → min_elevation: 1500
   - "coffee grown above 2000m" → min_elevation: 2000
   - "low elevation beans" → max_elevation: 1200

12. GENERAL GUIDELINES:
   - Be conservative - only set parameters you're confident about
   - Use fuzzy matching for names (case-insensitive, partial matches)
   - Set confidence based on how clear the query is
   - Provide reasoning for your interpretation
   - If query is ambiguous, prefer broader searches
   - Prefer using both search_text and tasting_notes_search when the query contains both general terms and flavor descriptions
   - Do not add unnecessary search_text if the query is already specific enough
   - Use wildcard syntax when users mention variations, alternatives, or partial matches

13. BOOLEAN COMBINATIONS:
   - Single origin vs blends: is_single_origin
   - In stock only: in_stock_only
   - Decaf: is_decaf

EXAMPLES:

Query: "Find me coffee beans that taste like a pina colada"
→ tasting_notes_search: "pineapple&coconut", use_tasting_notes_only: true, confidence: 0.9

Query: "light roast pink bourbon"
→ roast_level: "Light", variety: ["Pink Bourbon"], use_tasting_notes_only: false, confidence: 0.95

Query: "fruity Ethiopian coffee under £25"
→ tasting_notes_search: "fruit*|berry*", origin: ["ET"], max_price: 25.0, use_tasting_notes_only: true, confidence: 0.85

Query: "cartwheel natural process with chocolate notes"
→ roaster: "Cartwheel Coffee", process: ["Natural"], tasting_notes_search: "chocolate", use_tasting_notes_only: true, confidence: 0.7

Query: "chocolate coffee that's not bitter"
→ tasting_notes_search: "chocolate&!bitter", use_tasting_notes_only: true, confidence: 0.8

Query: "high altitude Colombian coffee with citrus flavors above 1800m"
→ search_text: "Colombian", tasting_notes_search: "citrus*|lemon*|orange*|tangerine*|lime*", origin: ["CO"], min_elevation: 1800, use_tasting_notes_only: false, confidence: 0.95

Query: "coffee from uk roasters"
→ roaster_location: ["GB"], use_tasting_notes_only: false, confidence: 0.9

Query: "light roast from european roasters with berry notes"
→ tasting_notes_search: "berry*", roast_level: "Light", roaster_location: ["XE"], use_tasting_notes_only: false, confidence: 0.85

Query: "Kenyan AA with wine-like acidity"
→ search_text: "AA", tasting_notes_search: "wine*|acidic*", origin: ["KE"], use_tasting_notes_only: false, confidence: 0.9

Query: "Colombian coffee from Huila or Nariño regions, natural or honey process"
→ origin: ["CO"], region: "Huila|Nariño", process: "Natural|Honey", use_tasting_notes_only: false, confidence: 0.95

Query: "any geisha variety with light to medium roast"
→ variety: "Ge*sha", roast_level: "Light|Medium-Light|Medium", use_tasting_notes_only: false, confidence: 0.9

Query: "farms starting with Finca, washed process but not fully washed"
→ farm: "Finca*", process: "Washed&!Fully", use_tasting_notes_only: false, confidence: 0.8

Query: "Indonesian coffee that is not chocolatey"
→ origin: ["ID"], tasting_notes_search: "!chocolate&!cocoa", use_tasting_notes_only: true, confidence: 0.85

Query: "washed kenyan"
→ origin: ["KE"], process: "Washed", use_tasting_notes_only: false, confidence: 0.9

Query: "coffees from south america"
→ origin: ["CO", "PE", "PA", "GT", "CR", "NI", "SV", "HN", "DO", "BR", "EC", "BO", "AR", "CL", "UY", "PY", "VE", "GY", "SR"], use_tasting_notes_only: false, confidence: 0.9

Query: "coffees from asia"
→ origin: ["IN", "ID", "VN", "TH", "MY", "PH", "CN", "TW", "JP", "KR", "LK", "PG"], use_tasting_notes_only: false, confidence: 0.9

Always provide a clear reasoning for your parameter choices.

Try to avoid using search_text if you can use the more specific fields.
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

            # Get available varietals
            varietals_query = """
                SELECT DISTINCT variety
                FROM origins
                WHERE variety IS NOT NULL AND variety != ''
                ORDER BY variety
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
                SELECT DISTINCT process
                FROM origins
                WHERE process IS NOT NULL AND process != ''
                ORDER BY process
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

            return SearchContext(
                available_tasting_notes=tasting_notes,
                available_varietals=varietals,
                available_roasters=roasters,
                available_processes=processes,
                available_roast_levels=roast_levels,
                available_countries=countries,
                available_roaster_locations=roaster_locations,
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

    async def translate_query(self, query: str) -> AISearchResponse:
        """Translate a natural language query to structured search parameters.

        Args:
            query: Natural language search query

        Returns:
            AISearchResponse with generated parameters or error
        """
        start_time = time.time()

        try:
            logger.debug(f"Translating AI search query: {query}")

            # Get current database context
            context = await self.get_search_context()

            # Prepare the context message for the AI
            context_message = f"""
User Query: "{query}"

Available Database Context:

TASTING NOTES:
{", ".join(context.available_tasting_notes)}

VARIETALS:
{", ".join(context.available_varietals)}

ROASTERS:
{", ".join(context.available_roasters)}

ROASTER LOCATIONS:
{", ".join(context.available_roaster_locations)}

PROCESSES:
{", ".join(context.available_processes)}

ROAST LEVELS:
{", ".join(context.available_roast_levels)}

COFFEE ORIGIN COUNTRIES:
[{", ".join([country.model_dump_json() for country in context.available_countries])}]

Please analyze the user query and generate appropriate search parameters.

Reminder of the user query: "{query}"
Reminder of the original prompt: {self._get_system_prompt()}
"""

            # Run the AI agent
            result = await self.agent.run(context_message)
            search_params = result.output

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

            return AISearchResponse(
                success=True,
                search_params=search_params,
                search_url=search_url,
                error_message=None,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"AI search translation failed: {str(e)}"
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
