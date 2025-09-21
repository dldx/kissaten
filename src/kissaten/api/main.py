"""
FastAPI application for Kissaten coffee bean search API.
"""

import logging
import re
from pathlib import Path
from typing import Literal

import uvicorn
from aiocache import cached
from aiocache.backends.memory import SimpleMemoryCache
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from kissaten.api.ai_search import create_ai_search_router
from kissaten.api.db import conn
from kissaten.api.fx import convert_price, create_fx_router, update_currency_rates
from kissaten.schemas import APIResponse, CoffeeBeanDiffUpdate
from kissaten.schemas.api_models import (
    APIBean,
    APICoffeeBean,
    APIRecommendation,
    APISearchResult,
)
from kissaten.scrapers import get_registry

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kissaten Coffee Bean API",
    description="Search and discover coffee beans from roasters worldwide",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class CacheControlledStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=360000"
        return response

# Serve static images
app.mount(
    "/data/roasters",
    CacheControlledStaticFiles(directory=Path(__file__).parent.parent.parent.parent / "data" / "roasters"),
    name="roasters-data",
)


def parse_boolean_search_query_for_field(query: str, field_expression: str) -> tuple[str, list[str]]:
    """
    Parse a boolean search query with wildcards and convert it to SQL for any field.

    Supports:
    - Wildcards: * (multiple chars), ? (single char)
    - OR operator: |
    - AND operator: &
    - NOT operator: ! or NOT
    - Parentheses for grouping: ()
    - Exact matches: "quoted text" (case-insensitive exact match, no wildcards)

    Args:
        query: The search query string
        field_expression: The SQL field expression to search in (e.g., "cb.roast_level", "o.region")

    Examples:
    - "choc*|floral" -> "(field_expression ILIKE ? OR field_expression ILIKE ?)"
    - "berry&(lemon|lime)" -> "(field_expression ILIKE ? AND (field_expression ILIKE ? OR field_expression ILIKE ?))"
    - "chocolate&!decaf" -> "(field_expression ILIKE ? AND NOT field_expression ILIKE ?)"
    - "fruit*&!(bitter|sour)" -> "(field_expression ILIKE ? AND NOT (field_expression ILIKE ? OR field_expression ILIKE ?))"
    - '"Peach"&fruity' -> "(field_expression ILIKE ? AND field_expression ILIKE ?)" (exact match for 'Peach')
    - '"passion fruit"&fruity' -> "(field_expression ILIKE ? AND field_expression ILIKE ?)"

    Returns:
        tuple: (sql_condition, parameters)
    """

    if not query.strip():
        return "", []

    # If no boolean operators, handle as simple wildcard search
    if not re.search(r"[|&!()]|NOT\b", query, re.IGNORECASE):
        # Check if it's a quoted exact match
        if query.strip().startswith('"') and query.strip().endswith('"'):
            exact_term = query.strip()[1:-1]  # Remove quotes
            if "array_to_string" in field_expression:
                # Case-insensitive exact match for array fields
                return (
                    "EXISTS (SELECT 1 FROM unnest(cb.tasting_notes) AS t(note) WHERE lower(note) = lower(?))",
                    [exact_term],
                )
            else:
                return f"{field_expression} ILIKE ?", [exact_term]
        else:
            # Regular wildcard search
            search_pattern = query.replace("*", "%").replace("?", "_")
            if "*" not in query and "?" not in query:
                search_pattern = f"%{search_pattern}%"
            return f"{field_expression} ILIKE ?", [search_pattern]

    def tokenize(text: str) -> list[str]:
        """Tokenize the search query into terms and operators, handling quoted strings"""
        # Replace NOT with ! for easier parsing
        text = re.sub(r"\bNOT\b", "!", text, flags=re.IGNORECASE)

        tokens = []
        i = 0
        current_token = ""

        while i < len(text):
            char = text[i]

            if char == '"':
                # Handle quoted strings - find the closing quote
                i += 1  # Skip opening quote
                quoted_content = ""
                while i < len(text) and text[i] != '"':
                    quoted_content += text[i]
                    i += 1

                if i < len(text):  # Found closing quote
                    i += 1  # Skip closing quote

                # Add the quoted content as a single token with a special marker
                if quoted_content.strip():
                    tokens.append(f"EXACT:{quoted_content.strip()}")

            elif char in "|&!()":
                # Add any accumulated token
                if current_token.strip():
                    tokens.append(current_token.strip())
                    current_token = ""
                # Add the operator
                tokens.append(char)
                i += 1

            elif char.isspace():
                # Add any accumulated token
                if current_token.strip():
                    tokens.append(current_token.strip())
                    current_token = ""
                i += 1

            else:
                current_token += char
                i += 1

        # Add final token if any
        if current_token.strip():
            tokens.append(current_token.strip())

        return [token for token in tokens if token]

    def convert_wildcard_term(term: str) -> tuple[str, str]:
        """Convert a single term with wildcards to SQL pattern and condition type"""
        if term.startswith("EXACT:"):
            # Exact match - remove the EXACT: prefix and use = instead of ILIKE
            exact_term = term[6:]  # Remove 'EXACT:' prefix
            return exact_term, "="
        else:
            # Wildcard/fuzzy match
            pattern = term.replace("*", "%").replace("?", "_")
            if "*" not in term and "?" not in term:
                pattern = f"%{pattern}%"
            return pattern, "ILIKE"

    def parse_expression(tokens: list[str]) -> tuple[str, list[str]]:
        """Parse expression using a more robust approach with proper operator precedence"""

        def parse_or_expression(pos: int) -> tuple[str, list[str], int]:
            """Parse OR expression (lowest precedence)"""
            left_cond, left_params, pos = parse_and_expression(pos)

            while pos < len(tokens) and tokens[pos] == "|":
                pos += 1  # skip '|'
                right_cond, right_params, pos = parse_and_expression(pos)
                left_cond = f"({left_cond} OR {right_cond})"
                left_params.extend(right_params)

            return left_cond, left_params, pos

        def parse_and_expression(pos: int) -> tuple[str, list[str], int]:
            """Parse AND expression (higher precedence than OR)"""
            left_cond, left_params, pos = parse_not_expression(pos)

            while pos < len(tokens) and tokens[pos] == "&":
                pos += 1  # skip '&'
                right_cond, right_params, pos = parse_not_expression(pos)
                left_cond = f"({left_cond} AND {right_cond})"
                left_params.extend(right_params)

            return left_cond, left_params, pos

        def parse_not_expression(pos: int) -> tuple[str, list[str], int]:
            """Parse NOT expression (highest precedence)"""
            if pos < len(tokens) and tokens[pos] == "!":
                pos += 1  # skip '!'
                condition, params, pos = parse_primary(pos)
                return f"NOT {condition}", params, pos
            else:
                return parse_primary(pos)

        def parse_primary(pos: int) -> tuple[str, list[str], int]:
            """Parse primary expression (terms or parenthesized expressions)"""
            if pos >= len(tokens):
                return "", [], pos

            token = tokens[pos]

            if token == "(":
                # Parse sub-expression
                pos += 1  # skip '('
                condition, params, pos = parse_or_expression(pos)
                if pos < len(tokens) and tokens[pos] == ")":
                    pos += 1  # skip ')'
                return condition, params, pos
            else:
                # It's a search term or a sequence of terms.
                # Consume all consecutive tokens that are not operators or parentheses.
                term_parts = []
                while pos < len(tokens) and tokens[pos] not in "|&()":
                    term_parts.append(tokens[pos])
                    pos += 1

                if not term_parts:
                    return "", [], pos  # Should not happen if token list is not empty

                full_term = " ".join(term_parts)
                pattern, operator = convert_wildcard_term(full_term)

                if operator == "=":
                    # For exact matches, we still use ILIKE for case-insensitive comparison
                    # but match the full field content when contained in arrays
                    if "array_to_string" in field_expression:
                        # For array fields, check if the exact term exists in the array (case-insensitive)
                        condition = (
                            "EXISTS (SELECT 1 FROM unnest(cb.tasting_notes) AS t(note) WHERE lower(note) = lower(?))"
                        )
                    else:
                        # For string fields, use exact case-insensitive match
                        condition = f"{field_expression} ILIKE ?"
                else:
                    condition = f"{field_expression} ILIKE ?"
                return condition, [pattern], pos

        condition, params, _ = parse_or_expression(0)
        return condition, params

    try:
        tokens = tokenize(query)
        if not tokens:
            return "", []

        condition, params = parse_expression(tokens)
        return condition, params

    except Exception:
        # Fallback to simple search if parsing fails
        # Check if it's a quoted exact match
        if query.strip().startswith('"') and query.strip().endswith('"'):
            exact_term = query.strip()[1:-1]  # Remove quotes
            if "array_to_string" in field_expression:
                return (
                    "EXISTS (SELECT 1 FROM unnest(cb.tasting_notes) AS t(note) WHERE lower(note) = lower(?))",
                    [exact_term],
                )
            else:
                return f"{field_expression} ILIKE ?", [exact_term]
        else:
            search_pattern = query.replace("*", "%").replace("?", "_")
            if "*" not in query and "?" not in query:
                search_pattern = f"%{search_pattern}%"
            return f"{field_expression} ILIKE ?", [search_pattern]


def get_roaster_slug_from_bean_url_path(bean_url_path: str) -> str:
    """Extract roaster slug from bean_url_path."""
    if bean_url_path and bean_url_path.startswith("/"):
        parts = bean_url_path[1:].split("/")
        if len(parts) >= 1:
            return parts[0]
    return ""


def get_roaster_slug_from_db(roaster_name: str) -> str:
    """Get the roaster directory slug from the registry based on roaster name."""
    registry = get_registry()
    for scraper_info in registry.list_scrapers():
        if scraper_info.roaster_name == roaster_name:
            return scraper_info.directory_name
    # Fallback: convert roaster name to directory format
    return roaster_name.lower().replace(" ", "_")


def get_hierarchical_location_codes(target_location: str) -> list[str]:
    """Get all location codes that include the target location hierarchically.

    For example:
    - For 'United Kingdom': returns ['GB', 'XE', 'EU'] (country, europe, eu)
    - For 'France': returns ['FR', 'XE', 'EU'] (country, europe, eu)
    - For 'Canada': returns ['CA'] (country only, not in europe)
    - For 'XE': returns ['XE'] (regional code)

    Args:
        target_location: Location name or code to find hierarchical matches for

    Returns:
        List of location codes that hierarchically include the target location
    """
    try:
        # Get all location codes from database
        location_codes_query = """
            SELECT code, location, region
            FROM roaster_location_codes
            ORDER BY code
        """
        location_results = conn.execute(location_codes_query).fetchall()

        # Build location hierarchy mapping
        location_hierarchy = {}
        code_to_info = {}

        for code, location, region in location_results:
            code_to_info[code] = {"location": location, "region": region}

        # Define hierarchical relationships based on the CSV structure
        # European countries belong to both Europe (XE) and may belong to EU
        european_countries = ["GB", "FR", "DE", "IT", "NL", "PL", "ES", "SE"]
        eu_countries = ["FR", "DE", "IT", "NL", "PL", "ES", "SE"]  # UK is not in EU post-Brexit
        na_countries = ["CA", "US", "MX"]
        sa_countries = ["BR", "CL", "CO", "PE", "AR"]
        asian_countries = ["JP", "HK", "SK", "SG", "TW", "CN", "IN", "VN", "TH", "MY", "PH", "ID"]
        african_countries = ["EG", "KE", "TZ", "UG", "RW", "ZA"]

        # Build the hierarchy
        for code, info in code_to_info.items():
            hierarchy = [code]  # Always include the country itself

            # Add regional codes based on location
            if code in european_countries:
                hierarchy.append("XE")  # Europe
                if code in eu_countries:
                    hierarchy.append("EU")  # European Union
            elif code in asian_countries:
                hierarchy.append("XA")  # Asia
            elif code in na_countries:
                hierarchy.append("XN")  # North America
            elif code in sa_countries:
                hierarchy.append("XS")  # South America
            elif code in african_countries:
                hierarchy.append("XF")  # Africa

            location_hierarchy[code] = hierarchy
            location_hierarchy[info["location"]] = hierarchy  # Also map by full name

        # Handle regional codes themselves
        location_hierarchy["XE"] = ["XE"]
        location_hierarchy["EU"] = ["EU"]
        location_hierarchy["Europe"] = ["XE"]
        location_hierarchy["European Union"] = ["EU"]
        location_hierarchy["XN"] = ["XN"]
        location_hierarchy["North America"] = ["XN"]
        location_hierarchy["XS"] = ["XS"]
        location_hierarchy["South America"] = ["XS"]
        location_hierarchy["XF"] = ["XF"]
        location_hierarchy["Africa"] = ["XF"]

        # Get the hierarchy for the target location
        target_upper = target_location.upper()

        # Try exact match first (code or name)
        if target_location in location_hierarchy:
            return location_hierarchy[target_location]
        elif target_upper in location_hierarchy:
            return location_hierarchy[target_upper]

        # Try partial matching for location names
        for key, codes in location_hierarchy.items():
            if target_location.lower() in key.lower() or key.lower() in target_location.lower():
                return codes

        # If no match found, return the original as a single-item list
        return [target_location]

    except Exception as e:
        print(f"Error building location hierarchy: {e}")
        return [target_location]


def normalize_process_name(process: str) -> str:
    """Normalize process name for URL-friendly slugs."""
    if not process:
        return ""
    # Convert to lowercase, replace spaces and special chars with hyphens
    normalized = re.sub(r"[^a-zA-Z0-9\s]", "", process.lower())
    normalized = re.sub(r"\s+", "-", normalized.strip())
    return normalized


def categorize_process(process: str) -> str:
    """Categorize a process into major process groups."""
    if not process:
        return "other"

    process_lower = process.lower()

    # Washed processes
    if any(keyword in process_lower for keyword in ["washed", "lavado", "washing"]):
        return "washed"

    # Anaerobic processes (check before natural to catch "anaerobic natural")
    if "anaerobic" in process_lower or "anaerobes" in process_lower or "anaerobico" in process_lower:
        return "anaerobic"

    # Natural processes
    if any(keyword in process_lower for keyword in ["natural", "dry"]):
        return "natural"

    # Honey processes
    if "honey" in process_lower:
        return "honey"

    # Fermentation processes
    if any(keyword in process_lower for keyword in ["ferment", "yeast", "culturing", "bacteria"]):
        return "fermentation"

    # Decaf processes
    if any(keyword in process_lower for keyword in ["decaf", "ethyl acetate", "swiss water", "sugarcane"]):
        return "decaf"

    # Experimental/specialty processes
    if any(
        keyword in process_lower
        for keyword in ["experimental", "thermal shock", "carbonic", "maceration", "co-ferment"]
    ):
        return "experimental"

    return "other"


def normalize_varietal_name(varietal: str) -> str:
    """Normalize varietal name for URL-friendly slugs."""
    if not varietal:
        return ""
    # Convert to lowercase, replace spaces and special chars with hyphens
    normalized = re.sub(r"[^a-zA-Z0-9\s]", "", varietal.lower())
    normalized = re.sub(r"\s+", "-", normalized.strip())
    return normalized


