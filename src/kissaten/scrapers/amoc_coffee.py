"""AMOC (A Matter of Concrete) Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="amoc",
    display_name="AMOC Coffee",
    roaster_name="A Matter of Concrete",
    website="https://amatterofconcrete.com",
    description="Netherlands-based specialty coffee roaster from Rotterdam",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class AmocCoffeeScraper(BaseScraper):
    """Scraper for AMOC (A Matter of Concrete) Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize AMOC Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="A Matter of Concrete",
            base_url="https://amatterofconcrete.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee category URL
        """
        return ["https://amatterofconcrete.com/product-category/coffee/all/"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from AMOC Coffee store using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_with_playwright,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # AMOC uses optimized mode with screenshots
            batch_size=2,
        )

    async def _extract_product_urls_with_playwright(self, store_url: str) -> list[str]:
        """Extract product URLs using base class Playwright fetch method.

        Args:
            store_url: URL of the coffee category page

        Returns:
            List of product URLs for coffee products
        """
        product_urls = []

        try:
            # Use base class fetch_page with Playwright for JavaScript-rendered content
            soup = await self.fetch_page(store_url, use_playwright=True)

            if not soup:
                logger.error(f"Failed to fetch store page: {store_url}")
                return []

            # Look for product links in the rendered HTML using CSS selectors
            # Based on the actual AMOC website structure analysis
            selectors = [
                ".woocommerce-LoopProduct-link",  # Main product title links
                '.product-small a[href*="/product/"]',  # Product container links
                'a[aria-label][href*="/product/"]',  # Image links with aria-label
                '.box-image a[href*="/product/"]',  # Image container links
                'a[href*="/product/"]',  # Fallback for any product links
            ]

            # Extract links using BeautifulSoup selectors
            for selector in selectors:
                try:
                    links = soup.select(selector)
                    for link in links:
                        if isinstance(link, Tag):
                            href = link.get("href", "")
                            if href and isinstance(href, str):
                                full_url = self.resolve_url(href)
                                if self.is_coffee_product_url(full_url, ["/product/"]):
                                    product_urls.append(full_url)
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")

            # Also look for all product links in the HTML
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                if isinstance(link, Tag):
                    href = link.get("href", "")
                    if href and isinstance(href, str) and "/product/" in href:
                        full_url = self.resolve_url(href)
                        if self.is_coffee_product_url(full_url, ["/product/"]):
                            product_urls.append(full_url)

        except Exception as e:
            logger.error(f"Error extracting URLs with Playwright: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls
