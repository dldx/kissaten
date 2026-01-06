"""Rose Coffee Roasters scraper
"""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rose-coffee",
    display_name="Rose Coffee Roasters",
    roaster_name="Rose Coffee Roasters",
    website="https://rose-coffee.com",
    description="Zurich-based specialty coffee roaster",
    requires_api_key=True,  # Using AI extraction for best results
    currency="CHF",
    country="Switzerland",
    status="available",
)
class RoseCoffeeScraper(BaseScraper):
    """Scraper for Rose Coffee Roasters."""
    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Rose Coffee Roasters",
            base_url="https://rose-coffee.com",
            rate_limit_delay=1.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for complex Shopify sites)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            "https://rose-coffee.com/collections/all-coffees",
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
            translate_to_english=False,
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
            # Find main product and return that
            main_product = soup.select("div.product")
            if len(main_product) > 0:
                return main_product[0]
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
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Extract all product URLs and filter out sold out items
        all_product_urls = []
        all_product_url_el = soup.select('a[href*="/products/"]')
        for el in all_product_url_el:
            # Check if "Sold out" appears in the parent elements
            if "Sold out" not in el.parent.parent.text:
                href = el.get('href')
                if href:
                    all_product_urls.append(self.resolve_url(href))

        # Filter out excluded products (non-single bag items, subscriptions, etc.)
        excluded_products = [
            "subscription",
            "sample-box",
            "giftcard",
            "tasting-pack"
        ]

        filtered_urls = []
        for url in all_product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} available coffee product URLs from {store_url}")
        return list(set(filtered_urls))