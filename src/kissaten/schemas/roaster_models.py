"""Roaster API models for Kissaten."""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from .api_models import APISearchResult
from .geography_models import TopNote, TopOrigin, TopProcess, TopVariety


class RoasterStatistics(BaseModel):
    """Aggregate statistics for a roaster."""

    total_beans: int
    available_beans: int
    total_origins: int = Field(
        default=0,
        description="Number of distinct origin countries featured across this roaster's beans",
    )
    total_varieties: int = Field(
        default=0,
        description="Number of distinct coffee varieties across this roaster's beans",
    )
    avg_cupping_score: Optional[float] = None
    avg_price_usd: Optional[float] = None


class FlavourCategoryCount(BaseModel):
    """A primary flavour category with its share of this roaster's tasting notes."""

    primary_category: str
    count: int = Field(description="Number of bean-note occurrences in this category")
    percentage: float = Field(description="Share of this roaster's categorised notes (0-100)")


class RoastLevelCount(BaseModel):
    """A roast level with the number of beans the roaster offers at that level."""

    roast_level: str
    count: int


class UniquenessInsight(BaseModel):
    """Identifies a category (in one dimension) where this roaster most differs
    from the global average across all roasters.

    Dimensions:
      - ``flavour``: tasting-note primary_category (e.g. "Stone Fruit").
      - ``origin``: source country (ISO alpha-2 code, e.g. "ET").
      - ``process``: processing category slug (e.g. "anaerobic_carbonic").
      - ``varietal``: varietal family slug (e.g. "geisha").
    """

    dimension: Literal["flavour", "origin", "process", "varietal"]
    primary_category: str = Field(
        description="Raw category key (flavour name, ISO country code, process/varietal family slug)"
    )
    display_label: str = Field(
        description="Human-readable label for chips and headlines (e.g. 'Ethiopia', 'Anaerobic & Carbonic')"
    )
    this_roaster_pct: float = Field(
        description="Share of this roaster's beans/notes that fall in this category (0-100)"
    )
    global_pct: float = Field(
        description="Share of all roasters' beans/notes that fall in this category (0-100)"
    )
    lift: float = Field(
        description="Signed difference between this_roaster_pct and global_pct (percentage points)"
    )
    percentile: float = Field(
        description="Percentage of roasters whose share of this category is below this roaster's (0-100)"
    )
    sample_size: int = Field(
        description="Number of beans/notes that contributed to this roaster's denominator for this dimension"
    )
    link: Optional[str] = Field(
        None,
        description=(
            "Absolute site path to explore this category further (e.g. '/origins/et'). "
            "Null when no dedicated route exists for this category."
        ),
    )


class UniquenessReport(BaseModel):
    """Multi-dimensional uniqueness summary for a roaster.

    ``top`` is the single strongest standout across all four dimensions
    (highest percentile, tie-broken by lift). ``by_dimension`` carries the
    winning insight per dimension, excluding the dimension that produced
    ``top`` (so the headline and chip do not duplicate each other).
    """

    top: Optional[UniquenessInsight] = Field(
        None,
        description="The single strongest standout across all dimensions; null when no dimension passes thresholds",
    )
    by_dimension: Dict[str, UniquenessInsight] = Field(
        default_factory=dict,
        description="Per-dimension winning insight (excluding the top dimension); only includes passing dimensions",
    )


class RoasterDetailResponse(BaseModel):
    """Response for roaster detail endpoint."""

    id: int
    name: str
    slug: str
    website: Optional[str] = None
    location: Optional[str] = None
    country_code: Optional[str] = None
    country_slug: Optional[str] = None
    region_slug: Optional[str] = None
    description: Optional[str] = Field(
        None,
        description="Short marketing/description text from the roaster (when available)",
    )
    last_scraped: Optional[str] = None
    statistics: RoasterStatistics
    beans: List[APISearchResult] = Field(
        default_factory=list,
        description="All beans currently cataloged for this roaster",
    )
    top_origins: List[TopOrigin] = Field(
        default_factory=list,
        description="Top origin countries represented in this roaster's beans",
    )
    varietals: List[TopVariety] = Field(default_factory=list)
    processing_methods: List[TopProcess] = Field(default_factory=list)
    common_tasting_notes: List[TopNote] = Field(default_factory=list)
    flavour_categories: List[FlavourCategoryCount] = Field(
        default_factory=list,
        description="Primary tasting-note category distribution for this roaster's beans",
    )
    roast_distribution: List[RoastLevelCount] = Field(
        default_factory=list,
        description="Roast level distribution for this roaster's beans (Light → Dark)",
    )
    uniqueness: Optional[UniquenessReport] = Field(
        None,
        description=(
            "Multi-dimensional uniqueness report: the single strongest standout "
            "(``top``) plus per-dimension winners (``by_dimension``). None when no "
            "dimension clears the lift/percentile thresholds."
        ),
    )