"""Search and API response schemas."""

from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

T = TypeVar("T")


class SearchQuery(BaseModel):
    """Structured search request."""

    # Text search
    query: str | None = Field(None, max_length=200, description="Search query text")

    # Filters
    roaster: str | None = Field(None, description="Filter by roaster name")
    origin: str | None = Field(None, description="Filter by origin")
    roast_level: str | None = Field(None, description="Filter by roast level")
    roast_profile: str | None = Field(None, description="Filter by roast profile (Espresso/Filter)")
    process: str | None = Field(None, description="Filter by processing method")
    variety: str | None = Field(None, description="Filter by coffee variety")

    # Price range
    min_price: Decimal | None = Field(None, ge=0, description="Minimum price filter")
    max_price: Decimal | None = Field(None, ge=0, description="Maximum price filter")

    # Weight range
    min_weight: int | None = Field(None, ge=0, description="Minimum weight filter (grams)")
    max_weight: int | None = Field(None, ge=0, description="Maximum weight filter (grams)")

    # Availability
    in_stock_only: bool = Field(False, description="Show only in-stock items")

    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")

    # Sorting
    sort_by: str = Field("name", description="Sort field")
    sort_order: str = Field("asc", description="Sort order (asc/desc)")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_field(cls, v):
        """Validate sort field."""
        valid_fields = [
            "name",
            "roaster",
            "price",
            "weight",
            "scraped_at",
            "origin",
            "variety",
            "roast_level",
            "roast_profile",
        ]
        if v not in valid_fields:
            raise ValueError(f"Sort field must be one of: {valid_fields}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v.lower()

    @model_validator(mode="after")
    def validate_ranges(self):
        """Validate price and weight ranges."""
        if self.max_price is not None and self.min_price is not None and self.max_price < self.min_price:
            raise ValueError("max_price must be greater than or equal to min_price")

        if self.max_weight is not None and self.min_weight is not None and self.max_weight < self.min_weight:
            raise ValueError("max_weight must be greater than or equal to min_weight")

        return self


class PaginationInfo(BaseModel):
    """Pagination information."""

    page: int = Field(..., ge=1, description="Current page")
    per_page: int = Field(..., ge=1, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class APIResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper."""

    success: bool = Field(..., description="Whether the request was successful")
    data: T | None = Field(None, description="Response data")
    message: str | None = Field(None, description="Response message")
    pagination: PaginationInfo | None = Field(None, description="Pagination information")
    metadata: dict | None = Field(None, description="Additional metadata")

    @classmethod
    def success_response(
        cls,
        data: T | None = None,
        message: str | None = None,
        pagination: PaginationInfo | None = None,
        metadata: dict | None = None,
    ):
        """Create a successful response."""
        return cls(success=True, data=data, message=message, pagination=pagination, metadata=metadata)

    @classmethod
    def error_response(cls, message: str, metadata: dict | None = None):
        """Create an error response."""
        return cls(success=False, data=None, message=message, pagination=None, metadata=metadata)
