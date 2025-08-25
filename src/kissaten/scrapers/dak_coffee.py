"""Dak Coffee Roasters scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dak",
    display_name="Dak Coffee Roasters",
    roaster_name="Dak Coffee Roasters",
    website="dakcoffeeroasters.com",
    description="Amsterdam-based specialty coffee roaster",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class DakCoffeeScraper(BaseScraper):
    """Scraper for Dak Coffee Roasters (dakcoffeeroasters.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dak Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Dak Coffee Roasters",
            base_url="https://www.dakcoffeeroasters.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs
        """
        return [
            "https://www.dakcoffeeroasters.com/shop",
            "https://www.dakcoffeeroasters.com/shop?filter=Espresso%2CFilter",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Dak Coffee Roasters using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # JavaScript-heavy React site requires Playwright
            batch_size=2,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        This site uses Snipcart for e-commerce, so we need to extract product data
        from the Snipcart elements and construct the individual product URLs.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        # Use Playwright to handle the React site
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright is required for Dak Coffee scraper")
            return []

        product_urls = []

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto(store_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)  # Wait for React to render

                # Extract product data from Snipcart elements
                snipcart_elements = await page.query_selector_all("[data-item-id][data-item-name]")
                logger.info(f"Found {len(snipcart_elements)} Snipcart products")

                for element in snipcart_elements:
                    try:
                        item_name = await element.get_attribute("data-item-name")
                        if item_name:
                            # Convert product name to URL slug
                            # Example: "Big Apple - Colombia" -> "big-apple"
                            slug = self._name_to_slug(item_name)
                            if slug:
                                # Construct the product URL with default parameters
                                product_url = (
                                    f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}?quantity=200g&roast=filter"
                                )
                                product_urls.append(product_url)
                                logger.debug(f"Generated URL for '{item_name}': {product_url}")
                    except Exception as e:
                        logger.warning(f"Error processing Snipcart element: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error extracting from Dak Coffee store: {e}")
            finally:
                await browser.close()

        logger.info(f"Extracted {len(product_urls)} product URLs from Dak Coffee")
        return product_urls

    def _name_to_slug(self, name: str) -> str:
        """Convert a product name to a URL slug.

        Args:
            name: Product name like "Big Apple - Colombia"

        Returns:
            URL slug like "big-apple"
        """
        if not name:
            return ""

        # Take only the part before the first dash (coffee name, not origin)
        coffee_name = name.split(" - ")[0].strip()

        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = coffee_name.lower()
        slug = "".join(c if c.isalnum() else "-" for c in slug)
        slug = "-".join(part for part in slug.split("-") if part)  # Remove empty parts

        return slug
