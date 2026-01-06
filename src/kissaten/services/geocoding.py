"""OpenCage geocoding service for region deduplication."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class OpenCageGeocoder:
    """OpenCage API client for geocoding regions."""

    def __init__(self, api_key: str | None = None, cache_dir: Path | None = None):
        self.api_key = api_key or os.getenv("OPENCAGE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenCage API key required. Set OPENCAGE_API_KEY environment variable "
                "or pass api_key parameter. Get key from: https://opencagedata.com/api"
            )

        self.base_url = "https://api.opencagedata.com/geocode/v1/json"
        self.timeout = 30.0
        self.max_retries = 3

        # Cache directory for full API responses
        self.cache_dir = cache_dir or Path("data/geocoding_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cached_response(
        self, region: str, country_code: str
    ) -> dict[str, Any] | None:
        """Check if we have a cached response for this region."""
        country_cache = self.cache_dir / country_code.upper()
        if not country_cache.exists():
            return None

        # Use same normalization as _cache_response
        import re
        import unicodedata

        nfkd_form = unicodedata.normalize("NFKD", region)
        ascii_only = nfkd_form.encode("ASCII", "ignore").decode("ASCII")
        normalized = re.sub(r"[^a-zA-Z0-9\s]", "", ascii_only.lower())
        normalized = re.sub(r"\s+", "-", normalized.strip())

        filename = f"{normalized}.json"
        cache_file = country_cache / filename

        if cache_file.exists():
            logger.info(f"Using cached geocoding result for '{region}'")
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)

        return None

    async def geocode_region(
        self, region: str, country_code: str, retries: int = 0
    ) -> dict[str, Any] | None:
        """
        Geocode a region within a country using OpenCage API.

        Args:
            region: Region name to geocode
            country_code: Two-letter ISO country code (e.g., 'PA')
            retries: Current retry attempt (internal use)

        Returns:
            Full OpenCage API response as dict, or None on error
        """
        # Check cache first
        cached = self._get_cached_response(region, country_code)
        if cached is not None:
            return cached

        query = f"{region}, {country_code}"

        params = {
            "q": query,
            "key": self.api_key,
            "countrycode": country_code.lower(),
            "no_annotations": 0,  # Get full details including bounds, timezone, etc.
            "limit": 5,  # Get top 5 results for AI selection
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                result = response.json()

                # Save to cache
                self._cache_response(region, country_code, result)

                return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and retries < self.max_retries:
                # Rate limit hit, exponential backoff
                wait_time = 2**retries
                logger.warning(
                    f"Rate limit hit for '{query}', waiting {wait_time}s before retry "
                    f"(attempt {retries + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)
                return await self.geocode_region(region, country_code, retries + 1)

            logger.error(f"HTTP error geocoding '{query}': {e}")
            return None

        except Exception as e:
            logger.error(f"Error geocoding '{query}': {e}")
            return None

    def _cache_response(
        self, region: str, country_code: str, response: dict[str, Any]
    ):
        """Save full API response to cache for future reference."""
        country_cache = self.cache_dir / country_code.upper()
        country_cache.mkdir(exist_ok=True)

        # Use normalized region name as filename
        # Import here to avoid circular dependency
        import re
        import unicodedata

        # Simple normalization for filename
        nfkd_form = unicodedata.normalize("NFKD", region)
        ascii_only = nfkd_form.encode("ASCII", "ignore").decode("ASCII")
        normalized = re.sub(r"[^a-zA-Z0-9\s]", "", ascii_only.lower())
        normalized = re.sub(r"\s+", "-", normalized.strip())

        filename = f"{normalized}.json"
        cache_file = country_cache / filename

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)

    def extract_state_name(self, geocoding_result: dict[str, Any]) -> str | None:
        """
        Extract state/province name from geocoding result.

        Priority: state > state_district > province > county
        """
        if not geocoding_result or "results" not in geocoding_result:
            return None

        results = geocoding_result["results"]
        if not results:
            return None

        # Get top result
        top_result = results[0]
        components = top_result.get("components", {})

        # Extract state-level administrative division
        # Priority order for coffee-growing regions
        for key in ["state", "state_district", "province", "county"]:
            if key in components:
                return components[key]

        return None

    def extract_metadata(self, geocoding_result: dict[str, Any]) -> dict[str, Any]:
        """
        Extract comprehensive metadata from geocoding result.

        Returns dict with ISO codes, bounds, geometry, elevation, and ALL administrative/component data.
        Stores all available geographic information for future use.
        """
        if not geocoding_result or "results" not in geocoding_result:
            return {}

        results = geocoding_result["results"]
        if not results:
            return {}

        top_result = results[0]
        components = top_result.get("components", {})

        # Start with ALL component fields from OpenCage API
        # This includes: ISO codes, continent, country, state, county, city, village,
        # town, hamlet, suburb, neighbourhood, postcode, road, etc.
        metadata = {}

        # Add all component fields, preserving original key names
        for key, value in components.items():
            # Handle ISO_3166-2 which can be a list or string
            if key == "ISO_3166-2":
                if isinstance(value, list):
                    metadata["iso_3166_2"] = value[0] if value else None
                else:
                    metadata["iso_3166_2"] = value
            # Convert other ISO keys to snake_case for consistency
            elif key == "ISO_3166-1_alpha-2":
                metadata["iso_3166_1_alpha_2"] = value
            elif key == "ISO_3166-1_alpha-3":
                metadata["iso_3166_1_alpha_3"] = value
            else:
                # Store all other fields with original key names
                metadata[key] = value

        # Add geometry and bounds from top-level result
        if "bounds" in top_result:
            metadata["bounds"] = top_result["bounds"]
        if "geometry" in top_result:
            metadata["geometry"] = top_result["geometry"]

        # Add elevation from annotations
        annotations = top_result.get("annotations", {})
        if "elevation" in annotations:
            elevation_data = annotations["elevation"]
            # Store elevation in meters (primary) and feet (for reference)
            metadata["elevation_m"] = elevation_data.get("meters")
            metadata["elevation_ft"] = elevation_data.get("feet")

        # Remove None values for cleaner JSON
        return {k: v for k, v in metadata.items() if v is not None}
