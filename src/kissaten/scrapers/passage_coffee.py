"""Celsius Roasters scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="passage-coffee",
    display_name="Passage Coffee",
    roaster_name="Passage Coffee",
    website="https://passagecoffee.com",
    description="Specialty coffee roaster based in Mitaka, Tokyo, Japan",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class PassageCoffeeScraper(BaseScraper):
    """Scraper for Passage Coffee (passagecoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Passage Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Passage Coffee",
            base_url="https://passagecoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing both filter and espresso coffee collection URLs
        """
        return [
            "https://passagecoffee.com/en/collections/beans?filter.v.availability=1",
        ]

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
            translate_to_english=True,
        )

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
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            if "/products" not in (url or ""):
                return soup  # Only modify product pages
            # Remove product carousel element
            product_carousels = soup.select("div[id*='product-recommendations']")
            if len(product_carousels) > 0:
                product_carousels[0].decompose()

            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
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

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                'a.grid-product__link[href*="/products/"]',
            ],
        )

        # Filter out excluded products
        excluded_products = []

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url for excluded in excluded_products):
                filtered_urls.append(self.resolve_url(url.split("?")[0]))

        return filtered_urls
