"""Lilo Coffee Roasters scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from kissaten.schemas.coffee_bean import PriceOption

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="lilo-coffee-roasters",
    display_name="Lilo Coffee Roasters",
    roaster_name="Lilo Coffee Roasters",
    website="https://coffee.liloinveve.com",
    description="Coffee roaster based in Osaka, Japan",
    requires_api_key=True,
    currency="JPY", # Japanese Yen
    country="Japan",
    status="available",
)
class LiloCoffeeRoastersScraper(BaseScraper):
    """Scraper for Lilo Coffee Roasters (coffee.liloinveve.com) with AI-powered extraction."""
    def __init__(self, api_key: str | None = None):
        """Initialize Lilo Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Lilo Coffee Roasters",
            base_url="https://coffee.liloinveve.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://coffee.liloinveve.com/collections/coffee", "https://coffee.liloinveve.com/collections/coffee?page=2"]

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
            product_carousels = soup.select(".js-product-rec-wrapper")
            if len(product_carousels) > 0:
                product_carousels[0].decompose()

            # Remove gift wrapping section
            gift_wrapping_sections = soup.select("section[data-url*='/products/gift-wrapping']")
            if len(gift_wrapping_sections) > 0:
                gift_wrapping_sections[0].decompose()
            main_section = soup.select("div.product__section")
            # Return only the main product section to save tokens
            if len(main_section) == 0:
                return soup
            else:
                return main_section[0]
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
            translate_to_english=True,
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
        product_urls = []
        for el in soup.select("a.js-product--details-link[href*='/products/']"):
            if "SOLD OUT" in el.parent.parent.text:
                continue  # Skip sold out products
            href = el.get("href")
            if href:
                full_url = self.resolve_url(href.split("?")[0])
                product_urls.append(full_url)

        # Filter out excluded products (merchandise and non-coffee items)
        excluded_products = [
            "はじめての水出しコーヒーセット",
            "-set-",
            "-gift-",
            "定期購入-シングルオリジンコース",
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return list(set(filtered_urls))  # Remove duplicates
