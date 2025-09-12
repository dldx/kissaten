"""API response models that extend the base CoffeeBean schema."""

import datetime
from pydantic import Field, model_validator

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

    # Add convenience field with full country name
    country_full_name: str | None = Field(None, description="Full country name")


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

    # Allow relative URLs for image_url (common in our data)
    image_url: str | None = Field(None, description="Product image URL (can be relative)")

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
