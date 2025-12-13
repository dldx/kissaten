"""Café Aconcagua scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cafe-aconcagua",
    display_name="Café Aconcagua",
    roaster_name="Café Aconcagua",
    website="https://cafeaconcagua.cl",
    description="Coffee roastery based in Chile",
    requires_api_key=True,
    currency="CLP", # Chilean Peso
    country="Chile",
    status="available",
)
class CafeAconcaguaScraper(BaseScraper):
    """Scraper for Café Aconcagua (cafeaconcagua.cl) with AI-powered extraction."""
    def __init__(self, api_key: str | None = None):
        """Initialize Café Aconcagua scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Café Aconcagua",
            base_url="https://cafeaconcagua.cl",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://cafeaconcagua.cl/collections/coleccion-tradicional?filter.v.availability=1", "https://cafeaconcagua.cl/collections/cafe-tostado-fresco?filter.v.availability=1", "https://cafeaconcagua.cl/collections/coleccion-prime?filter.v.availability=1"]

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Postprocess extracted CoffeeBean object."""
        return bean

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
            use_playwright=False,
            use_optimized_mode=False,
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
            product_carousels = soup.select("product-recommendations")
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
        product_urls = [self.resolve_url(str(a['href']).split("?")[0]) for a in soup.select("a.full-unstyled-link") if a.has_attr('href')]
        # Filter out excluded products (merchandise and non-coffee items)
        excluded_products = ["pack-"
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return list(set(filtered_urls))  # Remove duplicates
