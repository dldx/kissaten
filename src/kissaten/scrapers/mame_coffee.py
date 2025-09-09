"""Mame Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mame-coffee",
    display_name="Mame Coffee",
    roaster_name="MAME Roastery",
    website="https://mame.coffee",
    description="Swiss specialty coffee roaster offering daily coffee and competition-grade beans",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class MameCoffeeScraper(BaseScraper):
    """Scraper for Mame Coffee (mame.coffee) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Mame Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="MAME Roastery",
            base_url="https://mame.coffee",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing both daily coffee and competition coffee collection URLs
        """
        return [
            "https://mame.coffee/product-category/coffee/",  # Daily coffee
            "https://mame.coffee/product-category/competition-coffees/",  # Competition coffees
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Mame Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
        )

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
            url_path_patterns=["/product/"],
            selectors=[
                # Common WooCommerce product link selectors
                'a[href*="/product/"]',
                '.woocommerce-LoopProduct-link',
                '.product-item a',
                '.product-link',
                '.product a',
                '.wc-block-grid__product a',
                # Mame specific selectors based on HTML structure
                'h2 a',  # Product title links
                '.entry-title a',
                'h3 a',
            ],
        )

        # Filter out excluded products (subscriptions, equipment, and sampler sets)
        excluded_products = [
            "subscription",  # Monthly coffee subscriptions
            "equipment",  # Coffee equipment/accessories
            "sampler",  # Sampler packs/sets
            "box-set",  # Box sets and multi-coffee packages
            "gift",  # Gift cards
            "monthly-mame"
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
