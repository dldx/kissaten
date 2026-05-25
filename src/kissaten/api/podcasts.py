from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from kissaten.api.podcast_db import search_podcasts
from kissaten.schemas.podcast import PodcastSearchResponse, PodcastSearchHit
from kissaten.schemas import APIResponse

router = APIRouter(prefix="/v1/podcasts", tags=["Podcasts"])

@router.get("/search", response_model=APIResponse[PodcastSearchResponse])
async def search_podcast_segments(
    query: Optional[str] = Query("", description="Search query for podcast segments"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of segments to return"),
    process: Optional[str] = Query(None, description="Filter by canonical process ID"),
    variety: Optional[str] = Query(None, description="Filter by canonical variety ID"),
    origin: Optional[str] = Query(None, description="Filter by canonical origin ID (country)"),
    producer: Optional[str] = Query(None, description="Filter by producer or farm name"),
):
    """
    Search for relevant segments across podcast transcripts.
    Uses weighted FTS and entity matching for high-quality retrieval.
    """
    try:
        hits = await search_podcasts(
            query=query,
            limit=limit,
            process_filter=process,
            variety_filter=variety,
            origin_filter=origin,
            producer_filter=producer,
        )

        data = PodcastSearchResponse(hits=hits, total_hits=len(hits), query=query)

        return APIResponse.success_response(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
