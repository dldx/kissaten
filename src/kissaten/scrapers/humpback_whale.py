"""Humpback Whale Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@register_scraper(
    name="humpback-whale",
    display_name="Humpback Whale Coffee",
    roaster_name="Humpback Whale Coffee",
    website="https://humpbackwhalecoffee.com",
    description="Speciality coffee roaster based in Munich, Germany.",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="available",
)
class   HumpbackWhaleCoffeeScraper(BaseScraper):
    """Scraper for Humpback Whale Coffee (humpbackwhalecoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Humpback Whale Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Humpback Whale Coffee",
            base_url="https://humpbackwhalecoffee.com",
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
        return ["https://humpbackwhalecoffee.com/product"]


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
            if "/products/" not in (url or ""):
                return soup  # Only modify product pages
            # Remove unneeded sections
            unneeded_sections = [
                "section[aria-labelledby='related-heading']",
            ]
            for section in unneeded_sections:
                product_section = soup.select(section)
                logger.info(f"Found {len(product_section)} sections matching {section}")
                if len(product_section) > 0:
                    product_section[0].decompose()
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None
    
    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        bean.currency = "EUR"
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

        # Get all product URLs using the base class method
        product_urls_el = soup.select("section[aria-labelledby='product-heading']")[0].select('a[href*="product"]')
        product_urls = [el.get("href") for el in product_urls_el]

        # Filter out excluded products
        excluded_products = []

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(self.resolve_url(url ))

        return filtered_urls
