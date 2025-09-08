"""Koppi coffee roastery scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="koppi",
    display_name="Koppi",
    roaster_name="Koppi",
    website="https://koppi.se",
    description="Swedish specialty coffee roastery known for their Nordic light roasting style "
    "and single-origin coffees",
    requires_api_key=True,
    currency="SEK",
    country="Sweden",
    status="available",
)
class KoppiScraper(BaseScraper):
    """Scraper for Koppi (koppi.se) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Koppi scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Koppi",
            base_url="https://koppi.se",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://koppi.se/collections/frontpage"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Koppi using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,  # Enable screenshot mode for better extraction
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                # Generic Shopify product link selectors
                'a[href*="/products/"]',
                '.product-item a',
                '.product-link',
                '.product-card a',
                '.product a',
                # Specific selectors for Koppi
                'h3 a[href*="/products/"]',
                'h4 a[href*="/products/"]',
                '.product-title a',
                '.grid-product__link',
            ],
        )

        # Filter out non-coffee products (subscriptions, merchandise, equipment, etc.)
        excluded_products = [
            "subscription",  # Monthly subscription, gift pack subscription
            "holiday-pack",  # Gift pack subscription
            "monthly-subscription",  # Monthly subscription
            "sweatshirt",  # Koppi sweatshirt
            "tote-bag",  # Koppi tote bag
            "cap",  # Koppi cap
            "hat",  # Any hats
            "shirt",  # T-shirts
            "hoodie",  # Hoodies
            "bag",  # Bags
            "merch",  # General merchandise
            "merchandise",  # General merchandise
            "gift-card",  # Gift cards
            "gift",  # General gift items (except coffee gifts)
            "wholesale",  # Wholesale products
            "aeropress-filters",  # AeroPress filters
            "hario-v60-filters",  # Hario V60 filters
            "filter",  # Paper filters
            "equipment",  # Brewing equipment
            "grinder",  # Coffee grinders
            "kettle",  # Kettles
            "dripper",  # Drippers
            "chemex",  # Chemex products
            "v60",  # V60 products (unless it's coffee)
        ]

        filtered_urls = []
        for url in product_urls:
            url_lower = url.lower()

            # Check if any excluded product identifier is in the URL
            is_excluded = any(excluded in url_lower for excluded in excluded_products)

            # Additional check for subscription patterns
            if "subscription" in url_lower or "gift-pack" in url_lower:
                is_excluded = True

            # Additional check for merchandise patterns
            if any(merch_term in url_lower for merch_term in ["sweatshirt", "tote", "cap", "hat"]):
                is_excluded = True

            # Additional check for equipment patterns
            if any(equip_term in url_lower for equip_term in ["filter", "aeropress", "hario", "v60"]):
                # Only exclude if it's clearly equipment, not coffee
                if not any(coffee_term in url_lower for coffee_term in ["coffee", "bean", "roast", "espresso"]):
                    is_excluded = True

            if not is_excluded:
                filtered_urls.append(url)
                logger.debug(f"Including product URL: {url}")
            else:
                logger.debug(f"Excluding non-coffee product URL: {url}")

        logger.info(f"Found {len(filtered_urls)} coffee product URLs out of {len(product_urls)} total products")
        return filtered_urls
