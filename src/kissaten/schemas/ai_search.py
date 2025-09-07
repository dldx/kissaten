"""AI search schemas for natural language search query processing."""

from pydantic import BaseModel, Field


class Country(BaseModel):
    """Country data for AI search query processing."""

    country_full_name: str = Field(..., description="Name of the country")
    country_code: str = Field(..., description="Two letter code of the country")



class SearchContext(BaseModel):
    """Context data for AI search query processing."""

    available_tasting_notes: list[str] = Field(
        ..., description="List of tasting notes available in the database"
    )
    available_varietals: list[str] = Field(
        ..., description="List of coffee varietals available in the database"
    )
    available_roasters: list[str] = Field(
        ..., description="List of roaster names available in the database"
    )
    available_processes: list[str] = Field(
        ..., description="List of processing methods available in the database"
    )
    available_roast_levels: list[str] = Field(
        ..., description="List of roast levels available in the database"
    )
    available_countries: list[Country] = Field(
        ..., description="List of countries available in the database"
    )
    available_roaster_locations: list[str] = Field(
        ..., description="List of roaster locations available in the database"
    )


class AISearchQuery(BaseModel):
    """Natural language search query for AI processing."""

    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")


class SearchParameters(BaseModel):
    """Structured search parameters generated from natural language query."""

    # Reasoning first
    reasoning: str | None = Field(None, description="AI reasoning for the search translation")

    # Text search parameters
    search_text: str | None = Field(None, description="Processed search text for general search")
    tasting_notes_search: str | None = Field(None, description="Specific tasting notes search query")
    use_tasting_notes_only: bool = Field(False, description="Whether to search only in tasting notes")

    # Filter parameters
    roaster: list[str] | None = Field(None, description="Roaster names to filter by")
    roaster_location: list[str] | None = Field(None, description="Roaster locations to filter by")
    variety: str | None = Field(None, description="Coffee varieties to filter by (supports wildcards)")
    process: str | None = Field(None, description="Processing methods to filter by (supports wildcards)")
    roast_level: str | None = Field(None, description="Roast level to filter by (supports wildcards)")
    roast_profile: str | None = Field(None, description="Roast profile (supports wildcards)")
    origin: list[str] | None = Field(None, description="Origin country two letter codes to filter by")
    region: str | None = Field(None, description="Regions to filter by (supports wildcards)")
    producer: str | None = Field(None, description="Producer names to filter by (supports wildcards)")
    farm: str | None = Field(None, description="Farm names to filter by (supports wildcards)")

    # Range parameters
    min_price: float | None = Field(None, ge=0, description="Minimum price")
    max_price: float | None = Field(None, ge=0, description="Maximum price")
    min_weight: int | None = Field(None, ge=0, description="Minimum weight in grams")
    max_weight: int | None = Field(None, ge=0, description="Maximum weight in grams")
    min_elevation: int | None = Field(None, ge=0, le=3000, description="Minimum elevation in meters above sea level")
    max_elevation: int | None = Field(None, ge=0, le=3000, description="Maximum elevation in meters above sea level")

    # Boolean parameters
    in_stock_only: bool = Field(False, description="Only show in-stock items")
    is_decaf: bool | None = Field(None, description="Filter by decaf status")
    is_single_origin: bool | None = Field(None, description="Filter by single origin status")

    # Sorting
    sort_by: str = Field("name", description="Field to sort by")
    sort_order: str = Field("asc", description="Sort order (asc/desc)")

    # Metadata
    confidence: float = Field(1.0, ge=0, le=1, description="Confidence in the interpretation")



class AISearchResponse(BaseModel):
    """Response from AI search query processing."""

    success: bool = Field(..., description="Whether the AI search was successful")
    search_params: SearchParameters | None = Field(None, description="Generated search parameters")
    search_url: str | None = Field(None, description="Generated search URL")
    error_message: str | None = Field(None, description="Error message if search failed")
    processing_time_ms: float | None = Field(None, description="Processing time in milliseconds")