def categorize_varietal(varietal: str) -> str:
    """Categorize a varietal into major varietal groups."""
    if not varietal:
        return "other"

    varietal_lower = varietal.lower()

    # Typica family
    if any(
        keyword in varietal_lower
        for keyword in ["typica", "kona", "jamaica blue mountain", "ethiopian", "mocha", "kent"]
    ):
        return "typica"

    # Bourbon family
    if any(keyword in varietal_lower for keyword in ["bourbon", "santos", "mundo novo", "caturra", "catuai"]):
        return "bourbon"

    # Heirloom varieties
    if any(keyword in varietal_lower for keyword in ["heirloom", "landrace", "native", "wild", "forest"]):
        return "heirloom"

    # Geisha/Gesha varieties
    if any(keyword in varietal_lower for keyword in ["geisha", "gesha"]):
        return "geisha"

    # SL varieties (SL28, SL34, etc.)
    if any(keyword in varietal_lower for keyword in ["sl28", "sl34", "sl ", "scott labs"]):
        return "sl_varieties"
    # Use regex too
    if re.search(r"sl\d+", varietal_lower):
        return "sl_varieties"

    # Hybrid varieties
    if any(keyword in varietal_lower for keyword in ["hybrid", "f1", "ruiru", "batian", "castillo", "colombia"]):
        return "hybrid"

    # Pacamara and large bean varieties
    if any(keyword in varietal_lower for keyword in ["pacamara", "maragogype", "elephant bean"]):
        return "large_bean"

    # Other Arabica varieties
    if any(
        keyword in varietal_lower for keyword in ["pacas", "villa sarchi", "tekisic", "red catuai", "yellow catuai"]
    ):
        return "arabica_other"

    return "other"


@app.get("/health")
@app.get("/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Kissaten API is running"}


# Initialize database and load data on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and load coffee bean data."""
    await init_database()
    # Load currency rates first, before loading coffee data (which calculates USD prices)
    await update_currency_rates()
    await load_coffee_data(data_dir=Path(__file__).parent.parent.parent.parent / "data" / "roasters")
    await load_tasting_notes_categories()

    # Include AI search router
    ai_search_router = create_ai_search_router(conn)
    app.include_router(ai_search_router)

    # Include FX/currency router
    fx_router = create_fx_router()
    app.include_router(fx_router)


