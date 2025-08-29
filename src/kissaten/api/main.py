"""
FastAPI application for Kissaten coffee bean search API.
"""

import json
import re
from pathlib import Path

import duckdb
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from kissaten.schemas import APIResponse
from kissaten.schemas.api_models import APIBean, APICoffeeBean, APIRecommendation, APISearchResult
from kissaten.scrapers import get_registry

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

# Serve static images
app.mount(
    "/data/roasters",
    StaticFiles(directory=Path(__file__).parent.parent.parent.parent / "data" / "roasters"),
    name="roasters-data",
)

# Database connection
DATABASE_PATH = Path(__file__).parent.parent.parent.parent / "data" / "kissaten.duckdb"
conn = duckdb.connect(str(DATABASE_PATH))


def parse_boolean_search_query(query: str) -> tuple[str, list[str]]:
    """
    Parse a boolean search query with wildcards and convert it to SQL.

    Supports:
    - Wildcards: * (multiple chars), ? (single char)
    - OR operator: |
    - AND operator: &
    - NOT operator: ! or NOT
    - Parentheses for grouping: ()

    Examples:
    - "choc*|floral" -> "(tasting_notes ILIKE ? OR tasting_notes ILIKE ?)"
    - "berry&(lemon|lime)" -> "(tasting_notes ILIKE ? AND (tasting_notes ILIKE ? OR tasting_notes ILIKE ?))"
    - "chocolate&!decaf" -> "(tasting_notes ILIKE ? AND NOT tasting_notes ILIKE ?)"
    - "fruit*&!(bitter|sour)" -> "(tasting_notes ILIKE ? AND NOT (tasting_notes ILIKE ? OR tasting_notes ILIKE ?))"

    Returns:
        tuple: (sql_condition, parameters)
    """

    if not query.strip():
        return "", []

    # If no boolean operators, handle as simple wildcard search
    if not re.search(r"[|&!()]|NOT\b", query, re.IGNORECASE):
        search_pattern = query.replace("*", "%").replace("?", "_")
        if "*" not in query and "?" not in query:
            search_pattern = f"%{search_pattern}%"
        return "array_to_string(cb.tasting_notes, ' ') ILIKE ?", [search_pattern]

    def tokenize(text: str) -> list[str]:
        """Tokenize the search query into terms and operators"""
        # Replace NOT with ! for easier parsing
        text = re.sub(r"\bNOT\b", "!", text, flags=re.IGNORECASE)
        # Split by operators and parentheses, keeping the delimiters
        tokens = re.split(r"([|&!()])", text)
        # Remove empty strings and strip whitespace
        return [token.strip() for token in tokens if token.strip()]

    def convert_wildcard_term(term: str) -> str:
        """Convert a single term with wildcards to SQL pattern"""
        pattern = term.replace("*", "%").replace("?", "_")
        if "*" not in term and "?" not in term:
            pattern = f"%{pattern}%"
        return pattern

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
                # It's a search term
                pattern = convert_wildcard_term(token)
                condition = "array_to_string(cb.tasting_notes, ' ') ILIKE ?"
                return condition, [pattern], pos + 1

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
        search_pattern = query.replace("*", "%").replace("?", "_")
        if "*" not in query and "?" not in query:
            search_pattern = f"%{search_pattern}%"
        return "array_to_string(cb.tasting_notes, ' ') ILIKE ?", [search_pattern]


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
    await load_coffee_data()


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
            bean_url_path VARCHAR  -- Store the full bean URL path from directory structure
        )
    """)

    # Create origins table to handle multiple origins per bean
    conn.execute("""
        CREATE TABLE IF NOT EXISTS origins (
            id INTEGER PRIMARY KEY,
            bean_id INTEGER,
            country VARCHAR,
            region VARCHAR,
            producer VARCHAR,
            farm VARCHAR,
            elevation INTEGER,
            latitude DOUBLE,
            longitude DOUBLE,
            process VARCHAR,
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

    # Create a view to simplify queries by joining coffee beans with their primary origin
    conn.execute("""
        CREATE OR REPLACE VIEW coffee_beans_with_origin AS
        SELECT
            cb.*,
            o.country,
            o.region,
            o.producer,
            o.farm,
            o.elevation,
            o.latitude,
            o.longitude,
            o.process,
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


async def load_coffee_data():
    """Load coffee bean data from JSON files into DuckDB using DuckDB's native glob functionality."""
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "roasters"
    countrycodes_path = Path(__file__).parent.parent / "database" / "countrycodes.csv"

    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

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
                "UK": "GB",
                "SOUTH KOREA": "KR",
                "NORTH KOREA": "KP",
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
                filename
            FROM read_json('{json_pattern}',
                filename=true,
                auto_detect=true,
                union_by_name=true,
                ignore_errors=true
            ) as json_data
        """)

        # Insert coffee beans with simplified structure (origins moved to separate table)
        conn.execute("""
            INSERT INTO coffee_beans (
                id, name, roaster, url, is_single_origin, price_paid_for_green_coffee,
                currency_of_price_paid_for_green_coffee, roast_level, roast_profile, weight, price, currency,
                is_decaf, cupping_score, tasting_notes, description, in_stock, scraped_at, scraper_version,
                filename, image_url, clean_url_slug, bean_url_path
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY name) as id,
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
                is_decaf,
                cupping_score,
                COALESCE(tasting_notes, []) as tasting_notes,
                COALESCE(description, '') as description,
                COALESCE(in_stock, true) as in_stock,
                TRY_CAST(scraped_at AS TIMESTAMP) as scraped_at,
                COALESCE(scraper_version, '1.0') as scraper_version,
                filename,
                -- Generate static image URL based on filename and roaster path, only if original image_url exists
                CASE
                    WHEN filename IS NOT NULL AND image_url IS NOT NULL AND image_url != '' THEN
                        '/static/data/' ||
                        regexp_replace(split_part(filename, '/data/', -1), '\\.json$', '.png', 'g')
                    ELSE ''
                END as image_url,
                -- Generate clean URL slug by removing timestamp from filename
                CASE
                    WHEN filename IS NOT NULL THEN
                        regexp_replace(
                            regexp_replace(split_part(filename, '/', -1), '\\.json$', '', 'g'),
                            '_\\d{6}$', '', 'g'
                        )
                    ELSE ''
                END as clean_url_slug,
                -- Generate bean_url_path from actual directory structure
                CASE
                    WHEN filename IS NOT NULL THEN
                        '/' || split_part(filename, '/', -3) || '/' ||
                        regexp_replace(
                            regexp_replace(split_part(filename, '/', -1), '\\.json$', '', 'g'),
                            '_\\d{6}$', '', 'g'
                        )
                    ELSE ''
                END as bean_url_path
            FROM raw_coffee_data
            WHERE name IS NOT NULL AND name != ''
        """)

        # Insert origins data from the origins array in JSON
        conn.execute("""
            INSERT INTO origins (
                id, bean_id, country, region, producer, farm, elevation,
                latitude, longitude, process, variety, harvest_date
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY cb.id) as id,
                cb.id as bean_id,
                COALESCE(t.origin.country, '') as country,
                COALESCE(t.origin.region, '') as region,
                COALESCE(t.origin.producer, '') as producer,
                COALESCE(t.origin.farm, '') as farm,
                COALESCE(TRY_CAST(t.origin.elevation AS INTEGER), 0) as elevation,
                TRY_CAST(t.origin.latitude AS DOUBLE) as latitude,
                TRY_CAST(t.origin.longitude AS DOUBLE) as longitude,
                COALESCE(t.origin.process, '') as process,
                COALESCE(t.origin.variety, '') as variety,
                TRY_CAST(t.origin.harvest_date AS TIMESTAMP) as harvest_date
            FROM raw_coffee_data rcd
            JOIN coffee_beans cb ON cb.filename = rcd.filename
            CROSS JOIN UNNEST(rcd.origins) AS t(origin)
            WHERE rcd.origins IS NOT NULL
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

        # Get counts for logging
        result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
        bean_count = result[0] if result else 0
        result = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
        roaster_count = result[0] if result else 0

        print(f"Loaded {bean_count} coffee beans from {roaster_count} roasters using DuckDB glob with registry")

        # Clean up temporary view
        conn.execute("DROP VIEW IF EXISTS raw_coffee_data")

    except Exception as e:
        print(f"Error loading coffee data with DuckDB glob: {e}")
        # Fallback: if glob fails, we could implement a simple directory scan
        # For now, just log the error
        raise


# API Endpoints


@app.get("/", response_model=APIResponse[dict])
async def root():
    """Root endpoint with API information."""
    return APIResponse.success_response(
        data={"message": "Welcome to Kissaten Coffee Bean API"}, metadata={"version": "1.0.0"}
    )


@app.get("/v1/search", response_model=APIResponse[list[APISearchResult]])
async def search_coffee_beans(
    query: str | None = Query(None, description="Search query text"),
    roaster: list[str] | None = Query(None, description="Filter by roaster names (multiple allowed)"),
    country: list[str] | None = Query(None, description="Filter by origin countries (multiple allowed)"),
    roast_level: str | None = Query(None, description="Filter by roast level"),
    roast_profile: str | None = Query(None, description="Filter by roast profile (Espresso/Filter/Omni)"),
    process: str | None = Query(None, description="Filter by processing method"),
    variety: str | None = Query(None, description="Filter by coffee variety"),
    min_price: float | None = Query(None, description="Minimum price filter"),
    max_price: float | None = Query(None, description="Maximum price filter"),
    min_weight: int | None = Query(None, description="Minimum weight filter (grams)"),
    max_weight: int | None = Query(None, description="Maximum weight filter (grams)"),
    in_stock_only: bool = Query(False, description="Show only in-stock items"),
    is_decaf: bool | None = Query(None, description="Filter by decaf status"),
    is_single_origin: bool | None = Query(None, description="Filter by single origin status"),
    min_cupping_score: float | None = Query(None, description="Minimum cupping score filter (0-100)"),
    max_cupping_score: float | None = Query(None, description="Maximum cupping score filter (0-100)"),
    tasting_notes_only: bool = Query(
        False,
        description=(
            "Search only in tasting notes (supports wildcards *, ? and boolean operators "
            "| (OR), & (AND), ! (NOT), parentheses for grouping)"
        ),
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
):
    """Search coffee beans with filters and pagination."""

    # Build SQL query
    where_conditions = []
    params = []

    if query:
        if tasting_notes_only:
            # Parse boolean search query with wildcards, operators, and parentheses
            condition, search_params = parse_boolean_search_query(query)
            if condition:
                where_conditions.append(condition)
                params.extend(search_params)
        else:
            # Default search across name, description, and tasting notes
            where_conditions.append(
                "(cb.name ILIKE ? OR cb.description ILIKE ? OR array_to_string(cb.tasting_notes, ' ') ILIKE ?)"
            )
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term])

    if roaster:
        roaster_conditions = []
        for r in roaster:
            roaster_conditions.append("cb.roaster = ?")
            params.append(r)
        where_conditions.append(f"({' OR '.join(roaster_conditions)})")

    if country:
        country_conditions = []
        for c in country:
            country_conditions.append("EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND o.country ILIKE ?)")
            params.append(f"%{c}%")
        where_conditions.append(f"({' OR '.join(country_conditions)})")

    if roast_level:
        where_conditions.append("cb.roast_level ILIKE ?")
        params.append(f"%{roast_level}%")

    if roast_profile:
        where_conditions.append("cb.roast_profile ILIKE ?")
        params.append(f"%{roast_profile}%")

    if process:
        where_conditions.append("EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND o.process ILIKE ?)")
        params.append(f"%{process}%")

    if variety:
        where_conditions.append("EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND o.variety ILIKE ?)")
        params.append(f"%{variety}%")

    if min_price is not None:
        where_conditions.append("cb.price >= ?")
        params.append(min_price)

    if max_price is not None:
        where_conditions.append("cb.price <= ?")
        params.append(max_price)

    if min_weight is not None:
        where_conditions.append("cb.weight >= ?")
        params.append(min_weight)

    if max_weight is not None:
        where_conditions.append("cb.weight <= ?")
        params.append(max_weight)

    if in_stock_only:
        where_conditions.append("cb.in_stock = true")

    if is_decaf is not None:
        where_conditions.append("cb.is_decaf = ?")
        params.append(is_decaf)

    if is_single_origin is not None:
        where_conditions.append("cb.is_single_origin = ?")
        params.append(is_single_origin)

    if min_cupping_score is not None:
        where_conditions.append("cb.cupping_score >= ?")
        params.append(min_cupping_score)

    if max_cupping_score is not None:
        where_conditions.append("cb.cupping_score <= ?")
        params.append(max_cupping_score)

    # Build WHERE clause
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    # Validate sort fields
    valid_sort_fields = ["cb.name", "cb.roaster", "cb.price", "cb.weight", "cb.scraped_at", "cb.country", "cb.variety"]
    sort_field_mapping = {
        "name": "cb.name",
        "roaster": "cb.roaster",
        "price": "cb.price",
        "weight": "cb.weight",
        "scraped_at": "cb.scraped_at",
        "country": "cb.country",
        "variety": "cb.variety",
        "elevation": "cb.elevation",
        "cupping_score": "cb.cupping_score",
    }

    if sort_by in sort_field_mapping:
        sort_by = sort_field_mapping[sort_by]
    elif sort_by not in valid_sort_fields:
        sort_by = "cb.name"

    if sort_order.lower() not in ["asc", "desc"]:
        sort_order = "asc"

    # Get total count of unique beans (deduplicated by clean_url_slug)
    count_query = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT cb.clean_url_slug
            FROM coffee_beans_with_origin cb
            {where_clause}
        ) unique_beans
    """
    total_count = conn.execute(count_query, params).fetchone()[0]

    # Calculate pagination
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page

    # Build main query - simplified approach using the existing view
    # We'll get the beans first, then fetch origins separately
    subquery_where_clause = where_clause.replace("cb.", "cb_inner.") if where_clause else ""

    main_query = f"""
        SELECT DISTINCT
            cb.id as bean_id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
            cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description, cb.in_stock,
            cb.scraped_at, cb.scraper_version, cb.filename, cb.image_url, cb.clean_url_slug,
            cb.bean_url_path, cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
            cb.harvest_date,
            -- Get first origin for backward compatibility
            FIRST_VALUE(cb.country) OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as country,
            FIRST_VALUE(cb.region) OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as region,
            FIRST_VALUE(cb.producer) OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as producer,
            FIRST_VALUE(cb.farm) OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as farm,
            FIRST_VALUE(cb.elevation) OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as elevation,
            FIRST_VALUE(cb.process) OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as process,
            FIRST_VALUE(cb.variety) OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as variety,
            FIRST_VALUE(cb.country_full_name) OVER (PARTITION BY cb.clean_url_slug ORDER BY cb.scraped_at DESC) as country_full_name
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
            FROM coffee_beans_with_origin cb_inner
            {subquery_where_clause}
        ) cb
        WHERE cb.rn = 1
        ORDER BY {sort_by.replace("cb.", "cb.")} {sort_order.upper()}
        LIMIT ? OFFSET ?
    """

    results = conn.execute(main_query, params + [per_page, offset]).fetchall()

    # Convert results to dictionaries
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
        "is_decaf",
        "cupping_score",
        "tasting_notes",
        "description",
        "in_stock",
        "scraped_at",
        "scraper_version",
        "filename",
        "image_url",
        "clean_url_slug",
        "bean_url_path",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
        "harvest_date",
        "country",  # primary origin fields for backward compatibility
        "region",
        "producer",
        "farm",
        "elevation",
        "process",
        "variety",
        "latitude",
        "longitude",
        "country_full_name",
        "origins",  # array of all origins
    ]

    coffee_beans = []
    for row in results:
        bean_dict = dict(zip(columns, row))
        # Rename bean_id to id for API consistency
        bean_dict["id"] = bean_dict.pop("bean_id")

        # Fetch all origins for this bean
        origins_query = """
            SELECT o.country, o.region, o.producer, o.farm, o.elevation,
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
                "elevation": origin_row[4] or 0,
                "process": origin_row[5] if origin_row[5] and origin_row[5].strip() else None,
                "variety": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
                "harvest_date": origin_row[7],
                "latitude": origin_row[8] or 0.0,
                "longitude": origin_row[9] or 0.0,
                "country_full_name": origin_row[10] if origin_row[10] and origin_row[10].strip() else None,
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
        ]
        for field in fields_to_remove:
            bean_dict.pop(field, None)

        # Use bean_url_path directly from database, no need to generate
        if not bean_dict.get("bean_url_path"):
            bean_dict["bean_url_path"] = ""

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
        metadata={"total_results": total_count, "search_query": query, "filters_applied": len(where_conditions)},
    )


