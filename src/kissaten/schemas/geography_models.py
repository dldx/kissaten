"""Geographical hierarchy API models for Kissaten."""

from typing import Optional, List
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
    top_regions: List[RegionSummary]
    top_roasters: List[TopRoaster]
    common_tasting_notes: List[TopNote]
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
    varietals: List[str]
    processing_methods: List[str]