async def init_database():
    """Initialize the DuckDB database with required tables."""
    # Create coffee beans table (simplified - origin info moved to separate table)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coffee_beans (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            roaster VARCHAR,
            url VARCHAR,
            is_single_origin BOOLEAN,
            price_paid_for_green_coffee DOUBLE,
            currency_of_price_paid_for_green_coffee VARCHAR,
            roast_level VARCHAR,
            roast_profile VARCHAR,
            weight INTEGER,
            price DOUBLE,
            currency VARCHAR,
            price_usd DOUBLE,  -- Normalized price in USD for sorting/filtering
            is_decaf BOOLEAN,
            cupping_score DOUBLE,
            tasting_notes VARCHAR[], -- Array of strings
            description TEXT,
            in_stock BOOLEAN,
            scraped_at TIMESTAMP,
            scraper_version VARCHAR,
            filename VARCHAR,  -- Store the original JSON filename
            image_url VARCHAR,  -- Store the image URL
            clean_url_slug VARCHAR,  -- Store clean URL without timestamp
            bean_url_path VARCHAR,  -- Store the full bean URL path from directory structure
            date_added TIMESTAMP  -- Date when this coffee was first scraped/added
        )
    """)

    # Add price_usd column if it doesn't exist (migration for existing databases)
    try:
        conn.execute("ALTER TABLE coffee_beans ADD COLUMN price_usd DOUBLE")
        print("Added price_usd column to existing coffee_beans table")
    except Exception:
        # Column already exists, which is fine
        pass

    # Add date_added column if it doesn't exist (migration for existing databases)
    try:
        conn.execute("ALTER TABLE coffee_beans ADD COLUMN date_added TIMESTAMP")
        print("Added date_added column to existing coffee_beans table")
    except Exception:
        # Column already exists, which is fine
        pass

    # Create origins table to handle multiple origins per bean
    conn.execute("""
        CREATE TABLE IF NOT EXISTS origins (
            id INTEGER PRIMARY KEY,
            bean_id INTEGER,
            country VARCHAR,
            region VARCHAR,
            producer VARCHAR,
            farm VARCHAR,
            elevation_min INTEGER DEFAULT 0,
            elevation_max INTEGER DEFAULT 0,
            latitude DOUBLE,
            longitude DOUBLE,
            process VARCHAR,
            process_common_name VARCHAR,
            variety VARCHAR,
            harvest_date TIMESTAMP,
            FOREIGN KEY (bean_id) REFERENCES coffee_beans (id)
        )
    """)

    # Create roasters table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roasters (
            id INTEGER PRIMARY KEY,
            name VARCHAR UNIQUE,
            slug VARCHAR UNIQUE,
            website VARCHAR,
            location VARCHAR,
            email VARCHAR,
            active BOOLEAN,
            last_scraped TIMESTAMP,
            total_beans_scraped INTEGER
        )
    """)

    # Create country codes table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS country_codes (
            name VARCHAR,
            alpha_2 VARCHAR PRIMARY KEY,
            alpha_3 VARCHAR,
            country_code VARCHAR,
            iso_3166_2 VARCHAR,
            region VARCHAR,
            sub_region VARCHAR,
            intermediate_region VARCHAR,
            region_code VARCHAR,
            sub_region_code VARCHAR,
            intermediate_region_code VARCHAR
        )
    """)

    # Create roaster location codes table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roaster_location_codes (
            location VARCHAR,
            code VARCHAR PRIMARY KEY,
            region VARCHAR
        )
    """)

    # Create tasting notes categories table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasting_notes_categories (
            tasting_note VARCHAR PRIMARY KEY,
            primary_category VARCHAR,
            secondary_category VARCHAR,
            tertiary_category VARCHAR,
            confidence DOUBLE
        )
    """)

    # Create currency exchange rates table for conversion
    conn.execute("""
        CREATE TABLE IF NOT EXISTS currency_rates (
            base_currency VARCHAR NOT NULL,
            target_currency VARCHAR NOT NULL,
            rate DOUBLE NOT NULL,
            fetched_at TIMESTAMP NOT NULL,
            data_timestamp INTEGER  -- Unix timestamp from API
        )
    """)

    # Create a view to simplify queries by joining coffee beans with their primary origin
    conn.execute("""
        CREATE OR REPLACE VIEW coffee_beans_with_origin AS
        SELECT
            cb.*,
            o.country,
            o.region,
            o.producer,
            o.farm,
            o.elevation_min,
            o.elevation_max,
            o.latitude,
            o.longitude,
            o.process,
            o.process_common_name,
            o.variety,
            o.harvest_date,
            cc.name as country_full_name
        FROM coffee_beans cb
        LEFT JOIN (
            -- Get the first origin for each bean (primary origin)
            SELECT DISTINCT ON (bean_id) *
            FROM origins
            ORDER BY bean_id, id
        ) o ON cb.id = o.bean_id
        LEFT JOIN country_codes cc ON o.country = cc.alpha_2
    """)

    # Create a view for roasters with location codes
    conn.execute("""
        CREATE OR REPLACE VIEW roasters_with_location AS
        SELECT
            r.*,
            rlc.code as roaster_country_code
        FROM roasters r
        LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
    """)


def normalize_country_code(country_value: str, country_mapping: dict) -> str:
    """
    Normalize country codes from various formats to ISO alpha-2 codes.

    Args:
        country_value: The country value from scraped data (could be name, code, etc.)
        country_mapping: Dictionary mapping various formats to alpha-2 codes

    Returns:
        Normalized ISO alpha-2 country code or original value if no match found
    """
    if not country_value or not isinstance(country_value, str):
        return ""

    # Clean the input - remove extra whitespace and convert to uppercase for comparison
    cleaned_value = country_value.strip().upper()

    # Return the mapping if found, otherwise return original value
    return country_mapping.get(cleaned_value, country_value)


async def calculate_usd_prices():
    """Calculate USD prices for all coffee beans using current exchange rates."""
    try:
        # Update all beans with USD prices using DuckDB's CASE statement for efficient batch processing
        conn.execute("""
            UPDATE coffee_beans
            SET price_usd =
                CASE
                    WHEN currency = 'USD' OR currency IS NULL THEN price
                    WHEN price IS NULL OR price = 0 THEN NULL
                    ELSE
                        CASE
                            WHEN currency = 'USD' THEN price
                            ELSE
                                price / COALESCE((
                                    SELECT rate
                                    FROM currency_rates cr
                                    WHERE cr.base_currency = 'USD'
                                    AND cr.target_currency = coffee_beans.currency
                                    ORDER BY cr.fetched_at DESC
                                    LIMIT 1
                                ), 1.0)
                        END
                END
            WHERE price IS NOT NULL
        """)

        # Get statistics about the conversion
        stats_result = conn.execute("""
            SELECT
                COUNT(*) as total_beans,
                COUNT(price_usd) as beans_with_usd_price,
                COUNT(DISTINCT currency) as unique_currencies
            FROM coffee_beans
            WHERE price IS NOT NULL
        """).fetchone()

        if stats_result:
            total, with_usd, currencies = stats_result
            print(f"USD price calculation complete: {with_usd}/{total} beans processed across {currencies} currencies")

    except Exception as e:
        print(f"Error calculating USD prices: {e}")


async def apply_diffjson_updates(data_dir: Path):
    """Apply partial updates from diffjson files to existing coffee beans."""
    import glob
    import json

    # Find all diffjson files
    diffjson_pattern = str(data_dir / "**" / "*.diffjson")
    diffjson_files = glob.glob(diffjson_pattern, recursive=True)

    if not diffjson_files:
        print("No diffjson files found - skipping partial updates")
        return

    print(f"Processing {len(diffjson_files)} diffjson update files...")
    updates_applied = 0

    for diffjson_file in diffjson_files:
        try:
            with open(diffjson_file) as f:
                raw_update_data = json.load(f)

            # Validate the diffjson data using Pydantic schema
            try:
                diff_update = CoffeeBeanDiffUpdate.model_validate(raw_update_data)
            except Exception as validation_error:
                print(f"  Skipping {diffjson_file}: validation failed - {validation_error}")
                continue

            # Extract URL from validated update data
            url = str(diff_update.url)

            # Check if bean exists in database
            existing_bean = conn.execute("SELECT id FROM coffee_beans WHERE url = ?", [url]).fetchone()

            if not existing_bean:
                print(f"  Skipping {diffjson_file}: no matching bean found for URL {url}")
                continue

            bean_id = existing_bean[0]

            # Convert the validated model to dict and exclude None values and URL
            update_data = diff_update.model_dump(exclude_none=True, exclude={"url"})

            # Build UPDATE query for fields that exist in the validated diffjson
            update_fields = []
            update_params = []

            # Handle special case for tasting_notes (array field)
            if "tasting_notes" in update_data:
                update_fields.append("tasting_notes = ?")
                update_params.append(update_data["tasting_notes"])
                del update_data["tasting_notes"]  # Remove so it's not processed again

            # Handle all other fields
            for field, value in update_data.items():
                update_fields.append(f"{field} = ?")
                update_params.append(value)

            if update_fields:
                # Execute update
                update_query = f"""
                    UPDATE coffee_beans
                    SET {", ".join(update_fields)}
                    WHERE id = ?
                """
                update_params.append(bean_id)

                conn.execute(update_query, update_params)

                updates_applied += 1
            else:
                print(f"  Skipping {diffjson_file}: no updatable fields found")

        except Exception as e:
            print(f"  Error processing {diffjson_file}: {e}")
            continue

    if updates_applied > 0:
        # Recalculate USD prices for updated beans
        await calculate_usd_prices()
        print(f"Applied {updates_applied} diffjson updates")
    else:
        print("No diffjson updates were applied")


async def load_coffee_data(data_dir: Path):
    """Load coffee bean data from JSON files into DuckDB using DuckDB's native glob functionality."""
    countrycodes_path = Path(__file__).parent.parent / "database" / "countrycodes.csv"
    processing_methods_mapping_path = Path(__file__).parent.parent / "database/processing_methods_mappings.json"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

    # Load processing methods mapping
    processing_mapping = {}
    if processing_methods_mapping_path.exists():
        try:
            import json

            with open(processing_methods_mapping_path, "r", encoding="utf-8") as f:
                mapping_data = json.load(f)

            for mapping in mapping_data:
                original_name = mapping.get("original_name", "")
                common_name = mapping.get("common_name", "")
                if original_name and common_name:
                    processing_mapping[original_name] = common_name

            print(f"Loaded {len(processing_mapping)} processing method mappings")
        except Exception as e:
            print(f"Error loading processing methods mapping: {e}")
    else:
        print(f"Processing methods mapping file not found: {processing_methods_mapping_path}")

    # Get scraper registry to map directory names to roaster info
    registry = get_registry()
    scraper_infos = registry.list_scrapers()

    # Create mapping from directory name to roaster info
    directory_to_roaster = {}
    for scraper_info in scraper_infos:
        directory_to_roaster[scraper_info.directory_name] = scraper_info

    # Clear existing data
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.execute("DELETE FROM country_codes")
    conn.execute("DELETE FROM roaster_location_codes")

    # Load country codes from CSV
    country_mapping = {}
    if countrycodes_path.exists():
        try:
            conn.execute(f"""
                INSERT INTO country_codes
                SELECT * FROM read_csv('{countrycodes_path}', header=true, auto_detect=true)
            """)
            result = conn.execute("SELECT COUNT(*) FROM country_codes").fetchone()
            country_count = result[0] if result else 0
            print(f"Loaded {country_count} country codes")

            # Create country mapping for normalization
            # Include various formats: uppercase names, lowercase names, alpha-2, alpha-3
            country_codes_data = conn.execute("""
                SELECT name, alpha_2, alpha_3 FROM country_codes
            """).fetchall()

            for row in country_codes_data:
                country_name, alpha_2, alpha_3 = row
                if country_name and alpha_2:
                    # Map uppercase country name to alpha-2
                    country_mapping[country_name.upper()] = alpha_2
                    # Map lowercase country name to alpha-2
                    country_mapping[country_name.lower()] = alpha_2
                    # Map alpha-2 to itself (in case it's already correct)
                    country_mapping[alpha_2.upper()] = alpha_2
                    # Map alpha-3 to alpha-2
                    if alpha_3:
                        country_mapping[alpha_3.upper()] = alpha_2

            # Add special mappings for common variations
            special_mappings = {
                "BOLIVIA": "BO",
                "bolivia": "BO",
                "UNITED STATES": "US",
                "USA": "US",
                "UNITED KINGDOM": "GB",
                "SOUTH KOREA": "KR",
                "DEMOCRATIC REPUBLIC OF CONGO": "CD",
                "REPUBLIC OF CONGO": "CG",
                "CONGO": "CG",
                "IVORY COAST": "CI",
                "CAPE VERDE": "CV",
                "CZECH REPUBLIC": "CZ",
                "EAST TIMOR": "TL",
                "RUSSIA": "RU",
                "SOUTH AFRICA": "ZA",
                "PALESTINE": "PS",
            }

            country_mapping.update(special_mappings)

            print(f"Created country mapping with {len(country_mapping)} entries")
        except Exception as e:
            print(f"Error loading country codes: {e}")
    else:
        print(f"Country codes file not found: {countrycodes_path}")

    # Load roaster location codes from CSV
    roaster_location_codes_path = Path(__file__).parent.parent / "database" / "roaster_location_codes.csv"
    if roaster_location_codes_path.exists():
        try:
            conn.execute(f"""
                INSERT INTO roaster_location_codes
                SELECT * FROM read_csv('{roaster_location_codes_path}', header=true, auto_detect=true)
            """)
            result = conn.execute("SELECT COUNT(*) FROM roaster_location_codes").fetchone()
            location_count = result[0] if result else 0
            print(f"Loaded {location_count} roaster location codes")
        except Exception as e:
            print(f"Error loading roaster location codes: {e}")
    else:
        print(f"Roaster location codes file not found: {roaster_location_codes_path}")

    # Insert roasters from the registry
    try:
        roaster_values = []
        for i, scraper_info in enumerate(scraper_infos, 1):
            roaster_values.append(
                (
                    i,
                    scraper_info.roaster_name,
                    scraper_info.directory_name,
                    scraper_info.website,
                    f"{scraper_info.country}",
                    "",  # email
                    True,  # active
                    None,  # last_scraped
                    0,  # total_beans_scraped
                )
            )

        # Use a proper INSERT with all values
        for values in roaster_values:
            conn.execute(
                """
                INSERT INTO roasters (
                    id, name, slug, website, location, email, active,
                    last_scraped, total_beans_scraped
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (name) DO NOTHING
            """,
                values,
            )

        result = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
        roaster_count = result[0] if result else 0
        print(f"Loaded {roaster_count} roasters from registry")
    except Exception as e:
        print(f"Error inserting roasters from registry: {e}")

    try:
        # Use DuckDB's glob functionality to read all JSON files directly
        json_pattern = str(data_dir / "**" / "*.json")

        # Create a temporary view with the raw JSON data, including file path for roaster extraction
        conn.execute(f"""
            CREATE OR REPLACE TEMPORARY VIEW raw_coffee_data AS
            SELECT
                json_data.*,
                -- Extract roaster directory name from file path
                split_part(filename, '/', -3) as roaster_directory,
                -- Extract scrape date from file path (e.g., 20250911)
                split_part(filename, '/', -2) as scrape_date,
                filename
            FROM read_json('{json_pattern}',
                filename=true,
                auto_detect=true,
                union_by_name=true,
                ignore_errors=true
            ) as json_data
        """)

        # Create a view to identify the latest scrape date for each roaster
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW latest_scrapes AS
            SELECT
                roaster_directory,
                MAX(scrape_date) as latest_scrape_date
            FROM raw_coffee_data
            GROUP BY roaster_directory
        """)

        # Create a view to identify the earliest scrape date for each unique coffee bean
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW earliest_coffee_dates AS
            SELECT
                roaster_directory,
                url,
                MIN(scraped_at) as date_added
            FROM raw_coffee_data
            WHERE url IS NOT NULL AND url != ''
            GROUP BY roaster_directory, url
        """)

        # Create a view with only the latest scrape data for each roaster, deduplicated by URL
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW latest_coffee_data AS
            SELECT rcd.*
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY rcd.roaster_directory, rcd.url
                           ORDER BY rcd.scraped_at DESC
                       ) as rn
                FROM raw_coffee_data rcd
                JOIN latest_scrapes ls ON rcd.roaster_directory = ls.roaster_directory
                    AND rcd.scrape_date = ls.latest_scrape_date
                WHERE rcd.url IS NOT NULL AND rcd.url != ''
            ) rcd
            WHERE rcd.rn = 1
        """)

        # Create a comprehensive view that handles both in-stock and out-of-stock beans
        # with proper stock status based on whether they appear in the latest scrape
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW all_coffee_beans_with_stock_status AS
            SELECT
                rcd.*,
                -- Determine stock status: in-stock if URL exists in latest scrape, out-of-stock otherwise
                CASE
                    WHEN latest_urls.url IS NOT NULL THEN true
                    ELSE false
                END as calculated_in_stock,
                -- Use latest scrape data if available, otherwise use historical data
                COALESCE(latest_data.scraped_at, rcd.scraped_at) as final_scraped_at,
                COALESCE(latest_data.scraper_version, rcd.scraper_version) as final_scraper_version,
                COALESCE(latest_data.filename, rcd.filename) as final_filename,
                -- Add the date when this coffee was first added/scraped
                ecd.date_added
            FROM (
                -- Get the most recent version of each unique bean (by URL and roaster)
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY roaster_directory, url
                           ORDER BY scrape_date DESC, scraped_at DESC
                       ) as rn
                FROM raw_coffee_data
                WHERE url IS NOT NULL AND url != ''
            ) rcd
            LEFT JOIN (
                -- Get URLs that exist in the latest scrape (these are in-stock)
                SELECT DISTINCT roaster_directory, url
                FROM latest_coffee_data
            ) latest_urls ON rcd.roaster_directory = latest_urls.roaster_directory
                         AND rcd.url = latest_urls.url
            LEFT JOIN latest_coffee_data latest_data ON rcd.roaster_directory = latest_data.roaster_directory
                                                    AND rcd.url = latest_data.url
            LEFT JOIN earliest_coffee_dates ecd ON rcd.roaster_directory = ecd.roaster_directory
                                               AND rcd.url = ecd.url
            WHERE rcd.rn = 1
        """)

        # Insert all coffee beans with correct stock status
        conn.execute("""
            INSERT INTO coffee_beans (
                id, name, roaster, url, is_single_origin, price_paid_for_green_coffee,
                currency_of_price_paid_for_green_coffee, roast_level, roast_profile, weight, price, currency,
                price_usd, is_decaf, cupping_score, tasting_notes, description, in_stock, scraped_at, scraper_version,
                filename, image_url, clean_url_slug, bean_url_path, date_added
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY calculated_in_stock DESC, name) as id,
                COALESCE(name, '') as name,
                COALESCE(roaster, 'Unknown Roaster') as roaster,
                COALESCE(url, '') as url,
                COALESCE(is_single_origin, true) as is_single_origin,
                TRY_CAST(price_paid_for_green_coffee AS DOUBLE) as price_paid_for_green_coffee,
                currency_of_price_paid_for_green_coffee,
                roast_level,
                roast_profile,
                TRY_CAST(weight AS INTEGER) as weight,
                TRY_CAST(price AS DOUBLE) as price,
                COALESCE(currency, 'EUR') as currency,
                -- Initialize price_usd as NULL, will be calculated after currency rates are available
                NULL as price_usd,
                is_decaf,
                cupping_score,
                COALESCE(tasting_notes, []) as tasting_notes,
                COALESCE(description, '') as description,
                calculated_in_stock as in_stock,  -- Use calculated stock status
                TRY_CAST(final_scraped_at AS TIMESTAMP) as scraped_at,
                COALESCE(final_scraper_version, '1.0') as scraper_version,
                final_filename as filename,
                -- Generate static image URL based on filename and roaster path, only if original image_url exists
                CASE
                    WHEN final_filename IS NOT NULL AND image_url IS NOT NULL AND image_url != '' THEN
                        '/static/data/' ||
                        regexp_replace(split_part(final_filename, '/data/', -1), '\\.json$', '.png', 'g')
                    ELSE ''
                END as image_url,
                -- Generate clean URL slug by removing timestamp from filename
                regexp_replace(
                    regexp_replace(split_part(final_filename, '/', -1), '\\.json$', '', 'g'),
                    '_\\d{6}$', '', 'g'
                ) as clean_url_slug,
                -- Generate bean_url_path from actual directory structure
                CASE
                    WHEN final_filename IS NOT NULL THEN
                        '/' || roaster_directory || '/' ||
                        regexp_replace(
                            regexp_replace(split_part(final_filename, '/', -1), '\\.json$', '', 'g'),
                            '_\\d{6}$', '', 'g'
                        )
                    ELSE ''
                END as bean_url_path,
                -- Add the date when this coffee was first scraped/added
                TRY_CAST(date_added AS TIMESTAMP) as date_added
            FROM all_coffee_beans_with_stock_status
            WHERE name IS NOT NULL AND name != ''
        """)

        # Insert origins data from all beans (both in-stock and out-of-stock)
        conn.execute("""
            INSERT INTO origins (
                id, bean_id, country, region, producer, farm, elevation_min, elevation_max,
                latitude, longitude, process, process_common_name, variety, harvest_date
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY cb.id) as id,
                cb.id as bean_id,
                COALESCE(t.origin.country, '') as country,
                COALESCE(t.origin.region, '') as region,
                COALESCE(t.origin.producer, '') as producer,
                COALESCE(t.origin.farm, '') as farm,
                COALESCE(TRY_CAST(t.origin.elevation_min AS INTEGER), 0) as elevation_min,
                COALESCE(TRY_CAST(t.origin.elevation_max AS INTEGER), 0) as elevation_max,
                TRY_CAST(t.origin.latitude AS DOUBLE) as latitude,
                TRY_CAST(t.origin.longitude AS DOUBLE) as longitude,
                COALESCE(t.origin.process, '') as process,
                '' as process_common_name,  -- Will be populated after origins are inserted
                COALESCE(t.origin.variety, '') as variety,
                TRY_CAST(t.origin.harvest_date AS TIMESTAMP) as harvest_date
            FROM all_coffee_beans_with_stock_status abs
            JOIN coffee_beans cb ON cb.filename = abs.final_filename
            CROSS JOIN UNNEST(abs.origins) AS t(origin)
            WHERE abs.origins IS NOT NULL
        """)

        # Now update roaster names based on directory mapping using parameterized queries
        for directory_name, scraper_info in directory_to_roaster.items():
            conn.execute(
                """
                UPDATE coffee_beans
                SET roaster = ?
                WHERE filename LIKE ?
            """,
                [scraper_info.roaster_name, f"%/{directory_name}/%"],
            )

        # Apply processing methods mapping to convert process to process_common_name
        if processing_mapping:
            print("Applying processing methods mapping...")

            # Get all unique process values that need mapping
            raw_processes = conn.execute("""
                SELECT DISTINCT process, COUNT(*) as count
                FROM origins
                WHERE process IS NOT NULL AND process != ''
                GROUP BY process
                ORDER BY count DESC
            """).fetchall()

            mapping_stats = {"mapped": 0, "unchanged": 0}

            for process_value, count in raw_processes:
                common_name = processing_mapping.get(process_value)

                if common_name:
                    # Update all origins with this process value
                    conn.execute(
                        """
                        UPDATE origins
                        SET process_common_name = ?
                        WHERE process = ?
                    """,
                        [common_name, process_value],
                    )

                    mapping_stats["mapped"] += count
                else:
                    # Keep the original process name as the common name if no mapping exists
                    conn.execute(
                        """
                        UPDATE origins
                        SET process_common_name = process
                        WHERE process = ? AND (process_common_name IS NULL OR process_common_name = '')
                    """,
                        [process_value],
                    )
                    mapping_stats["unchanged"] += count

            mapped_count = mapping_stats["mapped"]
            unchanged_count = mapping_stats["unchanged"]
            print(f"Processing methods mapping complete: {mapped_count} mapped, {unchanged_count} unchanged")

        # Normalize country codes using the mapping
        if country_mapping:
            print("Normalizing country codes...")

            # Get all unique country values that need normalization from origins table
            raw_countries = conn.execute("""
                SELECT DISTINCT country, COUNT(*) as count
                FROM origins
                WHERE country IS NOT NULL AND country != ''
                GROUP BY country
                ORDER BY count DESC
            """).fetchall()

            normalization_stats = {"normalized": 0, "unchanged": 0}

            for country_value, count in raw_countries:
                normalized_country = normalize_country_code(country_value, country_mapping)

                if normalized_country != country_value:
                    # Update all origins with this country value
                    conn.execute(
                        """
                        UPDATE origins
                        SET country = ?
                        WHERE country = ?
                    """,
                        [normalized_country, country_value],
                    )

                    normalization_stats["normalized"] += count
                    print(f"  Normalized '{country_value}' -> '{normalized_country}' ({count} origins)")
                else:
                    normalization_stats["unchanged"] += count

            normalized_count = normalization_stats["normalized"]
            unchanged_count = normalization_stats["unchanged"]
            print(f"Country normalization complete: {normalized_count} normalized, {unchanged_count} unchanged")

        # Calculate USD prices for all coffee beans after currency rates are available
        print("Calculating USD prices for currency conversion...")
        await calculate_usd_prices()

        # Apply diffjson updates if any exist
        await apply_diffjson_updates(data_dir)

        # Get counts for logging
        result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
        bean_count = result[0] if result else 0
        result = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
        roaster_count = result[0] if result else 0

        print(f"Loaded {bean_count} coffee beans from {roaster_count} roasters using DuckDB glob with registry")

        # Get counts for in-stock vs out-of-stock
        in_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = true").fetchone()
        out_of_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = false").fetchone()
        in_stock_count = in_stock_result[0] if in_stock_result else 0
        out_of_stock_count = out_of_stock_result[0] if out_of_stock_result else 0

        print(f"  - In stock: {in_stock_count} beans")
        print(f"  - Out of stock: {out_of_stock_count} beans")

        # Clean up temporary views
        conn.execute("DROP VIEW IF EXISTS raw_coffee_data")
        conn.execute("DROP VIEW IF EXISTS latest_scrapes")
        conn.execute("DROP VIEW IF EXISTS earliest_coffee_dates")
        conn.execute("DROP VIEW IF EXISTS latest_coffee_data")
        conn.execute("DROP VIEW IF EXISTS all_coffee_beans_with_stock_status")

    except Exception as e:
        print(f"Error loading coffee data with DuckDB glob: {e}")
        # Fallback: if glob fails, we could implement a simple directory scan
        # For now, just log the error
        raise


