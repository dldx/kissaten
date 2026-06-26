"""AI search API endpoints."""

import logging
import os
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..ai.extractor import CoffeeDataExtractor
from ..ai.search_agent import AISearchAgent
from ..schemas import APIResponse, CoffeeBean, CoffeeBeanOptional
from ..schemas.ai_search import AISearchQuery, AISearchResponse


class SearchFeedback(BaseModel):
    """Request body for AI search result feedback."""

    query_hash: str
    vote: Literal["up", "down"]

logger = logging.getLogger(__name__)

# Create router for AI search endpoints
router = APIRouter(prefix="/v1/ai", tags=["AI Search"])


def create_ai_search_router(database_connection) -> APIRouter:
    """Create AI search router with database connection."""

    # Initialize AI search agent
    try:
        ai_agent = AISearchAgent(database_connection)
    except ValueError as e:
        logger.error(f"Failed to initialize AI search agent: {e}")
        ai_agent = None

    # Initialize Coffee Data Extractor
    try:
        extractor = CoffeeDataExtractor()
    except Exception as e:
        logger.error(f"Failed to initialize CoffeeDataExtractor: {e}")
        extractor = None

    @router.post("/extract", response_model=APIResponse[CoffeeBeanOptional])
    async def extract_coffee_data_from_image(file: UploadFile, optional: bool = False):
        """Extract structured coffee bean information from an image."""
        if extractor is None or ai_agent is None:
            raise HTTPException(
                status_code=503,
                detail="Coffee extraction service unavailable. Please check Google API key configuration.",
            )

        start_time = time.time()
        try:
            logger.info("Processing coffee extraction from image")

            # Read image bytes
            image_bytes = await file.read()

            # Check cache first (only in strict mode to avoid schema conflicts)
            query_hash = ai_agent.cache._hash_image_query(image_bytes)
            cache_hit = None
            if not optional:
                cache_hit = ai_agent.cache.get_cached_query(image_data=image_bytes)

            if cache_hit:
                processing_time = (time.time() - start_time) * 1000
                logger.info(f"Returning cached coffee extraction result (processing time: {processing_time:.2f}ms)")
                # Convert SearchParameters back to CoffeeBean (serialized as JSON in cache)
                # Since we stored CoffeeBean.model_dump() in search_params field of cache,
                # we can reconstruct it.
                bean_dict = cache_hit.search_params.model_dump()
                bean = CoffeeBean(**bean_dict)
                return APIResponse.success_response(
                    data=bean,
                    metadata={"query_hash": cache_hit.entry_id, "processing_time_ms": processing_time},
                )

            # Cache miss — check global rate limit
            rate_limit_max_requests = int(os.getenv("AI_RATE_LIMIT_MAX_REQUESTS", "10"))
            rate_limit_window_hours = int(os.getenv("AI_RATE_LIMIT_WINDOW_HOURS", "24"))
            rate_limit = ai_agent.cache.check_rate_limit(
                window_hours=rate_limit_window_hours, max_requests=rate_limit_max_requests
            )

            if not rate_limit["allowed"]:
                processing_time = (time.time() - start_time) * 1000
                reset_at = rate_limit.get("reset_at")
                reset_at_str = reset_at.isoformat() if reset_at else None
                logger.warning(
                    f"Rate limit exceeded for extraction: {rate_limit['current_count']}/{rate_limit['limit']} "
                    f"fresh AI requests in {rate_limit['window_hours']}h window"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": {
                            "rate_limited": True,
                            "error_message": "AI extraction rate limit exceeded. Please try again later.",
                            "rate_limit_remaining": 0,
                            "rate_limit_reset_at": reset_at_str,
                            "rate_limit_limit": rate_limit["limit"],
                        }
                    },
                )

            # Log fresh request
            ai_agent.cache.log_fresh_request("image")

            # Call extractor with image as screenshot_bytes
            bean = await extractor.extract_coffee_data(
                html_content="",
                # Placeholder URL for manually uploaded beans
                product_url="https://kissaten.app/manually-uploaded-coffee-bean",
                screenshot_bytes=image_bytes,
                use_one_shot_mode=True,  # Use one-shot mode for ai_search
                use_optional_schema=optional,
            )

            if not bean:
                return APIResponse.error_response(message="Failed to extract coffee bean information from image")

            # Ignore extracted price as it is frequently unreliable from images in strict mode
            if not optional:
                bean.price = None
                bean.price_options = []

            # Cache the result (only in strict mode to avoid schema conflicts)
            entry_id = query_hash
            if not optional:
                try:
                    entry_id = ai_agent.cache.cache_query(bean, image_data=image_bytes)  # type: ignore
                except Exception as cache_err:
                    logger.error(f"Failed to cache extraction result: {cache_err}")

            processing_time = (time.time() - start_time) * 1000
            return APIResponse.success_response(
                data=bean,
                metadata={"query_hash": entry_id, "processing_time_ms": processing_time},
            )

        except Exception as e:
            logger.error(f"Coffee extraction error: {e}")
            raise HTTPException(status_code=500, detail=f"Coffee extraction failed: {str(e)}")

    @router.post("/imagesearch", response_model=APIResponse[AISearchResponse])
    async def ai_image_search(file: UploadFile):
        """Translate natural language query to structured search parameters."""
        if ai_agent is None:
            raise HTTPException(
                status_code=503, detail="AI search service unavailable. Please check Google API key configuration."
            )

        try:
            logger.info("Processing AI image search query")

            # Translate the query using AI
            response = await ai_agent.translate_query(image_data=file.file.read())

            if response.rate_limited:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": {
                            "rate_limited": True,
                            "error_message": response.error_message,
                            "rate_limit_remaining": response.rate_limit_remaining,
                            "rate_limit_reset_at": response.rate_limit_reset_at,
                            "rate_limit_limit": response.rate_limit_limit,
                        }
                    },
                )

            if not response.success:
                return APIResponse.error_response(
                    message=response.error_message or "AI search translation failed",
                    metadata={"processing_time_ms": response.processing_time_ms},
                )

            return APIResponse.success_response(
                data=response,
                metadata={
                    "confidence": response.search_params.confidence if response.search_params else None,
                    "processing_time_ms": response.processing_time_ms,
                },
            )

        except Exception as e:
            logger.error(f"AI search error: {e}")
            raise HTTPException(status_code=500, detail=f"AI search failed: {str(e)}")

    @router.post("/search", response_model=APIResponse[AISearchResponse])
    async def ai_search(query: AISearchQuery):
        """Translate natural language query to structured search parameters."""
        if ai_agent is None:
            raise HTTPException(
                status_code=503, detail="AI search service unavailable. Please check Google API key configuration."
            )

        try:
            logger.info(f"Processing AI search query: {query.query}")

            # Translate the query using AI
            response = await ai_agent.translate_query(query.query)

            if response.rate_limited:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": {
                            "rate_limited": True,
                            "error_message": response.error_message,
                            "rate_limit_remaining": response.rate_limit_remaining,
                            "rate_limit_reset_at": response.rate_limit_reset_at,
                            "rate_limit_limit": response.rate_limit_limit,
                        }
                    },
                )

            if not response.success:
                return APIResponse.error_response(
                    message=response.error_message or "AI search translation failed",
                    metadata={"processing_time_ms": response.processing_time_ms},
                )

            return APIResponse.success_response(
                data=response,
                metadata={
                    "query": query.query,
                    "confidence": response.search_params.confidence if response.search_params else None,
                    "processing_time_ms": response.processing_time_ms,
                },
            )

        except Exception as e:
            logger.error(f"AI search error: {e}")
            raise HTTPException(status_code=500, detail=f"AI search failed: {str(e)}")

    @router.post("/search/redirect", response_model=APIResponse[dict])
    async def ai_search_redirect(query: AISearchQuery):
        """Translate natural language query and return search URL for frontend navigation."""
        if ai_agent is None:
            raise HTTPException(
                status_code=503, detail="AI search service unavailable. Please check Google API key configuration."
            )

        try:
            logger.info(f"Processing AI search redirect: {query.query}")

            # Translate the query using AI
            response = await ai_agent.translate_query(query.query)

            if not response.success or not response.search_url:
                # Fall back to regular search with the original query
                from urllib.parse import urlencode

                fallback_url = f"/search?q={urlencode({'': query.query})[1:]}"
                return APIResponse.success_response(
                    data={"redirect_url": fallback_url, "ai_success": False},
                    message="AI search failed, falling back to regular search",
                    metadata={"processing_time_ms": response.processing_time_ms if response else None}
                )

            # Return the generated search URL for frontend navigation
            return APIResponse.success_response(
                data={"redirect_url": response.search_url, "ai_success": True},
                message="AI search successful",
                metadata={
                    "query": query.query,
                    "confidence": response.search_params.confidence if response.search_params else None,
                    "processing_time_ms": response.processing_time_ms,
                }
            )

        except Exception as e:
            logger.error(f"AI search redirect error: {e}")
            # Fall back to regular search
            from urllib.parse import urlencode

            fallback_url = f"/search?q={urlencode({'': query.query})[1:]}"
            return APIResponse.success_response(
                data={"redirect_url": fallback_url, "ai_success": False},
                message="AI search failed, falling back to regular search",
                metadata={"error": str(e)}
            )

    @router.get("/health")
    async def ai_search_health():
        """Check AI search service health."""
        if ai_agent is None:
            return APIResponse.error_response(message="AI search service unavailable. Google API key not configured.")

        return APIResponse.success_response(data={"status": "healthy"}, message="AI search service is operational")

    @router.get("/cache/stats")
    async def get_cache_stats():
        """Get AI search cache statistics."""
        if ai_agent is None:
            raise HTTPException(
                status_code=503, detail="AI search service unavailable. Please check Google API key configuration."
            )

        try:
            stats = ai_agent.cache.get_cache_stats()
            return APIResponse.success_response(
                data=stats,
                message="Cache statistics retrieved successfully"
            )
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

    @router.post("/cache/cleanup")
    async def cleanup_cache():
        """Count expired cache entries (preserved for dataset building)."""
        if ai_agent is None:
            raise HTTPException(
                status_code=503, detail="AI search service unavailable. Please check Google API key configuration."
            )

        try:
            expired_count = ai_agent.cache.cleanup_expired()
            return APIResponse.success_response(
                data={"expired_count": expired_count},
                message=f"Found {expired_count} expired cache entries (preserved for dataset building)"
            )
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to cleanup cache: {str(e)}")

    @router.delete("/cache")
    async def clear_cache(query_type: str | None = None):
        """Clear cache entries.

        Args:
            query_type: Optional filter - 'text' or 'image'. If not provided, clears all.
        """
        if ai_agent is None:
            raise HTTPException(
                status_code=503, detail="AI search service unavailable. Please check Google API key configuration."
            )

        try:
            if query_type and query_type not in ["text", "image"]:
                raise HTTPException(status_code=400, detail="query_type must be 'text' or 'image'")

            deleted_count = ai_agent.cache.clear_cache(query_type)
            return APIResponse.success_response(
                data={"deleted_count": deleted_count},
                message=f"Cleared {deleted_count} cache entries" + (f" ({query_type})" if query_type else "")
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

    @router.post("/feedback")
    async def submit_feedback(feedback: SearchFeedback):
        """Record thumbs-up or thumbs-down feedback for an AI search result."""
        if ai_agent is None:
            raise HTTPException(status_code=503, detail="AI search service unavailable.")
        try:
            counts = ai_agent.cache.submit_feedback(feedback.query_hash, feedback.vote)
            if counts is None:
                raise HTTPException(status_code=404, detail="Cache entry not found")
            return APIResponse.success_response(
                data=counts,
                message="Feedback recorded",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")

    return router
