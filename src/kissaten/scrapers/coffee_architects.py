"""Coffee Architects coffee roaster scraper implementation with AI-powered extraction.

Coffee Architects (coffee-architects.com) is a specialty coffee roaster based
in Zurich, Switzerland. The storefront migrated from a Squarespace single-page
site (where beans were rendered as images inside an "Angebot" section and
needed pseudo-URL based image extraction) to a standard Shopify store. The
full catalogue is only 6 coffee products and lives under ``/collections/all``;
``/products.json`` exposes them directly. This scraper therefore uses the
standard Shopify JSON discovery flow (products.json for listing + stock, AI
extraction on the server-rendered product detail pages).
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

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
class CoffeeArchitectsScraper(ShopifyJsonScraper):
    """Scraper for Coffee Architects (coffee-architects.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Architects scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Architects",
            base_url="https://www.coffee-architects.com",
            products_json_urls=[
                "https://www.coffee-architects.com/collections/all/products.json",
                "https://www.coffee-architects.com/products.json",
            ],
            scrape_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Exclude equipment / merch / services (no such products currently in
        # the catalogue, but guard against future additions).
        self.exclude_slugs = [
            "gift-card",
            "subscription",
            "workshop",
            "training",
        ]

    def preprocess_product_url(self, url: str) -> str:
        """Strip collection segments so product URLs are canonical."""
        return url.replace("/collections/all", "")

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # Shopify exposes og:price:amount but not og:price:currency, so the
        # base currency detection never fires; Coffee Architects prices in
        # CHF. Pin the currency up front.
        self.store_currency = "CHF"
        bean.currency = "CHF"
        return super().postprocess_extracted_bean(bean)

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using Shopify JSON context.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_product_urls,
            ai_extractor=self.ai_extractor,
            use_optimized_mode=True,
        )
