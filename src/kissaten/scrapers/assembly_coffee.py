"""Assembly Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="assembly-coffee",
    display_name="Assembly Coffee",
    roaster_name="Assembly Coffee London",
    website="https://assemblycoffee.co.uk",
    description="Award-winning specialty coffee roastery founded in 2015 and based in Brixton, London",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AssemblyCoffeeScraper(BaseScraper):
    """Scraper for Assembly Coffee (assemblycoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Assembly Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Assembly Coffee London",
            base_url="https://assemblycoffee.co.uk",
            rate_limit_delay=1.5,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the espresso and pour over coffee URLs
        """
        return [
            "https://assemblycoffee.co.uk/collections/buy-coffee?constraint=brew_espresso",
            "https://assemblycoffee.co.uk/collections/buy-coffee?constraint=brew_Pour_Over",
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

        # Track which store URL we've processed to avoid duplicates
        processed_store_urls = set()

        async def get_filtered_product_urls(store_url: str) -> list[str]:
            # Only return URLs for the first store URL to avoid processing duplicates
            if store_url not in processed_store_urls:
                processed_store_urls.add(store_url)
                return product_urls
            return []

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_filtered_product_urls,
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

        # Limit extraction to the collection grid container as requested
        collection_grid = soup.find("div", class_="collectionGrid-container")
        if collection_grid:
            # Create a new soup object with just the collection grid content
            limited_soup = BeautifulSoup(str(collection_grid), "html.parser")
            logger.debug(f"Limiting product extraction to div.collectionGrid-container for {store_url}")
        else:
            # Fallback to full page if container not found
            limited_soup = soup
            logger.warning(f"div.collectionGrid-container not found, using full page for {store_url}")

        # Custom selectors for Assembly Coffee
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link",
            ".grid-product__link",
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            limited_soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        # Filter coffee products using base class method and specific exclusions
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]):
                # Additional filtering for specific excluded products
                excluded_products = [
                    "discovery",  # Sample pack
                    "assembly-sample-pack",
                    "assembly-house-selection",  # Assembly house selection products
                    "assembly-cofffee-pods-selected-espresso",
                ]
                if not any(excluded in url.lower() for excluded in excluded_products):
                    coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
