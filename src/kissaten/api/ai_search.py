"""AI search API endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from ..ai.search_agent import AISearchAgent
from ..schemas import APIResponse
from ..schemas.ai_search import AISearchQuery, AISearchResponse

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

    return router
