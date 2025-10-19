"""Sango Speciality Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sango",
    display_name="Sango Speciality Coffee",
    roaster_name="Sango Speciality Coffee",
    website="https://sangoamsterdam.com",
    description="Micro-roastery based in Amsterdam, focused on ethical sourcing.",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class SangoSpecialityCoffeeScraper(BaseScraper):
    """Scraper for Sango Speciality Coffee (sangoamsterdam.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Sango Speciality Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sango Speciality Coffee",
            base_url="https://sangoamsterdam.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs for different coffee collections
        """
        return [
            "https://sangoamsterdam.com/collections/all?filter.p.product_type=Coffee+Beans&filter.p.product_type=Competition&filter.p.product_type=Espresso&filter.p.product_type=Filter&filter.p.product_type=Filter+-+PEARLS",
            "https://sangoamsterdam.com/collections/all?filter.p.product_type=Coffee+Beans&filter.p.product_type=Competition&filter.p.product_type=Espresso&filter.p.product_type=Filter&filter.p.product_type=Filter+-+PEARLS&page=2",
        ]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | None:
        """Fetch a page and return its BeautifulSoup object.

        Args:
            url: URL of the page to fetch
            use_playwright: Whether to use Playwright for fetching

        Returns:
            BeautifulSoup object of the page, or None if fetch failed
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            if "/products" not in kwargs.get("url", ""):
                return soup  # Only modify product pages
            # Remove product carousel element
            product_carousels =  soup.select("section[id*='featured_collection']")
            if len(product_carousels) > 0:
                product_carousels[0].decompose()
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Start with basic scraping, can enable if needed
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

        all_product_url_el = soup.select('.product-grid a[href*="/products/"][aria-labelledby*="CardLink-template"]')
        all_product_urls = []
        for el in all_product_url_el:
            if not "Sold out" in el.parent.parent.parent.text:
                all_product_urls.append(f"{self.base_url}{el['href'].split('?')[0]}")

        # Filter out equipment and non-coffee products
        filtered_urls = []
        for url in all_product_urls:
            if self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products by URL patterns.

        Args:
            url: Product URL to check

        Returns:
            True if URL appears to be for coffee beans
        """
        # Exclude equipment and accessories
        excluded_patterns = [
            "meter",
            "digital",
            "water",
            "brewer",
            "grinder",
            "equipment",
            "accessories",
            "subscription",
            "gift",
            "merch",
            "capsule",
            "capsules",
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