async def load_tasting_notes_categories():
    """Load tasting notes categorizations from CSV file into database."""
    csv_file_path = Path(__file__).parent.parent / "database" / "tasting_notes_categorized.csv"

    # Check if the CSV file exists
    if not csv_file_path.exists():
        print(f"Tasting notes categories CSV file not found: {csv_file_path}")
        print("Skipping tasting notes categories loading")
        return

    try:
        # Clear existing data first
        conn.execute("DELETE FROM tasting_notes_categories")

        # Load data from CSV
        conn.execute(f"""
            INSERT INTO tasting_notes_categories
            SELECT * FROM read_csv_auto('{csv_file_path}')
        """)

        # Create the comprehensive view that joins coffee beans with categorized tasting notes
        conn.execute("""
            CREATE OR REPLACE VIEW coffee_beans_with_categorized_notes AS
            SELECT
                cb.*,
                list(DISTINCT tnc.primary_category) as primary_categories,
                list(DISTINCT tnc.secondary_category) as secondary_categories,
                list(DISTINCT tnc.tertiary_category) as tertiary_categories,
                avg(tnc.confidence) as avg_categorization_confidence
            FROM coffee_beans cb
            LEFT JOIN (
                SELECT
                    cb.id as bean_id,
                    tnc.primary_category,
                    tnc.secondary_category,
                    tnc.tertiary_category,
                    tnc.confidence
                FROM coffee_beans cb,
                     unnest(cb.tasting_notes) as note_table(note)
                INNER JOIN tasting_notes_categories tnc ON note_table.note = tnc.tasting_note
                WHERE cb.tasting_notes IS NOT NULL
            ) tnc ON cb.id = tnc.bean_id
            GROUP BY cb.id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
                     cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
                     cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency, cb.price_usd,
                     cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description,
                     cb.in_stock, cb.scraped_at, cb.scraper_version, cb.filename,
                     cb.image_url, cb.clean_url_slug, cb.bean_url_path, cb.date_added
        """)

        # Get count of loaded categorizations
        result = conn.execute("SELECT COUNT(*) FROM tasting_notes_categories").fetchone()
        categorizations_count = result[0] if result else 0
        print(f"Loaded {categorizations_count} tasting note categorizations from {csv_file_path}")
        print("Created coffee_beans_with_categorized_notes view")

    except Exception as e:
        print(f"Error loading tasting notes categories: {e}")
        # Don't raise the error as this is optional data


# API Endpoints


@app.get("/", response_model=APIResponse[dict])
async def root():
    """Root endpoint with API information."""
    return APIResponse.success_response(
        data={"message": "Welcome to Kissaten Coffee Bean API"}, metadata={"version": "1.0.0"}
    )


@app.get("/v1/search", response_model=APIResponse[list[APISearchResult]])
@cached(ttl=600, cache=SimpleMemoryCache)
async def search_coffee_beans(
    query: str | None = Query(None, description="Search query text for names, descriptions, and general content"),
    tasting_notes_query: str | None = Query(
        None,
        description=(
            "Search query specifically for tasting notes. Supports: "
            "wildcards (* and ?), boolean operators (| OR, & AND, ! NOT), "
            'parentheses for grouping, and exact matches with "quotes"'
        ),
    ),
    roaster: list[str] | None = Query(None, description="Filter by roaster names (multiple allowed)"),
    roaster_location: list[str] | None = Query(None, description="Filter by roaster locations (multiple allowed)"),
    origin: list[str] | None = Query(None, description="Filter by origin countries (multiple allowed)"),
    region: str | None = Query(
        None,
        description="Filter by origin region (supports wildcards *, ? and boolean operators | (OR), & (AND), ! (NOT), parentheses for grouping)",
    ),
    producer: str | None = Query(
        None,
        description="Filter by producer name (supports wildcards *, ? and boolean operators | (OR), & (AND), ! (NOT), parentheses for grouping)",
    ),
    farm: str | None = Query(
        None,
        description="Filter by farm name (supports wildcards *, ? and boolean operators | (OR), & (AND), ! (NOT), parentheses for grouping)",
    ),
    roast_level: str | None = Query(
        None,
        description="Filter by roast level (supports wildcards *, ? and boolean operators | (OR), & (AND), ! (NOT), parentheses for grouping)",
    ),
    roast_profile: str | None = Query(
        None,
        description="Filter by roast profile (Espresso/Filter/Omni) (supports wildcards *, ? and boolean operators | (OR), & (AND), ! (NOT), parentheses for grouping)",
    ),
    process: str | None = Query(
        None,
        description="Filter by processing method (supports wildcards *, ? and boolean operators | (OR), & (AND), ! (NOT), parentheses for grouping)",
    ),
    variety: str | None = Query(
        None,
        description="Filter by coffee variety (supports wildcards *, ? and boolean operators | (OR), & (AND), ! (NOT), parentheses for grouping)",
    ),
    min_price: float | None = Query(
        None, description="Minimum price filter (in target currency if convert_to_currency is specified)"
    ),
    max_price: float | None = Query(
        None, description="Maximum price filter (in target currency if convert_to_currency is specified)"
    ),
    min_weight: int | None = Query(None, description="Minimum weight filter (grams)"),
    max_weight: int | None = Query(None, description="Maximum weight filter (grams)"),
    in_stock_only: bool = Query(False, description="Show only in-stock items"),
    is_decaf: bool | None = Query(None, description="Filter by decaf status"),
    is_single_origin: bool | None = Query(None, description="Filter by single origin status"),
    min_cupping_score: float | None = Query(None, description="Minimum cupping score filter (0-100)"),
    max_cupping_score: float | None = Query(None, description="Maximum cupping score filter (0-100)"),
    min_elevation: int | None = Query(None, description="Minimum elevation filter (meters above sea level)"),
    max_elevation: int | None = Query(None, description="Maximum elevation filter (meters above sea level)"),
    tasting_notes_only: bool = Query(
        False,
        description=(
            "DEPRECATED: Use tasting_notes_query parameter instead. "
            "When true, treats 'query' parameter as tasting notes search"
        ),
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Literal[
        "name",
        "roaster",
        "price",
        "weight",
        "date_added",
        "origin",
        "variety",
        "elevation",
        "cupping_score",
        "relevance",
    ] = Query("name", description="Sort field"),
    sort_order: Literal["asc", "desc", "random"] = Query("asc", description="Sort order (asc/desc/random)"),
    convert_to_currency: str | None = Query(
        None, description="Convert prices to this currency code (e.g., EUR, GBP, JPY)"
    ),
):
    """Search coffee beans with filters and pagination."""

    # Build SQL query
    score_components = []
    params = []

    # Handle regular query (searches name, description, and tasting notes)
    if query:
        if tasting_notes_only:
            condition, search_params = parse_boolean_search_query_for_field(
                query, "array_to_string(cb.tasting_notes, ' ')"
            )
            if condition:
                score_components.append(f"(CASE WHEN {condition} THEN 1 ELSE 0 END)")
                params.extend(search_params)
        else:
            condition = "(cb.name ILIKE ? OR cb.description ILIKE ? OR array_to_string(cb.tasting_notes, ' ') ILIKE ?)"
            score_components.append(f"(CASE WHEN {condition} THEN 1 ELSE 0 END)")
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term])

    # Handle separate tasting notes query
    if tasting_notes_query:
        condition, search_params = parse_boolean_search_query_for_field(
            tasting_notes_query, "array_to_string(cb.tasting_notes, ' ')"
        )
        if condition:
            score_components.append(f"(CASE WHEN {condition} THEN 1 ELSE 0 END)")
            params.extend(search_params)

    if roaster:
        placeholders = ", ".join(["?" for _ in roaster])
        score_components.append(f"(CASE WHEN cb.roaster IN ({placeholders}) THEN 1 ELSE 0 END)")
        params.extend(roaster)

    if roaster_location:
        # This logic is complex, so we wrap the whole generated condition.
        roaster_location_conditions = []
        roaster_params = []
        for location_code in roaster_location:
            registry = get_registry()
            matching_roasters = [
                scraper_info.roaster_name
                for scraper_info in registry.list_scrapers()
                if location_code.upper()
                in [code.upper() for code in get_hierarchical_location_codes(scraper_info.country)]
            ]
            if matching_roasters:
                placeholders = ", ".join(["?" for _ in matching_roasters])
                roaster_location_conditions.append(f"cb.roaster IN ({placeholders})")
                roaster_params.extend(matching_roasters)

        if roaster_location_conditions:
            full_condition = f"({' OR '.join(roaster_location_conditions)})"
            score_components.append(f"(CASE WHEN {full_condition} THEN 1 ELSE 0 END)")
            params.extend(roaster_params)

    if origin:
        origin_conditions = [
            "EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND o.country = ?)" for c in origin
        ]
        score_components.append(f"(CASE WHEN {' OR '.join(origin_conditions)} THEN 1 ELSE 0 END)")
        params.extend([c.upper() for c in origin])

    # Generic function to handle boolean search fields
    def add_boolean_search_score(field_query, sql_field, is_origin_field=False):
        if field_query:
            condition, search_params = parse_boolean_search_query_for_field(field_query, sql_field)
            if condition:
                if is_origin_field:
                    # Special handling for process which checks two fields
                    if sql_field == "o.process":
                        common_name_condition, common_name_search_params = parse_boolean_search_query_for_field(
                            field_query, "o.process_common_name"
                        )
                        final_condition = f"EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND ({condition} OR {common_name_condition}))"
                        params.extend(search_params)
                        params.extend(common_name_search_params)
                    else:
                        final_condition = f"EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND {condition})"
                        params.extend(search_params)
                else:
                    final_condition = condition
                    params.extend(search_params)
                score_components.append(f"(CASE WHEN {final_condition} THEN 1 ELSE 0 END)")

    add_boolean_search_score(region, "o.region", is_origin_field=True)
    add_boolean_search_score(producer, "o.producer", is_origin_field=True)
    add_boolean_search_score(farm, "o.farm", is_origin_field=True)
    add_boolean_search_score(roast_level, "cb.roast_level")
    add_boolean_search_score(roast_profile, "cb.roast_profile")
    add_boolean_search_score(process, "o.process", is_origin_field=True)
    add_boolean_search_score(variety, "o.variety", is_origin_field=True)

    # --- Range filters: each pair (min/max) counts as one filter match ---

    def add_range_score(min_val, max_val, field_name, is_origin_field=False):
        conditions = []
        range_params = []
        if min_val is not None:
            conditions.append(f"{field_name} >= ?")
            range_params.append(min_val)
        if max_val is not None:
            conditions.append(f"{field_name} <= ?")
            range_params.append(max_val)
        if conditions:
            full_condition = " AND ".join(conditions)
            if is_origin_field:
                final_condition = f"EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND {full_condition})"
            else:
                final_condition = full_condition
            score_components.append(f"(CASE WHEN {final_condition} THEN 1 ELSE 0 END)")
            params.extend(range_params)

    # Price range (handles currency conversion for filtering)
    price_field = "cb.price_usd" if convert_to_currency else "cb.price"
    min_p, max_p = min_price, max_price
    if convert_to_currency and convert_to_currency.upper() != "USD":
        if min_p is not None:
            min_p = convert_price(min_p, convert_to_currency.upper(), "USD")
        if max_p is not None:
            max_p = convert_price(max_p, convert_to_currency.upper(), "USD")
    add_range_score(min_p, max_p, price_field)

    add_range_score(min_weight, max_weight, "cb.weight")
    add_range_score(min_cupping_score, max_cupping_score, "cb.cupping_score")
    add_range_score(min_elevation, max_elevation, "o.elevation_max", is_origin_field=True)

    # --- Boolean filters ---

    if in_stock_only:
        score_components.append("(CASE WHEN cb.in_stock = true THEN 1 ELSE 0 END)")
    if is_decaf is not None:
        score_components.append("(CASE WHEN cb.is_decaf = ? THEN 1 ELSE 0 END)")
        params.append(is_decaf)
    if is_single_origin is not None:
        score_components.append("(CASE WHEN cb.is_single_origin = ? THEN 1 ELSE 0 END)")
        params.append(is_single_origin)

    # SCORING: Build the score calculation and filtering clauses
    score_calculation_clause = " + ".join(score_components) if score_components else "0"

    is_scoring_mode = sort_by.lower() == "relevance"
    max_possible_score = len(score_components)

    # UNIFIED FILTERING LOGIC
    # Build the final parameters list that includes the score filter value if needed.
    final_params = list(params)  # Start with the base parameters for the score calculation
    filter_clause = ""

    if max_possible_score > 0:
        if is_scoring_mode:
            # SCORING MODE: Return if any filter matches (score > 0)
            filter_clause = "WHERE score > 0"
        else:
            # STRICT FILTERING MODE: Return only if ALL filters match (score = max)
            filter_clause = "WHERE score = ?"
            # Add the max score as the parameter for the WHERE clause
            final_params.append(max_possible_score)

    # Validate sort fields
    sort_field_mapping = {
        "name": "sb.name",
        "roaster": "sb.roaster",
        "price": "sb.price_usd/sb.weight",
        "weight": "sb.weight",
        "date_added": "sb.date_added",
        "origin": "sb.country",
        "variety": "sb.variety",
        "elevation": "sb.elevation_min",
        "cupping_score": "sb.cupping_score",
        # 'score' is a valid sort key, handled below
    }
    # Note: 'sb.name' is a valid default for sort_by_sql, so no need for complex handling
    sort_by_sql = sort_field_mapping.get(sort_by, "sb.name")

    if sort_order.lower() not in ["asc", "desc", "random"]:
        sort_order = "asc"

    if is_scoring_mode:
        # In scoring mode, always sort by score descending first.
        # A secondary sort can be applied if the user sorts by something else (e.g., name).
        secondary_sort_by = sort_field_mapping.get("name")  # Default secondary sort
        order_by_clause = f"score DESC, {secondary_sort_by} ASC"
    elif sort_order.lower() == "random":
        order_by_clause = f"hash(concat({sort_by_sql}, sb.scraped_at, current_date()))"
    else:
        # In strict mode, use the user-provided sort field.
        order_by_clause = f"{sort_by_sql} {sort_order.upper()}"

    # The count query uses the dynamically built filter clause
    count_query = f"""
        SELECT COUNT(*)
        FROM (
            SELECT
                ({score_calculation_clause}) AS score
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
                FROM coffee_beans_with_origin cb
            ) cb
            WHERE cb.rn = 1
        ) scored_beans
        {filter_clause}
    """
    # Use the final_params list which now includes the parameter for `WHERE score = ?`
    count_result = conn.execute(count_query, final_params).fetchone()
    total_count = count_result[0] if count_result else 0

    # Calculate pagination
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0

    # The main query also uses the unified filter_clause for consistency.
    main_query = f"""
        WITH scored_beans AS (
            SELECT
                *,
                ({score_calculation_clause}) AS score
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
                FROM coffee_beans_with_origin cb
            ) cb
            WHERE cb.rn = 1
        )
        SELECT DISTINCT
            sb.id as bean_id, sb.name, sb.roaster, sb.url, sb.is_single_origin,
            sb.roast_level, sb.roast_profile, sb.weight,
            {f'''CASE WHEN '{convert_to_currency.upper()}' = 'USD' THEN sb.price_usd WHEN sb.price_usd IS NOT NULL AND '{convert_to_currency.upper()}' != 'USD' THEN sb.price_usd * COALESCE((SELECT rate FROM currency_rates cr WHERE cr.base_currency = 'USD' AND cr.target_currency = '{convert_to_currency.upper()}' ORDER BY cr.fetched_at DESC LIMIT 1), 1.0) ELSE sb.price END''' if convert_to_currency else "sb.price"} as price,
            {f"'{convert_to_currency.upper()}'" if convert_to_currency else "sb.currency"} as currency,
            sb.price as original_price, sb.currency as original_currency,
            {f"sb.currency != '{convert_to_currency.upper()}'" if convert_to_currency else "FALSE"} as price_converted,
            sb.is_decaf, sb.cupping_score,

            -- === START OF CHANGE ===
            -- This subquery transforms the tasting_notes array.
            -- It unnests the notes, joins with the categories table,
            -- and re-aggregates the result into a list of structs.
            (
                SELECT list(struct_pack(note := u.note, primary_category := tnc.primary_category))
                FROM unnest(sb.tasting_notes) AS u(note)
                LEFT JOIN tasting_notes_categories AS tnc ON u.note = tnc.tasting_note
            ) AS tasting_notes_with_categories,
            -- === END OF CHANGE ===

            sb.description, sb.in_stock, sb.scraped_at, sb.scraper_version, sb.image_url,
            sb.clean_url_slug, sb.bean_url_path, sb.price_paid_for_green_coffee,
            sb.currency_of_price_paid_for_green_coffee, sb.harvest_date, sb.date_added,
            rwl.roaster_country_code,
            FIRST_VALUE(sb.country) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as country,
            FIRST_VALUE(sb.region) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as region,
            FIRST_VALUE(sb.producer) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as producer,
            FIRST_VALUE(sb.farm) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as farm,
            FIRST_VALUE(sb.elevation_min) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as elevation_min,
            FIRST_VALUE(sb.elevation_max) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as elevation_max,
            FIRST_VALUE(sb.process) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as process,
            FIRST_VALUE(sb.variety) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as variety,
            FIRST_VALUE(sb.country_full_name) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as country_full_name,
            sb.score
        FROM scored_beans sb
        LEFT JOIN roasters_with_location rwl ON sb.roaster = rwl.name
        {filter_clause.replace("score", "sb.score")}
        ORDER BY {order_by_clause}
        LIMIT ? OFFSET ?
    """

    # Use final_params and add the pagination parameters at the end
    results = conn.execute(main_query, final_params + [per_page, offset]).fetchall()

    columns = [
        "bean_id",
        "name",
        "roaster",
        "url",
        "is_single_origin",
        "roast_level",
        "roast_profile",
        "weight",
        "price",
        "currency",
        "original_price",
        "original_currency",
        "price_converted",
        "is_decaf",
        "cupping_score",
        "tasting_notes_with_categories",
        "description",
        "in_stock",
        "scraped_at",
        "scraper_version",
        "image_url",
        "clean_url_slug",
        "bean_url_path",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
        "harvest_date",
        "date_added",
        "roaster_country_code",
        "country",
        "region",
        "producer",
        "farm",
        "elevation_min",
        "elevation_max",
        "process",
        "variety",
        "country_full_name",
        "score",
    ]

    coffee_beans = []
    for row in results:
        bean_dict = dict(zip(columns, row))
        # Rename bean_id to id for API consistency
        bean_dict["id"] = bean_dict.pop("bean_id")
        # Rename the key to match the expected API schema field 'tasting_notes'
        bean_dict["tasting_notes"] = bean_dict.pop("tasting_notes_with_categories")

        # Fetch all origins for this bean
        origins_query = """
            SELECT o.country, o.region, o.producer, o.farm, o.elevation_min, o.elevation_max,
                   o.process, o.variety, o.harvest_date, o.latitude, o.longitude,
                   cc.name as country_full_name
            FROM origins o
            LEFT JOIN country_codes cc ON cc.alpha_2 = o.country
            WHERE o.bean_id = ?
            ORDER BY o.id
        """
        origins_results = conn.execute(origins_query, [bean_dict["id"]]).fetchall()

        # Convert origins to list of APIBean objects
        origins = []
        for origin_row in origins_results:
            origin_data = {
                "country": origin_row[0] if origin_row[0] and origin_row[0].strip() else None,
                "region": origin_row[1] if origin_row[1] and origin_row[1].strip() else None,
                "producer": origin_row[2] if origin_row[2] and origin_row[2].strip() else None,
                "farm": origin_row[3] if origin_row[3] and origin_row[3].strip() else None,
                "elevation_min": origin_row[4] or 0,
                "elevation_max": origin_row[5] or 0,
                "process": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
                "variety": origin_row[7] if origin_row[7] and origin_row[7].strip() else None,
                "harvest_date": origin_row[8],
                "latitude": origin_row[9] or 0.0,
                "longitude": origin_row[10] or 0.0,
                "country_full_name": origin_row[11] if origin_row[11] and origin_row[11].strip() else None,
            }
            origins.append(APIBean(**origin_data))

        bean_dict["origins"] = origins

        # Remove flattened origin fields since we now have origins array
        fields_to_remove = [
            "country",
            "region",
            "producer",
            "farm",
            "elevation",
            "process",
            "variety",
            "latitude",
            "longitude",
            "filename",
        ]
        for field in fields_to_remove:
            bean_dict.pop(field, None)

        # Use bean_url_path directly from database, no need to generate
        if not bean_dict.get("bean_url_path"):
            bean_dict["bean_url_path"] = ""

        # Round price to 2 decimal places if it exists
        if bean_dict.get("price") is not None:
            bean_dict["price"] = round(bean_dict["price"], 2)

        # Create APISearchResult object
        search_result = APISearchResult(**bean_dict)
        coffee_beans.append(search_result)

    # Create pagination info
    from kissaten.schemas.search import PaginationInfo

    pagination = PaginationInfo(
        page=page,
        per_page=per_page,
        total_items=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

    return APIResponse.success_response(
        data=coffee_beans,
        pagination=pagination,
        metadata={
            "total_results": total_count,
            "max_possible_score": max_possible_score,
            "search_query": query,
            "tasting_notes_query": tasting_notes_query,
            "currency_conversion": {
                "enabled": convert_to_currency is not None,
                "target_currency": convert_to_currency.upper() if convert_to_currency else None,
                "converted_results": sum(1 for bean in coffee_beans if getattr(bean, "price_converted", False)),
            }
            if convert_to_currency
            else None,
        },
    )


@app.get("/v1/roasters", response_model=APIResponse[list[dict]])
@cached(ttl=600, cache=SimpleMemoryCache)
async def get_roasters():
    """Get all roasters with their coffee bean counts and location codes for client-side filtering."""

    # Build base query
    query = """
        SELECT
            r.id, r.name, r.slug, r.website, r.location, r.email, r.active,
            r.last_scraped, r.total_beans_scraped,
            COUNT(cb.id) as current_beans_count
        FROM roasters r
        LEFT JOIN coffee_beans cb ON r.name = cb.roaster
        GROUP BY r.id, r.name, r.slug, r.website, r.location, r.email, r.active, r.last_scraped, r.total_beans_scraped
        ORDER BY r.name COLLATE NOCASE
    """

    results = conn.execute(query).fetchall()

    # Get scraper registry to map roaster names to location codes
    registry = get_registry()
    roaster_to_location_codes = {}

    for scraper_info in registry.list_scrapers():
        location_codes = get_hierarchical_location_codes(scraper_info.country)
        roaster_to_location_codes[scraper_info.roaster_name] = location_codes

    roasters = []
    for row in results:
        roaster_name = row[1]
        location_codes = roaster_to_location_codes.get(roaster_name, [])

        roaster_dict = {
            "id": row[0],
            "name": roaster_name,
            "slug": row[2],
            "website": row[3],
            "location": row[4],
            "email": row[5],
            "active": row[6],
            "last_scraped": row[7],
            "total_beans_scraped": row[8],
            "current_beans_count": row[9],
            "location_codes": location_codes,  # New field for client-side filtering
        }
        roasters.append(roaster_dict)

    metadata = {
        "total_roasters": len(roasters),
        "has_location_codes": True,
        "description": "Location codes included for client-side filtering",
    }

    return APIResponse.success_response(data=roasters, metadata=metadata)


@app.get("/v1/roaster-locations", response_model=APIResponse[list[dict]])
@cached(ttl=600, cache=SimpleMemoryCache)
async def get_roaster_locations():
    """Get all available roaster location codes with hierarchical roaster counts."""
    try:
        # Get all location codes
        location_codes_query = """
            SELECT rlc.code, rlc.location, rlc.region
            FROM roaster_location_codes rlc
            ORDER BY rlc.location
        """
        location_results = conn.execute(location_codes_query).fetchall()

        # Get all roasters with their country information from registry
        registry = get_registry()
        roaster_countries = {}
        for scraper_info in registry.list_scrapers():
            roaster_countries[scraper_info.roaster_name] = scraper_info.country

        locations = []
        for code, location, region in location_results:
            # Count roasters that belong to this location hierarchically
            roaster_count = 0

            # For each roaster, check if it belongs to this location code
            for roaster_name, roaster_country in roaster_countries.items():
                # Get hierarchical codes for this roaster's country
                roaster_location_codes = get_hierarchical_location_codes(roaster_country)
                if code in roaster_location_codes:
                    roaster_count += 1

            # Determine location type
            location_type = "country"
            if code in ["XE", "EU"]:
                location_type = "region"

            # Get list of included countries for regional codes
            included_countries = []
            if code == "XE":  # Europe
                included_countries = ["GB", "FR", "DE", "IT", "NL", "PL", "ES", "SE"]
            elif code == "EU":  # European Union
                included_countries = ["FR", "DE", "IT", "NL", "PL", "ES", "SE"]

            location_data = {
                "code": code,
                "location": location,
                "region": region,
                "roaster_count": roaster_count,
                "location_type": location_type,
                "included_countries": included_countries,
            }

            locations.append(location_data)

        # Sort by roaster count (descending), then by location name
        locations.sort(key=lambda x: (-x["roaster_count"], x["location"]))

        return APIResponse(
            success=True,
            data=locations,
            message=f"Retrieved {len(locations)} roaster locations with hierarchical counts",
            pagination=None,
            metadata={
                "count": len(locations),
                "hierarchical": True,
                "description": "Roaster counts include hierarchical relationships "
                + "(e.g., UK roasters count towards both GB and XE)",
            },
        )

    except Exception as e:
        print(f"Error retrieving roaster locations: {e}")
        return APIResponse(
            success=False,
            data=[],
            message=f"Error retrieving roaster locations: {str(e)}",
            pagination=None,
            metadata={},
        )


@app.get("/v1/countries", response_model=APIResponse[list[dict]])
@cached(ttl=600, cache=SimpleMemoryCache)
async def get_countries():
    """Get all coffee origin countries with bean counts and full country names."""
    query = """
        SELECT
            o.country,
            cc.name as country_full_name,
            COUNT(DISTINCT cb.id) as bean_count,
            COUNT(DISTINCT cb.roaster) as roaster_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        LEFT JOIN country_codes cc ON o.country = cc.alpha_2
        WHERE o.country IS NOT NULL AND o.country != ''
        GROUP BY o.country, cc.name
        ORDER BY bean_count DESC
    """

    results = conn.execute(query).fetchall()

    countries = []
    for row in results:
        country_dict = {
            "country_code": row[0],
            "country_name": row[1] or row[0],  # Fallback to code if name not found
            "bean_count": row[2],
            "roaster_count": row[3],
        }
        countries.append(country_dict)

    return APIResponse.success_response(data=countries)


@app.get("/v1/country-codes", response_model=APIResponse[list[dict]])
@cached(ttl=600, cache=SimpleMemoryCache)
async def get_country_codes():
    """Get all country codes with full details."""
    query = """
        SELECT
            name, alpha_2, alpha_3, country_code, region, sub_region
        FROM country_codes
        ORDER BY name
    """

    results = conn.execute(query).fetchall()

    country_codes = []
    for row in results:
        country_dict = {
            "name": row[0],
            "alpha_2": row[1],
            "alpha_3": row[2],
            "country_code": row[3],
            "region": row[4],
            "sub_region": row[5],
        }
        country_codes.append(country_dict)

    return APIResponse.success_response(data=country_codes)


@app.get("/v1/beans/{roaster_slug}/{bean_slug}", response_model=APIResponse[APICoffeeBean])
async def get_bean_by_slug(
    roaster_slug: str,
    bean_slug: str,
    convert_to_currency: str | None = Query(
        None, description="Convert prices to this currency code (e.g., EUR, GBP, JPY)"
    ),
):
    """Get a specific coffee bean by roaster slug and bean slug from URL-friendly paths."""

    expected_bean_url_path = f"/{roaster_slug}/{bean_slug}"

    # Query is updated to transform the tasting_notes array
    query = """
        SELECT DISTINCT
            cb.id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
            cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score,

            -- === START OF CHANGE ===
            (
                SELECT list(struct_pack(note := u.note, primary_category := tnc.primary_category))
                FROM unnest(cb.tasting_notes) AS u(note)
                LEFT JOIN tasting_notes_categories AS tnc ON u.note = tnc.tasting_note
            ) AS tasting_notes_with_categories,
            -- === END OF CHANGE ===

            cb.description, cb.in_stock,
            cb.scraped_at, cb.date_added, cb.scraper_version, cb.image_url, cb.clean_url_slug,
            cb.bean_url_path, cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
            rwl.roaster_country_code
        FROM coffee_beans cb
        LEFT JOIN roasters_with_location rwl ON cb.roaster = rwl.name
        WHERE cb.bean_url_path = ?
        ORDER BY cb.scraped_at DESC
        LIMIT 1
    """

    result = conn.execute(query, [expected_bean_url_path]).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail=f"Bean '{bean_slug}' not found for roaster '{roaster_slug}'")

    # Update the columns list to match the new query alias
    columns = [
        "id",
        "name",
        "roaster",
        "url",
        "is_single_origin",
        "roast_level",
        "roast_profile",
        "weight",
        "price",
        "currency",
        "is_decaf",
        "cupping_score",
        "tasting_notes_with_categories",  # Updated column name
        "description",
        "in_stock",
        "scraped_at",
        "date_added",
        "scraper_version",
        "image_url",
        "clean_url_slug",
        "bean_url_path",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
        "roaster_country_code",
    ]

    bean_data = dict(zip(columns, result))

    # Rename the key to match the expected Pydantic schema field 'tasting_notes'
    bean_data["tasting_notes"] = bean_data.pop("tasting_notes_with_categories")

    # Fetch all origins for this bean (this part is unchanged)
    origins_query = """
        SELECT o.country, o.region, o.producer, o.farm, o.elevation_min, o.elevation_max,
               o.process, o.variety, o.harvest_date, o.latitude, o.longitude,
               cc.name as country_full_name
        FROM origins o
        LEFT JOIN country_codes cc ON o.country = cc.alpha_2
        WHERE o.bean_id = ?
        ORDER BY o.id
    """
    origins_results = conn.execute(origins_query, [bean_data["id"]]).fetchall()

    origins = []
    for origin_row in origins_results:
        origin_data = {
            "country": origin_row[0] if origin_row[0] and origin_row[0].strip() else None,
            "region": origin_row[1] if origin_row[1] and origin_row[1].strip() else None,
            "producer": origin_row[2] if origin_row[2] and origin_row[2].strip() else None,
            "farm": origin_row[3] if origin_row[3] and origin_row[3].strip() else None,
            "elevation_min": origin_row[4] or 0,
            "elevation_max": origin_row[5] or origin_row[4] or 0,
            "process": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
            "variety": origin_row[7] if origin_row[7] and origin_row[7].strip() else None,
            "harvest_date": origin_row[8],
            "latitude": origin_row[9] or 0.0,
            "longitude": origin_row[10] or 0.0,
            "country_full_name": origin_row[11],
        }
        origins.append(APIBean(**origin_data))

    bean_data["origins"] = origins

    # Set default for bean_url_path if needed
    if not bean_data.get("bean_url_path"):
        bean_data["bean_url_path"] = ""

    # Handle currency conversion (this part is unchanged)
    if convert_to_currency and convert_to_currency.upper() != bean_data.get("currency", "").upper():
        original_price = bean_data.get("price")
        original_currency = bean_data.get("currency")
        if original_price and original_currency:
            converted_price = convert_price(original_price, original_currency.upper(), convert_to_currency.upper())
            if converted_price is not None:
                bean_data["original_price"] = original_price
                bean_data["original_currency"] = original_currency
                bean_data["price"] = round(converted_price, 2)
                bean_data["currency"] = convert_to_currency.upper()
                bean_data["price_converted"] = True
            else:
                bean_data["price_converted"] = False
        else:
            bean_data["price_converted"] = False
    else:
        bean_data["price_converted"] = False

    # Convert to APICoffeeBean object
    coffee_bean = APICoffeeBean(**bean_data)

    return APIResponse.success_response(data=coffee_bean)

