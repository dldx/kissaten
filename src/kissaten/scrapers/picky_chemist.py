"""The Picky Chemist scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@register_scraper(
    name="picky-chemist",
    display_name="The Picky Chemist",
    roaster_name="The Picky Chemist",
    website="https://en.thepickychemist.com",
    description="Speciality coffee roaster based in Belgium.",
    requires_api_key=True,
    currency="EUR",
    country="Belgium",
    status="available",
)
class   PickyChemistScraper(BaseScraper):
    """Scraper for The Picky Chemist (en.thepickychemist.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Picky Chemist scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Picky Chemist",
            base_url="https://en.thepickychemist.com",
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
        return ["https://en.thepickychemist.com/boutique"]


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

    
    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        bean.currency = "EUR"
        bean.roast_level = "light"
        bean.roast_profile = "Omni"
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
        product_urls_el = soup.select('a[data-hook="product-item-container"]')
        product_urls = [el.get("href") for el in product_urls_el if "Out of Stock" not in el.text]

        # Filter out excluded products
        excluded_products = ["2-60g"]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(self.resolve_url(url ))

        return filtered_urls
