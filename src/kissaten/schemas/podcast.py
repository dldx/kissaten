from pydantic import BaseModel, Field
from typing import List, Optional

class PodcastSearchHit(BaseModel):
    """A search result from podcast segments."""
    segment_id: str
    episode_id: str
    podcast_name: str
    episode_title: str
    url: Optional[str] = None
    media_type: str = "podcast"
    audio_url: Optional[str] = None
    published_date: Optional[str] = None
    title: str
    summary: str
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    relevance_score: float
    matched_entities: List[str] = Field(default_factory=list)

class PodcastSearchResponse(BaseModel):
    """Response containing podcast search results."""
    hits: List[PodcastSearchHit]
    total_hits: int
    query: str
