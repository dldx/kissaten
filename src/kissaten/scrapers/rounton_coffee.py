"""Rounton Coffee scraper implementation.

Rounton Coffee Roasters is a specialty coffee roastery based in North Yorkshire, UK.
They focus on sustainable sourcing and are proud members of 1% for the planet.
"""

import logging

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rounton-coffee",
    display_name="Rounton Coffee",
    roaster_name="Rounton Coffee Roasters",
    website="https://rountoncoffee.co.uk",
    description="Specialty coffee roastery from North Yorkshire, focusing on sustainable sourcing",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RountonCoffeeScraper(BaseScraper):
    """Scraper for Rounton Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Rounton Coffee Roasters",
            base_url="https://rountoncoffee.co.uk",
            rate_limit_delay=1.5,  # Be respectful to the site
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

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://rountoncoffee.co.uk/collections/coffee",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Rounton Coffee.

        Returns:
            List of CoffeeBean objects
        """
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Shopify sites usually work fine with httpx
            )

        # Fallback to traditional scraping if AI is not available
        return await self._scrape_traditional()

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        product_urls = []

        # Custom extraction for Rounton Coffee to handle URL spaces properly
        selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link",
            ".grid-product__link",
            "a.product-title",
        ]

        for selector in selectors:
            try:
                links = soup.select(selector)
                if links:
                    for link in links:
                        href = link.get("href")
                        if href and isinstance(href, str):
                            # Clean the href to remove any leading/trailing spaces
                            href = href.strip()

                            # Ensure it's a product URL
                            if "/products/" in href:
                                # Resolve to full URL, making sure to clean it
                                if href.startswith("/"):
                                    full_url = f"{self.base_url}{href}"
                                else:
                                    full_url = href

                                # Final cleanup to remove any spaces
                                full_url = full_url.replace(" ", "")

                                # Filter out non-coffee products
                                if self.is_coffee_product_url(full_url, ["/products/"]):
                                    product_urls.append(full_url)
                    break  # Use first successful selector
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Extracted {len(unique_urls)} product URLs from {store_url}")
        if unique_urls:
            logger.debug(f"Sample URLs: {unique_urls[:3]}")

        excluded_patterns = ["sample-pack", "gift-box"]
        unique_urls = [url for url in unique_urls if not any(pattern in url.lower() for pattern in excluded_patterns)]

        return unique_urls

    async def _extract_bean_with_ai(
        self, ai_extractor, soup: BeautifulSoup, product_url: str, use_optimized_mode: bool = False
    ) -> CoffeeBean | None:
        """Extract coffee bean data using AI.

        Args:
            ai_extractor: AI extractor instance
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            use_optimized_mode: Whether to use optimized mode (with screenshots)

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Get the HTML content for AI processing
            html_content = str(soup)

            # Use AI extractor to get structured data
            if use_optimized_mode:
                # For complex sites that benefit from visual analysis
                screenshot_bytes = await self.take_screenshot(product_url)
                bean: CoffeeBean = await ai_extractor.extract_coffee_data(
                    html_content, product_url, screenshot_bytes, use_optimized_mode=True
                )
            else:
                # Standard mode for most sites (Rounton Coffee appears well-structured)
                bean: CoffeeBean = await ai_extractor.extract_coffee_data(html_content, product_url)

            # if we don't have country and process and variety, then we probably don't have a valid bean
            if not bean.origins[0].country and not bean.origins[0].process and not bean.origins[0].variety:
                logger.warning(f"Failed to extract data from {product_url}")
                return None

            if bean:
                # Ensure correct roaster details
                bean.roaster = "Rounton Coffee Roasters"
                bean.currency = "GBP"
                return bean

        except Exception as e:
            logger.error(f"AI extraction failed for {product_url}: {e}")

        return None
