"""Coffee bean data schema."""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from kissaten.database import fx


class RoastLevel(Enum):
    """Roast level enum."""

    EXTRA_LIGHT = "Extra-Light"
    LIGHT = "Light"
    MEDIUM_LIGHT = "Medium-Light"
    MEDIUM = "Medium"
    MEDIUM_DARK = "Medium-Dark"
    DARK = "Dark"

class PriceOption(BaseModel):
    """Price option for the coffee bean."""

    weight: int | None = Field(None, gt=0, description="Weight in grams")
    price: float = Field(..., gt=0, description="Price of roasted coffee in local currency")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        """Validate price is reasonable."""
        if v is not None and (v < 0):
            raise ValueError("Price must be positive")
        return v

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v):
        """Validate weight is reasonable for coffee."""
        if v is not None and (v <= 10 or v > 10000):
            raise ValueError("Weight must be between 10g and 10kg")
        return v

class CoffeeBeanDiffUpdate(BaseModel):
    """Schema for partial coffee bean updates via diffjson files.

    This model defines which fields can be updated without overwriting
    the entire coffee bean record. Only the fields present in the diffjson
    will be updated in the database.
    """

    # Required field - must specify which bean to update
    url: HttpUrl = Field(..., description="Product URL to identify which bean to update")

    # Updatable fields (all optional)
    name: str | None = Field(None, min_length=1, max_length=200, description="Coffee bean name")
    roast_level: RoastLevel | None = Field(None, description="Roast level")
    roast_profile: Literal["Espresso", "Filter", "Omni"] | None = Field(
        None, description="Is it for espresso or filter? If both, use 'Omni'"
    )
    price_options: list[PriceOption] | None = Field(
        None,
        description="List of price options for the coffee bean. If there are multiple price options, include them all.",
    )
    price: float | None = Field(None, gt=0, description="Price of roasted coffee in local currency")
    weight: int | None = Field(None, gt=0, description="Weight in grams")
    currency: str | None = Field(None, max_length=3, description="Currency code")
    is_decaf: bool | None = Field(None, description="Whether the coffee is decaffeinated")
    cupping_score: float | None = Field(
        None, ge=70, le=100, description="Cupping score (70-100). Only add if explicitly stated"
    )
    description: str | None = Field(
        None,
        max_length=5000,
        description="Product description. Try to extract the exact description from the product page.",
    )
    in_stock: bool | None = Field(
        None, description="Stock availability. If there is no mention of it being out of stock, set to True."
    )
    tasting_notes: list[str] | None = Field(None, description="Flavour notes in order they appear in the description")
    scraped_at: datetime | None = Field(None, description="Scraping timestamp")

    # Scraping metadata (updatable for tracking purposes)
    scraper_version: str | None = Field(None, description="Scraper version used")

    @field_validator("tasting_notes")
    @classmethod
    def clean_tasting_notes(cls, v):
        """Clean and normalize tasting notes."""
        if not v:
            return None
        # Remove empty strings and normalize
        cleaned = [note.strip().title() for note in v if note and note.strip()]
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for note in cleaned:
            if note not in seen:
                seen.add(note)
                deduped.append(note)
        return deduped if deduped else None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        """Validate price is reasonable."""
        if v is not None and (v < 0):
            raise ValueError("Price must be positive")
        return v

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v):
        """Validate weight is reasonable for coffee."""
        if v is not None and (v < 50 or v > 10000):
            raise ValueError("Weight must be between 50g and 10kg")
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        validate_assignment=True,
        use_enum_values=True,
        # Exclude None values when serializing to match diffjson format
        exclude_none=True,
    )

    @model_validator(mode="after")
    @classmethod
    def check_prices(cls, model):
        """Ensure that USD price is between 0 and 200."""
        max_price_usd = 150
        if model.price is not None and model.currency is not None:
            usd_price = model.price / fx.rates[model.currency]
            if usd_price < 0 or usd_price > max_price_usd:
                min_price = 0 * fx.rates[model.currency]
                max_price = max_price_usd * fx.rates[model.currency]
                raise ValueError(f"Price in {model.currency} must be between {min_price:.2f} and {max_price:.2f}.")
        return model


