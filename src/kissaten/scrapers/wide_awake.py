"""Wide Awake Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@register_scraper(
    name="wide-awake-coffee",
    display_name="Wide Awake Coffee",
    roaster_name="Wide Awake Coffee",
    website="https://wideawake.coffee",
    description="Speciality coffee roaster based in Brussels, Belgium.",
    requires_api_key=True,
    currency="EUR",
    country="Belgium",
    status="available",
)
class WideAwakeCoffeeScraper(BaseScraper):
    """Scraper for Wide Awake Coffee (wideawake.coffee) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Wide Awake Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Wide Awake Coffee",
            base_url="https://wideawake.coffee",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://wideawake.coffee/collections/frontpage?filter.v.availability=1&sort_by=manual"]


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

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
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
            # Keep the first four div.shopify-section and remove the rest
            shopify_sections = soup.find_all("div", class_="shopify-section")
            logger.info(f"Found {len(shopify_sections)} sections matching div.shopify-section")
            for section in shopify_sections[4:]:
                section.decompose()
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
                # Shopify product link selectors
                'a[href*="/products/"]',
            ],
        )

        # Filter out excluded products
        excluded_products = [
            "discovery-box",
            "subscription",
            "6kg",
            "steep-bags",
            "cascara",
            "matcha",
            "hojicha",
            "verbena"
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(self.resolve_url(url ))

        return filtered_urls
