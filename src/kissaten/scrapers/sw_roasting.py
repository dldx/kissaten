"""S&W Roasting scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sw-roasting",
    display_name="S&W Roasting",
    roaster_name="S&W Roasting",
    website="https://www.swroasting.coffee",
    description="Specialty coffee roaster offering single origins, blends, and roaster selections",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class SWRoastingScraper(BaseScraper):
    """Scraper for S&W Roasting (swroasting.coffee) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize S&W Roasting scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="S&W Roasting",
            base_url="https://www.swroasting.coffee",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        raise Exception("Not implemented yet. Needs cookie handling.")  # TODO: Implement cookie handling
        return [
            "https://www.swroasting.coffee/shop/single-origin-coffees-lighter-roasts/2?page=1&limit=30&sort_by=category_order&sort_order=asc",
            "https://www.swroasting.coffee/shop/roasters-select/5?page=1&limit=30&sort_by=category_order&sort_order=asc",
            "https://www.swroasting.coffee/shop/blends-and-medium-roasts/3?page=1&limit=30&sort_by=category_order&sort_order=asc",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from S&W Roasting using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # May need JS for dynamic content
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []


        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/", "/shop/product/"],
            selectors=[
                # Generic product link selectors
                'a[href*="/product/"]',
                'a[href*="/shop/product/"]',
                '.product-item a',
                '.product-link',
                '.product-card a',
                '.product a',
                # S&W specific selectors based on URL structure
                '.product-wrapper a',
                '.item a',
                'h3 a',  # Product title links
                'h4 a',  # Alternative title links
            ],
        )

        # Filter out excluded products (cold brew, thank the fellas, samples)
        excluded_products = [
            "cold-brew",  # Cold brew products
            "cold brew",  # Alternative spelling
            "thank-the-fellas",  # Thank the fellas products
            "thank the fellas",  # Alternative spelling
            "sample",  # Sample products
            "samples",  # Plural samples
            "tasting",  # Tasting samples
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
