"""AI agent for selecting best geocoding result."""

import logging
import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModelSettings

logger = logging.getLogger(__name__)


class RegionSelection(BaseModel):
    """Selected region from geocoding results."""

    selected_index: int | None = Field(
        default=None, description="Index of selected result (0-based), None if invalid"
    )
    canonical_state: str | None = Field(
        default=None,
        description="State/province name (administrative level 1), None if invalid region",
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in selection (0.0-1.0)"
    )
    reasoning: str = Field(description="Brief explanation of selection decision")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional geographical metadata from OpenCage",
    )


class RegionSelector:
    """AI agent for selecting best geocoding result using Gemini Flash."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.agent = Agent(
            "gemini-2.5-flash-lite",
            output_type=RegionSelection,
            system_prompt=self._get_system_prompt(),
            model_settings=GeminiModelSettings(
                gemini_thinking_config={"thinking_budget": 0}
            ),
        )

    def _get_system_prompt(self) -> str:
        return """You are an expert geographical data analyst specializing in administrative region mapping.

Your task is to select the BEST matching geographical region from OpenCage geocoding results.

Context:
- You are processing region names from geographical origin data
- Region names in source data vary widely: "Boquete", "Boquete Valley", "Jaramillo, Boquete"
- Your goal is to identify the most appropriate administrative/geographical unit

Selection Criteria (in priority order):
1. **Administrative Level**: Choose appropriate granularity (province/state vs. tiny hamlet)
2. **Elevation Match**: Coffee regions are typically at higher elevations (800-2500m). If elevation range is provided, prefer results whose elevation falls within or near that range
3. **Confidence Score**: OpenCage provides confidence (1-10), prefer higher scores
4. **Component Completeness**: Results with more administrative components are more precise
5. **Geographical Accuracy**: Consider bounds and geographical context
6. **Name Clarity**: Prefer results that disambiguate (e.g., "Boquete, Chiriquí" vs just "Boquete")
7. **Coffee growing relevance**: Prefer results that are relevant to coffee growing

Common Patterns:
- If original query is "Jaramillo, Boquete", the result should be the broader "Boquete"
  region (Jaramillo is a district within Boquete)
- If query is "Chiriquí", prefer the province-level result, not a town with same name
- If query is "Volcán", prefer the rural location, not the town itself.
- Handle spelling variations: "Volcan" → "Volcán", "Chiriqui" → "Chiriquí"

Output Requirements:
- selected_index: 0-based index of chosen result, OR None if no valid match
- canonical_state: The STATE/PROVINCE name ONLY (e.g., "Chiriquí", not "Boquete, Chiriquí"), OR None if invalid
- confidence: Your confidence in selection (0.0-1.0), considering all factors above
- reasoning: 1-2 sentence explanation of why this result was chosen (or why it was rejected)

IMPORTANT: Extract only the state/province level (administrative level 1), NOT districts or towns.
Examples:
- "Boquete" → canonical_state: "Chiriquí" (state)
- "Jaramillo, Boquete" → canonical_state: "Chiriquí" (state)
- "Volcán, Chiriquí" → canonical_state: "Chiriquí" (state)

INVALID REGION DETECTION:
Return selected_index=None and canonical_state=None if:
- All results have very low confidence (<3 out of 10)
- Results are in wrong country (e.g., querying Panama but got results from Colombia)
- Results are obviously unrelated (e.g., "Coffee Street" for a region name)
- Result refers to an urban area (coffee farms are rural)
- No state/province data available in any result
- Region name appears to be a typo or nonsense text
- Query is just the country name itself (e.g., "Panama" in Panama) - we need regions WITHIN the country, not the country
- Result is the entire country rather than a specific administrative region within it

Be decisive. Geographical data needs consistency, so even with uncertainty, select the most reasonable option.
However, if the data is clearly invalid, it's better to return None than propagate incorrect information."""

    async def select_best_result(
        self,
        original_region: str,
        country_code: str,
        geocoding_results: list[dict],
        elevation_range: tuple[float, float] | None = None,
    ) -> RegionSelection:
        """
        Select best region from OpenCage geocoding results using AI.

        Args:
            original_region: Original region name from coffee data
            country_code: Two-letter ISO country code
            geocoding_results: List of result dicts from OpenCage API
            elevation_range: Optional tuple of (min_elevation_m, max_elevation_m) for coffee beans from this region

        Returns:
            RegionSelection with selected result and confidence
        """

        # Format results for AI analysis
        formatted_results = []
        for i, result in enumerate(geocoding_results):
            components = result.get("components", {})
            if components["_category"] != "place":
                continue

            # Extract elevation from annotations if available
            elevation_m = None
            annotations = result.get("annotations", {})
            if "elevation" in annotations:
                elevation_m = annotations["elevation"].get("meters")

            formatted_results.append(
                {
                    "index": i,
                    "formatted": result.get("formatted", ""),
                    "components": components,
                    "confidence": result.get("confidence", 0),
                    "elevation_m": elevation_m,
                    "bounds": result.get("bounds", {}),
                    "geometry": result.get("geometry", {}),
                }
            )

        elevation_context = ""
        if elevation_range:
            min_elev, max_elev = elevation_range
            elevation_context = f"\n\nElevation data for coffee beans from this region: {min_elev:.0f}-{max_elev:.0f} meters\nNote: Coffee is typically grown at higher elevations (800-2400m). Use this to validate geographical accuracy."

        prompt = f"""Original region name: "{original_region}"
Country: {country_code}{elevation_context}

OpenCage geocoding results ({len(formatted_results)} results):

{formatted_results}

Analyze these results and select the BEST match for this geographical region.
Consider the selection criteria in your system prompt and provide a confident decision."""

        try:
            result = await self.agent.run(prompt)
            return result.output
        except Exception as e:
            logger.error(f"Error selecting region for '{original_region}': {e}")
            # Fallback: try to extract state from first result, but mark as invalid if not found
            first_result = geocoding_results[0]
            components = first_result.get("components", {})
            fallback_state = components.get(
                "state", components.get("province", None)
            )

            # If no state/province found, mark as invalid
            if not fallback_state:
                return RegionSelection(
                    selected_index=None,
                    canonical_state=None,
                    confidence=0.0,
                    reasoning=f"AI selection failed and no state/province found in results: {e}",
                    metadata={},
                )

            return RegionSelection(
                selected_index=0,
                canonical_state=fallback_state,
                confidence=0.2,
                reasoning=f"AI selection failed, using first result with caution: {e}",
                metadata={},
            )