class Bean(BaseModel):
    """Origin of coffee bean."""

    country: str | None = Field(
        None, min_length=1, max_length=100, description="Country of origin as a two letter code. eg. CO, KE, BR, etc."
    )
    region: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Region of origin within the country. eg. Antioquia, Huila, etc.",
    )
    producer: str | None = Field(
        None, min_length=1, max_length=100, description="Producer name. This is usually a person's name."
    )
    farm: str | None = Field(None, min_length=1, max_length=100, description="Farm name.")
    elevation_min: int = Field(
        0,
        ge=0,
        le=3000,
        description="Minimum elevation in meters above sea level. eg. 1500, 1600, etc. 0 if not known.",
    )
    elevation_max: int = Field(
        0,
        ge=0,
        le=3000,
        description="Maximum elevation in meters above sea level. eg. 1500, 1600, etc. 0 if not known.",
    )
    latitude: float | None = Field(
        None,
        ge=-90,
        le=90,
        description="Latitude of the coffee farm. Do not guess. If not present, return None.",
    )
    longitude: float | None = Field(
        None,
        ge=-180,
        le=180,
        description="Longitude of the coffee farm. Do not guess. If not present, return None.",
    )
    process: str | None = Field(
        None,
        max_length=100,
        description="Processing method. (e.g. Washed, Natural, Honey). Leave blank if not specified.",
    )
    variety: str | None = Field(
        None,
        max_length=100,
        description="Coffee variety or varietal. (e.g. Catuai, Bourbon, etc.). "
        "Leave blank if there is no specific variety mentioned.",
    )
    harvest_date: datetime | None = Field(
        None, description="Harvest date. If a range is provided, use the earliest date."
    )

    @field_validator("country")
    @classmethod
    def clean_country(cls, v):
        """Clean and normalize country."""
        if v:
            return v.strip().upper()
        return v

    @field_validator("region")
    @classmethod
    def clean_region(cls, v):
        """Clean and normalize region."""
        if v:
            return v.strip().title()
        return v

    @field_validator("farm")
    @classmethod
    def clean_farm(cls, v):
        """Clean and normalize farm."""
        if v:
            return v.strip().title()
        return v

    @field_validator("harvest_date")
    @classmethod
    def validate_harvest_date(cls, v):
        """Validate harvest date is reasonable."""
        if v is not None:
            # Get current time - use UTC if the input datetime is timezone-aware
            now = datetime.now(timezone.utc) if v.tzinfo is not None else datetime.now()
            min_date = datetime(2020, 1, 1, tzinfo=timezone.utc) if v.tzinfo is not None else datetime(2020, 1, 1)

            if v > now:
                raise ValueError("Harvest date cannot be in the future")
            if v < min_date:
                raise ValueError("Harvest date must be after 2020")
        return v

    def __str__(self) -> str:
        """String representation of origin."""
        elevation_str = (
            f"{self.elevation_min}m"
            if self.elevation_min == self.elevation_max
            else f"{self.elevation_min}-{self.elevation_max}m"
        )
        return f"{self.country} - {self.region} - {self.farm} - {elevation_str}"

    def __repr__(self) -> str:
        """Representation of origin."""
        elevation_str = (
            f"{self.elevation_min}m"
            if self.elevation_min == self.elevation_max
            else f"{self.elevation_min}-{self.elevation_max}m"
        )
        return f"{self.country} - {self.region} - {self.farm} - {elevation_str}"