@app.get("/v1/roasters", response_model=APIResponse[list[dict]])
async def get_roasters():
    """Get all roasters with their coffee bean counts."""
    query = """
        SELECT
            r.id, r.name, r.slug, r.website, r.location, r.email, r.active,
            r.last_scraped, r.total_beans_scraped,
            COUNT(cb.id) as current_beans_count
        FROM roasters r
        LEFT JOIN coffee_beans cb ON r.name = cb.roaster
        GROUP BY r.id, r.name, r.slug, r.website, r.location, r.email, r.active, r.last_scraped, r.total_beans_scraped
        ORDER BY r.name
    """

    results = conn.execute(query).fetchall()

    roasters = []
    for row in results:
        roaster_dict = {
            "id": row[0],
            "name": row[1],
            "slug": row[2],
            "website": row[3],
            "location": row[4],
            "email": row[5],
            "active": row[6],
            "last_scraped": row[7],
            "total_beans_scraped": row[8],
            "current_beans_count": row[9],
        }
        roasters.append(roaster_dict)

    return APIResponse.success_response(data=roasters)


@app.get("/v1/roasters/{roaster_name}/beans", response_model=APIResponse[list[dict]])
async def get_roaster_beans(roaster_name: str):
    """Get all coffee beans from a specific roaster with full country names."""
    query = """
        SELECT
            cb.id, cb.name, cb.roaster, cb.url, cb.country, cb.region, cb.producer, cb.farm, cb.elevation,
            cb.is_single_origin, cb.process, cb.variety, cb.harvest_date, cb.price_paid_for_green_coffee,
            cb.currency_of_price_paid_for_green_coffee, cb.roast_level, cb.roast_profile,
            cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description, cb.in_stock, cb.scraped_at,
            cb.scraper_version, cb.filename, cb.image_url, cb.clean_url_slug, cb.bean_url_path,
            cb.country_full_name
        FROM coffee_beans_with_origin cb
        WHERE cb.roaster ILIKE ?
        ORDER BY cb.name
    """

    results = conn.execute(query, [f"%{roaster_name}%"]).fetchall()

    if not results:
        raise HTTPException(status_code=404, detail=f"No beans found for roaster: {roaster_name}")

    columns = [
        "id",
        "name",
        "roaster",
        "url",
        "country",
        "region",
        "producer",
        "farm",
        "elevation",
        "is_single_origin",
        "process",
        "variety",
        "harvest_date",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
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
        "filename",
        "image_url",
        "clean_url_slug",
        "bean_url_path",
        "country_full_name",
    ]

    coffee_beans = []
    for row in results:
        bean_dict = dict(zip(columns, row))
        # Use bean_url_path directly from database
        if not bean_dict.get("bean_url_path"):
            bean_dict["bean_url_path"] = ""
        coffee_beans.append(bean_dict)

    return APIResponse.success_response(data=coffee_beans)


