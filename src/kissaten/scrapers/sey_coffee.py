"""Sey Coffee scraper.

Brooklyn-based specialty coffee roaster known for exceptional sourcing,
price transparency, and detailed producer partnerships.
"""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sey-coffee",
    display_name="Sey Coffee",
    roaster_name="Sey Coffee",
    website="https://www.seycoffee.com",
    description="Brooklyn-based specialty coffee roaster known for exceptional "
    "sourcing and price transparency",
    requires_api_key=True,  # Using AI extraction for best results
    currency="USD",
    country="United States",
    status="available",
)
class SeyCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Sey Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Sey Coffee",
            base_url="https://www.seycoffee.com",
            products_json_urls=[
                "https://www.seycoffee.com/collections/coffee/products.json",
                # "https://www.seycoffee.com/collections/archived-coffees/products.json",
            ],
            scrape_product_pages=True,
            use_optimized_mode=True,
            rate_limit_delay=1.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Exclude non-coffee products
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "test-roast",
            "recurring",
        ]

        # Initialize AI extractor (recommended for complex custom sites)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Extract bean data with canonical URL check to avoid duplicates."""
        # Predict canonical URL from slug - Sey uses /products/slug exclusively
        try:
            slug = product_url.split("/products/")[-1].split("?")[0].rstrip("/")
        except (IndexError, AttributeError):
            # Fallback to base class behavior if URL structure is unexpected
            return await super()._extract_bean_with_ai(
                ai_extractor, soup, product_url, use_optimized_mode, translate_to_english
            )

        canonical_url = f"https://www.seycoffee.com/products/{slug}"

        # If we already have this bean under any variation, skip
        if self._is_bean_already_scraped_anywhere(canonical_url) or self._is_bean_already_scraped_anywhere(product_url):
            logger.info(f"Skipping {product_url} as it is already in historical data")
            return None

        # Proceed with AI extraction
        bean = await super()._extract_bean_with_ai(
            ai_extractor,
            soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )

        if bean:
            # If the bean is in the archive, it's out of stock
            if "/collections/archived-coffees/" in product_url:
                bean.in_stock = False
                logger.info(f"Marked {product_url} as out of stock (archived)")

            # Update bean URL to canonical and mark as scraped
            bean.url = canonical_url
            self._mark_bean_as_scraped(canonical_url)

        return bean