class CoffeeBean(BaseModel):
    """Coffee bean data model with validation."""

    # Basic Information
    name: str = Field(..., min_length=1, max_length=200, description="Coffee bean name")
    roaster: str = Field(..., min_length=1, max_length=100, description="Roaster name")
    url: HttpUrl = Field(..., description="Product URL")
    image_url: HttpUrl | None = Field(None, description="Product image URL")

    description: str | None = Field(
        None,
        max_length=5000,
        description="Product description. Try to extract the exact description from the product page.",
    )

    # Origin and Processing
    origins: list[Bean] = Field(
        ...,
        description="""Origins of each coffee bean. For single origin, there should only be one bean.
        For blends, there should be two or more.""",
    )
    is_single_origin: bool = Field(True, description="Whether the coffee is a single origin or a blend")
    price_paid_for_green_coffee: float | None = Field(None, description="Price paid for 1kg of green coffee.")
    currency_of_price_paid_for_green_coffee: str | None = Field(
        None, description="Currency of price paid for green coffee."
    )

    # Product Details
    roast_level: RoastLevel | None = Field(None, description="Roast level")
    roast_profile: Literal["Espresso", "Filter", "Omni"] | None = Field(
        None, description="Is it for espresso or filter? If both, use 'Omni'"
    )
    price_options: list[PriceOption] = Field(
        ...,
        description="List of price options for the coffee bean. If there are multiple price options, include them all.",
    )
    price: float | None = Field(None, gt=0, description="Price of roasted coffee in local currency")
    weight: int | None = Field(None, gt=0, description="Weight in grams")
    currency: str | None = Field("GBP", max_length=3, description="Currency code")
    is_decaf: bool = Field(False, description="Whether the coffee is decaffeinated")
    cupping_score: float | None = Field(
        None, ge=70, le=100, description="Cupping score (70-100). Only add if explicitly stated"
    )

    # Flavor Profile
    tasting_notes: list[str] | None = Field(
        default_factory=list, description="Flavour notes in order they appear in the description"
    )

    # Availability and Metadata
    in_stock: bool | None = Field(
        None, description="Stock availability. If there is no mention of it being out of stock, set to True."
    )
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Scraping timestamp")

    # Scraping metadata
    scraper_version: str = Field("1.0", description="Scraper version used")
    raw_data: str | None = Field(None, description="Raw scraped data for debugging")

    @field_validator("tasting_notes")
    @classmethod
    def clean_tasting_notes(cls, v):
        """Clean and normalize tasting notes."""
        if not v:
            return []
        if not isinstance(v[0], str):
            return v
        # Remove empty strings and normalize
        cleaned = [note.strip().title() for note in v if note and note.strip()]
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for note in cleaned:
            if note not in seen:
                seen.add(note)
                deduped.append(note)
        return deduped

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        validate_assignment=True,
        use_enum_values=True,
    )

    @field_validator("price_options")
    @classmethod
    def unique_price_options(cls, v):
        """Validate price options are reasonable and remove duplicates."""
        if v is not None:
            # Remove duplicates by comparing weight and price
            seen = set()
            unique_options = []
            for option in v:
                # Create a hashable key from weight and price
                key = (option.weight, option.price)
                if key not in seen:
                    seen.add(key)
                    unique_options.append(option)
            return unique_options
        return []

    @model_validator(mode="after")
    @classmethod
    def check_prices(cls, model):
        """Ensure that USD prices are between 0 and 300 for 200g."""
        max_price_usd = 300  # for 200g
        max_price_usd_per_g = max_price_usd / 200
        if model.price_options is not None:
            for price_option in model.price_options:
                usd_price = price_option.price / (fx.rates[model.currency] * price_option.weight)
                if usd_price < 0 or usd_price > max_price_usd_per_g:
                    min_price = 0 * fx.rates[model.currency]
                    max_price = max_price_usd_per_g * fx.rates[model.currency]
                    raise ValueError(
                        f"Price per gram in {model.currency} must be between {min_price:.2f} and {max_price:.2f}."
                    )
        return model

    @model_validator(mode="after")
    @classmethod
    def set_default_price_option(cls, model):
        """Set the default price option to the nearest to 200g."""
        # Only set if price and weight are not already set
        if (
            model.price_options is not None
            and len(model.price_options) > 0
            and model.price is None
            and model.weight is None
        ):
            # Filter options that have valid weights
            valid_options = [opt for opt in model.price_options if opt.weight is not None]
            if valid_options:
                # Select option nearest to 200g in weight
                nearest_option = min(valid_options, key=lambda x: abs(x.weight - 200))
                # Use object.__setattr__ to avoid triggering validation recursion
                object.__setattr__(model, "price", nearest_option.price)
                object.__setattr__(model, "weight", nearest_option.weight)
        return model