@app.get("/v1/countries", response_model=APIResponse[list[dict]])
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


@app.get("/v1/stats", response_model=APIResponse[dict])
async def get_stats():
    """Get database statistics and analytics."""

    # Total counts
    total_beans = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()[0]
    total_roasters = conn.execute("SELECT COUNT(*) FROM roasters").fetchone()[0]
    total_countries = conn.execute(
        "SELECT COUNT(DISTINCT country) FROM origins WHERE country IS NOT NULL AND country != ''"
    ).fetchone()[0]

    # Price statistics
    price_stats = conn.execute("""
        SELECT
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price) as avg_price,
            MEDIAN(price) as median_price
        FROM coffee_beans
        WHERE price IS NOT NULL AND price > 0
    """).fetchone()

    # Top roasters by bean count
    top_roasters = conn.execute("""
        SELECT roaster, COUNT(*) as bean_count
        FROM coffee_beans
        GROUP BY roaster
        ORDER BY bean_count DESC
        LIMIT 5
    """).fetchall()

    # Most common processes
    top_processes = conn.execute("""
        SELECT process, COUNT(*) as count
        FROM coffee_beans
        WHERE process IS NOT NULL AND process != ''
        GROUP BY process
        ORDER BY count DESC
        LIMIT 5
    """).fetchall()

    stats = {
        "total_beans": total_beans,
        "total_roasters": total_roasters,
        "total_countries": total_countries,
        "price_statistics": {
            "min_price": price_stats[0] if price_stats[0] else 0,
            "max_price": price_stats[1] if price_stats[1] else 0,
            "avg_price": round(price_stats[2], 2) if price_stats[2] else 0,
            "median_price": round(price_stats[3], 2) if price_stats[3] else 0,
        },
        "top_roasters": [{"roaster": r[0], "bean_count": r[1]} for r in top_roasters],
        "top_processes": [{"process": p[0], "count": p[1]} for p in top_processes],
    }

    return APIResponse.success_response(data=stats)


