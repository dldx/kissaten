"""Outpost Coffee scraper implementation.

Outpost Coffee Roasters is a specialty coffee roastery based in Nottingham, UK.
They focus on high-quality single-origin coffees and innovative processing methods.
"""

import logging

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="outpost-coffee",
    display_name="Outpost Coffee",
    roaster_name="Outpost Coffee Roasters",
    website="https://outpost.coffee",
    description="Specialty coffee roastery from Nottingham, focusing on innovative processing methods",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class OutpostCoffeeScraper(BaseScraper):
    """Scraper for Outpost Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Outpost Coffee Roasters",
            base_url="https://outpost.coffee",
            rate_limit_delay=1.5,  # Be respectful to the site
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs

        NOTE: The dedicated ``coffees`` collection exists but is currently
        empty roaster-side (verified live: its listing HTML contains only a
        gift-card link and "no products" markers). The ``all`` collection is
        the only listing that still exposes the coffee products (BROKEN
        PROMISE, CHEAT CODE, COOL KIDS, LOW RIDER, ...), alongside equipment
        and merch which are filtered out below.
        """
        return [
            "https://outpost.coffee/collections/all",
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Use the base class method with Outpost Coffee's URL patterns
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
                ".grid-product__link",
                "h3 a",
            ],
        )

        excluded_products = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "test-roast",
            "fellow-",
            "lucky-dip",
        ]
        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        # The 'all' collection also carries brewing equipment and merch that
        # the legacy excluded_products list doesn't cover (aeropress, V60,
        # Fellow, La Marzocco, tote bags, running caps, ...). Filter those by
        # slug so only coffee beans reach the AI extraction stage.
        equipment_and_merch_slugs = [
            "aeropress",
            "aero-press",
            "v60",
            "hario",
            "fellow",
            "la-marzocco",
            "stagg",
            "grinder",
            "filter-papers",
            "filtropa",
            "dripper",
            "kettle",
            "tote",
            "cap",
            "shirt",
            "mug",
            "cup",
        ]
        coffee_urls = []
        for url in filtered_urls:
            slug = url.rstrip("/").rsplit("/", 1)[-1].lower()
            if any(marker in slug for marker in equipment_and_merch_slugs):
                logger.debug(f"Skipping equipment/merch product: {url}")
                continue
            coffee_urls.append(url)

        logger.info(
            f"Outpost Coffee: {len(coffee_urls)} coffee URLs after filtering "
            f"({len(product_urls)} raw product links from {store_url})"
        )
        return coffee_urls
