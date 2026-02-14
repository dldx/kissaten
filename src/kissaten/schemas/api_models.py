"""API response models that extend the base CoffeeBean schema."""

import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .coffee_bean import Bean, CoffeeBean


class APIBean(Bean):
    """Bean model for API responses with relaxed validation."""

    # Override fields to allow empty strings (converted to None) or make them fully optional
    country: str | None = Field(None, description="Country of origin as a two letter code")
    region: str | None = Field(None, description="Region of origin within the country")
    producer: str | None = Field(None, description="Producer name")
    farm: str | None = Field(None, description="Farm name")
    process: str | None = Field(None, description="Processing method")
    variety: str | None = Field(None, description="Coffee variety or varietal")
    variety_canonical: list[str] | None = Field(None, description="Canonical/standardized varietal names (array)")

    # Add convenience field with full country name
    country_full_name: str | None = Field(None, description="Full country name")
    region_canonical: str | None = Field(None, description="Canonical region/state name")
    farm_canonical: str | None = Field(None, description="Canonical farm name")

class TastingNote(BaseModel):
    """Represents a tasting note with its assigned primary category."""

    note: str
    primary_category: str | None = None

class APICoffeeBean(CoffeeBean):
    """CoffeeBean model for API responses with additional fields and relaxed validation."""

    roaster_country_code: str | None = Field(
        None, description="Two letter country code of the roaster (e.g. CA, US, GB, etc.)"
    )
    # Override origins to use APIBean
    origins: list[APIBean] = Field(
        ...,
        description="Origins of each coffee bean. For single origin, there should only be one bean."
    )
    tasting_notes: list[TastingNote | str] | None = Field(
        default_factory=list, description="List of tasting notes with primary category"
    )

    # Override price_options to make it optional for search results
    price_options: list | None = Field(None, description="List of price options (optional for search results)")

    # Allow relative URLs for image_url (common in our data)
    image_url: str | None = Field(None, description="Product image URL (can be relative)")

    # Override is_decaf to allow None values for backward compatibility with existing data
    # New data will default to false via COALESCE in the INSERT statement
    is_decaf: bool | None = Field(None, description="Whether the coffee is decaffeinated")

    # Additional API-specific fields
    id: int | None = Field(None, description="Database ID")
    clean_url_slug: str | None = Field(None, description="Clean URL slug")
    bean_url_path: str | None = Field(None, description="Bean URL path")

    # Make raw_data optional and not required
    raw_data: str | None = Field(None, description="Raw scraped data for debugging")

    @model_validator(mode="after")
    @classmethod
    def check_prices(cls, model):
        """Ignore price validation for API models."""
        return model

    class Config:
        # Allow extra fields that might come from the database
        extra = "allow"



class APIRecommendation(APICoffeeBean):
    """Recommendation model extending APICoffeeBean with similarity score."""

    # Additional field specific to recommendations
    similarity_score: float = Field(..., description="Similarity score for this recommendation")

    class Config:
        # Allow extra fields that might come from the database
        extra = "allow"


class APISearchResult(APICoffeeBean):
    """Search result model extending APICoffeeBean for search responses."""

    # Additional field for when the coffee was first added/scraped
    date_added: datetime.datetime | None = Field(None, description="The date when this coffee was first scraped/added")

    class Config:
        # Allow extra fields that might come from the database
        extra = "allow"
