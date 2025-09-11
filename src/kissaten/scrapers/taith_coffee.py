"""Scraper for Taith Coffee.

Taith Coffee is a specialty coffee roaster based in Lewes, UK.
Website: https://taithcoffee.com
"""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="taith-coffee",
    display_name="Taith Coffee",
    roaster_name="Taith Coffee",
    website="https://taithcoffee.com",
    description="Specialty coffee roaster from Lewes, UK",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class TaithCoffeeScraper(BaseScraper):
    """Scraper for Taith Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Taith Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Taith Coffee",
            base_url="https://taithcoffee.com",
            rate_limit_delay=1.0,
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
        return ["https://taithcoffee.com/shop/coffee"]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans with efficient stock updates.

        Args:
            force_full_update: If True, perform full scraping for all products

        Returns:
            List of CoffeeBean objects
        """
        if force_full_update:
            # Use the high-level base class method for full scraping
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,
                use_optimized_mode=False,  # Use standard mode for cost efficiency
                translate_to_english=False,
                max_concurrent=2,
                output_dir=Path("data"),
            )

        # For efficient updates, use our custom implementation
        self.start_session()

        # Get all current product URLs
        all_product_urls = []
        for store_url in self.get_store_urls():
            product_urls = await self._extract_product_urls_from_store(store_url)
            all_product_urls.extend(product_urls)

        # Use built-in diffjson functionality for efficient updates
        base_output_dir = Path("data")

        in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
            all_product_urls, base_output_dir, force_full_update
        )

        # Find and scrape only new products (not scraped in any previous session)
        new_urls = [url for url in all_product_urls if not self._is_bean_already_scraped_anywhere(url)]

        logger.info(f"Stock updates: {in_stock_count} in stock, {out_of_stock_count} out of stock")
        logger.info(f"New products to scrape: {len(new_urls)}")

        beans = []
        if new_urls:
            beans = await self._scrape_new_products_with_ai(new_urls)

        # Update session stats
        if self.session:
            self.session.beans_found = len(beans)
            self.session.beans_processed = len(beans)

        self.end_session(success=True)
        return beans

    async def _scrape_new_products_with_ai(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape only new products using the base class AI extraction method.

        Args:
            product_urls: List of new product URLs to scrape

        Returns:
            List of CoffeeBean objects
        """
        # Use the base class method for AI extraction
        return await self.process_product_batch(
            product_urls=product_urls,
            extract_function=self._extract_single_product,
            batch_size=2,
            save_to_file=True,
            output_dir=Path("data"),
        )

    async def _extract_single_product(self, product_url: str) -> CoffeeBean | None:
        """Extract a single product using AI.

        Args:
            product_url: URL of the product page

        Returns:
            CoffeeBean object or None if extraction failed
        """
        try:
            # Fetch the page
            soup = await self.fetch_page(product_url)
            if not soup:
                logger.warning(f"Failed to fetch page: {product_url}")
                return None

            # Extract bean data using AI
            bean = await self._extract_bean_with_ai(
                ai_extractor=self.ai_extractor,
                soup=soup,
                product_url=product_url,
                use_optimized_mode=False,  # Use standard mode for cost efficiency
                translate_to_english=False,
            )

            if bean:
                # Ensure correct roaster details
                bean.roaster = "Taith Coffee"
                bean.currency = "GBP"

                # Mark as scraped to avoid reprocessing
                self._mark_bean_as_scraped(product_url)

                # Return the bean - base class will handle saving and image download
                return bean

        except Exception as e:
            logger.error(f"Error extracting product {product_url}: {e}")

        return None

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

        # Custom selectors for Taith Coffee's Squarespace structure
        custom_selectors = [
            'a[href*="/shop/p/"]',  # Direct product links
            ".product-link",  # Generic product links
            ".product-item a",  # Product item links
        ]

        # Use the base class method for extracting product URLs
        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/shop/p/"],
            selectors=custom_selectors,
        )
