"""Coborn Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coborn",
    display_name="Coborn Coffee",
    roaster_name="Coborn Coffee",
    website="https://coborncoffee.com",
    description="UK-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CobornCoffeeScraper(BaseScraper):
    """Scraper for Coborn Coffee (coborncoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coborn Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coborn Coffee",
            base_url="https://www.coborncoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the shop URL
        """
        return ["https://www.coborncoffee.com/shop"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Coborn Coffee shop using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_with_playwright,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # We handle Playwright in the URL extraction
            batch_size=2,
        )

    async def _extract_product_urls_with_playwright(self, store_url: str) -> list[str]:
        """Extract product URLs using Playwright to handle JavaScript-rendered content.

        Args:
            store_url: URL of the shop page

        Returns:
            List of product URLs for coffee products
        """
        product_urls = []

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Navigate to shop page
                await page.goto(store_url, wait_until="networkidle")

                # Wait for products to load (Squarespace uses dynamic loading)
                await page.wait_for_timeout(3000)

                # Look for product links using various selectors
                # Squarespace uses specific classes for product items
                selectors = [
                    'a[href*="/products/"]',  # Direct product links
                    ".ProductList-item a",  # Product list items
                    ".grid-item a",  # Grid layout items
                    ".sqs-block-product a",  # Product blocks
                    ".product-block a",  # Product blocks
                ]

                for selector in selectors:
                    try:
                        links = await page.locator(selector).all()
                        for link in links:
                            href = await link.get_attribute("href")
                            if href:
                                full_url = self.resolve_url(href)
                                if self.is_coffee_product_url(full_url, ["/shop/p/"]):
                                    product_urls.append(full_url)
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")

                # Also try getting links from the page content
                content = await page.content()
                soup = BeautifulSoup(content, "lxml")

                # Look for product links in the rendered HTML
                all_links = soup.find_all("a", href=True)
                for link in all_links:
                    if isinstance(link, Tag):
                        href = link.get("href", "")
                        if href and isinstance(href, str) and "/shop/p/" in href:
                            product_url = self.resolve_url(href)
                            if self.is_coffee_product_url(product_url, ["/shop/p/"]):
                                product_urls.append(product_url)

            except Exception as e:
                logger.error(f"Error extracting URLs with Playwright: {e}")
            finally:
                await browser.close()

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls
