"""Tim Wendelboe scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="tim-wendelboe",
    display_name="Tim Wendelboe",
    roaster_name="Tim Wendelboe",
    website="https://timwendelboe.no",
    description="Norwegian specialty coffee roaster and world barista champion",
    requires_api_key=True,
    currency="NOK",
    country="Norway",
    status="available",
)
class TimWendelboeScraper(BaseScraper):
    """Scraper for Tim Wendelboe (timwendelboe.no) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Tim Wendelboe scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Tim Wendelboe",
            base_url="https://timwendelboe.no",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing both filter and espresso coffee collection URLs
        """
        return [
            "https://timwendelboe.no/product-category/coffee/filter-coffee/",
            "https://timwendelboe.no/product-category/coffee/espresso/",
        ]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Tim Wendelboe with efficient stock updates."""
        self.start_session()
        from pathlib import Path

        output_dir = Path("data")

        all_product_urls = []
        for store_url in self.get_store_urls():
            product_urls = await self._extract_product_urls_from_store(store_url)
            all_product_urls.extend(product_urls)

        if force_full_update:
            logger.info(
                f"Force full update enabled - performing full scraping for all {len(all_product_urls)} products"
            )
            return await self._scrape_new_products(all_product_urls)

        in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
            all_product_urls, output_dir, force_full_update
        )

        new_urls = []
        for url in all_product_urls:
            if not self._is_bean_already_scraped_anywhere(url):
                new_urls.append(url)

        logger.info(f"Found {in_stock_count} existing products for stock updates")
        logger.info(f"Found {out_of_stock_count} products now out of stock")
        logger.info(f"Found {len(new_urls)} new products for full scraping")

        if new_urls:
            return await self._scrape_new_products(new_urls)

        return []

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""
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
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=[
                # WooCommerce product link selectors
                'a[href*="/product/"]',
                '.woocommerce-LoopProduct-link',
                '.product-item a',
                '.product-link',
                '.wc-block-grid__product a',
                # Tim Wendelboe specific selectors based on HTML structure
                '.product a',
                '.product-wrapper a',
            ],
        )

        # Filter out excluded products
        excluded_products = [
            "test-roast-1kg",
            "coffee-berry-fizz",
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
