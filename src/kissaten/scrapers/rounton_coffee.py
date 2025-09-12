"""Rounton Coffee scraper implementation.

Rounton Coffee Roasters is a specialty coffee roastery based in North Yorkshire, UK.
They focus on sustainable sourcing and are proud members of 1% for the planet.
"""

import logging

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rounton-coffee",
    display_name="Rounton Coffee",
    roaster_name="Rounton Coffee Roasters",
    website="https://rountoncoffee.co.uk",
    description="Specialty coffee roastery from North Yorkshire, focusing on sustainable sourcing",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RountonCoffeeScraper(BaseScraper):
    """Scraper for Rounton Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Rounton Coffee Roasters",
            base_url="https://rountoncoffee.co.uk",
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

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://rountoncoffee.co.uk/collections/coffee",
        ]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Rounton Coffee with efficient stock updates.

        This method will check for existing beans and create diffjson stock updates
        for products that already have bean files, or do full scraping for new products.

        Args:
            force_full_update: If True, perform full scraping for all products instead of diffjson updates

        Returns:
            List of CoffeeBean objects (only new products, or all products if force_full_update=True)
        """
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

        product_urls = []

        # Custom extraction for Rounton Coffee to handle URL spaces properly
        selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link",
            ".grid-product__link",
            "a.product-title",
        ]

        for selector in selectors:
            try:
                links = soup.select(selector)
                if links:
                    for link in links:
                        href = link.get("href")
                        if href and isinstance(href, str):
                            # Clean the href to remove any leading/trailing spaces
                            href = href.strip()

                            # Ensure it's a product URL
                            if "/products/" in href:
                                # Resolve to full URL, making sure to clean it
                                if href.startswith("/"):
                                    full_url = f"{self.base_url}{href}"
                                else:
                                    full_url = href

                                # Final cleanup to remove any spaces
                                full_url = full_url.replace(" ", "")

                                # Filter out non-coffee products
                                if self.is_coffee_product_url(full_url, ["/products/"]):
                                    product_urls.append(full_url)
                    break  # Use first successful selector
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Extracted {len(unique_urls)} product URLs from {store_url}")
        if unique_urls:
            logger.debug(f"Sample URLs: {unique_urls[:3]}")

        excluded_patterns = ["sample-pack", "gift-box"]
        unique_urls = [url for url in unique_urls if not any(pattern in url.lower() for pattern in excluded_patterns)]

        return unique_urls
