"""Template for creating new coffee roaster scrapers.

Copy this file and modify it for new roasters. This template demonstrates:

1. NEW APPROACH (RECOMMENDED): Use scrape_with_ai_extraction() for AI-powered scraping
   - Minimal code required (just URL extraction)
   - Built-in session management, batch processing, error handling
   - Concurrent processing and rate limiting
   - Automatic bean saving and deduplication
   - Efficient diffjson stock updates for existing products
   - Session continuation support (resume interrupted scraping)

2. LEGACY APPROACH: Traditional manual parsing (for educational purposes)
   - Full manual control over scraping workflow
   - Custom extraction logic for each field
   - More code but complete flexibility

For new scrapers, strongly prefer the AI-powered approach unless you have
specific requirements that need manual control.

QUICK START GUIDE:
1. Copy this file and rename it to your_roaster_name.py
2. Update the @register_scraper decorator with your roaster's details
3. Update the __init__ method with your roaster's base URL and settings
4. Update get_store_urls() to return your roaster's coffee collection URLs
5. Modify _extract_product_urls_from_store() with your roaster's URL patterns
6. Test with: python -m kissaten.cli scrape your-roaster-name --api-key YOUR_KEY
7. Most scrapers will work with just these changes - no AI training required!

DIFFJSON STOCK UPDATES:
- The scraper automatically creates diffjson files for existing products
- Only new products get full AI extraction (much faster subsequent runs)
- Out-of-stock products are automatically detected and marked
- Session continuation: if scraping is interrupted, restart and it will continue
- Use --force-full-update to bypass diffjson and re-scrape everything
"""

import logging
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="example",  # CLI name - should be lowercase, no spaces
    display_name="Example Coffee Roaster",  # Human-readable name
    roaster_name="Example Coffee Co",  # Official company name
    website="https://example-coffee.com",  # Website domain
    description="Example template for new scrapers",
    requires_api_key=True,  # Set to True if using AI extraction (RECOMMENDED)
    currency="USD",  # Default currency for this roaster
    country="United States",  # Country where roaster is based
    status="experimental",  # available, experimental, or deprecated
)
class ExampleCoffeeScraper(BaseScraper):
    """Example scraper template - replace with actual roaster implementation."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Example Coffee Co",
            base_url="https://example-coffee.com",
            rate_limit_delay=1.0,  # Seconds between requests
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (RECOMMENDED for new scrapers)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            "https://example-coffee.com/collections/coffee",
            # Add more URLs if the roaster has multiple collection pages
        ]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Example Coffee with efficient stock updates.

        This method will check for existing beans and create diffjson stock updates
        for products that already have bean files, or do full scraping for new products.

        Args:
            force_full_update: If True, perform full scraping for all products instead of diffjson updates

        Returns:
            List of CoffeeBean objects (only new products, or all products if force_full_update=True)
        """
        # Start session and get all current product URLs from the website
        self.start_session()
        output_dir = Path("data")

        all_product_urls = []
        for store_url in self.get_store_urls():
            product_urls = await self._extract_product_urls_from_store(store_url)
            all_product_urls.extend(product_urls)

        if force_full_update:
            # Force full scraping for all products
            logger.info(
                f"Force full update enabled - performing full scraping for all {len(all_product_urls)} products"
            )
            return await self._scrape_new_products(all_product_urls)

        # Create diffjson stock updates for existing products
        in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
            all_product_urls, output_dir, force_full_update
        )

        # Find new products that need full scraping
        new_urls = []
        for url in all_product_urls:
            if not self._is_bean_already_scraped_anywhere(url):
                new_urls.append(url)

        logger.info(f"Found {in_stock_count} existing products for stock updates")
        logger.info(f"Found {out_of_stock_count} products now out of stock")
        logger.info(f"Found {len(new_urls)} new products for full scraping")

        # Perform full AI extraction only for new products
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

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Set to True for JavaScript-heavy sites
            use_optimized_mode=False,  # Set to True to go straight to screenshots mode
            translate_to_english=False,  # Set to True if site is not in English
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page using the new base class method.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Use the new base class method with roaster-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # Adjust URL path patterns for your roaster's structure:
            # Common patterns: ["/products/"], ["/product/"], ["/shop/p/"], ["/coffee/"]
            url_path_patterns=["/products/"],
            selectors=[
                # Add roaster-specific CSS selectors if the default ones don't work
                # Leave empty to use default selectors from base class
                "a.product-link",
                ".product-item a",
                'a[href*="/products/"]',
            ],
        )

    async def _extract_product_urls(self, soup: BeautifulSoup) -> list[str]:
        """Extract product URLs from the store index page (legacy method for traditional scraping).

        NOTE: For new scrapers, use _extract_product_urls_from_store() with the new
        base class extract_product_urls_from_soup() method instead.

        Args:
            soup: BeautifulSoup object of the store page

        Returns:
            List of product URLs
        """
        product_urls = []

        # TODO: Replace with actual selectors for this roaster
        # Example patterns to look for:

        # Method 1: Look for product links by class
        product_links = soup.find_all("a", class_="product-link")

        # Method 2: Look for links in product containers
        if not product_links:
            containers = soup.find_all("div", class_="product-item")
            for container in containers:
                if isinstance(container, Tag):
                    link = container.find("a")
                    if isinstance(link, Tag):
                        product_links.append(link)

        # Method 3: Look for any links with /products/ in href
        if not product_links:
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                if isinstance(link, Tag):
                    href = link.get("href")
                    if href and isinstance(href, str) and "/products/" in href:
                        product_links.append(link)

        for link in product_links:
            if isinstance(link, Tag):
                href = link.get("href")
                if href and isinstance(href, str):
                    product_url = self.resolve_url(href)

                    # Filter out non-coffee products using base class method
                    if self.is_coffee_product_url(product_url, required_path_patterns=["/products/"]):
                        product_urls.append(product_url)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    def _is_coffee_product(self, name: str) -> bool:
        """Check if this product is actually coffee beans (not equipment/gifts)."""
        # Use base class method
        return self.is_coffee_product_name(name)
