"""atmans Coffee scraper for extracting coffee bean information.

atmans Coffee is a specialty coffee roaster based in Barcelona, Spain.
They offer curated selection of specialty coffees from around the world,
focusing on Process, Origin and Variety (POV).
"""

import logging

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from ..schemas import CoffeeBean
from ..schemas.coffee_bean import Bean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="atmans-coffee",
    display_name="atmans Coffee",
    roaster_name="atmans Coffee",
    website="https://www.atmanscoffee.com",
    description="Specialty coffee roaster based in Barcelona, Spain with curated selection focusing on POV",
    requires_api_key=True,
    currency="EUR",
    country="Spain",
    status="available",
)
class AtmansCoffeeScraper(BaseScraper):
    """Scraper for atmans Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="atmans Coffee",
            base_url="https://www.atmanscoffee.com",
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
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
            "https://www.atmanscoffee.com/en/collections/all-coffees",
            # Check if there are more pages by looking at pagination
            "https://www.atmanscoffee.com/en/collections/all-coffees?page=2",
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

        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=get_new_product_urls,
                ai_extractor=self.ai_extractor,
                use_playwright=False,
                translate_to_english=True,
            )
        logger.warning("AI extractor not available - traditional scraping not implemented for atmans Coffee")
        return []

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page, focusing on filter-container.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # First, try to find the filter-container element
        filter_container = soup.find("filter-container")
        if filter_container:
            logger.debug("Found filter-container, extracting products from it")
            # Create a new BeautifulSoup object from the filter-container
            from bs4 import BeautifulSoup
            filter_soup = BeautifulSoup(str(filter_container), "lxml")
            # Extract URLs specifically from the filter-container
            product_urls = self.extract_product_urls_from_soup(
                filter_soup,
                url_path_patterns=["/products/"],
                selectors=[
                    'a[href*="/products/"]',
                    ".product-item a",
                    ".product-link",
                    ".grid-product__link",
                    ".product-card a",
                    ".product-title a",
                ],
            )
        else:
            logger.warning("filter-container not found, using full page")
            # Fallback to full page if filter-container not found
            product_urls = self.extract_product_urls_from_soup(
                soup,
                url_path_patterns=["/products/"],
                selectors=[
                    'a[href*="/products/"]',
                    ".product-item a",
                    ".product-link",
                    ".grid-product__link",
                    ".product-card a",
                    ".product-title a",
                ],
            )

        # Filter out excluded products
        excluded_products = [
            "pack-de-muestras",  # Sample pack
            "beanz",  # Alternative spelling
            "coffee-bag",  # Coffee bag (non-bean)
            "suscripcion-",
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
