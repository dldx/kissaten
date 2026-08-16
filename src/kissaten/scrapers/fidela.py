"""Fidela Coffee scraper implementation with Shopify JSON extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="fidela",
    display_name="Fidela",
    roaster_name="Fidela",
    website="https://fidelacoffee.com",
    description="UK specialty coffee roaster sourcing exceptional single origin "
    "coffees from Colombia with transparency and care",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FidelaScraper(ShopifyJsonScraper):
    """Scraper for Fidela (fidelacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Fidela Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Fidela",
            base_url="https://fidelacoffee.com",
            products_json_urls=["https://fidelacoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, sample packs,
        # gift bundles, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "bundle",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Send the bean bag image as the visual screenshot for AI extraction.

        Fidela prints the tasting notes on the bag label, so the AI reads them
        best from the product image. The image is downloaded from the Shopify
        JSON metadata and passed as ``screenshot_bytes`` to the extractor
        instead of a full-page screenshot, which contains unrelated content
        (related products, banners) that can contaminate the tasting notes.
        """
        url_str = str(product_url)

        # Build a soup purely from the Shopify JSON context (no page fetch).
        if url_str in self._shopify_product_data:
            product_json = self._shopify_product_data[url_str]
            context_html = self._format_shopify_context(product_json)
            soup = BeautifulSoup(context_html, "lxml")

        # Download the main product image (the bean bag photo) for visual analysis.
        screenshot_bytes = None
        images = self._shopify_product_data.get(url_str, {}).get("images", [])
        if images:
            image_url = str(images[0].get("src", ""))
            if image_url:
                logger.info(f"Downloading bean image for visual AI analysis: {image_url}")
                try:
                    response = await self.client.get(image_url)
                    response.raise_for_status()
                    screenshot_bytes = response.content
                except Exception as e:
                    logger.warning(f"Failed to download bean image {image_url}: {e}")

        bean = await ai_extractor.extract_coffee_data(
            str(soup),
            url_str,
            screenshot_bytes=screenshot_bytes,
            use_optimized_mode=True,
            default_currency=self.store_currency,
        )

        if bean:
            bean.roaster = self.roaster_name
            return self.postprocess_extracted_bean(bean)

        return None
