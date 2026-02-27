"""
FastAPI application for Kissaten coffee bean search API.
"""

import json
import logging
import os
import re
import time
import unicodedata
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple

import uvicorn
from aiocache import cached
from aiocache.backends.memory import SimpleMemoryCache
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from starlette.responses import Response
from starlette.types import Scope

from kissaten.api.ai_search import create_ai_search_router
from kissaten.api.db import (
    conn,
    normalize_farm_name,
    normalize_process_name,
    normalize_region_name,
    normalize_varietal_name,
)
from kissaten.api.fx import convert_price, create_fx_router
from kissaten.schemas import APIResponse, PaginationInfo
from kissaten.schemas.api_models import (
    APIBean,
    APICoffeeBean,
    APIRecommendation,
    APISearchResult,
)
from kissaten.schemas.geography_models import (
    CountryDetailResponse,
    CountryStatistics,
    ElevationInfo,
    FarmDetailResponse,
    FarmSummary,
    OriginSearchResult,
    RegionDetailResponse,
    RegionStatistics,
    RegionSummary,
    TopNote,
    TopProcess,
    TopRoaster,
    TopVariety,
)
from kissaten.scrapers import get_registry

# Profiling configuration
ENABLE_PROFILING = os.environ.get("KISSATEN_PROFILING") == "1"


class BeanPathsRequest(BaseModel):
    """Request model for fetching beans by their URL paths."""

    bean_url_paths: list[str] = Field(
        ...,
        description="List of bean_url_path strings to fetch",
        min_length=1,
        max_length=100,
    )


@dataclass
class FilterParams:
    """Container for all filter parameters used in coffee bean searches."""

    query: str | None = None
    tasting_notes_query: str | None = None
    roaster: list[str] | None = None
    roaster_location: list[str] | None = None
    origin: list[str] | None = None
    region: str | None = None
    producer: str | None = None
    farm: str | None = None
    roast_level: str | None = None
    roast_profile: str | None = None
    process: str | None = None
    variety: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_weight: int | None = None
    max_weight: int | None = None
    in_stock_only: bool = False
    is_decaf: bool | None = None
    is_single_origin: bool | None = None
    min_cupping_score: float | None = None
    max_cupping_score: float | None = None
    min_elevation: int | None = None
    max_elevation: int | None = None
    convert_to_currency: str | None = None
    tasting_notes_only: bool = False  # Only used in search_coffee_beans


class FilterResult(NamedTuple):
    """Result of building filter conditions."""

    conditions: list[str]
    params: list
    score_components: list[str] | None = None  # Only used for scoring mode


from pyinstrument import Profiler
from pyinstrument.renderers.html import HTMLRenderer
from pyinstrument.renderers.speedscope import SpeedscopeRenderer


def validate_currency_code(code: str | None) -> str | None:
    """Validate that a currency code is a valid ISO 4217 code (3 uppercase letters)."""
    if code is None:
        return None
    code = code.upper()
    if not re.match(r"^[A-Z]{3}$", code):
        raise HTTPException(status_code=400, detail=f"Invalid currency code: {code}")
    return code


def register_profiling_middleware(app: FastAPI):
    @app.middleware("http")
    async def profile_request(request: Request, call_next):
        """Profile the current request

        Taken from https://pyinstrument.readthedocs.io/en/latest/guide.html#profile-a-web-request-in-fastapi
        with slight improvements.

        """
        profile_type_to_ext = {"html": "html", "speedscope": "speedscope.json"}
        profile_type_to_renderer = {
            "html": HTMLRenderer,
            "speedscope": SpeedscopeRenderer,
        }
        if request.query_params.get("profile", False):
            profile_type = request.query_params.get("profile_format", "speedscope")
            with Profiler(interval=0.001, async_mode="enabled") as profiler:
                response = await call_next(request)
            extension = profile_type_to_ext[profile_type]
            renderer = profile_type_to_renderer[profile_type]()
            with open(Path(__file__).parent.parent.parent.parent / f"profile.{extension}", "w") as out:
                out.write(profiler.output(renderer=renderer))
            return response
        return await call_next(request)


def build_coffee_bean_filters(filter_params: FilterParams, use_scoring: bool = False) -> FilterResult:
    """
    Build filter conditions and parameters for coffee bean queries.

    Args:
        filter_params: Container with all filter parameters
        use_scoring: If True, builds score components for relevance scoring.
                    If False, builds simple filter conditions.

    Returns:
        FilterResult with conditions, params, and optionally score_components
    """
    conditions = []
    params = []
    score_components = [] if use_scoring else None

    def add_condition(condition: str, condition_params: list):
        """Add a condition, either as filter or score component."""
        if use_scoring:
            score_components.append(f"(CASE WHEN {condition} THEN 1 ELSE 0 END)")
        else:
            conditions.append(condition)
        params.extend(condition_params)

    # Handle regular query (searches name, description, and tasting notes)
    if filter_params.query:
        if filter_params.tasting_notes_only:
            condition, search_params = parse_boolean_search_query_for_field(
                filter_params.query, "array_to_string(cb.tasting_notes, ' ')"
            )
            if condition:
                add_condition(condition, search_params)
        else:
            condition = "(cb.name_unaccented ILIKE strip_accents(?) OR cb.description ILIKE ? OR array_to_string(cb.tasting_notes, ' ') ILIKE ?)"
            search_term = f"%{filter_params.query}%"
            add_condition(condition, [search_term, search_term, search_term])

    # Handle separate tasting notes query
    if filter_params.tasting_notes_query:
        condition, search_params = parse_boolean_search_query_for_field(
            filter_params.tasting_notes_query, "array_to_string(cb.tasting_notes, ' ')"
        )
        if condition:
            add_condition(condition, search_params)

    if filter_params.roaster:
        placeholders = ", ".join(["?" for _ in filter_params.roaster])
        condition = f"cb.roaster IN ({placeholders})"
        add_condition(condition, filter_params.roaster)

    if filter_params.roaster_location:
        roaster_location_conditions = []
        roaster_params = []
        for location_code in filter_params.roaster_location:
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
            add_condition(full_condition, roaster_params)

    if filter_params.origin:
        origin_conditions = [
            "EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND o.country = ?)" for c in filter_params.origin
        ]
        condition = f"({' OR '.join(origin_conditions)})"
        add_condition(condition, [c.upper() for c in filter_params.origin])

    # Generic function to handle boolean search fields
    def add_boolean_search_filter(field_query, sql_field, is_origin_field=False):
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
                    # Special handling for region to use canonical state mapping
                    elif sql_field == "o.region":
                        # For region searches, we need to match against both the original region name
                        # and the canonical state name after normalization
                        # This ensures searches work with both "La Mesa Cundinamarca" and "La Mesa, Cundinamarca"

                        # Check if this is a simple query (no wildcards/operators) that can use normalized matching
                        is_simple_query = not any(
                            char in field_query for char in ["*", "?", "|", "&", "!", "(", ")"]
                        ) and not (field_query.strip().startswith('"') and field_query.strip().endswith('"'))

                        if is_simple_query:
                            # Normalize the search query
                            normalized_search = normalize_region_name(field_query)
                            # Match against precalculated normalized region column
                            final_condition = """EXISTS (
                                SELECT 1 FROM origins o
                                WHERE o.bean_id = cb.id
                                AND (
                                    o.region_normalized = ?
                                    OR normalize_region_name(o.state_canonical) = ?
                                )
                            )"""
                            params.extend([normalized_search, normalized_search])
                        else:
                            # Complex query with wildcards/operators - use ILIKE matching
                            canonical_condition, canonical_params = parse_boolean_search_query_for_field(
                                field_query, "o.state_canonical_unaccented"
                            )
                            # Match if either the original region OR the canonical state matches
                            final_condition = f"EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND ({condition} OR {canonical_condition}))"
                            params.extend(search_params)
                            params.extend(canonical_params)
                    # Special handling for farm to use canonical farm mapping
                    elif sql_field == "o.farm":
                        # Check if this is a simple query (no wildcards/operators)
                        is_simple_query = not any(
                            char in field_query for char in ["*", "?", "|", "&", "!", "(", ")"]
                        ) and not (field_query.strip().startswith('"') and field_query.strip().endswith('"'))

                        if is_simple_query:
                            normalized_search = normalize_farm_name(field_query)
                            final_condition = """EXISTS (
                                SELECT 1 FROM origins o
                                WHERE o.bean_id = cb.id
                                AND (
                                    o.farm_normalized = ?
                                    OR normalize_farm_name(o.farm_canonical) = ?
                                )
                            )"""
                            params.extend([normalized_search, normalized_search])
                        else:
                            final_condition = (
                                f"EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND {condition})"
                            )
                            params.extend(search_params)
                    # Special handling for variety which checks both original and canonical fields
                    elif sql_field == "o.variety":
                        # For variety_canonical (array field), we need to check if any element matches
                        # Build a condition that unnests the array and checks each element

                        # Parse the same search query for the canonical field
                        # We need to adapt the condition to work with array elements
                        if (
                            "*" in field_query
                            or "?" in field_query
                            or "|" in field_query
                            or "&" in field_query
                            or "!" in field_query
                            or "(" in field_query
                        ):
                            # Complex boolean query - apply to each array element
                            # Use EXISTS with UNNEST to check if any canonical name matches
                            canonical_subquery = f"""
                                EXISTS (
                                    SELECT 1 FROM unnest(o.variety_canonical) AS t(canon_var)
                                    WHERE {condition.replace(sql_field, "canon_var")}
                                )
                            """
                            canonical_params = search_params  # Reuse same params
                        else:
                            # Simple query - reuse the parsed condition and params
                            # The condition already has proper ILIKE logic from parse_boolean_search_query_for_field
                            canonical_subquery = f"""
                                EXISTS (
                                    SELECT 1 FROM unnest(o.variety_canonical) AS t(canon_var)
                                    WHERE {condition.replace(sql_field, "canon_var")}
                                )
                            """
                            canonical_params = search_params  # Reuse same params

                        # Search in both original variety field and canonical variety field
                        final_condition = f"EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND ({condition} OR {canonical_subquery}))"
                        params.extend(search_params)
                        params.extend(canonical_params)
                    else:
                        final_condition = f"EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND {condition})"
                        params.extend(search_params)
                else:
                    final_condition = condition
                    params.extend(search_params)

                if use_scoring:
                    score_components.append(f"(CASE WHEN {final_condition} THEN 1 ELSE 0 END)")
                else:
                    conditions.append(final_condition)

    add_boolean_search_filter(filter_params.region, "o.region", is_origin_field=True)
    add_boolean_search_filter(filter_params.producer, "o.producer_unaccented", is_origin_field=True)
    add_boolean_search_filter(filter_params.farm, "o.farm", is_origin_field=True)
    add_boolean_search_filter(filter_params.roast_level, "cb.roast_level")
    add_boolean_search_filter(filter_params.roast_profile, "cb.roast_profile")
    add_boolean_search_filter(filter_params.process, "o.process", is_origin_field=True)
    add_boolean_search_filter(filter_params.variety, "o.variety", is_origin_field=True)

    # Range filters
    def add_range_filter(min_val, max_val, field_name, is_origin_field=False):
        range_conditions = []
        range_params = []
        if min_val is not None:
            range_conditions.append(f"{field_name} >= ?")
            range_params.append(min_val)
        if max_val is not None:
            range_conditions.append(f"{field_name} <= ?")
            range_params.append(max_val)
        if range_conditions:
            full_condition = " AND ".join(range_conditions)
            if is_origin_field:
                final_condition = f"EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND {full_condition})"
            else:
                final_condition = full_condition
            add_condition(final_condition, range_params)

    # Price range (handles currency conversion for filtering)
    price_field = "cb.price_usd" if filter_params.convert_to_currency else "cb.price"
    min_p, max_p = filter_params.min_price, filter_params.max_price
    if filter_params.convert_to_currency and filter_params.convert_to_currency.upper() != "USD":
        if min_p is not None:
            min_p = convert_price(conn, min_p, filter_params.convert_to_currency.upper(), "USD")
        if max_p is not None:
            max_p = convert_price(conn, max_p, filter_params.convert_to_currency.upper(), "USD")
    add_range_filter(min_p, max_p, price_field)

    add_range_filter(filter_params.min_weight, filter_params.max_weight, "cb.weight")
    add_range_filter(filter_params.min_cupping_score, filter_params.max_cupping_score, "cb.cupping_score")
    add_range_filter(filter_params.min_elevation, filter_params.max_elevation, "o.elevation_max", is_origin_field=True)

    # Boolean filters
    if filter_params.in_stock_only:
        add_condition("cb.in_stock = true", [])
    if filter_params.is_decaf is not None:
        add_condition("cb.is_decaf = ?", [filter_params.is_decaf])
    if filter_params.is_single_origin is not None:
        add_condition("cb.is_single_origin = ?", [filter_params.is_single_origin])

    return FilterResult(conditions, params, score_components)


# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize database and load data on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Include AI search router
    ai_search_router = create_ai_search_router(conn)
    app.include_router(ai_search_router)

    # Include FX/currency router
    fx_router = create_fx_router()
    app.include_router(fx_router)
    yield
    conn.close()


# Initialize FastAPI app
app = FastAPI(
    title="Kissaten Coffee Bean API",
    description="Search and discover coffee beans from roasters worldwide",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add profiler
register_profiling_middleware(app)


class CacheControlledStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=360000"
        return response


# Serve static images (only if the directories exist, e.g. skip in CI / fresh dev envs)
_roasters_dir = Path(__file__).parent.parent.parent.parent / "data" / "roasters"
_flavours_dir = Path(__file__).parent.parent.parent.parent / "data" / "flavours"

if _roasters_dir.exists():
    app.mount(
        "/data/roasters",
        CacheControlledStaticFiles(directory=_roasters_dir),
        name="roasters-data",
    )

if _flavours_dir.exists():
    app.mount(
        "/data/flavours",
        CacheControlledStaticFiles(directory=_flavours_dir),
        name="flavours-data",
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

    # Use strip_accents on the search term for pre-computed _unaccented columns; plain ? otherwise
    param_sql = "strip_accents(?)" if "_unaccented" in field_expression else "?"

    # If no boolean operators, handle as simple wildcard search
    if not re.search(r"[|&!()]|NOT\b", query, re.IGNORECASE):
        # Check if it's a quoted exact match
        if query.strip().startswith('"') and query.strip().endswith('"'):
            exact_term = query.strip()[1:-1]  # Remove quotes
            if "array_to_string" in field_expression:
                return (
                    f"EXISTS (SELECT 1 FROM unnest(cb.tasting_notes) AS t(note) WHERE lower(note) = lower({param_sql}))",
                    [exact_term],
                )
            else:
                return f"{field_expression} ILIKE {param_sql}", [exact_term]
        else:
            # Regular wildcard search
            search_pattern = query.replace("*", "%").replace("?", "_")
            if "*" not in query and "?" not in query:
                search_pattern = f"%{search_pattern}%"
            return f"{field_expression} ILIKE {param_sql}", [search_pattern]

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
                        condition = f"EXISTS (SELECT 1 FROM unnest(cb.tasting_notes) AS t(note) WHERE lower(note) = lower({param_sql}))"
                    else:
                        # For string fields, use exact case-insensitive match
                        condition = f"{field_expression} ILIKE {param_sql}"
                else:
                    condition = f"{field_expression} ILIKE {param_sql}"
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
                    f"EXISTS (SELECT 1 FROM unnest(cb.tasting_notes) AS t(note) WHERE lower(note) = lower({param_sql}))",
                    [exact_term],
                )
            else:
                return f"{field_expression} ILIKE {param_sql}", [exact_term]
        else:
            search_pattern = query.replace("*", "%").replace("?", "_")
            if "*" not in query and "?" not in query:
                search_pattern = f"%{search_pattern}%"
            return f"{field_expression} ILIKE {param_sql}", [search_pattern]


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


def categorize_varietal(varietal: str) -> str:
    """Categorize a varietal into major varietal groups."""
    if not varietal:
        return "other"

    varietal_lower = varietal.lower()

    # Typica family
    if any(keyword in varietal_lower for keyword in ["typica", "kona", "jamaica blue mountain", "mocha", "kent"]):
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


@app.get("/v1/stats", response_model=APIResponse[dict])
@cached(cache=SimpleMemoryCache, ttl=3600)
async def get_global_stats():
    """Get global statistics for the landing page."""
    try:
        # Total uniquely identified beans (latest version of each slug)
        beans_query = "SELECT COUNT(DISTINCT clean_url_slug) FROM coffee_beans"

        # Total roasters
        roasters_query = "SELECT COUNT(*) FROM roasters WHERE active = true"

        # Total unique farms (using pre-calculated canonical mapping)
        farms_query = """
            SELECT COUNT(DISTINCT COALESCE(o.farm_canonical, o.farm_normalized))
            FROM origins o
            WHERE (o.farm_normalized IS NOT NULL AND o.farm_normalized != '')
               OR (o.farm_canonical IS NOT NULL AND o.farm_canonical != '')
        """

        # Total flavour descriptors
        flavours_query = "SELECT COUNT(DISTINCT tasting_note) FROM tasting_notes_categories"

        # Total countries roasters are based in
        roaster_countries_query = "SELECT COUNT(DISTINCT location) FROM roasters WHERE active = true"

        # Total origin countries
        origin_countries_query = (
            "SELECT COUNT(DISTINCT country) FROM origins WHERE country IS NOT NULL AND country != ''"
        )

        total_beans = conn.execute(beans_query).fetchone()[0]
        total_roasters = conn.execute(roasters_query).fetchone()[0]
        total_farms = conn.execute(farms_query).fetchone()[0]
        total_flavours = conn.execute(flavours_query).fetchone()[0]
        total_roaster_countries = conn.execute(roaster_countries_query).fetchone()[0]
        total_origin_countries = conn.execute(origin_countries_query).fetchone()[0]

        return APIResponse.success_response(
            data={
                "total_beans": total_beans,
                "total_roasters": total_roasters,
                "total_farms": total_farms,
                "total_flavours": total_flavours,
                "total_roaster_countries": total_roaster_countries,
                "total_origin_countries": total_origin_countries,
            }
        )
    except Exception as e:
        logger.error(f"Error fetching global stats: {e}")
        raise HTTPException(status_code=500, detail="Database error while fetching statistics")


def _build_currency_select_sql(convert_to_currency: str | None) -> tuple[str, str, str, list]:
    """
    Build parameterized SQL fragments for currency-aware price selection.

    Instead of interpolating the currency code directly into f-strings (SQL injection risk),
    this function returns pre-defined SQL templates with ? placeholders, together with the
    matching parameter list.  The currency code has already been validated by
    validate_currency_code(), but we add this layer of parameterization as defense-in-depth.

    Returns:
        Tuple of (price_sql, currency_sql, price_converted_sql, params) where params
        are the positional values that correspond to the ? placeholders in the SQL fragments.
    """
    if convert_to_currency:
        cur = convert_to_currency.upper()
        price_sql = (
            "CASE WHEN ? = 'USD' THEN sb.price_usd "
            "WHEN sb.price_usd IS NOT NULL AND ? != 'USD' THEN "
            "sb.price_usd * COALESCE("
            "(SELECT rate FROM currency_rates cr "
            " WHERE cr.base_currency = 'USD' AND cr.target_currency = ? "
            " ORDER BY cr.fetched_at DESC LIMIT 1), 1.0) "
            "ELSE sb.price END"
        )
        currency_sql = "?"
        price_converted_sql = "sb.currency != ?"
        params: list = [cur, cur, cur, cur, cur]  # 5 placeholders above
    else:
        price_sql = "sb.price"
        currency_sql = "sb.currency"
        price_converted_sql = "FALSE"
        params = []
    return price_sql, currency_sql, price_converted_sql, params


# API Endpoints


@app.get("/", response_model=APIResponse[dict])
async def root():
    """Root endpoint with API information."""
    return APIResponse.success_response(
        data={"message": "Welcome to Kissaten Coffee Bean API"}, metadata={"version": "1.0.0"}
    )


@app.get("/v1/search", response_model=APIResponse[list[APISearchResult]])
@cached(cache=SimpleMemoryCache)
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
    convert_to_currency = validate_currency_code(convert_to_currency)

    # Create filter parameters object
    filter_params = FilterParams(
        query=query,
        tasting_notes_query=tasting_notes_query,
        roaster=roaster,
        roaster_location=roaster_location,
        origin=origin,
        region=region,
        producer=producer,
        farm=farm,
        roast_level=roast_level,
        roast_profile=roast_profile,
        process=process,
        variety=variety,
        min_price=min_price,
        max_price=max_price,
        min_weight=min_weight,
        max_weight=max_weight,
        in_stock_only=in_stock_only,
        is_decaf=is_decaf,
        is_single_origin=is_single_origin,
        min_cupping_score=min_cupping_score,
        max_cupping_score=max_cupping_score,
        min_elevation=min_elevation,
        max_elevation=max_elevation,
        convert_to_currency=convert_to_currency,
        tasting_notes_only=tasting_notes_only,
    )

    # Build filters using shared function
    filter_result = build_coffee_bean_filters(filter_params, use_scoring=True)
    score_components = filter_result.score_components
    params = filter_result.params

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
    try:
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
    except Exception as e:
        logger.error(f"Error executing count query: {e}")
        raise HTTPException(status_code=400, detail="Invalid query parameters. Please check your filters.")

    # Calculate pagination
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 0

    # The main query also uses the unified filter_clause for consistency.
    # Pre-build the parameterized currency SQL fragments (must be before the f-string below).
    price_sql, currency_sql, price_converted_sql, currency_params = _build_currency_select_sql(convert_to_currency)
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
            {price_sql} as price,
            {currency_sql} as currency,
            sb.price as original_price, sb.currency as original_currency,
            {price_converted_sql} as price_converted,
            sb.is_decaf, sb.cupping_score,

            (
                SELECT list(struct_pack(
                    note := note_value,
                    primary_category := (SELECT primary_category FROM tasting_notes_categories WHERE tasting_note = note_value LIMIT 1)
                ))
                FROM unnest(sb.tasting_notes) AS u(note_value)
            ) AS tasting_notes_with_categories,

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

    # Parameters must be passed in order of `?` appearance in the SQL:
    # 1. params         → score_calculation_clause in the WITH CTE
    # 2. currency_params → price/currency columns in the outer SELECT
    # 3. score_threshold → filter_clause WHERE (only in strict mode: WHERE score = ?)
    # 4. per_page/offset → LIMIT ? OFFSET ?
    score_threshold_params = [max_possible_score] if (max_possible_score > 0 and not is_scoring_mode) else []
    results = conn.execute(
        main_query,
        list(params) + currency_params + score_threshold_params + [per_page, offset],
    ).fetchall()

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
                   o.process, o.variety, o.variety_canonical, o.harvest_date, o.latitude, o.longitude,
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
                "variety_canonical": origin_row[8] if origin_row[8] else None,
                "harvest_date": origin_row[9],
                "latitude": origin_row[10] or 0.0,
                "longitude": origin_row[11] or 0.0,
                "country_full_name": origin_row[12] if origin_row[12] and origin_row[12].strip() else None,
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
        try:
            search_result = APISearchResult(**bean_dict)
        except ValidationError as e:
            logger.error(f"Validation error for bean ID {bean_dict.get('bean_url_path')}: {e}")
            logger.error(f"Bean data: {bean_dict}")
            raise e

        coffee_beans.append(search_result)

    # Create pagination info

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


@app.post("/v1/search/by-paths", response_model=APIResponse[list[APISearchResult]])
async def search_beans_by_paths(
    request: BeanPathsRequest = Body(...),
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
    convert_to_currency: str | None = Query(
        None, description="Convert prices to this currency code (e.g., EUR, GBP, JPY)"
    ),
):
    """
    Search coffee beans by a list of bean_url_path values with optional filters.

    This endpoint accepts a POST request with a list of bean_url_path strings in the body,
    and applies the same filter parameters as the search endpoint.
    """
    convert_to_currency = validate_currency_code(convert_to_currency)

    # Create filter parameters object
    filter_params = FilterParams(
        query=query,
        tasting_notes_query=tasting_notes_query,
        roaster=roaster,
        roaster_location=roaster_location,
        origin=origin,
        region=region,
        producer=producer,
        farm=farm,
        roast_level=roast_level,
        roast_profile=roast_profile,
        process=process,
        variety=variety,
        min_price=min_price,
        max_price=max_price,
        min_weight=min_weight,
        max_weight=max_weight,
        in_stock_only=in_stock_only,
        is_decaf=is_decaf,
        is_single_origin=is_single_origin,
        min_cupping_score=min_cupping_score,
        max_cupping_score=max_cupping_score,
        min_elevation=min_elevation,
        max_elevation=max_elevation,
        convert_to_currency=convert_to_currency,
        tasting_notes_only=False,
    )

    # Build filters using shared function
    filter_result = build_coffee_bean_filters(filter_params, use_scoring=False)
    conditions = filter_result.conditions
    params = filter_result.params

    # Add bean_url_path filter
    path_placeholders = ", ".join(["?" for _ in request.bean_url_paths])
    path_condition = f"sb.bean_url_path IN ({path_placeholders})"
    conditions.append(path_condition)
    params.extend(request.bean_url_paths)

    # Build WHERE clause - replace 'cb' with 'sb' to match our query alias
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    where_clause = where_clause.replace("cb.", "sb.")

    # Build the main query. Pre-build the parameterized currency SQL fragments first.
    price_sql, currency_sql, price_converted_sql, currency_params = _build_currency_select_sql(convert_to_currency)
    main_query = f"""
        WITH latest_beans AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
            FROM coffee_beans_with_origin cb
        )
        SELECT DISTINCT
            sb.id as bean_id, sb.name, sb.roaster, sb.url, sb.is_single_origin,
            sb.roast_level, sb.roast_profile, sb.weight,
            {price_sql} as price,
            {currency_sql} as currency,
            sb.price as original_price, sb.currency as original_currency,
            {price_converted_sql} as price_converted,
            sb.is_decaf, sb.cupping_score,

            (
                SELECT list(struct_pack(
                    note := note_value,
                    primary_category := (SELECT primary_category FROM tasting_notes_categories WHERE tasting_note = note_value LIMIT 1)
                ))
                FROM unnest(sb.tasting_notes) AS u(note_value)
            ) AS tasting_notes_with_categories,

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
            FIRST_VALUE(sb.country_full_name) OVER (PARTITION BY sb.clean_url_slug ORDER BY sb.scraped_at DESC) as country_full_name
        FROM latest_beans sb
        LEFT JOIN roasters_with_location rwl ON sb.roaster = rwl.name
        WHERE sb.rn = 1 AND {where_clause}
        ORDER BY sb.name
    """

    # Use the currency_params computed above together with filter params.
    results = conn.execute(main_query, currency_params + params).fetchall()

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
                   o.process, o.variety, o.variety_canonical, o.harvest_date, o.latitude, o.longitude,
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
                "variety_canonical": origin_row[8] if origin_row[8] else None,
                "harvest_date": origin_row[9],
                "latitude": origin_row[10] or 0.0,
                "longitude": origin_row[11] or 0.0,
                "country_full_name": origin_row[12] if origin_row[12] and origin_row[12].strip() else None,
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

    return APIResponse.success_response(
        data=coffee_beans,
        metadata={
            "total_results": len(coffee_beans),
            "requested_paths": len(request.bean_url_paths),
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
@cached(cache=SimpleMemoryCache)
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
@cached(cache=SimpleMemoryCache)
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


@app.get("/v1/origins", response_model=APIResponse[list[dict]])
@cached(cache=SimpleMemoryCache)
async def get_origins():
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


@app.get("/v1/origins/{country_code}", response_model=APIResponse[CountryDetailResponse])
@cached(cache=SimpleMemoryCache)
async def get_country_detail(country_code: str):
    """Get detailed statistics and hierarchy for a specific country."""
    # Setup profiling helper
    query_count = 0
    request_id = int(time.time())
    temp_table = f"_country_beans_{request_id}"

    def profiled_execute(query, params=None):
        nonlocal query_count
        query_count += 1

        if not ENABLE_PROFILING:
             return conn.execute(query, params) if params is not None else conn.execute(query)

        profile_file = f"duckdb_profile_{request_id}_country_q{query_count}.json"
        conn.execute("PRAGMA enable_profiling = 'json'")
        conn.execute(f"PRAGMA profiling_output = '{profile_file}'")

        start = time.perf_counter()
        result = conn.execute(query, params) if params is not None else conn.execute(query)
        duration = time.perf_counter() - start

        print(f"PROFILER [COUNTRY Q{query_count}]: Took {duration:.4f}s - Saved to {profile_file}")
        preview = " ".join(query.split())[:80] + "..."
        print(f"      SQL: {preview}")

        return result

    try:
        country_code = country_code.upper()

        # Get country name
        country_name_query = "SELECT name FROM country_codes WHERE alpha_2 = ?"
        country_name_result = conn.execute(country_name_query, [country_code]).fetchone()
        if not country_name_result:
            # Check if any beans exist for this country code even if not in country_codes table
            exists_query = "SELECT COUNT(*) FROM origins WHERE country = ?"
            count = conn.execute(exists_query, [country_code]).fetchone()[0]
            if count == 0:
                raise HTTPException(status_code=404, detail=f"Country '{country_code}' not found")
            country_name = country_code
        else:
            country_name = country_name_result[0]

        # Step 1: Materialize (Single slow scan)
        profiled_execute(
            f"""
            CREATE TEMPORARY TABLE {temp_table} AS
            SELECT
                o.bean_id, cb.roaster, cb.price_usd, cb.tasting_notes,
                o.state_canonical, o.region, o.region_normalized, o.farm, o.farm_canonical,
                o.elevation_min, o.elevation_max,
                o.variety, o.variety_canonical,
                o.process, o.process_common_name
            FROM origins o
            JOIN coffee_beans cb ON o.bean_id = cb.id
            WHERE o.country = ?
        """,
            [country_code],
        )

        # Step 2: Get aggregate statistics (Instant from temp table)
        stats_query = f"""
            SELECT
                COUNT(DISTINCT bean_id) as total_beans,
                COUNT(DISTINCT roaster) as total_roasters,
                COUNT(DISTINCT COALESCE(state_canonical, region)) filter (where region is not null and region != '') as total_regions,
                COUNT(DISTINCT COALESCE(farm_canonical, farm)) filter (where farm is not null and farm != '') as total_farms,
                AVG((NULLIF(elevation_min, 0) + NULLIF(elevation_max, 0)) / 2) as avg_elevation,
                AVG(price_usd) as avg_price_usd
            FROM {temp_table}
        """
        stats_row = profiled_execute(stats_query).fetchone()
        statistics = CountryStatistics(
            total_beans=stats_row[0] or 0,
            total_roasters=stats_row[1] or 0,
            total_regions=stats_row[2] or 0,
            total_farms=stats_row[3] or 0,
            avg_elevation=int(stats_row[4]) if stats_row[4] is not None else None,
            avg_price_usd=stats_row[5],
        )

        # Step 3: Top lists (Fast from temp table)
        roasters_query = f"""
            SELECT
                roaster,
                COUNT(DISTINCT bean_id) as bean_count
            FROM {temp_table}
            GROUP BY roaster
            ORDER BY bean_count DESC, roaster ASC
            LIMIT 10
        """
        roasters_rows = profiled_execute(roasters_query).fetchall()
        top_roasters = [TopRoaster(roaster_name=row[0], bean_count=row[1]) for row in roasters_rows]

        notes_query = f"""
            SELECT
                note,
                COUNT(DISTINCT bean_id) as frequency
            FROM (
                SELECT unnest(tasting_notes) as note, bean_id
                FROM {temp_table}
            )
            GROUP BY note
            ORDER BY frequency DESC, note ASC
            LIMIT 15
        """
        notes_rows = profiled_execute(notes_query).fetchall()
        common_tasting_notes = [TopNote(note=row[0], frequency=row[1]) for row in notes_rows]

        varietal_query = f"""
            SELECT
                canonical_variety,
                COUNT(DISTINCT bean_id) as count
            FROM (
                SELECT
                    unnest(CASE
                        WHEN variety_canonical IS NOT NULL AND len(variety_canonical) > 0 THEN variety_canonical
                        ELSE [variety]
                    END) as canonical_variety,
                    bean_id
                FROM {temp_table}
            )
            WHERE canonical_variety IS NOT NULL AND canonical_variety != ''
            GROUP BY canonical_variety
            ORDER BY count DESC, canonical_variety ASC
            LIMIT 10
        """
        varietal_rows = profiled_execute(varietal_query).fetchall()
        varietals = [TopVariety(variety=row[0], count=row[1]) for row in varietal_rows]

        process_query = f"""
            SELECT
                COALESCE(NULLIF(process_common_name, ''), NULLIF(process, ''), 'Unknown') as process_name,
                COUNT(DISTINCT bean_id) as count
            FROM {temp_table}
            GROUP BY process_name
            ORDER BY count DESC, process_name ASC
            LIMIT 10
        """
        process_rows = profiled_execute(process_query).fetchall()
        processing_methods = [TopProcess(process=row[0], count=row[1]) for row in process_rows]

        elevation_query = f"""
            SELECT
                MIN(NULLIF(elevation_min, 0)) as min_elevation,
                MAX(NULLIF(elevation_max, 0)) as max_elevation,
                AVG((NULLIF(elevation_min, 0) + NULLIF(elevation_max, 0)) / 2) as avg_elevation
            FROM {temp_table}
            WHERE elevation_min > 0 OR elevation_max > 0
        """
        elev_row = profiled_execute(elevation_query).fetchone()
        elevation_distribution = ElevationInfo(
            min=elev_row[0], max=elev_row[1], avg=int(elev_row[2]) if elev_row[2] is not None else None
        )

        regions_query = f"""
            SELECT
                FIRST(region) as region_name,
                COUNT(DISTINCT bean_id) as bean_count,
                COUNT(DISTINCT COALESCE(farm_canonical, farm)) FILTER (WHERE farm IS NOT NULL AND farm != '') as farm_count,
                BOOL_OR(state_canonical IS NOT NULL) as is_geocoded
            FROM {temp_table}
            WHERE region IS NOT NULL AND region != ''
            GROUP BY region_normalized
            ORDER BY bean_count DESC, region_name ASC
            LIMIT 10
        """
        regions_rows = profiled_execute(regions_query).fetchall()
        top_regions = [
            RegionSummary(region_name=row[0], bean_count=row[1], farm_count=row[2], is_geocoded=row[3])
            for row in regions_rows
        ]

        response_data = CountryDetailResponse(
            country_code=country_code,
            country_name=country_name,
            statistics=statistics,
            top_roasters=top_roasters,
            top_regions=top_regions,
            common_tasting_notes=common_tasting_notes,
            varietals=varietals,
            processing_methods=processing_methods,
            elevation_distribution=elevation_distribution,
        )
        return APIResponse.success_response(data=response_data)
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {temp_table}")
        conn.execute("PRAGMA disable_profiling")


@app.get("/v1/origins/{country_code}/regions", response_model=APIResponse[list[RegionSummary]])
@cached(cache=SimpleMemoryCache)
async def get_country_regions(country_code: str):
    """List all regions for a specific country, deduplicated by canonical state."""
    country_code = country_code.upper()

    query = """
        SELECT
            -- Prefer the canonical state name (from geocoding) when available;
            -- fall back to the most frequent raw region name for non-geocoded rows.
            COALESCE(
                MODE(o.state_canonical) FILTER (WHERE o.state_canonical IS NOT NULL),
                MODE(o.region)
            ) as region_name,
            COUNT(DISTINCT cb.id) as bean_count,
            COUNT(DISTINCT COALESCE(o.farm_canonical, o.farm_normalized)) filter (where o.farm is not null and o.farm != '') as farm_count,
            -- Check if region has been geocoded to a canonical state
            BOOL_OR(o.state_canonical IS NOT NULL) as is_geocoded
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.country = ?
          AND o.region IS NOT NULL
          AND o.region != ''
        -- Group by the canonical state slug when geocoded, otherwise by the
        -- raw region slug.  This merges all raw variants (e.g. "Sidama",
        -- "Sidamo", "Bensa, Sidama") that map to the same canonical state.
        GROUP BY COALESCE(normalize_region_name(o.state_canonical), o.region_normalized)
        ORDER BY bean_count DESC, region_name ASC
    """
    rows = conn.execute(query, [country_code]).fetchall()
    regions = [
        RegionSummary(region_name=row[0], bean_count=row[1], farm_count=row[2], is_geocoded=row[3]) for row in rows
    ]

    # Get unknown regions (where region is NULL or empty) as a single aggregated entry
    unknown_regions_query = """
        SELECT
            COUNT(DISTINCT cb.id) as bean_count,
            COUNT(DISTINCT COALESCE(o.farm_canonical, o.farm_normalized)) filter (where o.farm is not null and o.farm != '') as farm_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.country = ?
          AND (o.region IS NULL OR o.region = '')
    """
    unknown_regions_row = conn.execute(unknown_regions_query, [country_code]).fetchone()
    if unknown_regions_row and unknown_regions_row[0] > 0:
        regions.append(
            RegionSummary(
                region_name="Unknown Region",
                bean_count=unknown_regions_row[0],
                farm_count=unknown_regions_row[1],
                is_geocoded=False,
            )
        )

    return APIResponse.success_response(data=regions)


@app.get("/v1/origins/{country_code}/{region_slug}", response_model=APIResponse[RegionDetailResponse])
@cached(cache=SimpleMemoryCache)
async def get_region_detail(country_code: str, region_slug: str):
    """Get detailed statistics and farms for a specific region (state level) within a country."""
    # Setup profiling helper
    query_count = 0
    request_id = int(time.time())
    temp_table = f"_region_beans_{request_id}"

    def profiled_execute(query, params=None):
        nonlocal query_count
        query_count += 1

        if not ENABLE_PROFILING:
            return conn.execute(query, params) if params is not None else conn.execute(query)

        profile_file = f"duckdb_profile_{request_id}_q{query_count}.json"
        conn.execute("PRAGMA enable_profiling = 'json'")
        conn.execute(f"PRAGMA profiling_output = '{profile_file}'")

        start = time.perf_counter()
        result = conn.execute(query, params) if params is not None else conn.execute(query)
        duration = time.perf_counter() - start

        print(f"PROFILER [Q{query_count}]: Took {duration:.4f}s - Saved to {profile_file}")
        preview = " ".join(query.split())[:80] + "..."
        print(f"      SQL: {preview}")

        return result

    try:
        country_code = country_code.upper()
        region_slug = region_slug.lower()

        # Step 1: Materialize the IDs for this region (The single slow scan)
        if region_slug == "unknown-region":
            region_filter_sql = "o.country = ? AND (o.region IS NULL OR o.region = '')"
            filter_params = [country_code]
        else:
            # Must use the same COALESCE expression as the regions-list GROUP BY
            # so that a geocoded row groups by its canonical slug, not the raw
            # region_normalized.  Using OR would leak rows whose raw slug
            # matches but whose canonical slug belongs to a different group
            # (e.g. region='Sidama Bensa' → canonical='sidama', not 'sidama-bensa').
            region_filter_sql = (
                "o.country = ? AND COALESCE(normalize_region_name(o.state_canonical), o.region_normalized) = ?"
            )
            filter_params = [country_code, region_slug]

        profiled_execute(
            f"""
            CREATE TEMPORARY TABLE {temp_table} AS
            SELECT DISTINCT bean_id, state_canonical, region, country
            FROM origins o
            WHERE {region_filter_sql}
        """,
            filter_params,
        )

        # Check if we found anything
        count_row = conn.execute(f"SELECT COUNT(*) FROM {temp_table}").fetchone()
        if not count_row or count_row[0] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Region '{region_slug}' not found in country '{country_code}'",
            )

        # Step 2: Get display info (Instant from temp table)
        if region_slug == "unknown-region":
            display_region_name = "Unknown Region"
        else:
            # Prefer the canonical state name (from geocoding) when available;
            # fall back to the most frequent raw region name for non-geocoded rows.
            # This is consistent with the regions-list endpoint.
            name_row = profiled_execute(f"""
                SELECT COALESCE(
                    MODE(state_canonical) FILTER (WHERE state_canonical IS NOT NULL),
                    MODE(region) FILTER (WHERE region IS NOT NULL AND region != '')
                ) as display_name
                FROM {temp_table}
            """).fetchone()
            display_region_name = name_row[0] if name_row and name_row[0] else region_slug

        country_name_query = "SELECT name FROM country_codes WHERE alpha_2 = ?"
        country_name_result = profiled_execute(country_name_query, [country_code]).fetchone()
        country_name = country_name_result[0] if country_name_result else country_code

        # Step 3: Run all detail queries against the temp table (Extremely fast)
        # Re-use region_filter_sql on every origins join so a bean that appears in
        # multiple regions only contributes data for the region being viewed.
        stats_query = f"""
            SELECT
                COUNT(DISTINCT cb.id) as total_beans,
                COUNT(DISTINCT cb.roaster) as total_roasters,
                COUNT(DISTINCT COALESCE(o.farm_canonical, o.farm_normalized)) FILTER (WHERE o.farm IS NOT NULL AND o.farm != '') as total_farms,
                AVG((NULLIF(o.elevation_min, 0) + NULLIF(o.elevation_max, 0)) / 2) as avg_elevation,
                AVG(cb.price_usd) as avg_price_usd
            FROM {temp_table} t
            JOIN coffee_beans cb ON t.bean_id = cb.id
            JOIN origins o ON t.bean_id = o.bean_id AND {region_filter_sql}
        """
        stats_row = profiled_execute(stats_query, filter_params).fetchone()
        statistics = RegionStatistics(
            total_beans=stats_row[0] or 0,
            total_roasters=stats_row[1] or 0,
            total_farms=stats_row[2] or 0,
            avg_elevation=int(stats_row[3]) if stats_row[3] is not None else None,
            avg_price_usd=stats_row[4],
        )

        farms_query = f"""
            SELECT
                COALESCE(ANY_VALUE(o.farm_canonical), arg_max(o.farm, length(o.farm))) as farm_display_name,
                arg_max(o.producer, length(o.producer)) as producer_display_name,
                COUNT(DISTINCT cb.id) as bean_count,
                AVG((NULLIF(o.elevation_min, 0) + NULLIF(o.elevation_max, 0)) / 2) as avg_elevation
            FROM {temp_table} t
            JOIN origins o ON t.bean_id = o.bean_id AND {region_filter_sql}
            JOIN coffee_beans cb ON t.bean_id = cb.id
            WHERE o.farm IS NOT NULL AND o.farm != ''
            GROUP BY COALESCE(o.farm_canonical, o.farm_normalized)
            ORDER BY bean_count DESC
        """
        farms_rows = profiled_execute(farms_query, filter_params).fetchall()
        farms = [
            FarmSummary(
                farm_name=row[0],
                producer_name=row[1],
                bean_count=row[2],
                avg_elevation=int(row[3]) if row[3] is not None else None,
            )
            for row in farms_rows
        ]

        unknown_farms_query = f"""
            SELECT
                COUNT(DISTINCT cb.id) as bean_count,
                AVG((NULLIF(o.elevation_min, 0) + NULLIF(o.elevation_max, 0)) / 2) as avg_elevation
            FROM {temp_table} t
            JOIN origins o ON t.bean_id = o.bean_id AND {region_filter_sql}
            JOIN coffee_beans cb ON t.bean_id = cb.id
            WHERE (o.farm IS NULL OR o.farm = '')
        """
        unknown_farms_row = profiled_execute(unknown_farms_query, filter_params).fetchone()
        if unknown_farms_row and unknown_farms_row[0] > 0:
            farms.append(
                FarmSummary(
                    farm_name="Unknown Farm",
                    producer_name=None,
                    bean_count=unknown_farms_row[0],
                    avg_elevation=int(unknown_farms_row[1]) if unknown_farms_row[1] is not None else None,
                )
            )

        roasters_query = f"""
            SELECT
                cb.roaster,
                COUNT(DISTINCT cb.id) as bean_count
            FROM {temp_table} t
            JOIN coffee_beans cb ON t.bean_id = cb.id
            GROUP BY cb.roaster
            ORDER BY bean_count DESC, cb.roaster ASC
            LIMIT 10
        """
        roasters_rows = profiled_execute(roasters_query).fetchall()
        top_roasters = [TopRoaster(roaster_name=row[0], bean_count=row[1]) for row in roasters_rows]

        notes_query = f"""
            SELECT
                note,
                COUNT(DISTINCT bean_id) as frequency
            FROM (
                SELECT unnest(cb.tasting_notes) as note, cb.id as bean_id
                FROM {temp_table} t
                JOIN coffee_beans cb ON t.bean_id = cb.id
            )
            GROUP BY note
            ORDER BY frequency DESC, note ASC
            LIMIT 15
        """
        notes_rows = profiled_execute(notes_query).fetchall()
        common_tasting_notes = [TopNote(note=row[0], frequency=row[1]) for row in notes_rows]

        varietal_query = f"""
            SELECT
                canonical_variety,
                COUNT(DISTINCT bean_id) as count
            FROM (
                SELECT
                    unnest(CASE
                        WHEN o.variety_canonical IS NOT NULL AND len(o.variety_canonical) > 0 THEN o.variety_canonical
                        ELSE [o.variety]
                    END) as canonical_variety,
                    cb.id as bean_id
                FROM {temp_table} t
                JOIN origins o ON t.bean_id = o.bean_id AND {region_filter_sql}
                JOIN coffee_beans cb ON t.bean_id = cb.id
            )
            WHERE canonical_variety IS NOT NULL AND canonical_variety != ''
            GROUP BY canonical_variety
            ORDER BY count DESC, canonical_variety ASC
            LIMIT 10
        """
        varietal_rows = profiled_execute(varietal_query, filter_params).fetchall()
        varietals = [TopVariety(variety=row[0], count=row[1]) for row in varietal_rows]

        process_query = f"""
            SELECT
                COALESCE(NULLIF(o.process_common_name, ''), NULLIF(o.process, ''), 'Unknown') as process_name,
                COUNT(DISTINCT cb.id) as count
            FROM {temp_table} t
            JOIN origins o ON t.bean_id = o.bean_id AND {region_filter_sql}
            JOIN coffee_beans cb ON t.bean_id = cb.id
            GROUP BY process_name
            ORDER BY count DESC, process_name ASC
            LIMIT 10
        """
        process_rows = profiled_execute(process_query, filter_params).fetchall()
        processing_methods = [TopProcess(process=row[0], count=row[1]) for row in process_rows]

        elevation_query = f"""
            SELECT
                MIN(NULLIF(o.elevation_min, 0)) as min_elevation,
                MAX(NULLIF(o.elevation_max, 0)) as max_elevation,
                AVG((NULLIF(o.elevation_min, 0) + NULLIF(o.elevation_max, 0)) / 2) as avg_elevation
            FROM {temp_table} t
            JOIN origins o ON t.bean_id = o.bean_id AND {region_filter_sql}
            WHERE (o.elevation_min > 0 OR o.elevation_max > 0)
        """
        elev_row = profiled_execute(elevation_query, filter_params).fetchone()
        elevation_range = ElevationInfo(
            min=elev_row[0], max=elev_row[1], avg=int(elev_row[2]) if elev_row[2] is not None else None
        )

        is_geocoded_query = f"SELECT BOOL_OR(state_canonical IS NOT NULL) FROM {temp_table}"
        is_geocoded_row = profiled_execute(is_geocoded_query).fetchone()
        is_geocoded = is_geocoded_row[0] if is_geocoded_row and is_geocoded_row[0] is not None else False

        response_data = RegionDetailResponse(
            region_name=display_region_name,
            country_code=country_code,
            country_name=country_name,
            statistics=statistics,
            top_farms=farms,
            top_roasters=top_roasters,
            common_tasting_notes=common_tasting_notes,
            varietals=varietals,
            processing_methods=processing_methods,
            elevation_range=elevation_range,
            is_geocoded=is_geocoded,
        )

        return APIResponse.success_response(data=response_data)
    finally:
        # Final cleanup
        conn.execute(f"DROP TABLE IF EXISTS {temp_table}")
        conn.execute("PRAGMA disable_profiling")


@app.get("/v1/origins/{country_code}/{region_slug}/{farm_slug}", response_model=APIResponse[FarmDetailResponse])
@cached(cache=SimpleMemoryCache)
async def get_farm_detail(
    country_code: str,
    region_slug: str,
    farm_slug: str,
    convert_to_currency: str | None = Query(None, description="Currency to convert prices to (e.g. USD, EUR)"),
):
    """Get detailed information for a specific farm, including associated beans."""
    convert_to_currency = validate_currency_code(convert_to_currency)
    # Setup profiling helper
    query_count = 0
    request_id = int(time.time())
    temp_table = f"_farm_beans_{request_id}"

    def profiled_execute(query, params=None):
        nonlocal query_count
        query_count += 1

        if not ENABLE_PROFILING:
             return conn.execute(query, params) if params is not None else conn.execute(query)

        profile_file = f"duckdb_profile_{request_id}_farm_q{query_count}.json"
        conn.execute("PRAGMA enable_profiling = 'json'")
        conn.execute(f"PRAGMA profiling_output = '{profile_file}'")

        start = time.perf_counter()
        result = conn.execute(query, params) if params is not None else conn.execute(query)
        duration = time.perf_counter() - start

        print(f"PROFILER [FARM Q{query_count}]: Took {duration:.4f}s - Saved to {profile_file}")
        preview = " ".join(query.split())[:80] + "..."
        print(f"      SQL: {preview}")

        return result

    try:
        country_code = country_code.upper()
        region_slug = region_slug.lower()
        farm_slug = farm_slug.lower()

        # Step 1: Materialize the target rows for this specific farm (The single slow scan)
        if region_slug == "unknown-region":
            region_filter_sql = "(o.region IS NULL OR o.region = '')"
            region_params = []
        else:
            region_filter_sql = "COALESCE(normalize_region_name(o.state_canonical), o.region_normalized) = ?"
            region_params = [region_slug]

        if farm_slug == "unknown-farm":
            farm_filter_sql = "(o.farm IS NULL OR o.farm = '')"
            farm_params = []
        else:
            farm_filter_sql = "(normalize_farm_name(o.farm_canonical) = ? OR o.farm_normalized = ?)"
            farm_params = [farm_slug, farm_slug]

        profiled_execute(f"""
            CREATE TEMPORARY TABLE {temp_table} AS
            SELECT DISTINCT
                o.bean_id, o.country, o.region, o.state_canonical, o.farm, o.farm_canonical,
                o.farm_normalized, o.producer, o.latitude, o.longitude, o.elevation_min,
                o.elevation_max, o.process, o.process_common_name, o.variety, o.variety_canonical
            FROM origins o
            WHERE o.country = ?
            AND {region_filter_sql}
            AND {farm_filter_sql}
        """, [country_code] + region_params + farm_params)

        # Check if we found anything
        count_row = conn.execute(f"SELECT COUNT(*) FROM {temp_table}").fetchone()
        if not count_row or count_row[0] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Farm '{farm_slug}' not found in region '{region_slug}' (Country: {country_code})",
            )

        # Step 2: Get display info (Instant from temp table)
        farm_display_name_row = profiled_execute(f"""
            SELECT
                COALESCE(
                    ANY_VALUE(farm_canonical),
                    arg_max(farm, length(farm)),
                    ANY_VALUE(farm_normalized),
                    'Unknown Farm'
                )
            FROM {temp_table}
        """).fetchone()
        actual_farm = farm_display_name_row[0]

        if region_slug == "unknown-region":
            actual_region = "Unknown Region"
        else:
            region_name_row = profiled_execute(f"""
                SELECT COALESCE(ANY_VALUE(state_canonical), arg_max(region, length(region)))
                FROM {temp_table}
            """).fetchone()
            actual_region = region_name_row[0] if region_name_row and region_name_row[0] else region_slug

        country_name_query = "SELECT name FROM country_codes WHERE alpha_2 = ?"
        country_name_result = profiled_execute(country_name_query, [country_code]).fetchone()
        country_name = country_name_result[0] if country_name_result else country_code

        # Step 3: Get farm environmental details (Instant from temp table)
        farm_row = profiled_execute(f"""
            SELECT
                AVG(latitude) as latitude,
                AVG(longitude) as longitude,
                MIN(NULLIF(elevation_min, 0)) as elevation_min,
                MAX(NULLIF(elevation_max, 0)) as max_elevation
            FROM {temp_table}
        """).fetchone()
        lat, lng, elev_min, elev_max = farm_row

        # Step 4: Get beans and their nested data (Using temp table)
        beans_query = f"""
            SELECT DISTINCT
                cb.id as bean_id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
                cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
                cb.is_decaf, cb.cupping_score,
                (
                    SELECT list(struct_pack(
                        note := note_value,
                        primary_category := (SELECT primary_category FROM tasting_notes_categories WHERE tasting_note = note_value LIMIT 1)
                    ))
                    FROM unnest(cb.tasting_notes) AS u(note_value)
                ) AS tasting_notes_with_categories,
                cb.description, cb.in_stock, cb.scraped_at, cb.scraper_version, cb.image_url,
                cb.clean_url_slug, cb.bean_url_path, cb.price_paid_for_green_coffee,
                cb.currency_of_price_paid_for_green_coffee, rwl.roaster_country_code
            FROM (
                SELECT DISTINCT ON (clean_url_slug) *
                FROM coffee_beans cb_inner
                WHERE id IN (SELECT bean_id FROM {temp_table})
                ORDER BY clean_url_slug, scraped_at DESC
            ) cb
            LEFT JOIN roasters_with_location rwl ON cb.roaster = rwl.name
            ORDER BY cb.name ASC
        """
        bean_rows = profiled_execute(beans_query).fetchall()

        columns = [
            "id", "name", "roaster", "url", "is_single_origin", "roast_level", "roast_profile",
            "weight", "price", "currency", "is_decaf", "cupping_score", "tasting_notes_with_categories",
            "description", "in_stock", "scraped_at", "scraper_version", "image_url", "clean_url_slug",
            "bean_url_path", "price_paid_for_green_coffee", "currency_of_price_paid_for_green_coffee",
            "roaster_country_code"
        ]

        coffee_beans = []
        for row in bean_rows:
            bean_dict = dict(zip(columns, row))
            bean_dict["tasting_notes"] = bean_dict.pop("tasting_notes_with_categories")

            if convert_to_currency:
                target_currency = convert_to_currency.upper()
                if bean_dict.get("price") is not None and bean_dict.get("currency"):
                    converted = convert_price(conn, bean_dict["price"], bean_dict["currency"], target_currency)
                    if converted is not None:
                        bean_dict["price"] = round(converted, 2)
                        bean_dict["currency"] = target_currency

                if bean_dict.get("price_paid_for_green_coffee") is not None and bean_dict.get("currency_of_price_paid_for_green_coffee"):
                    converted_green = convert_price(
                        conn, bean_dict["price_paid_for_green_coffee"],
                        bean_dict["currency_of_price_paid_for_green_coffee"], target_currency
                    )
                    if converted_green is not None:
                        bean_dict["price_paid_for_green_coffee"] = round(converted_green, 2)
                        bean_dict["currency_of_price_paid_for_green_coffee"] = target_currency

            # Fetch origins for this bean using the full origins table, but limited to this bean
            origins_query = """
                SELECT o.country, o.region, o.producer, o.farm, o.elevation_min, o.elevation_max,
                       COALESCE(NULLIF(o.process_common_name, ''), o.process) as process, o.variety, o.variety_canonical, o.harvest_date, o.latitude, o.longitude,
                       cc.name as country_full_name
                FROM origins o
                LEFT JOIN country_codes cc ON o.country = cc.alpha_2
                WHERE o.bean_id = ?
                ORDER BY o.id
            """
            origins_results = conn.execute(origins_query, [bean_dict["id"]]).fetchall()
            origins = [APIBean(**{
                "country": r[0], "region": r[1], "producer": r[2], "farm": r[3], "elevation_min": r[4],
                "elevation_max": r[5], "process": r[6], "variety": r[7], "variety_canonical": r[8],
                "harvest_date": r[9], "latitude": r[10], "longitude": r[11], "country_full_name": r[12]
            }) for r in origins_results]

            bean_dict["origins"] = origins
            coffee_beans.append(APISearchResult(**bean_dict))

        # Additional statistics (Fast from temp table)
        producer_rows = profiled_execute(f"""
            SELECT producer, COUNT(*) as mention_count
            FROM {temp_table}
            WHERE producer IS NOT NULL AND producer != ''
            GROUP BY producer
            ORDER BY mention_count DESC, length(producer) DESC
        """).fetchall()

        cleaned_producers = {}
        for p_name, p_count in producer_rows:
            norm_name = normalize_farm_name(p_name)
            if norm_name not in cleaned_producers:
                cleaned_producers[norm_name] = {"name": p_name, "mention_count": p_count}
            else:
                cleaned_producers[norm_name]["mention_count"] += p_count

        producers = sorted(cleaned_producers.values(), key=lambda x: (x["mention_count"], len(x["name"])), reverse=True)
        producer_name = producers[0]["name"] if producers else None

        notes_query = f"""
            SELECT note, COUNT(*) as frequency
            FROM (
                SELECT unnest(cb.tasting_notes) as note
                FROM coffee_beans cb
                WHERE id IN (SELECT bean_id FROM {temp_table})
            )
            GROUP BY note
            ORDER BY frequency DESC, note ASC
            LIMIT 10
        """
        notes_rows = profiled_execute(notes_query).fetchall()
        common_tasting_notes = [TopNote(note=row[0], frequency=row[1]) for row in notes_rows]

        varietal_query = f"""
            SELECT canonical_variety, COUNT(DISTINCT bean_id) as count
            FROM (
                SELECT
                    unnest(CASE
                        WHEN variety_canonical IS NOT NULL AND len(variety_canonical) > 0 THEN variety_canonical
                        ELSE [variety]
                    END) as canonical_variety,
                    bean_id
                FROM {temp_table}
            )
            WHERE canonical_variety IS NOT NULL AND canonical_variety != ''
            GROUP BY canonical_variety
            ORDER BY count DESC, canonical_variety ASC
        """
        varietal_rows = profiled_execute(varietal_query).fetchall()
        varietals = [TopVariety(variety=row[0], count=row[1]) for row in varietal_rows]

        process_query = f"""
            SELECT
                COALESCE(NULLIF(process_common_name, ''), NULLIF(process, ''), 'Unknown') as process_name,
                COUNT(DISTINCT bean_id) as count
            FROM {temp_table}
            GROUP BY process_name
            ORDER BY count DESC, process_name ASC
        """
        process_rows = profiled_execute(process_query).fetchall()
        processing_methods = [TopProcess(process=row[0], count=row[1]) for row in process_rows]

        response_data = FarmDetailResponse(
            farm_name=actual_farm, producer_name=producer_name, producers=producers,
            region_name=actual_region, country_code=country_code, country_name=country_name,
            latitude=lat, longitude=lng, elevation_min=elev_min, elevation_max=elev_max,
            beans=coffee_beans, varietals=varietals, processing_methods=processing_methods,
            common_tasting_notes=common_tasting_notes,
        )
        return APIResponse.success_response(data=response_data)
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {temp_table}")
        conn.execute("PRAGMA disable_profiling")


@app.get("/v1/country-codes", response_model=APIResponse[list[dict]])
@cached(cache=SimpleMemoryCache)
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


@app.get("/v1/search/origins", response_model=APIResponse[list[OriginSearchResult]])
async def search_origins(
    q: str = Query(..., description="Search query for countries, regions, or farms"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
):
    """Search for countries, regions, and farms matching the query."""
    if not q.strip():
        return APIResponse.success_response(data=[])

    search_term = f"%{q}%"

    # Search countries
    countries_query = """
        SELECT
            'country' as type,
            cc.name as name,
            cc.alpha_2 as country_code,
            cc.name as country_name,
            NULL as region_name,
            NULL as region_slug,
            NULL as farm_slug,
            NULL as producer_name,
            COUNT(DISTINCT cb.id) as bean_count
        FROM country_codes cc
        LEFT JOIN origins o ON cc.alpha_2 = o.country
        LEFT JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE strip_accents(cc.name) ILIKE strip_accents(?) OR cc.alpha_2 ILIKE ?
        GROUP BY cc.name, cc.alpha_2
        ORDER BY bean_count DESC
        LIMIT ?
    """

    # Search regions
    regions_query = """
        SELECT
            'region' as type,
            COALESCE(
                ANY_VALUE(o.state_canonical),
                arg_max(o.region, length(o.region))
            ) as name,
            o.country as country_code,
            arg_max(cc.name, length(cc.name)) as country_name,
            COALESCE(
                ANY_VALUE(o.state_canonical),
                arg_max(o.region, length(o.region))
            ) as region_name,
            normalize_region_name(COALESCE(o.state_canonical, o.region, 'unknown-region')) as region_slug,
            NULL as farm_slug,
            NULL as producer_name,
            COUNT(DISTINCT o.bean_id) as bean_count
        FROM origins o
        JOIN country_codes cc ON o.country = cc.alpha_2
        WHERE o.region_unaccented ILIKE strip_accents(?) OR o.state_canonical_unaccented ILIKE strip_accents(?)
        GROUP BY
            o.country,
            normalize_region_name(COALESCE(o.state_canonical, o.region, 'unknown-region'))
        ORDER BY bean_count DESC
        LIMIT ?
    """

    # Search farms
    farms_query = """
        SELECT
            'farm' as type,
            COALESCE(
                ANY_VALUE(o.farm_canonical),
                arg_max(o.farm, length(o.farm))
            ) as name,
            o.country as country_code,
            arg_max(cc.name, length(cc.name)) as country_name,
            COALESCE(
                ANY_VALUE(o.state_canonical),
                arg_max(o.region, length(o.region))
            ) as region_name,
            normalize_region_name(COALESCE(o.state_canonical, o.region, 'unknown-region')) as region_slug,
            normalize_farm_name(COALESCE(
                ANY_VALUE(o.farm_canonical),
                ANY_VALUE(o.farm_normalized)
            )) as farm_slug,
            arg_max(o.producer, length(o.producer)) as producer_name,
            COUNT(DISTINCT o.bean_id) as bean_count
        FROM origins o
        JOIN country_codes cc ON o.country = cc.alpha_2
        WHERE o.farm_unaccented ILIKE strip_accents(?)
        OR o.producer_unaccented ILIKE strip_accents(?)
        GROUP BY
            o.country,
            normalize_region_name(COALESCE(o.state_canonical, o.region, 'unknown-region')),
            COALESCE(o.farm_canonical, o.farm_normalized)
        ORDER BY bean_count DESC
        LIMIT ?
    """

    results = []

    # Run queries
    # Country results
    country_rows = conn.execute(countries_query, [search_term, search_term, limit]).fetchall()
    for row in country_rows:
        results.append(
            OriginSearchResult(
                type=row[0],
                name=row[1],
                country_code=row[2],
                country_name=row[3],
                region_name=row[4],
                region_slug=row[5],
                farm_slug=row[6],
                producer_name=row[7],
                bean_count=row[8],
            )
        )

    # Region results
    region_rows = conn.execute(regions_query, [search_term, search_term, limit]).fetchall()
    for row in region_rows:
        results.append(
            OriginSearchResult(
                type=row[0],
                name=row[1],
                country_code=row[2],
                country_name=row[3],
                region_name=row[4],
                region_slug=row[5],
                farm_slug=row[6],
                producer_name=row[7],
                bean_count=row[8],
            )
        )

    # Farm results
    farm_rows = conn.execute(farms_query, [search_term, search_term, limit]).fetchall()
    for row in farm_rows:
        results.append(
            OriginSearchResult(
                type=row[0],
                name=row[1],
                country_code=row[2],
                country_name=row[3],
                region_name=row[4],
                region_slug=row[5],
                farm_slug=row[6],
                producer_name=row[7],
                bean_count=row[8],
            )
        )

    # Sort results by bean count descending
    results.sort(key=lambda x: x.bean_count, reverse=True)

    # Final limit
    return APIResponse.success_response(data=results[:limit])


@app.get("/v1/beans/{roaster_slug}/{bean_slug}", response_model=APIResponse[APICoffeeBean])
async def get_bean_by_slug(
    roaster_slug: str,
    bean_slug: str,
    convert_to_currency: str | None = Query(
        None, description="Convert prices to this currency code (e.g., EUR, GBP, JPY)"
    ),
):
    """Get a specific coffee bean by roaster slug and bean slug from URL-friendly paths."""
    convert_to_currency = validate_currency_code(convert_to_currency)

    expected_bean_url_path = f"/{roaster_slug}/{bean_slug}"

    query = """
        SELECT DISTINCT
            cb.id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
            cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
            cb.is_decaf, cb.cupping_score,

            (
                SELECT list(struct_pack(
                    note := note_value,
                    primary_category := (SELECT primary_category FROM tasting_notes_categories WHERE tasting_note = note_value LIMIT 1)
                ))
                FROM unnest(cb.tasting_notes) AS u(note_value)
            ) AS tasting_notes_with_categories,

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
               o.process, o.variety, o.variety_canonical, o.harvest_date, o.latitude, o.longitude,
               cc.name as country_full_name,
               o.state_canonical AS region_canonical,
               COALESCE(o.farm_canonical, o.farm) AS farm_canonical
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
            "variety_canonical": origin_row[8] if origin_row[8] else None,
            "harvest_date": origin_row[9],
            "latitude": origin_row[10] or 0.0,
            "longitude": origin_row[11] or 0.0,
            "country_full_name": origin_row[12],
            "region_canonical": origin_row[13] if origin_row[13] and origin_row[13].strip() else None,
            "farm_canonical": origin_row[14] if origin_row[14] and origin_row[14].strip() else None,
        }
        origins.append(APIBean(**origin_data))

    bean_data["origins"] = origins

    # Set default for bean_url_path if needed
    if not bean_data.get("bean_url_path"):
        bean_data["bean_url_path"] = ""

    # Handle currency conversion
    if convert_to_currency and convert_to_currency.upper() != bean_data.get("currency", "").upper():
        original_price = bean_data.get("price")
        original_currency = bean_data.get("currency")
        if original_price and original_currency:
            converted_price = convert_price(
                conn, original_price, original_currency.upper(), convert_to_currency.upper()
            )
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
    convert_to_currency = validate_currency_code(convert_to_currency)

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
                       o.process, o.variety, o.variety_canonical, o.harvest_date, o.latitude, o.longitude,
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
                    "variety_canonical": origin_row[8] if origin_row[8] else None,
                    "harvest_date": origin_row[9],
                    "latitude": origin_row[10] or 0.0,
                    "longitude": origin_row[11],
                    "country_full_name": origin_row[12],
                }
                origins.append(APIBean(**origin_data))

            bean_data["origins"] = origins

            # Handle currency conversion if requested
            if convert_to_currency and convert_to_currency.upper() != bean_data.get("currency", "").upper():
                original_price = bean_data.get("price")
                original_currency = bean_data.get("currency")

                if original_price and original_currency:
                    converted_price = convert_price(
                        conn, original_price, original_currency.upper(), convert_to_currency.upper()
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
@cached(cache=SimpleMemoryCache)
async def get_processes():
    """Get all coffee processing methods grouped by categories."""
    # Setup profiling helper
    query_count = 0
    request_id = int(time.time())

    def profiled_execute(query, params=None):
        nonlocal query_count
        query_count += 1

        if not ENABLE_PROFILING:
            return conn.execute(query, params) if params is not None else conn.execute(query)

        profile_file = f"duckdb_profile_{request_id}_processes_q{query_count}.json"
        conn.execute("PRAGMA enable_profiling = 'json'")
        conn.execute(f"PRAGMA profiling_output = '{profile_file}'")

        start = time.perf_counter()
        result = conn.execute(query, params) if params is not None else conn.execute(query)
        duration = time.perf_counter() - start

        print(f"PROFILER [PROCESSES Q{query_count}]: Took {duration:.4f}s - Saved to {profile_file}")
        preview = " ".join(query.split())[:80] + "..."
        print(f"      SQL: {preview}")

        return result

    try:
        # Step 1: Optimized query using structs and lists to avoid N+1
        main_query = """
            WITH process_stats AS (
                SELECT
                    o.process_common_name as process_name,
                    STRING_AGG(DISTINCT o.process, ' ') as process_original_names,
                    COUNT(DISTINCT cb.id) as bean_count,
                    COUNT(DISTINCT cb.roaster) as roaster_count,
                    COUNT(DISTINCT o.country) as country_count
                FROM origins o
                JOIN coffee_beans cb ON o.bean_id = cb.id
                WHERE o.process_common_name IS NOT NULL AND o.process_common_name != ''
                GROUP BY o.process_common_name
            ),
            country_stats AS (
                SELECT
                    o.process_common_name as process_name,
                    o.country,
                    cc.name as country_full_name,
                    COUNT(DISTINCT cb.id) as bean_count
                FROM origins o
                LEFT JOIN country_codes cc ON o.country = cc.alpha_2
                JOIN coffee_beans cb ON o.bean_id = cb.id
                WHERE o.process_common_name IS NOT NULL AND o.process_common_name != ''
                  AND o.country IS NOT NULL AND o.country != ''
                GROUP BY o.process_common_name, o.country, cc.name
            )
            SELECT
                p.process_name,
                p.process_original_names,
                p.bean_count,
                p.roaster_count,
                p.country_count,
                (
                    SELECT list(struct_pack(
                        country_code := cs.country,
                        country_name := COALESCE(cs.country_full_name, cs.country),
                        bean_count := cs.bean_count
                    ) ORDER BY cs.bean_count DESC, cs.country_full_name ASC)
                    FROM country_stats cs
                    WHERE cs.process_name = p.process_name
                ) as countries
            FROM process_stats p
            ORDER BY p.bean_count DESC
        """

        results = profiled_execute(main_query).fetchall()

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
            process_name, process_original_names, bean_count, roaster_count, country_count, countries_list = row
            category = categorize_process(process_name)
            process_slug = normalize_process_name(process_name)

            process_data = {
                "name": process_name,
                "original_names": process_original_names,
                "slug": process_slug,
                "bean_count": bean_count,
                "roaster_count": roaster_count,
                "country_count": country_count,
                "countries": [dict(c) for c in countries_list] if countries_list else [],
                "category": category,
            }

            categories[category]["processes"].append(process_data)

        # Calculate category totals
        for category_data in categories.values():
            total_beans = sum(p["bean_count"] for p in category_data["processes"])
            category_data["total_beans"] = total_beans

        return APIResponse.success_response(data=categories, metadata={"total_processes": len(results)})
    finally:
        conn.execute("PRAGMA disable_profiling")


@app.get("/v1/processes/{process_slug}", response_model=APIResponse[dict])
async def get_process_details(process_slug: str, convert_to_currency: str = "EUR"):
    """Get details for a specific coffee processing method."""

    # First, find the actual process_common_name from the slug efficiently
    query = """
        SELECT process_common_name, COUNT(*) as bean_count
        FROM origins
        WHERE process_common_slug = ? OR process_slug = ?
        GROUP BY process_common_name
        ORDER BY bean_count DESC
        LIMIT 1
    """

    row = conn.execute(query, [process_slug, process_slug]).fetchone()
    actual_process_common_name = row[0] if row else None

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
    converted_avg_price = convert_price(conn, avg_price, "USD", convert_to_currency)

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
    convert_to_currency = validate_currency_code(convert_to_currency)
    # Setup profiling helper
    query_count = 0
    request_id = int(time.time())
    temp_table = f"_process_beans_{request_id}"

    def profiled_execute(query, params=None):
        nonlocal query_count
        query_count += 1

        if not ENABLE_PROFILING:
             return conn.execute(query, params) if params is not None else conn.execute(query)

        profile_file = f"duckdb_profile_{request_id}_procbeans_q{query_count}.json"
        conn.execute("PRAGMA enable_profiling = 'json'")
        conn.execute(f"PRAGMA profiling_output = '{profile_file}'")

        start = time.perf_counter()
        result = conn.execute(query, params) if params is not None else conn.execute(query)
        duration = time.perf_counter() - start

        print(f"PROFILER [PROCESS_BEANS Q{query_count}]: Took {duration:.4f}s - Saved to {profile_file}")
        preview = " ".join(query.split())[:80] + "..."
        print(f"      SQL: {preview}")

        return result

    try:
        # Step 1: Find the actual process name from the slug efficiently
        # We search specifically for the slug without a full table aggregation
        slug_query = """
            SELECT process_common_name, COUNT(*) as bean_count
            FROM origins
            WHERE process_common_slug = ?
               OR process_slug = ?
            GROUP BY process_common_name
            ORDER BY bean_count DESC
            LIMIT 1
        """
        slug_result = profiled_execute(slug_query, [process_slug, process_slug]).fetchone()

        if not slug_result:
            raise HTTPException(status_code=404, detail=f"Process '{process_slug}' not found")

        actual_process = slug_result[0]

        # Step 2: Materialize the IDs for this process
        profiled_execute(f"""
            CREATE TEMPORARY TABLE {temp_table} AS
            SELECT DISTINCT bean_id
            FROM origins
            WHERE process_common_name = ?
        """, [actual_process])

        # Step 3: Get total count (Deduplicated by slug)
        count_query = f"""
            SELECT COUNT(DISTINCT cb.clean_url_slug)
            FROM {temp_table} t
            JOIN coffee_beans cb ON t.bean_id = cb.id
        """
        total_count = profiled_execute(count_query).fetchone()[0]

        # Pagination
        offset = (page - 1) * per_page
        total_pages = (total_count + per_page - 1) // per_page

        # Sorting logic
        sort_field_mapping = {
            "name": "cb.name",
            "roaster": "cb.roaster",
            "price": "cb.price_usd",
            "weight": "cb.weight",
            "scraped_at": "cb.scraped_at",
        }
        sort_col = sort_field_mapping.get(sort_by, "cb.name")
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Step 4: Main query with aggregated origins and tasting notes (No N+1)
        main_query = f"""
            SELECT
                cb.id as id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
                cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
                cb.is_decaf, cb.cupping_score,
                (
                    SELECT list(struct_pack(
                        note := note_value,
                        primary_category := (SELECT primary_category FROM tasting_notes_categories WHERE tasting_note = note_value LIMIT 1)
                    ))
                    FROM unnest(cb.tasting_notes) AS u(note_value)
                ) AS tasting_notes,
                cb.description, cb.in_stock,
                cb.scraped_at, cb.scraper_version, cb.image_url, cb.clean_url_slug,
                cb.bean_url_path, cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
                rwl.roaster_country_code,
                (
                    SELECT list(struct_pack(
                        country := o.country,
                        region := o.region,
                        producer := o.producer,
                        farm := o.farm,
                        elevation_min := COALESCE(o.elevation_min, 0),
                        elevation_max := COALESCE(o.elevation_max, o.elevation_min, 0),
                        process := o.process,
                        variety := o.variety,
                        variety_canonical := o.variety_canonical,
                        harvest_date := o.harvest_date,
                        latitude := COALESCE(o.latitude, 0.0),
                        longitude := COALESCE(o.longitude, 0.0),
                        country_full_name := cc.name,
                        region_canonical := o.state_canonical,
                        farm_canonical := COALESCE(o.farm_canonical, o.farm)
                    ) ORDER BY o.id)
                    FROM origins o
                    LEFT JOIN country_codes cc ON o.country = cc.alpha_2
                    WHERE o.bean_id = cb.id
                ) as origins
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
                FROM coffee_beans cb_inner
                WHERE cb_inner.id IN (SELECT bean_id FROM {temp_table})
            ) cb
            LEFT JOIN roasters_with_location rwl ON cb.roaster = rwl.name
            WHERE cb.rn = 1
            ORDER BY {sort_col} {sort_dir}, cb.clean_url_slug ASC
            LIMIT ? OFFSET ?
        """

        results = profiled_execute(main_query, [per_page, offset]).fetchall()

        # Build objects
        coffee_beans = []
        for row in results:
            # result is already in a structure very close to what we need
            # but we need to handle Pydantic conversion and currency
            bean_dict = dict(zip([
                "id", "name", "roaster", "url", "is_single_origin", "roast_level",
                "roast_profile", "weight", "price", "currency", "is_decaf",
                "cupping_score", "tasting_notes", "description", "in_stock",
                "scraped_at", "scraper_version", "image_url", "clean_url_slug",
                "bean_url_path", "price_paid_for_green_coffee",
                "currency_of_price_paid_for_green_coffee", "roaster_country_code",
                "origins"
            ], row))

            # Handle currency conversion
            if convert_to_currency and convert_to_currency.upper() != bean_dict.get("currency", "").upper():
                original_price = bean_dict.get("price")
                original_currency = bean_dict.get("currency")
                if original_price and original_currency:
                    converted = convert_price(conn, original_price, original_currency.upper(), convert_to_currency.upper())
                    if converted is not None:
                        bean_dict["original_price"] = original_price
                        bean_dict["original_currency"] = original_currency
                        bean_dict["price"] = round(converted, 2)
                        bean_dict["currency"] = convert_to_currency.upper()
                        bean_dict["price_converted"] = True

            # Convert origins to correct objects
            bean_dict["origins"] = [APIBean(**dict(o)) for o in bean_dict["origins"]]

            # Create the final result
            coffee_beans.append(APISearchResult(**bean_dict))

    finally:
        conn.execute(f"DROP TABLE IF EXISTS {temp_table}")
        conn.execute("PRAGMA disable_profiling")

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
@cached(cache=SimpleMemoryCache)
async def get_varietals():
    """Get all coffee varietals grouped by categories."""
    # Setup profiling helper
    query_count = 0
    request_id = int(time.time())

    def profiled_execute(query, params=None):
        nonlocal query_count
        query_count += 1

        if not ENABLE_PROFILING:
            return conn.execute(query, params) if params is not None else conn.execute(query)

        profile_file = f"duckdb_profile_{request_id}_varietals_q{query_count}.json"
        conn.execute("PRAGMA enable_profiling = 'json'")
        conn.execute(f"PRAGMA profiling_output = '{profile_file}'")

        start = time.perf_counter()
        result = conn.execute(query, params) if params is not None else conn.execute(query)
        duration = time.perf_counter() - start

        print(f"PROFILER [VARIETALS Q{query_count}]: Took {duration:.4f}s - Saved to {profile_file}")
        preview = " ".join(query.split())[:80] + "..."
        print(f"      SQL: {preview}")

        return result

    try:
        # Step 1: Optimized query to get all varietal data in one go (Avoids N+1)
        # We'll get country-level bean counts and original name counts aggregated into JSON
        main_query = """
            WITH varietal_stats AS (
                SELECT
                    t.canon_var as canonical_variety,
                    COUNT(DISTINCT cb.id) as bean_count,
                    COUNT(DISTINCT cb.roaster) as roaster_count,
                    COUNT(DISTINCT o.country) as country_count
                FROM origins o
                JOIN coffee_beans cb ON o.bean_id = cb.id,
                unnest(o.variety_canonical) AS t(canon_var)
                WHERE t.canon_var IS NOT NULL AND t.canon_var != ''
                GROUP BY t.canon_var
            ),
            country_stats AS (
                SELECT
                    t.canon_var as canonical_variety,
                    o.country,
                    cc.name as country_full_name,
                    COUNT(DISTINCT cb.id) as bean_count
                FROM origins o
                JOIN coffee_beans cb ON o.bean_id = cb.id
                LEFT JOIN country_codes cc ON o.country = cc.alpha_2,
                unnest(o.variety_canonical) AS t(canon_var)
                WHERE t.canon_var IS NOT NULL AND t.canon_var != ''
                  AND o.country IS NOT NULL AND o.country != ''
                GROUP BY t.canon_var, o.country, cc.name
            ),
            original_names AS (
                SELECT
                    t.canon_var as canonical_variety,
                    o.variety as original_variety,
                    COUNT(DISTINCT cb.id) as bean_count
                FROM origins o
                JOIN coffee_beans cb ON o.bean_id = cb.id,
                unnest(o.variety_canonical) AS t(canon_var)
                WHERE t.canon_var IS NOT NULL AND t.canon_var != ''
                  AND o.variety IS NOT NULL AND o.variety != ''
                  AND NOT EXISTS (
                      SELECT 1 FROM varietal_mappings vm
                      WHERE vm.original_name = o.variety
                      AND vm.is_compound = true
                  )
                GROUP BY t.canon_var, o.variety
            )
            SELECT
                v.canonical_variety,
                v.bean_count,
                v.roaster_count,
                v.country_count,
                (
                    SELECT list(struct_pack(
                        country_code := cs.country,
                        country_name := COALESCE(cs.country_full_name, cs.country),
                        bean_count := cs.bean_count
                    ) ORDER BY cs.bean_count DESC, cs.country_full_name ASC)
                    FROM country_stats cs
                    WHERE cs.canonical_variety = v.canonical_variety
                ) as countries,
                (
                    SELECT string_agg(onm.original_variety, ' ' ORDER BY onm.bean_count DESC, onm.original_variety ASC)
                    FROM original_names onm
                    WHERE onm.canonical_variety = v.canonical_variety
                ) as original_names
            FROM varietal_stats v
            ORDER BY v.bean_count DESC
        """

        results = profiled_execute(main_query).fetchall()

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
            varietal_name, bean_count, roaster_count, country_count, countries_list, original_names_str = row
            category = categorize_varietal(varietal_name)
            varietal_slug = normalize_varietal_name(varietal_name)

            varietal_data = {
                "name": varietal_name,
                "slug": varietal_slug,
                "bean_count": bean_count,
                "roaster_count": roaster_count,
                "country_count": country_count,
                "countries": [dict(c) for c in countries_list] if countries_list else [],
                "category": category,
                "original_names": original_names_str or "",
            }

            categories[category]["varietals"].append(varietal_data)

        # Calculate category totals
        for category_data in categories.values():
            total_beans = sum(v["bean_count"] for v in category_data["varietals"])
            category_data["total_beans"] = total_beans

        return APIResponse.success_response(data=categories, metadata={"total_varietals": len(results)})
    finally:
        conn.execute("PRAGMA disable_profiling")


@app.get("/v1/varietals/{varietal_slug}", response_model=APIResponse[dict])
async def get_varietal_details(varietal_slug: str, convert_to_currency: str = "EUR"):
    """Get details for a specific coffee varietal (searches both original and canonical names)."""
    # Normalise to lowercase so the lookup is case-insensitive
    varietal_slug = varietal_slug.lower()

    # First, try to find the actual canonical varietal name from the slug efficiently
    query = """
        SELECT canon_var, COUNT(*) as bean_count
        FROM (
            SELECT unnest(variety_canonical) as canon_var,
                   unnest(variety_canonical_slugs) as canon_slug
            FROM origins
        ) t
        WHERE t.canon_slug = ?
        GROUP BY canon_var
        ORDER BY bean_count DESC
        LIMIT 1
    """

    row = conn.execute(query, [varietal_slug]).fetchone()
    actual_varietal = None
    if row:
        actual_varietal = row[0]

    if not actual_varietal:
        raise HTTPException(status_code=404, detail=f"Varietal '{varietal_slug}' not found")

    stats_query = """
        SELECT
            COUNT(DISTINCT cb.id) as total_beans,
            COUNT(DISTINCT cb.roaster) as total_roasters,
            COUNT(DISTINCT o.country) as total_countries,
            MEDIAN(cb.price_usd/cb.weight)*100 as avg_price
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE list_contains(o.variety_canonical_slugs, ?)
    """

    stats_result = conn.execute(stats_query, [varietal_slug]).fetchone()
    stats = stats_result if stats_result else (0, 0, 0, 0)

    countries_query = """
        SELECT
            o.country,
            cc.name as country_full_name,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        LEFT JOIN country_codes cc ON o.country = cc.alpha_2
        WHERE list_contains(o.variety_canonical_slugs, ?)
        GROUP BY o.country, cc.name
        ORDER BY bean_count DESC
    """

    countries = conn.execute(countries_query, [varietal_slug]).fetchall()

    roasters_query = """
        SELECT
            cb.roaster,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE list_contains(o.variety_canonical_slugs, ?)
        GROUP BY cb.roaster
        ORDER BY bean_count DESC
    LIMIT 10
    """

    roasters = conn.execute(roasters_query, [varietal_slug]).fetchall()

    tasting_notes_query = """
        SELECT
            note,
            COUNT(*) as frequency
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id,
        unnest(cb.tasting_notes) AS t(note)
        WHERE list_contains(o.variety_canonical_slugs, ?)
        AND t.note IS NOT NULL AND t.note != ''
        GROUP BY t.note
        ORDER BY frequency DESC
        LIMIT 10
    """

    tasting_notes = conn.execute(tasting_notes_query, [varietal_slug]).fetchall()

    processing_methods_query = """
        SELECT
            o.process_common_name,
            COUNT(*) as frequency
        FROM origins o
        WHERE list_contains(o.variety_canonical_slugs, ?)
        AND o.process_common_name IS NOT NULL AND o.process_common_name != ''
        GROUP BY o.process_common_name
        ORDER BY frequency DESC
        LIMIT 10
    """

    processing_methods = conn.execute(processing_methods_query, [varietal_slug]).fetchall()
    converted_avg_price = convert_price(conn, stats[3], "USD", convert_to_currency) if stats[3] else 0

    original_names_query = """
        SELECT
            o.variety as original_variety,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE list_contains(o.variety_canonical_slugs, ?)
        AND o.variety IS NOT NULL
        AND o.variety != ''
        AND NOT EXISTS (
            SELECT 1 FROM varietal_mappings vm
            WHERE vm.original_name = o.variety
            AND vm.is_compound = true
        )
        GROUP BY o.variety
        ORDER BY bean_count DESC, o.variety
    """

    original_names = conn.execute(original_names_query, [varietal_slug]).fetchall()

    # Get World Coffee Research information for this varietal
    wcr_query = """
        SELECT description, link, species
        FROM coffee_varietals
        WHERE name = ?
    """
    wcr_result = conn.execute(wcr_query, [actual_varietal]).fetchone()

    # Build WCR info dict if data exists
    wcr_info = None
    if wcr_result:
        wcr_info = {"description": wcr_result[0], "link": wcr_result[1], "species": wcr_result[2]}

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
        "original_names": [{"name": row[0], "bean_count": row[1]} for row in original_names],
        "wcr_info": wcr_info,
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
    """Get coffee beans of a specific varietal (searches canonical names)."""
    convert_to_currency = validate_currency_code(convert_to_currency)
    # Setup profiling helper
    query_count = 0
    request_id = int(time.time())
    temp_table = f"_varietal_beans_{request_id}"

    def profiled_execute(query, params=None):
        nonlocal query_count
        query_count += 1

        if not ENABLE_PROFILING:
            return conn.execute(query, params) if params is not None else conn.execute(query)

        profile_file = f"duckdb_profile_{request_id}_varbeans_q{query_count}.json"
        conn.execute("PRAGMA enable_profiling = 'json'")
        conn.execute(f"PRAGMA profiling_output = '{profile_file}'")

        start = time.perf_counter()
        result = conn.execute(query, params) if params is not None else conn.execute(query)
        duration = time.perf_counter() - start

        print(f"PROFILER [VARIETAL_BEANS Q{query_count}]: Took {duration:.4f}s - Saved to {profile_file}")
        preview = " ".join(query.split())[:80] + "..."
        print(f"      SQL: {preview}")

        return result

    try:
        # Step 1: Find the actual canonical varietal name from the slug efficiently
        slug_query = """
            SELECT canon_var, COUNT(*) as bean_count
            FROM (
                SELECT unnest(variety_canonical) as canon_var,
                       unnest(variety_canonical_slugs) as canon_slug
                FROM origins
            ) t
            WHERE t.canon_slug = ?
            GROUP BY canon_var
            ORDER BY bean_count DESC
            LIMIT 1
        """
        slug_result = profiled_execute(slug_query, [varietal_slug]).fetchone()

        if not slug_result:
            raise HTTPException(status_code=404, detail=f"Varietal '{varietal_slug}' not found")

        actual_varietal = slug_result[0]

        profiled_execute(
            f"""
            CREATE TEMPORARY TABLE {temp_table} AS
            SELECT DISTINCT o.bean_id
            FROM origins o
            WHERE list_contains(o.variety_canonical_slugs, ?)
        """,
            [varietal_slug],
        )

        # Step 3: Get total count (Deduplicated by slug)
        count_query = f"""
            SELECT COUNT(DISTINCT cb.clean_url_slug)
            FROM {temp_table} t
            JOIN coffee_beans cb ON t.bean_id = cb.id
        """
        total_count = profiled_execute(count_query).fetchone()[0]

        # Pagination
        offset = (page - 1) * per_page
        total_pages = (total_count + per_page - 1) // per_page

        # Sorting logic
        sort_field_mapping = {
            "name": "cb.name",
            "roaster": "cb.roaster",
            "price": "cb.price_usd",
            "weight": "cb.weight",
            "scraped_at": "cb.scraped_at",
        }
        sort_col = sort_field_mapping.get(sort_by, "cb.name")
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Step 4: Main query with aggregated origins and tasting notes (No N+1)
        main_query = f"""
            SELECT
                cb.id as id, cb.name, cb.roaster, cb.url, cb.is_single_origin,
                cb.roast_level, cb.roast_profile, cb.weight, cb.price, cb.currency,
                cb.is_decaf, cb.cupping_score,
                (
                    SELECT list(struct_pack(
                        note := note_value,
                        primary_category := (SELECT primary_category FROM tasting_notes_categories WHERE tasting_note = note_value LIMIT 1)
                    ))
                    FROM unnest(cb.tasting_notes) AS u(note_value)
                ) AS tasting_notes,
                cb.description, cb.in_stock,
                cb.scraped_at, cb.scraper_version, cb.image_url, cb.clean_url_slug,
                cb.bean_url_path, cb.price_paid_for_green_coffee, cb.currency_of_price_paid_for_green_coffee,
                rwl.roaster_country_code,
                (
                    SELECT list(struct_pack(
                        country := o.country,
                        region := o.region,
                        producer := o.producer,
                        farm := o.farm,
                        elevation_min := COALESCE(o.elevation_min, 0),
                        elevation_max := COALESCE(o.elevation_max, o.elevation_min, 0),
                        process := o.process,
                        variety := o.variety,
                        variety_canonical := o.variety_canonical,
                        harvest_date := o.harvest_date,
                        latitude := COALESCE(o.latitude, 0.0),
                        longitude := COALESCE(o.longitude, 0.0),
                        country_full_name := cc.name,
                        region_canonical := o.state_canonical,
                        farm_canonical := COALESCE(o.farm_canonical, o.farm)
                    ) ORDER BY o.id)
                    FROM origins o
                    LEFT JOIN country_codes cc ON o.country = cc.alpha_2
                    WHERE o.bean_id = cb.id
                ) as origins
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
                FROM coffee_beans cb_inner
                WHERE cb_inner.id IN (SELECT bean_id FROM {temp_table})
            ) cb
            LEFT JOIN roasters_with_location rwl ON cb.roaster = rwl.name
            WHERE cb.rn = 1
            ORDER BY {sort_col} {sort_dir}, cb.clean_url_slug ASC
            LIMIT ? OFFSET ?
        """

        results = profiled_execute(main_query, [per_page, offset]).fetchall()

        # Build objects
        coffee_beans = []
        for row in results:
            bean_dict = dict(
                zip(
                    [
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
                        "roaster_country_code",
                        "origins",
                    ],
                    row,
                )
            )

            # Handle currency conversion
            if convert_to_currency and convert_to_currency.upper() != bean_dict.get("currency", "").upper():
                original_price = bean_dict.get("price")
                original_currency = bean_dict.get("currency")
                if original_price and original_currency:
                    converted = convert_price(
                        conn, original_price, original_currency.upper(), convert_to_currency.upper()
                    )
                    if converted is not None:
                        bean_dict["original_price"] = original_price
                        bean_dict["original_currency"] = original_currency
                        bean_dict["price"] = round(converted, 2)
                        bean_dict["currency"] = convert_to_currency.upper()
                        bean_dict["price_converted"] = True

            # Convert origins to correct objects
            bean_dict["origins"] = [APIBean(**dict(o)) for o in bean_dict["origins"]]

            # Create the final result
            coffee_beans.append(APISearchResult(**bean_dict))

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

    finally:
        conn.execute(f"DROP TABLE IF EXISTS {temp_table}")
        conn.execute("PRAGMA disable_profiling")


@app.get("/v1/tasting-note-categories", response_model=APIResponse[dict])
@cached(cache=SimpleMemoryCache)
async def get_tasting_note_categories(
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
    convert_to_currency: str | None = Query(
        None, description="Convert prices to this currency code (e.g., EUR, GBP, JPY)"
    ),
):
    """Get all tasting note categories grouped by primary, secondary, and tertiary category with counts, with optional filtering."""
    convert_to_currency = validate_currency_code(convert_to_currency)
    try:
        # Create filter parameters object
        filter_params = FilterParams(
            query=query,
            tasting_notes_query=tasting_notes_query,
            roaster=roaster,
            roaster_location=roaster_location,
            origin=origin,
            region=region,
            producer=producer,
            farm=farm,
            roast_level=roast_level,
            roast_profile=roast_profile,
            process=process,
            variety=variety,
            min_price=min_price,
            max_price=max_price,
            min_weight=min_weight,
            max_weight=max_weight,
            in_stock_only=in_stock_only,
            is_decaf=is_decaf,
            is_single_origin=is_single_origin,
            min_cupping_score=min_cupping_score,
            max_cupping_score=max_cupping_score,
            min_elevation=min_elevation,
            max_elevation=max_elevation,
            convert_to_currency=convert_to_currency,
        )

        # Build filters using shared function
        filter_result = build_coffee_bean_filters(filter_params, use_scoring=False)
        filter_conditions = filter_result.conditions
        params = filter_result.params

        # Build WHERE clause
        where_conditions = ["cb.rn = 1", "cb.tasting_notes IS NOT NULL"]
        if filter_conditions:
            where_conditions.extend(filter_conditions)
        where_clause = f"WHERE {' AND '.join(where_conditions)}"

        # The query is updated to include filtering and the tertiary_category in the grouping and selection.
        sql_query = f"""
        WITH filtered_beans AS (
            SELECT cb.id, unnest(cb.tasting_notes) as note
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
                FROM coffee_beans_with_origin cb
            ) cb
            {where_clause}
        ),
        note_bean_counts AS (
            SELECT
                tnc.tasting_note,
                tnc.primary_category,
                tnc.secondary_category,
                tnc.tertiary_category,
                COUNT(DISTINCT fb.id) as bean_count
            FROM tasting_notes_categories tnc
            LEFT JOIN filtered_beans fb ON tnc.tasting_note = fb.note
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

        results = conn.execute(sql_query, params).fetchall()

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
                   o.process, o.variety, o.variety_canonical, o.harvest_date, o.latitude, o.longitude,
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
                    "variety_canonical": origin_row[8] if origin_row[8] else None,
                    "harvest_date": origin_row[9],
                    "latitude": origin_row[10] or 0.0,
                    "longitude": origin_row[11] or 0.0,
                    "country_full_name": origin_row[12],
                }
                origins.append(APIBean(**origin_data))

            bean_dict["origins"] = origins
            search_result = APISearchResult(**bean_dict)
            coffee_beans.append(search_result)

        # Create pagination info

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


