"""Geographical hierarchy API models for Kissaten."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from .api_models import APISearchResult


class ElevationInfo(BaseModel):
    """Elevation statistics for a location."""
    min: Optional[int] = Field(None, description="Minimum elevation in meters")
    max: Optional[int] = Field(None, description="Maximum elevation in meters")
    avg: Optional[int] = Field(None, description="Average elevation in meters")


class RegionSummary(BaseModel):
    """Summary of a region within a country."""
    region_name: str
    bean_count: int
    farm_count: int
    is_geocoded: bool = Field(description="Whether the region has been mapped to a canonical state")
    median_elevation: Optional[int] = Field(None, description="Median elevation of beans in this region in meters")


class FarmSummary(BaseModel):
    """Summary of a farm within a region."""
    farm_name: str
    producer_name: Optional[str] = None
    bean_count: int
    avg_elevation: Optional[int] = None


class TopRoaster(BaseModel):
    """Roaster statistics for a location."""
    roaster_name: str
    bean_count: int


class TopNote(BaseModel):
    """Tasting note frequency for a location."""
    note: str
    frequency: int


class TopProcess(BaseModel):
    """Processing method distribution for a location."""
    process: str
    count: int


class TopVariety(BaseModel):
    """Varietal distribution for a location."""
    variety: str
    count: int


class ProducerSummary(BaseModel):
    """Producer mention statistics for a farm."""
    name: str
    mention_count: int


class CountryStatistics(BaseModel):
    """Aggregate statistics for a country."""
    total_beans: int
    total_roasters: int
    total_regions: int
    total_farms: int
    avg_elevation: Optional[int] = None
    avg_price_usd: Optional[float] = None


class CountryDetailResponse(BaseModel):
    """Response for country detail endpoint."""
    country_code: str
    country_name: str
    statistics: CountryStatistics
    top_roasters: List[TopRoaster]
    top_regions: List[RegionSummary] = Field(default_factory=list, description="Top regions within this country")
    common_tasting_notes: List[TopNote]
    varietals: List[TopVariety]
    processing_methods: List[TopProcess]
    elevation_distribution: ElevationInfo


class RegionStatistics(BaseModel):
    """Aggregate statistics for a region."""
    total_beans: int
    total_roasters: int
    total_farms: int
    avg_elevation: Optional[int] = None
    avg_price_usd: Optional[float] = None


class RegionDetailResponse(BaseModel):
    """Response for region detail endpoint."""
    region_name: str
    country_code: str
    country_name: str
    statistics: RegionStatistics
    top_farms: List[FarmSummary]
    top_roasters: List[TopRoaster]
    common_tasting_notes: List[TopNote]
    varietals: List[TopVariety]
    processing_methods: List[TopProcess]
    elevation_range: ElevationInfo
    is_geocoded: bool = Field(description="Whether the region has been mapped to a canonical state")


class FarmDetailResponse(BaseModel):
    """Response for farm detail endpoint."""
    farm_name: str
    producer_name: Optional[str] = None
    producers: List[ProducerSummary]
    region_name: str
    country_code: str
    country_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_min: Optional[int] = None
    elevation_max: Optional[int] = None
    beans: List[APISearchResult]
    varietals: List[TopVariety]
    processing_methods: List[TopProcess]
    common_tasting_notes: List[TopNote]


class OriginSearchResult(BaseModel):
    """A single result from an origin search (country, region, or farm)."""

    type: Literal["country", "region", "farm"]
    name: str
    country_code: str
    country_name: str
    region_name: Optional[str] = None
    region_slug: Optional[str] = None
    farm_slug: Optional[str] = None
    producer_name: Optional[str] = None
    bean_count: int


class LocationStatistics(BaseModel):
    """Aggregate statistics for a roaster location (country or region)."""

    available_beans: int = Field(description="Number of beans currently in stock")
    total_beans: int = Field(description="Total number of beans (all-time)")
    roaster_count: int = Field(description="Number of active roasters in this location")
    city_count: Optional[int] = Field(None, description="Number of cities/towns (only for country views)")
    country_count: Optional[int] = Field(None, description="Number of countries (only for regional views)")


class RoasterLocationSummary(BaseModel):
    """Summary of a roaster in a specific location."""

    id: int
    name: str
    slug: str
    website: str
    city: Optional[str] = None
    country_code: str
    country_name: str
    available_beans: int
    total_beans: int


class CountryInRegion(BaseModel):
    """A country within a region with its statistics."""

    name: str
    slug: str
    country_code: str
    roaster_count: int
    available_beans: int
    total_beans: int


class LocationDetailResponse(BaseModel):
    """Response for roaster location detail endpoint."""

    location_name: str
    location_type: Literal["country", "region"]
    location_slug: str
    country_code: Optional[str] = Field(None, description="ISO country code (only for countries)")
    region_code: Optional[str] = Field(None, description="Region code like XE, XA, XF, etc (only for regions)")
    region_name: Optional[str] = Field(None, description="Parent region name (only for countries)")
    region_slug: Optional[str] = Field(None, description="Parent region slug (only for countries)")
    statistics: LocationStatistics
    top_roasters: List[RoasterLocationSummary]
    top_cities: List[TopNote] = Field(
        default_factory=list, description="Top cities in this location (resuing TopNote for label/count)"
    )
    top_origins: List[TopNote] = Field(
        default_factory=list, description="Top countries sourcing from (resuing TopNote for label/count)"
    )
    varietals: List[TopVariety]
    countries: List[CountryInRegion] = Field(
        default_factory=list, description="List of countries in this region (only for regions)"
    )
