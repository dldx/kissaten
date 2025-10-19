"""Bugan Coffee Lab scraper implementation with AI-powered extraction."""

import logging

from pydantic import HttpUrl

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bugan",
    display_name="Bugan Coffee Lab",
    roaster_name="Bugan Coffee Lab",
    website="https://bugancoffeelab.com",
    description="Italian specialty coffee roaster and lab with locations in Milan and Bergamo",
    requires_api_key=True,
    currency="EUR",
    country="Italy",
    status="available",
)
class BuganCoffeeScraper(BaseScraper):
    """Scraper for Bugan Coffee Lab (bugancoffeelab.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bugan Coffee Lab scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bugan Coffee Lab",
            base_url="https://bugancoffeelab.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs for different pages
        """
        return [
            "https://bugancoffeelab.com/en/collections/specialty-coffee",
            "https://bugancoffeelab.com/en/collections/specialty-coffee?page=2",
            "https://bugancoffeelab.com/en/collections/specialty-coffee?page=3",
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
            translate_to_english=True,
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

        # Custom selectors for Bugan Coffee Lab
        custom_selectors = [
            'a[href*="/products/"]',
            'a[href*="/collections/specialty-coffee/products/"]',
            '.product-item a',
            '.grid__item a',
            'h2 a',  # Product title links
            'a.product-link',
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/", "/collections/specialty-coffee/products/"],
            selectors=custom_selectors,
        )

        # Filter out excluded products (cold brew, thank the fellas, samples)
        excluded_products = [
            "cold-brew",  # Cold brew products
            "cold brew",  # Alternative spelling
            "box-degustazione",  # Tasting samples
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # Correct domain name in product URL if needed
        bean.url = HttpUrl(str(bean.url).replace("https://en.bugan", "https://bugan"))
        return bean