# --- Flavour Images Endpoint ---
@app.get("/v1/flavour-images", response_model=APIResponse[list[dict]])
@cached(cache=SimpleMemoryCache)
async def get_flavour_images():
    """
    Returns available flavour images from /static/data/flavours/paintings.
    Each image is named after a tasting note or category.
    Includes attribution data from wikidata_flavour_images.json.
    """
    # Path to paintings directory (relative to repo root)
    paintings_dir = Path(__file__).parent.parent.parent.parent / "data" / "flavours" / "paintings"
    if not paintings_dir.exists():
        return JSONResponse(
            status_code=404, content={"success": False, "data": [], "message": "Paintings directory not found."}
        )

    # Load wikidata attribution data
    wikidata_file = Path(__file__).parent.parent / "database" / "wikidata_flavour_images.json"
    attribution_data = {}
    if wikidata_file.exists():
        try:
            with open(wikidata_file, encoding="utf-8") as f:
                wikidata = json.load(f)
                attribution_data = wikidata.get("results", {})
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"Failed to load wikidata attribution data: {e}")

    images = []
    for file in os.listdir(paintings_dir):
        if file.lower().endswith(".jpg"):
            # Remove extension, normalize unicode, replace underscores with spaces
            note = os.path.splitext(file)[0]
            note = unicodedata.normalize("NFKC", note)
            note = note.replace("_", " ").strip()

            # Look up attribution data for this tasting note
            attribution = attribution_data.get(note, {})

            image_data = {
                "note": note,
                "filename": file,
                "url": f"/static/data/flavours/paintings/{file}",
                "image_author": attribution.get("image_author", "").replace(" (page does not exist)", "")
                if attribution.get("image_author", "") is not None
                else "",
                "image_license": attribution.get("image_license"),
                "image_license_url": attribution.get("image_license_url"),
            }
            images.append(image_data)

    return {"success": True, "data": images}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