@app.get("/v1/beans/{roaster_slug}/{bean_slug}/recommendations", response_model=APIResponse[list[APIRecommendation]])
async def get_bean_recommendations_by_slug(
    roaster_slug: str,
    bean_slug: str,
    limit: int = Query(6, ge=1, le=20, description="Number of recommendations to return"),
    convert_to_currency: str | None = Query(
        None, description="Convert prices to this currency code (e.g., EUR, GBP, JPY)"
    ),
):
    """Get recommendations for a specific bean by roaster slug and bean slug."""

    # First get the target bean data
    try:
        bean_response = await get_bean_by_slug(roaster_slug, bean_slug, convert_to_currency)
        if not bean_response.data:
            raise HTTPException(status_code=404, detail="Bean not found")

        target_bean = bean_response.data

        # Now use the existing recommendation logic with the bean data
        target_notes = [note.note for note in target_bean.tasting_notes] or []
        target_roast = target_bean.roast_level
        target_roaster = target_bean.roaster
        target_id = target_bean.id

        # Use deduplication in recommendation query to get only latest versions
        recommendations_query = """
            WITH deduplicated_beans AS (
                SELECT cb.*,
                       ROW_NUMBER() OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as rn
                FROM coffee_beans cb
            ),
            similarity_scores AS (
                SELECT
                    cb.id,
                    cb.clean_url_slug,
                    -- Calculate similarity score based on available data
                    (
                        -- Tasting notes overlap (highest weight)
                        CASE
                            WHEN ? IS NOT NULL AND cb.tasting_notes IS NOT NULL THEN
                                (len(list_intersect(cb.tasting_notes, ?)) * 4.0)
                            ELSE 0
                        END +
                        -- Same roast level (medium weight)
                        CASE WHEN cb.roast_level = ? AND ? IS NOT NULL THEN 2.0 ELSE 0 END +
                        -- Different roaster bonus (encourage diversity)
                        CASE WHEN cb.roaster != ? THEN 1.0 ELSE 0 END
                    ) as similarity_score
                FROM deduplicated_beans cb
                WHERE cb.rn = 1  -- Only latest version of each bean
            )
            SELECT
                cb.id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
                cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
                cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description, cb.in_stock,
                cb.scraped_at, cb.scraper_version, cb.image_url, cb.clean_url_slug,
                cb.bean_url_path, cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
                ss.similarity_score
            FROM deduplicated_beans cb
            JOIN similarity_scores ss ON cb.id = ss.id
            WHERE cb.rn = 1 AND cb.id != ? AND ss.similarity_score > 0  -- Only latest versions with similarity
            ORDER BY ss.similarity_score DESC, cb.name ASC
            LIMIT ?
        """

        params = [
            target_notes,
            target_notes,  # For tasting notes overlap check and calculation
            target_roast,
            target_roast,  # For roast level comparison
            target_roaster,  # For roaster diversity
            target_id,  # Exclude original bean in final WHERE clause
            limit,  # Limit results
        ]

        results = conn.execute(recommendations_query, params).fetchall()

        columns = [
            "id",
            "name",
            "roaster",
            "url",
            "is_single_origin",
            "roast_level",
            "roast_profile",
            "weight",
            "price",
            "currency",
            "is_decaf",
            "cupping_score",
            "tasting_notes",
            "description",
            "in_stock",
            "scraped_at",
            "scraper_version",
            "image_url",
            "clean_url_slug",
            "bean_url_path",
            "price_paid_for_green_coffee",
            "currency_of_price_paid_for_green_coffee",
            "similarity_score",
        ]

        recommendations = []
        for row in results:
            bean_data = dict(zip(columns, row))

            # Set default for bean_url_path if needed
            if not bean_data.get("bean_url_path"):
                bean_data["bean_url_path"] = ""

            # Fetch origins for this recommended bean
            origins_query = """
                SELECT o.country, o.region, o.producer, o.farm, o.elevation_min, o.elevation_max,
                       o.process, o.variety, o.harvest_date, o.latitude, o.longitude,
                       cc.name as country_full_name
                FROM origins o
                LEFT JOIN country_codes cc ON o.country = cc.alpha_2
                WHERE o.bean_id = ?
                ORDER BY o.id
            """
            origins_results = conn.execute(origins_query, [bean_data["id"]]).fetchall()

            # Convert origins to list of APIBean objects
            origins = []
            for origin_row in origins_results:
                origin_data = {
                    "country": origin_row[0] if origin_row[0] and origin_row[0].strip() else None,
                    "region": origin_row[1] if origin_row[1] and origin_row[1].strip() else None,
                    "producer": origin_row[2] if origin_row[2] and origin_row[2].strip() else None,
                    "farm": origin_row[3] if origin_row[3] and origin_row[3].strip() else None,
                    "elevation_min": origin_row[4] or 0,
                    "elevation_max": origin_row[5] or 0,
                    "process": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
                    "variety": origin_row[7] if origin_row[7] and origin_row[7].strip() else None,
                    "harvest_date": origin_row[8],
                    "latitude": origin_row[9] or 0.0,
                    "longitude": origin_row[10],
                    "country_full_name": origin_row[11],
                }
                origins.append(APIBean(**origin_data))

            bean_data["origins"] = origins

            # Handle currency conversion if requested
            if convert_to_currency and convert_to_currency.upper() != bean_data.get("currency", "").upper():
                original_price = bean_data.get("price")
                original_currency = bean_data.get("currency")

                if original_price and original_currency:
                    converted_price = convert_price(
                        original_price, original_currency.upper(), convert_to_currency.upper()
                    )

                    if converted_price is not None:
                        # Store original price info
                        bean_data["original_price"] = original_price
                        bean_data["original_currency"] = original_currency
                        # Update price and currency
                        bean_data["price"] = round(converted_price, 2)
                        bean_data["currency"] = convert_to_currency.upper()
                        bean_data["price_converted"] = True
                    else:
                        bean_data["price_converted"] = False
                else:
                    bean_data["price_converted"] = False
            else:
                bean_data["price_converted"] = False

            # Create APIRecommendation object
            recommendation = APIRecommendation(**bean_data)
            recommendations.append(recommendation)

        return APIResponse.success_response(
            data=recommendations,
            metadata={
                "target_bean_roaster": roaster_slug,
                "target_bean_slug": bean_slug,
                "total_recommendations": len(recommendations),
                "recommendation_algorithm": "tasting_notes_and_attributes_similarity",
                "currency_conversion": {
                    "enabled": convert_to_currency is not None,
                    "target_currency": convert_to_currency.upper() if convert_to_currency else None,
                    "converted_results": sum(1 for rec in recommendations if getattr(rec, "price_converted", False)),
                }
                if convert_to_currency
                else None,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@app.get("/v1/processes", response_model=APIResponse[dict])
@cached(ttl=600, cache=SimpleMemoryCache)
async def get_processes():
    """Get all coffee processing methods grouped by categories."""

    # Get all processes with their bean counts
    query = """
        SELECT
            o.process_common_name,
            STRING_AGG(DISTINCT o.process, ' ') as process_original_names,
            COUNT(DISTINCT cb.id) as bean_count,
            COUNT(DISTINCT cb.roaster) as roaster_count,
            COUNT(DISTINCT o.country) as country_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.process_common_name IS NOT NULL AND o.process_common_name != ''
        GROUP BY o.process_common_name
        ORDER BY bean_count DESC
    """

    results = conn.execute(query).fetchall()

    # Group processes by category
    categories = {
        "washed": {"name": "Washed Processes", "processes": []},
        "natural": {"name": "Natural Processes", "processes": []},
        "anaerobic": {"name": "Anaerobic Processes", "processes": []},
        "honey": {"name": "Honey Processes", "processes": []},
        "fermentation": {"name": "Fermentation Processes", "processes": []},
        "decaf": {"name": "Decaf Processes", "processes": []},
        "experimental": {"name": "Experimental Processes", "processes": []},
        "other": {"name": "Other Processes", "processes": []},
    }

    for row in results:
        process_name, process_original_names, bean_count, roaster_count, country_count = row
        category = categorize_process(process_name)
        process_slug = normalize_process_name(process_name)

        # Get the countries for this process with bean counts
        countries_query = """
            SELECT DISTINCT
                o.country,
                cc.name as country_full_name,
                COUNT(DISTINCT cb.id) as bean_count
            FROM origins o
            LEFT JOIN country_codes cc ON o.country = cc.alpha_2
            JOIN coffee_beans cb ON o.bean_id = cb.id
            WHERE o.process_common_name = ? AND o.country IS NOT NULL AND o.country != ''
            GROUP BY o.country, cc.name
            ORDER BY bean_count DESC, cc.name, o.country
        """

        countries_results = conn.execute(countries_query, [process_name]).fetchall()
        countries = [
            {
                "country_code": country_row[0],
                "country_name": country_row[1] or country_row[0],
                "bean_count": country_row[2],
            }
            for country_row in countries_results
        ]

        process_data = {
            "name": process_name,
            "original_names": process_original_names,
            "slug": process_slug,
            "bean_count": bean_count,
            "roaster_count": roaster_count,
            "country_count": country_count,
            "countries": countries,
            "category": category,
        }

        categories[category]["processes"].append(process_data)

    # Calculate category totals
    for category_data in categories.values():
        total_beans = sum(p["bean_count"] for p in category_data["processes"])
        category_data["total_beans"] = total_beans

    return APIResponse.success_response(data=categories, metadata={"total_processes": len(results)})


@app.get("/v1/processes/{process_slug}", response_model=APIResponse[dict])
async def get_process_details(process_slug: str, convert_to_currency: str = "EUR"):
    """Get details for a specific coffee processing method."""

    # First, find the actual process_common_name from the slug
    # Use the process_common_name with the highest bean count if multiple have the same slug
    query = """
        SELECT o.process_common_name, o.process, COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.process_common_name IS NOT NULL AND o.process_common_name != ''
        GROUP BY o.process_common_name, o.process
        ORDER BY bean_count DESC, o.process_common_name
    """

    processes = conn.execute(query).fetchall()
    actual_process_common_name = None

    for process_common_name, process_name, bean_count in processes:
        if (normalize_process_name(process_common_name) == process_slug) or (
            process_name and normalize_process_name(process_name) == process_slug
        ):
            actual_process_common_name = process_common_name
            break

    if not actual_process_common_name:
        raise HTTPException(status_code=404, detail=f"Process '{process_slug}' not found")

    # Get detailed statistics for this process_common_name
    stats_query = """
        SELECT
            COUNT(DISTINCT cb.id) as total_beans,
            COUNT(DISTINCT cb.roaster) as total_roasters,
            COUNT(DISTINCT o.country) as total_countries,
            MEDIAN(cb.price_usd/cb.weight)*100 as avg_price
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.process_common_name = ?
    """

    stats_result = conn.execute(stats_query, [actual_process_common_name]).fetchone()
    stats = stats_result if stats_result else (0, 0, 0, 0)

    # Get top countries for this process_common_name
    countries_query = """
        SELECT
            o.country,
            cc.name as country_full_name,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        LEFT JOIN country_codes cc ON o.country = cc.alpha_2
        WHERE o.process_common_name = ?
        GROUP BY o.country, cc.name
        ORDER BY bean_count DESC
        LIMIT 6
    """

    countries = conn.execute(countries_query, [actual_process_common_name]).fetchall()

    # Get top roasters for this process_common_name
    roasters_query = """
        SELECT
            cb.roaster,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.process_common_name = ?
        GROUP BY cb.roaster
        ORDER BY bean_count DESC
        LIMIT 8
    """

    roasters = conn.execute(roasters_query, [actual_process_common_name]).fetchall()

    # Get most common tasting notes for this process_common_name
    tasting_notes_query = """
        SELECT
            note,
            COUNT(*) as frequency
        FROM (
            SELECT unnest(cb.tasting_notes) as note
            FROM origins o
            JOIN coffee_beans cb ON o.bean_id = cb.id
            WHERE o.process_common_name = ? AND cb.tasting_notes IS NOT NULL AND array_length(cb.tasting_notes) > 0
        ) t
        GROUP BY note
        ORDER BY frequency DESC
        LIMIT 10
    """

    tasting_notes = conn.execute(tasting_notes_query, [actual_process_common_name]).fetchall()

    # Get all original process names that map to this common name (for additional context)
    original_processes_query = """
        SELECT DISTINCT o.process, COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.process_common_name = ? AND o.process IS NOT NULL AND o.process != ''
        GROUP BY o.process
        ORDER BY bean_count DESC
    """

    original_processes = conn.execute(original_processes_query, [actual_process_common_name]).fetchall()

    avg_price = stats[3] if stats[3] else 0
    converted_avg_price = convert_price(avg_price, "USD", convert_to_currency)

    # Build response
    process_details = {
        "name": actual_process_common_name,
        "slug": process_slug,
        "category": categorize_process(actual_process_common_name),
        "original_names": [{"name": row[0], "bean_count": row[1]} for row in original_processes],
        "statistics": {
            "total_beans": stats[0] if stats[0] else 0,
            "total_roasters": stats[1] if stats[1] else 0,
            "total_countries": stats[2] if stats[2] else 0,
            "avg_price": round(converted_avg_price if converted_avg_price is not None else 0, 2) if stats[3] else 0,
        },
        "top_countries": [
            {"country_code": row[0], "country_name": row[1] or row[0], "bean_count": row[2]} for row in countries
        ],
        "top_roasters": [{"name": row[0], "bean_count": row[1]} for row in roasters],
        "common_tasting_notes": [{"note": row[0], "frequency": row[1]} for row in tasting_notes],
    }

    return APIResponse.success_response(data=process_details)


@app.get("/v1/processes/{process_slug}/beans", response_model=APIResponse[list[APISearchResult]])
async def get_process_beans(
    process_slug: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Items per page"),
    sort_by: str = Query("name", description="Sort field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
    convert_to_currency: str | None = Query(
        None, description="Convert prices to this currency code (e.g., EUR, GBP, JPY)"
    ),
):
    """Get coffee beans that use a specific processing method."""

    # First, find the actual process name from the slug
    # Use the process with the highest bean count if multiple processes have the same slug
    query = """
        SELECT o.process_common_name, o.process, COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.process_common_name IS NOT NULL AND o.process_common_name != ''
        GROUP BY o.process_common_name, o.process
        ORDER BY bean_count DESC, o.process_common_name
    """

    processes = conn.execute(query).fetchall()
    actual_process = None

    for process_common_name, process_name, bean_count in processes:
        if normalize_process_name(process_common_name) == process_slug or (
            process_name and normalize_process_name(process_name) == process_slug
        ):
            actual_process = process_common_name
            break

    if not actual_process:
        raise HTTPException(status_code=404, detail=f"Process '{process_slug}' not found")

    # Get total count for pagination
    count_query = """
        SELECT COUNT(DISTINCT cb.clean_url_slug)
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.process_common_name = ?
    """

    count_result = conn.execute(count_query, [actual_process]).fetchone()
    total_count = count_result[0] if count_result else 0

    # Calculate pagination
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page

    # Validate sort parameters
    sort_field_mapping = {
        "name": "cb.name",
        "roaster": "cb.roaster",
        "price": "cb.price_usd",
        "weight": "cb.weight",
        "scraped_at": "cb.scraped_at",
    }

    if sort_by in sort_field_mapping:
        sort_by = sort_field_mapping[sort_by]
    else:
        sort_by = "cb.name"

    if sort_order.lower() not in ["asc", "desc"]:
        sort_order = "asc"

    # Get beans for this process (deduplicated by clean_url_slug)
    main_query = f"""
        SELECT DISTINCT
            cb.id as bean_id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
            cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score,

            (
                SELECT list(struct_pack(note := u.note, primary_category := tnc.primary_category))
                FROM unnest(cb.tasting_notes) AS u(note)
                LEFT JOIN tasting_notes_categories AS tnc ON u.note = tnc.tasting_note
            ) AS tasting_notes_with_categories,

            cb.description, cb.in_stock,
            cb.scraped_at, cb.scraper_version, cb.image_url, cb.clean_url_slug,
            cb.bean_url_path, cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
            cb.roaster_country_code
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
            FROM coffee_beans cb_inner
            LEFT JOIN roasters_with_location rwl ON cb_inner.roaster = rwl.name
            WHERE cb_inner.id IN (
                SELECT DISTINCT cb2.id
                FROM origins o2
                JOIN coffee_beans cb2 ON o2.bean_id = cb2.id
                WHERE o2.process_common_name = ?
            )
        ) cb
        WHERE cb.rn = 1
        ORDER BY {sort_by} {sort_order.upper()}
        LIMIT ? OFFSET ?
    """

    results = conn.execute(main_query, [actual_process, per_page, offset]).fetchall()

    # Convert results to API format
    columns = [
        "id",
        "name",
        "roaster",
        "url",
        "is_single_origin",
        "roast_level",
        "roast_profile",
        "weight",
        "price",
        "currency",
        "is_decaf",
        "cupping_score",
        "tasting_notes_with_categories",
        "description",
        "in_stock",
        "scraped_at",
        "scraper_version",
        "image_url",
        "clean_url_slug",
        "bean_url_path",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
        "roaster_country_code",
    ]

    coffee_beans = []
    for row in results:
        bean_dict = dict(zip(columns, row))
        # Rename the key to match the expected Pydantic schema field 'tasting_notes'
        bean_dict["tasting_notes"] = bean_dict.pop("tasting_notes_with_categories")

        # Fetch origins for this bean
        origins_query = """
            SELECT o.country, o.region, o.producer, o.farm, o.elevation_min, o.elevation_max,
                   o.process, o.variety, o.harvest_date, o.latitude, o.longitude,
                   cc.name as country_full_name
            FROM origins o
            LEFT JOIN country_codes cc ON o.country = cc.alpha_2
            WHERE o.bean_id = ?
            ORDER BY o.id
        """
        origins_results = conn.execute(origins_query, [bean_dict["id"]]).fetchall()

        # Convert origins to APIBean objects
        origins = []
        for origin_row in origins_results:
            origin_data = {
                "country": origin_row[0] if origin_row[0] and origin_row[0].strip() else None,
                "region": origin_row[1] if origin_row[1] and origin_row[1].strip() else None,
                "producer": origin_row[2] if origin_row[2] and origin_row[2].strip() else None,
                "farm": origin_row[3] if origin_row[3] and origin_row[3].strip() else None,
                "elevation_min": origin_row[4],
                "elevation_max": origin_row[5] or 0,
                "process": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
                "variety": origin_row[7] if origin_row[7] and origin_row[7].strip() else None,
                "harvest_date": origin_row[8],
                "latitude": origin_row[9] or 0.0,
                "longitude": origin_row[10] or 0.0,
                "country_full_name": origin_row[11],
            }
            origins.append(APIBean(**origin_data))

        bean_dict["origins"] = origins

        # Set default for bean_url_path if needed
        if not bean_dict.get("bean_url_path"):
            bean_dict["bean_url_path"] = ""

        # Handle currency conversion if requested
        if convert_to_currency and convert_to_currency.upper() != bean_dict.get("currency", "").upper():
            original_price = bean_dict.get("price")
            original_currency = bean_dict.get("currency")

            if original_price and original_currency:
                converted_price = convert_price(original_price, original_currency.upper(), convert_to_currency.upper())

                if converted_price is not None:
                    # Store original price info
                    bean_dict["original_price"] = original_price
                    bean_dict["original_currency"] = original_currency
                    # Update price and currency
                    bean_dict["price"] = round(converted_price, 2)
                    bean_dict["currency"] = convert_to_currency.upper()
                    bean_dict["price_converted"] = True
                else:
                    bean_dict["price_converted"] = False
            else:
                bean_dict["price_converted"] = False
        else:
            bean_dict["price_converted"] = False

        # Create APISearchResult object
        search_result = APISearchResult(**bean_dict)
        coffee_beans.append(search_result)

    # Create pagination info
    from kissaten.schemas.search import PaginationInfo

    pagination = PaginationInfo(
        page=page,
        per_page=per_page,
        total_items=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

    return APIResponse.success_response(
        data=coffee_beans,
        pagination=pagination,
        metadata={
            "process_name": actual_process,
            "process_slug": process_slug,
            "total_results": total_count,
            "currency_conversion": {
                "enabled": convert_to_currency is not None,
                "target_currency": convert_to_currency.upper() if convert_to_currency else None,
                "converted_results": sum(1 for bean in coffee_beans if getattr(bean, "price_converted", False)),
            }
            if convert_to_currency
            else None,
        },
    )


@app.get("/v1/varietals", response_model=APIResponse[dict])
@cached(ttl=600, cache=SimpleMemoryCache)
async def get_varietals():
    """Get all coffee varietals grouped by categories."""

    # Get all varietals with their bean counts
    query = """
        SELECT
            o.variety,
            COUNT(DISTINCT cb.id) as bean_count,
            COUNT(DISTINCT cb.roaster) as roaster_count,
            COUNT(DISTINCT o.country) as country_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.variety IS NOT NULL AND o.variety != ''
        GROUP BY o.variety
        ORDER BY bean_count DESC
    """

    results = conn.execute(query).fetchall()

    # Group varietals by category
    categories = {
        "typica": {"name": "Typica Family", "varietals": []},
        "bourbon": {"name": "Bourbon Family", "varietals": []},
        "heirloom": {"name": "Heirloom Varieties", "varietals": []},
        "geisha": {"name": "Geisha/Gesha Varieties", "varietals": []},
        "sl_varieties": {"name": "SL Varieties", "varietals": []},
        "hybrid": {"name": "Hybrid Varieties", "varietals": []},
        "large_bean": {"name": "Large Bean Varieties", "varietals": []},
        "arabica_other": {"name": "Other Arabica Varieties", "varietals": []},
        "other": {"name": "Other Varieties", "varietals": []},
    }

    for row in results:
        varietal_name, bean_count, roaster_count, country_count = row
        category = categorize_varietal(varietal_name)
        varietal_slug = normalize_varietal_name(varietal_name)

        # Get the countries for this varietal with bean counts
        countries_query = """
            SELECT DISTINCT
                o.country,
                cc.name as country_full_name,
                COUNT(DISTINCT cb.id) as bean_count
            FROM origins o
            LEFT JOIN country_codes cc ON o.country = cc.alpha_2
            JOIN coffee_beans cb ON o.bean_id = cb.id
            WHERE o.variety = ? AND o.country IS NOT NULL AND o.country != ''
            GROUP BY o.country, cc.name
            ORDER BY bean_count DESC, cc.name, o.country
            LIMIT 10
        """

        countries_results = conn.execute(countries_query, [varietal_name]).fetchall()
        countries = [
            {
                "country_code": country_row[0],
                "country_name": country_row[1] or country_row[0],
                "bean_count": country_row[2],
            }
            for country_row in countries_results
        ]

        varietal_data = {
            "name": varietal_name,
            "slug": varietal_slug,
            "bean_count": bean_count,
            "roaster_count": roaster_count,
            "country_count": country_count,
            "countries": countries,
            "category": category,
        }

        categories[category]["varietals"].append(varietal_data)

    # Calculate category totals
    for category_data in categories.values():
        total_beans = sum(v["bean_count"] for v in category_data["varietals"])
        category_data["total_beans"] = total_beans

    return APIResponse.success_response(data=categories, metadata={"total_varietals": len(results)})


@app.get("/v1/varietals/{varietal_slug}", response_model=APIResponse[dict])
async def get_varietal_details(varietal_slug: str, convert_to_currency: str = "EUR"):
    """Get details for a specific coffee varietal."""

    # First, find the actual varietal name from the slug
    # Use the varietal with the highest bean count if multiple varietals have the same slug
    query = """
        SELECT o.variety, COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.variety IS NOT NULL AND o.variety != ''
        GROUP BY o.variety
        ORDER BY bean_count DESC, o.variety
    """

    varietals = conn.execute(query).fetchall()
    actual_varietal = None

    for varietal_name, bean_count in varietals:
        if normalize_varietal_name(varietal_name) == varietal_slug:
            actual_varietal = varietal_name
            break

    if not actual_varietal:
        raise HTTPException(status_code=404, detail=f"Varietal '{varietal_slug}' not found")

    # Get detailed statistics for this varietal
    stats_query = """
        SELECT
            COUNT(DISTINCT cb.id) as total_beans,
            COUNT(DISTINCT cb.roaster) as total_roasters,
            COUNT(DISTINCT o.country) as total_countries,
            MEDIAN(cb.price_usd/cb.weight)*100 as avg_price,
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.variety = ?
    """

    stats_result = conn.execute(stats_query, [actual_varietal]).fetchone()
    stats = stats_result if stats_result else (0, 0, 0, 0)

    # Get top countries for this varietal
    countries_query = """
        SELECT
            o.country,
            cc.name as country_full_name,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        LEFT JOIN country_codes cc ON o.country = cc.alpha_2
        WHERE o.variety = ?
        GROUP BY o.country, cc.name
        ORDER BY bean_count DESC
        LIMIT 10
    """

    countries = conn.execute(countries_query, [actual_varietal]).fetchall()

    # Get top roasters for this varietal
    roasters_query = """
        SELECT
            cb.roaster,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.variety = ?
        GROUP BY cb.roaster
        ORDER BY bean_count DESC
        LIMIT 10
    """

    roasters = conn.execute(roasters_query, [actual_varietal]).fetchall()

    # Get most common tasting notes for this varietal
    tasting_notes_query = """
        SELECT
            note,
            COUNT(*) as frequency
        FROM (
            SELECT unnest(cb.tasting_notes) as note
            FROM origins o
            JOIN coffee_beans cb ON o.bean_id = cb.id
            WHERE o.variety = ? AND cb.tasting_notes IS NOT NULL AND array_length(cb.tasting_notes) > 0
        ) t
        GROUP BY note
        ORDER BY frequency DESC
        LIMIT 10
    """

    tasting_notes = conn.execute(tasting_notes_query, [actual_varietal]).fetchall()

    # Get most common processing methods for this varietal
    processing_methods_query = """
        SELECT
            o.process_common_name,
            COUNT(DISTINCT cb.id) as frequency
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.variety = ? AND o.process_common_name IS NOT NULL AND o.process_common_name != ''
        GROUP BY o.process_common_name
        ORDER BY frequency DESC
        LIMIT 8
    """

    processing_methods = conn.execute(processing_methods_query, [actual_varietal]).fetchall()
    converted_avg_price = convert_price(stats[3], "USD", convert_to_currency) if stats[3] else 0

    # Build response
    varietal_details = {
        "name": actual_varietal,
        "slug": varietal_slug,
        "category": categorize_varietal(actual_varietal),
        "statistics": {
            "total_beans": stats[0] if stats[0] else 0,
            "total_roasters": stats[1] if stats[1] else 0,
            "total_countries": stats[2] if stats[2] else 0,
            "avg_price": round(converted_avg_price if converted_avg_price is not None else 0, 2),
        },
        "top_countries": [
            {"country_code": row[0], "country_name": row[1] or row[0], "bean_count": row[2]} for row in countries
        ],
        "top_roasters": [{"name": row[0], "bean_count": row[1]} for row in roasters],
        "common_tasting_notes": [{"note": row[0], "frequency": row[1]} for row in tasting_notes],
        "common_processing_methods": [{"process": row[0], "frequency": row[1]} for row in processing_methods],
    }

    return APIResponse.success_response(data=varietal_details)


@app.get("/v1/varietals/{varietal_slug}/beans", response_model=APIResponse[list[APISearchResult]])
async def get_varietal_beans(
    varietal_slug: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Items per page"),
    sort_by: str = Query("name", description="Sort field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
    convert_to_currency: str | None = Query(
        None, description="Convert prices to this currency code (e.g., EUR, GBP, JPY)"
    ),
):
    """Get coffee beans of a specific varietal."""

    # First, find the actual varietal name from the slug
    # Use the varietal with the highest bean count if multiple varietals have the same slug
    query = """
        SELECT o.variety, COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.variety IS NOT NULL AND o.variety != ''
        GROUP BY o.variety
        ORDER BY bean_count DESC, o.variety
    """

    varietals = conn.execute(query).fetchall()
    actual_varietal = None

    for varietal_name, bean_count in varietals:
        if normalize_varietal_name(varietal_name) == varietal_slug:
            actual_varietal = varietal_name
            break

    if not actual_varietal:
        raise HTTPException(status_code=404, detail=f"Varietal '{varietal_slug}' not found")

    # Get total count for pagination
    count_query = """
        SELECT COUNT(DISTINCT cb.clean_url_slug)
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.variety = ?
    """

    count_result = conn.execute(count_query, [actual_varietal]).fetchone()
    total_count = count_result[0] if count_result else 0

    # Calculate pagination
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page

    # Validate sort parameters
    sort_field_mapping = {
        "name": "cb.name",
        "roaster": "cb.roaster",
        "price": "cb.price_usd",
        "weight": "cb.weight",
        "scraped_at": "cb.scraped_at",
    }

    if sort_by in sort_field_mapping:
        sort_by = sort_field_mapping[sort_by]
    else:
        sort_by = "cb.name"

    if sort_order.lower() not in ["asc", "desc"]:
        sort_order = "asc"

    # Get beans for this varietal (deduplicated by clean_url_slug)
    main_query = f"""
        SELECT DISTINCT
            cb.id as bean_id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
            cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score,
            (
                SELECT list(struct_pack(note := u.note, primary_category := tnc.primary_category))
                FROM unnest(cb.tasting_notes) AS u(note)
                LEFT JOIN tasting_notes_categories AS tnc ON u.note = tnc.tasting_note
            ) AS tasting_notes_with_categories,
            cb.description, cb.in_stock,
            cb.scraped_at, cb.scraper_version, cb.image_url, cb.clean_url_slug,
            cb.bean_url_path, cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
            cb.roaster_country_code
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
            FROM coffee_beans cb_inner
            LEFT JOIN roasters_with_location rwl ON cb_inner.roaster = rwl.name
            WHERE cb_inner.id IN (
                SELECT DISTINCT cb2.id
                FROM origins o2
                JOIN coffee_beans cb2 ON o2.bean_id = cb2.id
                WHERE o2.variety = ?
            )
        ) cb
        WHERE cb.rn = 1
        ORDER BY {sort_by} {sort_order.upper()}
        LIMIT ? OFFSET ?
    """

    results = conn.execute(main_query, [actual_varietal, per_page, offset]).fetchall()

    # Convert results to API format
    columns = [
        "id",
        "name",
        "roaster",
        "url",
        "is_single_origin",
        "roast_level",
        "roast_profile",
        "weight",
        "price",
        "currency",
        "is_decaf",
        "cupping_score",
        "tasting_notes_with_categories",
        "description",
        "in_stock",
        "scraped_at",
        "scraper_version",
        "image_url",
        "clean_url_slug",
        "bean_url_path",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
        "roaster_country_code",
    ]

    coffee_beans = []
    for row in results:
        bean_dict = dict(zip(columns, row))
        # Rename the key to match the expected Pydantic schema field 'tasting_notes'
        bean_dict["tasting_notes"] = bean_dict.pop("tasting_notes_with_categories")

        # Fetch origins for this bean
        origins_query = """
            SELECT o.country, o.region, o.producer, o.farm, o.elevation_min, o.elevation_max,
                   o.process, o.variety, o.harvest_date, o.latitude, o.longitude,
                   cc.name as country_full_name
            FROM origins o
            LEFT JOIN country_codes cc ON o.country = cc.alpha_2
            WHERE o.bean_id = ?
            ORDER BY o.id
        """
        origins_results = conn.execute(origins_query, [bean_dict["id"]]).fetchall()

        # Convert origins to APIBean objects
        origins = []
        for origin_row in origins_results:
            origin_data = {
                "country": origin_row[0] if origin_row[0] and origin_row[0].strip() else None,
                "region": origin_row[1] if origin_row[1] and origin_row[1].strip() else None,
                "producer": origin_row[2] if origin_row[2] and origin_row[2].strip() else None,
                "farm": origin_row[3] if origin_row[3] and origin_row[3].strip() else None,
                "elevation_min": origin_row[4],
                "elevation_max": origin_row[5] or 0,
                "process": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
                "variety": origin_row[7] if origin_row[7] and origin_row[7].strip() else None,
                "harvest_date": origin_row[8],
                "latitude": origin_row[9] or 0.0,
                "longitude": origin_row[10] or 0.0,
                "country_full_name": origin_row[11],
            }
            origins.append(APIBean(**origin_data))

        bean_dict["origins"] = origins

        # Set default for bean_url_path if needed
        if not bean_dict.get("bean_url_path"):
            bean_dict["bean_url_path"] = ""

        # Handle currency conversion if requested
        if convert_to_currency and convert_to_currency.upper() != bean_dict.get("currency", "").upper():
            original_price = bean_dict.get("price")
            original_currency = bean_dict.get("currency")

            if original_price and original_currency:
                converted_price = convert_price(original_price, original_currency.upper(), convert_to_currency.upper())

                if converted_price is not None:
                    # Store original price info
                    bean_dict["original_price"] = original_price
                    bean_dict["original_currency"] = original_currency
                    # Update price and currency
                    bean_dict["price"] = round(converted_price, 2)
                    bean_dict["currency"] = convert_to_currency.upper()
                    bean_dict["price_converted"] = True
                else:
                    bean_dict["price_converted"] = False
            else:
                bean_dict["price_converted"] = False
        else:
            bean_dict["price_converted"] = False

        # Create APISearchResult object
        search_result = APISearchResult(**bean_dict)
        coffee_beans.append(search_result)

    # Create pagination info
    from kissaten.schemas.search import PaginationInfo

    pagination = PaginationInfo(
        page=page,
        per_page=per_page,
        total_items=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

    return APIResponse.success_response(
        data=coffee_beans,
        pagination=pagination,
        metadata={
            "varietal_name": actual_varietal,
            "varietal_slug": varietal_slug,
            "total_results": total_count,
            "currency_conversion": {
                "enabled": convert_to_currency is not None,
                "target_currency": convert_to_currency.upper() if convert_to_currency else None,
                "converted_results": sum(1 for bean in coffee_beans if getattr(bean, "price_converted", False)),
            }
            if convert_to_currency
            else None,
        },
    )


@app.get("/v1/tasting-note-categories", response_model=APIResponse[dict])
@cached(ttl=600, cache=SimpleMemoryCache)
async def get_tasting_note_categories():
    """Get all tasting note categories grouped by primary, secondary, and tertiary category with counts."""
    try:
        # The query is updated to include the tertiary_category in the grouping and selection.
        query = """
        WITH note_bean_counts AS (
            SELECT
                tnc.tasting_note,
                tnc.primary_category,
                tnc.secondary_category,
                tnc.tertiary_category,
                COUNT(DISTINCT cb.id) as bean_count
            FROM tasting_notes_categories tnc
            LEFT JOIN (
                SELECT cb.id, unnest(cb.tasting_notes) as note
                FROM coffee_beans cb
                WHERE cb.tasting_notes IS NOT NULL
            ) cb ON tnc.tasting_note = cb.note
            GROUP BY ALL -- Group by all selected columns
        )
        SELECT
            primary_category,
            secondary_category,
            tertiary_category, -- Added tertiary category
            COUNT(*) as note_count,
            SUM(bean_count) as total_bean_count,
            list(struct_pack(note := tasting_note, bean_count := bean_count)
                 ORDER BY bean_count DESC) as tasting_notes_with_counts,
            list(tasting_note ORDER BY tasting_note) as tasting_notes
        FROM note_bean_counts
        GROUP BY primary_category, secondary_category, tertiary_category -- Group by the full hierarchy
        ORDER BY primary_category, secondary_category, tertiary_category
        """

        results = conn.execute(query).fetchall()

        # Group by primary category as expected by the frontend
        categories = {}
        total_notes = 0
        total_unique_descriptors = set()

        for row in results:
            # Unpack results from the row, now including the tertiary category
            primary_cat = row[0]
            secondary_cat = row[1]
            tertiary_cat = row[2]  # New
            note_count = row[3]
            bean_count = row[4] or 0
            tasting_notes_with_counts = row[5] if row[5] else []
            tasting_notes = row[6] if row[6] else []

            # Add to totals
            total_notes += note_count
            total_unique_descriptors.update(tasting_notes)

            # Group by primary category
            if primary_cat not in categories:
                categories[primary_cat] = []

            # Append the full category object, including the tertiary level
            categories[primary_cat].append(
                {
                    "primary_category": primary_cat,
                    "secondary_category": secondary_cat,
                    "tertiary_category": tertiary_cat,  # Added to response
                    "note_count": note_count,
                    "bean_count": bean_count,
                    "tasting_notes": tasting_notes,
                    "tasting_notes_with_counts": tasting_notes_with_counts,
                }
            )

        # Calculate metadata
        metadata = {
            "total_notes": total_notes,
            "total_unique_descriptors": len(total_unique_descriptors),
            "total_primary_categories": len(categories),
        }

        return APIResponse.success_response(data={"categories": categories, "metadata": metadata})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/v1/search/by-tasting-category", response_model=APIResponse[list[APISearchResult]])
async def search_by_tasting_category(
    primary_category: str = Query(..., description="Primary tasting note category"),
    secondary_category: str | None = Query(None, description="Secondary tasting note category"),
    min_confidence: float = Query(0.5, description="Minimum confidence threshold", ge=0.0, le=1.0),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Search coffee beans by tasting note categories."""
    try:
        # Build the WHERE clause for category filtering
        category_filters = ["tnc.primary_category = ?"]
        params = [primary_category]

        if secondary_category:
            category_filters.append("tnc.secondary_category = ?")
            params.append(secondary_category)

        category_filters.append("tnc.confidence >= ?")
        params.append(min_confidence)

        category_where = " AND ".join(category_filters)

        # Count query using array functions instead of unnest
        count_query = f"""
        SELECT COUNT(DISTINCT cb.id)
        FROM coffee_beans cb
        INNER JOIN tasting_notes_categories tnc ON
            array_to_string(cb.tasting_notes, '|') LIKE '%' || tnc.tasting_note || '%'
        WHERE {category_where}
        """

        total_count_result = conn.execute(count_query, params).fetchone()
        total_count = total_count_result[0] if total_count_result else 0
        total_pages = (total_count + per_page - 1) // per_page

        # Main query with categorized notes
        offset = (page - 1) * per_page

        main_query = f"""
        SELECT DISTINCT
            cb.id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
            cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
            cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description,
            cb.in_stock, cb.scraped_at, cb.scraper_version,
            cb.image_url, cb.clean_url_slug, cb.bean_url_path,
            AVG(tnc.confidence) as avg_category_confidence
        FROM coffee_beans cb
        INNER JOIN tasting_notes_categories tnc ON
            array_to_string(cb.tasting_notes, '|') LIKE '%' || tnc.tasting_note || '%'
        WHERE {category_where}
        GROUP BY cb.id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
                 cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
                 cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
                 cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description,
                 cb.in_stock, cb.scraped_at, cb.scraper_version,
                 cb.image_url, cb.clean_url_slug, cb.bean_url_path, cb.date_added
        ORDER BY avg_category_confidence DESC, cb.name
        LIMIT ? OFFSET ?
        """

        query_params = params + [per_page, offset]
        results = conn.execute(main_query, query_params).fetchall()

        # Convert results to APISearchResult objects
        coffee_beans = []
        for row in results:
            bean_dict = {
                "id": row[0],
                "name": row[1],
                "roaster": row[2],
                "url": row[3],
                "is_single_origin": row[4],
                "price_paid_for_green_coffee": row[5],
                "currency_of_price_paid_for_green_coffee": row[6],
                "roast_level": row[7],
                "roast_profile": row[8],
                "weight": row[9] or 0,
                "price": row[10],
                "currency": row[11],
                "is_decaf": row[12],
                "cupping_score": row[13],
                "tasting_notes": row[14] or [],
                "description": row[15],
                "in_stock": row[16],
                "scraped_at": row[17],
                "scraper_version": row[18],
                "image_url": row[19],
                "clean_url_slug": row[20],
                "bean_url_path": row[21] or "",
                "avg_category_confidence": round(row[22], 3) if row[22] else 0,
            }

            # Get origins for this bean (reuse existing pattern)
            origins_query = """
            SELECT o.country, o.region, o.producer, o.farm, o.elevation_min, o.elevation_max,
                   o.process, o.variety, o.harvest_date, o.latitude, o.longitude,
                   cc.name as country_full_name
            FROM origins o
            LEFT JOIN country_codes cc ON o.country = cc.alpha_2
            WHERE o.bean_id = ?
            ORDER BY o.id
            """
            origins_results = conn.execute(origins_query, [bean_dict["id"]]).fetchall()

            origins = []
            for origin_row in origins_results:
                origin_data = {
                    "country": origin_row[0] if origin_row[0] and origin_row[0].strip() else None,
                    "region": origin_row[1] if origin_row[1] and origin_row[1].strip() else None,
                    "producer": origin_row[2] if origin_row[2] and origin_row[2].strip() else None,
                    "farm": origin_row[3] if origin_row[3] and origin_row[3].strip() else None,
                    "elevation_min": origin_row[4],
                    "elevation_max": origin_row[5] or origin_row[4],
                    "process": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
                    "variety": origin_row[7] if origin_row[7] and origin_row[7].strip() else None,
                    "harvest_date": origin_row[8],
                    "latitude": origin_row[9] or 0.0,
                    "longitude": origin_row[10] or 0.0,
                    "country_full_name": origin_row[11],
                }
                origins.append(APIBean(**origin_data))

            bean_dict["origins"] = origins
            search_result = APISearchResult(**bean_dict)
            coffee_beans.append(search_result)

        # Create pagination info
        from kissaten.schemas.search import PaginationInfo

        pagination = PaginationInfo(
            page=page,
            per_page=per_page,
            total_items=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

        return APIResponse.success_response(
            data=coffee_beans,
            pagination=pagination,
            metadata={
                "primary_category": primary_category,
                "secondary_category": secondary_category,
                "min_confidence": min_confidence,
                "total_results": total_count,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/v1/tasting-notes/{note_text}/details", response_model=APIResponse[dict])
async def get_tasting_note_details(note_text: str):
    """Get categorization details for a specific tasting note."""
    try:
        query = """
        SELECT
            tasting_note,
            primary_category,
            secondary_category,
            tertiary_category,
            confidence,
        FROM tasting_notes_categories
        WHERE tasting_note = ?
        """

        result = conn.execute(query, [note_text]).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"Tasting note '{note_text}' not found")

        # Count how many beans use this note
        beans_count_query = """
        SELECT COUNT(DISTINCT id)
        FROM coffee_beans cb, unnest(cb.tasting_notes) AS note
        WHERE note = ?
        """
        beans_count = conn.execute(beans_count_query, [note_text]).fetchone()[0]

        details = {
            "tasting_note": result[0],
            "primary_category": result[1],
            "secondary_category": result[2],
            "tertiary_category": result[3],
            "confidence": result[4],
            "beans_using_note": beans_count,
        }

        return APIResponse.success_response(data=details)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
