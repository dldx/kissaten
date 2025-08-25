"""Roaster data schema."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class RoasterConfig(BaseModel):
    """Scraping configuration for a roaster."""

    base_url: HttpUrl = Field(..., description="Base URL for the roaster")
    store_url: HttpUrl = Field(..., description="Store/shop URL")
    scraping_method: str = Field("beautifulsoup", description="Scraping method (beautifulsoup/playwright)")
    rate_limit_delay: float = Field(1.0, ge=0.1, le=10.0, description="Delay between requests in seconds")
    max_pages: int | None = Field(None, ge=1, description="Maximum pages to scrape")
    custom_headers: dict[str, str] | None = Field(None, description="Custom HTTP headers")

    # Selectors for different scraping methods
    selectors: dict[str, str] | None = Field(None, description="CSS selectors for data extraction")

    @field_validator("scraping_method")
    @classmethod
    def validate_scraping_method(cls, v):
        """Validate scraping method."""
        valid_methods = ["beautifulsoup", "playwright"]
        if v not in valid_methods:
            raise ValueError(f"Scraping method must be one of: {valid_methods}")
        return v


class Roaster(BaseModel):
    """Roaster information and metadata."""

    name: str = Field(..., min_length=1, max_length=100, description="Roaster name")
    website: HttpUrl = Field(..., description="Main website URL")
    location: str | None = Field(None, max_length=100, description="Location (city, country)")

    # Contact information
    email: str | None = Field(None, description="Contact email")
    social_media: dict[str, str] | None = Field(None, description="Social media handles")

    # Scraping configuration
    config: RoasterConfig = Field(..., description="Scraping configuration")

    # Metadata
    active: bool = Field(True, description="Whether scraping is active")
    last_scraped: str | None = Field(None, description="Last successful scrape timestamp")
    total_beans_scraped: int = Field(0, ge=0, description="Total beans scraped historically")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        """Clean roaster name."""
        return v.strip()

    @field_validator("location")
    @classmethod
    def clean_location(cls, v):
        """Clean location."""
        if v:
            return v.strip()
        return v

    model_config = ConfigDict(validate_assignment=True)