@app.get("/v1/beans/{roaster_slug}/{bean_slug}", response_model=APIResponse[APICoffeeBean])
async def get_bean_by_slug(roaster_slug: str, bean_slug: str):
    """Get a specific coffee bean by roaster slug and bean slug from URL-friendly paths."""

    # Construct the expected bean_url_path from the provided slugs
    expected_bean_url_path = f"/{roaster_slug}/{bean_slug}"

    # Query the database to get bean without flattened origins
    query = """
        SELECT DISTINCT
            cb.id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
            cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description, cb.in_stock,
            cb.scraped_at, cb.scraper_version, cb.filename, cb.image_url, cb.clean_url_slug,
            cb.bean_url_path, cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee
        FROM coffee_beans cb
        WHERE cb.bean_url_path = ?
        ORDER BY cb.scraped_at DESC
        LIMIT 1
    """

    result = conn.execute(query, [expected_bean_url_path]).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail=f"Bean '{bean_slug}' not found for roaster '{roaster_slug}'")

    # Convert result to dictionary
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
        "filename",
        "image_url",
        "clean_url_slug",
        "bean_url_path",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
    ]

    bean_data = dict(zip(columns, result))

    # Fetch all origins for this bean
    origins_query = """
        SELECT o.country, o.region, o.producer, o.farm, o.elevation,
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
            "elevation": origin_row[4] or 0,
            "process": origin_row[5] if origin_row[5] and origin_row[5].strip() else None,
            "variety": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
            "harvest_date": origin_row[7],
            "latitude": origin_row[8],
            "longitude": origin_row[9],
            "country_full_name": origin_row[10] if len(origin_row) > 10 else None,
        }
        origins.append(APIBean(**origin_data))

    bean_data["origins"] = origins

    # Set default for bean_url_path if needed
    if not bean_data.get("bean_url_path"):
        bean_data["bean_url_path"] = ""

    # Convert to APICoffeeBean object for proper validation
    coffee_bean = APICoffeeBean(**bean_data)

    return APIResponse.success_response(data=coffee_bean)


@app.get("/v1/beans/{roaster_slug}/{bean_slug}/recommendations", response_model=APIResponse[list[APIRecommendation]])
async def get_bean_recommendations_by_slug(
    roaster_slug: str,
    bean_slug: str,
    limit: int = Query(6, ge=1, le=20, description="Number of recommendations to return"),
):
    """Get recommendations for a specific bean by roaster slug and bean slug."""

    # First get the target bean data
    try:
        bean_response = await get_bean_by_slug(roaster_slug, bean_slug)
        if not bean_response.data:
            raise HTTPException(status_code=404, detail="Bean not found")

        target_bean = bean_response.data

        # Now use the existing recommendation logic with the bean data
        target_notes = target_bean.tasting_notes or []
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
                cb.scraped_at, cb.scraper_version, cb.filename, cb.image_url, cb.clean_url_slug,
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
            "filename",
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
                SELECT o.country, o.region, o.producer, o.farm, o.elevation,
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
                    "elevation": origin_row[4] or 0,
                    "process": origin_row[5] if origin_row[5] and origin_row[5].strip() else None,
                    "variety": origin_row[6] if origin_row[6] and origin_row[6].strip() else None,
                    "harvest_date": origin_row[7],
                    "latitude": origin_row[8],
                    "longitude": origin_row[9],
                    "country_full_name": origin_row[10] if len(origin_row) > 10 else None,
                }
                origins.append(APIBean(**origin_data))

            bean_data["origins"] = origins

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
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@app.get("/v1/roasters/{roaster_name}/beans/{bean_filename}", response_model=APIResponse[dict])
async def get_bean_by_filename(roaster_name: str, bean_filename: str):
    """Get a specific coffee bean by roaster directory name and clean bean filename (without timestamp)."""

    # Convert roaster_name to display format for matching
    roaster_display_name = roaster_name.replace("_", " ").title()

    # Query the database using clean_url_slug pattern matching to get the latest version
    query = """
        SELECT
            cb.id, cb.name, cb.roaster, cb.url, cb.country, cb.region, cb.producer, cb.farm, cb.elevation,
            cb.is_single_origin, cb.process, cb.variety, cb.harvest_date, cb.price_paid_for_green_coffee,
            cb.currency_of_price_paid_for_green_coffee, cb.roast_level, cb.roast_profile,
            cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description, cb.in_stock, cb.scraped_at,
            cb.scraper_version, cb.filename, cb.image_url, cb.clean_url_slug, cb.country_full_name
        FROM coffee_beans_with_origin cb
        WHERE cb.roaster ILIKE ? AND cb.clean_url_slug = ?
        ORDER BY cb.scraped_at DESC
        LIMIT 1
    """

    result = conn.execute(query, [f"%{roaster_display_name}%", bean_filename]).fetchone()

    if not result:
        raise HTTPException(
            status_code=404, detail=f"Bean file '{bean_filename}' not found for roaster '{roaster_name}'"
        )

    # Convert result to dictionary
    columns = [
        "id",
        "name",
        "roaster",
        "url",
        "country",
        "region",
        "producer",
        "farm",
        "elevation",
        "is_single_origin",
        "process",
        "variety",
        "harvest_date",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
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
        "filename",
        "image_url",
        "clean_url_slug",
        "country_full_name",
    ]

    bean_data = dict(zip(columns, result))

    # Add clean bean URL path using clean_url_slug
    if bean_data.get("clean_url_slug") and bean_data.get("roaster"):
        roaster_slug = get_roaster_slug_from_db(bean_data["roaster"])
        bean_data["bean_url_path"] = f"/{roaster_slug}/{bean_data['clean_url_slug']}"
    else:
        bean_data["bean_url_path"] = ""

    return APIResponse.success_response(data=bean_data)


@app.get("/v1/roasters/{roaster_name}/beans", response_model=APIResponse[list[dict]])
async def list_roaster_bean_files(roaster_name: str):
    """List all available bean files for a roaster with their filenames."""

    # Construct the file path
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "roasters"
    roaster_dir = data_dir / roaster_name

    if not roaster_dir.exists():
        raise HTTPException(status_code=404, detail=f"Roaster '{roaster_name}' not found")

    # Find the most recent scraping session directory
    session_dirs = [d for d in roaster_dir.iterdir() if d.is_dir()]
    if not session_dirs:
        raise HTTPException(status_code=404, detail=f"No data found for roaster '{roaster_name}'")

    # Get the most recent session directory
    latest_session = max(session_dirs, key=lambda x: x.name)

    beans = []
    for json_file in latest_session.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                bean_data = json.load(f)

            # Extract filename without extension
            filename = json_file.stem

            beans.append(
                {
                    "filename": filename,
                    "name": bean_data.get("name", ""),
                    "roaster": bean_data.get("roaster", ""),
                    "url": bean_data.get("url", ""),
                    "process": bean_data.get("process", ""),
                    "variety": bean_data.get("variety", ""),
                    "roast_level": bean_data.get("roast_level", ""),
                    "price": bean_data.get("price"),
                    "currency": bean_data.get("currency", "EUR"),
                    "weight": bean_data.get("weight"),
                    "in_stock": bean_data.get("in_stock"),
                    "tasting_notes": bean_data.get("tasting_notes", []),
                }
            )
        except (json.JSONDecodeError, Exception):
            # Skip files that can't be parsed
            continue

    return APIResponse.success_response(data=beans)


@app.get("/v1/search/bean", response_model=APIResponse[dict])
async def search_coffee_bean_by_roaster_and_name(
    roaster: str = Query(..., description="Roaster name"), name: str = Query(..., description="Bean name")
):
    """Find a specific coffee bean by roaster and name for direct linking."""
    query = """
        SELECT
            cb.id, cb.name, cb.roaster, cb.url, cb.country, cb.region, cb.producer, cb.farm, cb.elevation,
            cb.is_single_origin, cb.process, cb.variety, cb.harvest_date, cb.price_paid_for_green_coffee,
            cb.currency_of_price_paid_for_green_coffee, cb.roast_level, cb.roast_profile,
            cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description, cb.in_stock, cb.scraped_at,
            cb.scraper_version, cb.filename, cb.image_url, cb.clean_url_slug, cb.country_full_name
        FROM coffee_beans_with_origin cb
        WHERE cb.roaster ILIKE ? AND cb.name ILIKE ?
        ORDER BY
            -- Prioritize exact matches
            CASE WHEN LOWER(cb.roaster) = LOWER(?) AND LOWER(cb.name) = LOWER(?) THEN 1 ELSE 2 END,
            cb.scraped_at DESC
        LIMIT 1
    """

    roaster_pattern = f"%{roaster}%"
    name_pattern = f"%{name}%"

    result = conn.execute(query, [roaster_pattern, name_pattern, roaster, name]).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail=f"Coffee bean '{name}' from roaster '{roaster}' not found")

    columns = [
        "id",
        "name",
        "roaster",
        "url",
        "country",
        "region",
        "producer",
        "farm",
        "elevation",
        "is_single_origin",
        "process",
        "variety",
        "harvest_date",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
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
        "filename",
        "image_url",
        "clean_url_slug",
        "country_full_name",
    ]

    bean_dict = dict(zip(columns, result))

    # Add clean bean URL path using clean_url_slug
    if bean_dict.get("clean_url_slug") and bean_dict.get("roaster"):
        roaster_slug = get_roaster_slug_from_db(bean_dict["roaster"])
        bean_dict["bean_url_path"] = f"/{roaster_slug}/{bean_dict['clean_url_slug']}"
    else:
        bean_dict["bean_url_path"] = ""

    return APIResponse.success_response(data=bean_dict)


@app.get("/v1/beans/{bean_id}", response_model=APIResponse[dict])
async def get_coffee_bean(bean_id: int):
    """Get a specific coffee bean by ID with full country name."""
    query = """
        SELECT
            cb.id, cb.name, cb.roaster, cb.url, cb.country, cb.region, cb.producer, cb.farm, cb.elevation,
            cb.is_single_origin, cb.process, cb.variety, cb.harvest_date, cb.price_paid_for_green_coffee,
            cb.currency_of_price_paid_for_green_coffee, cb.roast_level, cb.roast_profile,
            cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score, cb.tasting_notes, cb.description, cb.in_stock, cb.scraped_at,
            cb.scraper_version, cb.filename, cb.image_url, cb.clean_url_slug, cb.country_full_name
        FROM coffee_beans_with_origin cb
        WHERE cb.id = ?
    """

    result = conn.execute(query, [bean_id]).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail=f"Coffee bean with ID {bean_id} not found")

    columns = [
        "id",
        "name",
        "roaster",
        "url",
        "country",
        "region",
        "producer",
        "farm",
        "elevation",
        "is_single_origin",
        "process",
        "variety",
        "harvest_date",
        "price_paid_for_green_coffee",
        "currency_of_price_paid_for_green_coffee",
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
        "filename",
        "image_url",
        "clean_url_slug",
        "country_full_name",
    ]

    bean_dict = dict(zip(columns, result))

    # Add clean bean URL path using clean_url_slug
    if bean_dict.get("clean_url_slug") and bean_dict.get("roaster"):
        roaster_slug = get_roaster_slug_from_db(bean_dict["roaster"])
        bean_dict["bean_url_path"] = f"/{roaster_slug}/{bean_dict['clean_url_slug']}"
    else:
        bean_dict["bean_url_path"] = ""

    return APIResponse.success_response(data=bean_dict)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
