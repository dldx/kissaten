"""Module Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@register_scraper(
    name="module-coffee",
    display_name="Module Coffee",
    roaster_name="Module Coffee",
    website="https://module-roast.com",
    description="Speciality coffee roaster based in Edinburgh, Scotland.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class   ModuleCoffeeScraper(BaseScraper):
    """Scraper for Module Coffee (module-roast.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Module Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Module Coffee",
            base_url="https://module-roast.com",
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
        return ["https://module-roast.com/shop/?filter.v.availability=1"]


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
            translate_to_english=False
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
            if "/shop/m" not in (url or ""):
                return soup  # Only modify product pages
            # Find product info section
            product_el = soup.select("div.content-wrapper > div > div.container-fluid")
            if len(product_el) == 2:
                return product_el[0].parent  # The parent contains the full product info including title, price, etc.
            logger.warning(f"No product section found for URL {url}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # bean.currency = "GBP"
        return bean

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

        # Get listing section
        listing_section = soup.select("div.current-releases")
        if len(listing_section) == 0:
            logger.warning(f"No listing section found for store URL {store_url}")
            return []
        # Get all product URLs using the base class method
        product_urls_el = listing_section[0].select('a[href*="/shop/m"]')
        product_urls = [el.get("href").split("?")[0] for el in product_urls_el]

        # Filter out excluded products
        excluded_products = ["gift-card", "tote-bag", "subscription"]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(self.resolve_url(url ))

        return list(set(filtered_urls))
