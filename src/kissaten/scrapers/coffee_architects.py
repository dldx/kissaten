"""Coffee Architects coffee roaster scraper implementation with AI-powered extraction from images."""

import logging
from pathlib import Path

from pydantic import HttpUrl

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffee-architects",
    display_name="Coffee Architects",
    roaster_name="Coffee Architects",
    website="https://www.coffee-architects.com",
    description="Specialty coffee roaster based in Zurich, Switzerland, "
    "focusing on high-quality single origins and blends.",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class CoffeeArchitectsScraper(BaseScraper):
    """Scraper for Coffee Architects (coffee-architects.com) with AI extraction from images."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Architects scraper."""
        super().__init__(
            roaster_name="Coffee Architects",
            base_url="https://www.coffee-architects.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape. Coffee Architects is a single-page site."""
        return ["https://www.coffee-architects.com"]

    def _get_slug_from_image_url(self, image_url: str) -> str:
        """Extract a slug from the Squarespace image URL."""
        parts = image_url.split("/")
        last_part = parts[-1]
        # Remove extension if any
        slug = last_part.split(".")[0].lower()
        # Clean up
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """
        Since this is a single-page site without separate product pages,
        we treat each bean image as a 'product'.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Find the section containing the beans.
        # It's inside a div.fluid-engine that has an <h2> with text "Angebot"
        angebot_section = None
        for engine in soup.select("div.fluid-engine"):
            h2 = engine.find("h2")
            if h2 and "angebot" in h2.get_text().lower():
                angebot_section = engine
                break

        if not angebot_section:
            logger.warning("Could not find 'Angebot' section in store page")
            return []

        pseudo_urls = []
        # Find all images in the "Angebot" (Offer) section
        # The site structure uses fluid-image-container for product images
        for container in angebot_section.select("div.fluid-image-container"):
            img = container.find("img")
            if not img:
                continue

            src = img.get("src") or img.get("data-src")
            if not src:
                continue

            # We try to extract a slug from the image URL to create a stable pseudo-URL
            # compatible with what the AI extraction will produce.
            image_url = self.resolve_url(src)
            slug = self._get_slug_from_image_url(image_url)
            if slug:
                pseudo_url = f"{self.base_url}/#{slug}"
                # Store the mapping so we can retrieve the image URL later
                if not hasattr(self, "_pseudo_to_image_map"):
                    self._pseudo_to_image_map = {}
                self._pseudo_to_image_map[pseudo_url] = image_url
                pseudo_urls.append(pseudo_url)

        return pseudo_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Custom scrape implementation to handle image-based extraction."""
        if not product_urls:
            return []

        if not self.session:
            self.start_session()

        coffee_beans = []
        output_dir = Path("data")

        for pseudo_url in product_urls:
            try:
                # Retrieve the image URL from our map
                image_url = self._pseudo_to_image_map.get(pseudo_url)
                if not image_url:
                    logger.warning(f"Could not find image URL for {pseudo_url}")
                    continue

                # Fetch the image bytes
                logger.info(f"Downloading image for AI extraction: {image_url}")
                response = await self.client.get(image_url)
                response.raise_for_status()
                image_bytes = response.content

                # Use AI to extract data from the image
                bean_optional = await self.ai_extractor.extract_coffee_data(
                    html_content="Single page website. Extract coffee details from the provided image.",
                    product_url=pseudo_url,
                    screenshot_bytes=image_bytes,
                    use_optimized_mode=True,
                    default_currency="CHF",
                    use_optional_schema=True,
                )

                if bean_optional and bean_optional.name:
                    # We use the pseudo_url we generated (which has the slug)
                    # to ensure it matches the duplicate detection.
                    # If the AI-extracted name would result in a different slug,
                    # we prefer the one from the image URL if possible, or just use pseudo_url.

                    # Ensure other required fields for CoffeeBean
                    bean = CoffeeBean(
                        name=bean_optional.name,
                        roaster=self.roaster_name,
                        url=HttpUrl(pseudo_url),
                        image_url=HttpUrl(image_url),
                        description=bean_optional.description or "",
                        origins=bean_optional.origins or [],
                        is_single_origin=(
                            bean_optional.is_single_origin
                            if bean_optional.is_single_origin is not None
                            else True
                        ),
                        price_options=bean_optional.price_options or [],
                        price=bean_optional.price,
                        weight=bean_optional.weight,
                        currency="CHF",
                        in_stock=bean_optional.in_stock if bean_optional.in_stock is not None else True,
                        tasting_notes=bean_optional.tasting_notes or [],
                    )

                    bean = self.postprocess_extracted_bean(bean)
                    if bean:
                        await self.save_bean_with_image(bean, output_dir)
                        self._mark_bean_as_scraped(pseudo_url)
                        coffee_beans.append(bean)

            except Exception as e:
                logger.error(f"Error extracting from {pseudo_url}: {e}")

        return coffee_beans

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Filter out beans that are clearly not coffee or are duplicates."""
        if not bean.name or "Coffee Architects" in bean.name:
            return None
        return super().postprocess_extracted_bean(bean)
