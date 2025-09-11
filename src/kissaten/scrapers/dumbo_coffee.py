"""Dumbo Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dumbo",
    display_name="Dumbo Coffee",
    roaster_name="Coffee Dumbo",
    website="https://www.coffeedumbo.tw",
    description="Taiwan-based specialty coffee roaster with Chinese and English options",
    requires_api_key=True,
    currency="GBP",  # They use GBP on their site
    country="Taiwan",
    status="available",
)
class DumboCoffeeScraper(BaseScraper):
    """Scraper for Dumbo Coffee (coffeedumbo.tw) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dumbo Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Dumbo",
            base_url="https://www.coffeedumbo.tw",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL for coffee beans
        """
        return ["https://www.coffeedumbo.tw/categories/%E5%92%96%E5%95%A1%E8%B1%86?limit=72"]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Dumbo Coffee store with efficient stock updates.

        This method will check for existing beans and create diffjson stock updates
        for products that already have bean files, or do full scraping for new products.

        Args:
            force_full_update: If True, perform full scraping for all products instead of diffjson updates

        Returns:
            List of CoffeeBean objects (only new products, or all products if force_full_update=True)
        """
        # Start session and get all current product URLs from the website
        self.start_session()
        output_dir = Path("data")

        all_product_urls = []
        for store_url in self.get_store_urls():
            product_urls = await self._extract_product_urls_from_store(store_url)
            all_product_urls.extend(product_urls)

        if force_full_update:
            # Force full scraping for all products
            logger.info(
                f"Force full update enabled - performing full scraping for all {len(all_product_urls)} products"
            )
            return await self._scrape_new_products(all_product_urls)

        # Create diffjson stock updates for existing products
        in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
            all_product_urls, output_dir, force_full_update
        )

        # Find new products that need full scraping
        new_urls = []
        for url in all_product_urls:
            if not self._is_bean_already_scraped_anywhere(url):
                new_urls.append(url)

        logger.info(f"Found {in_stock_count} existing products for stock updates")
        logger.info(f"Found {out_of_stock_count} products now out of stock")
        logger.info(f"Found {len(new_urls)} new products for full scraping")

        # Perform full AI extraction only for new products
        if new_urls:
            return await self._scrape_new_products(new_urls)

        return []

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction with optimized mode.

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
            use_playwright=True,  # Use Playwright for screenshot support
            use_optimized_mode=True,  # Use optimized mode for complex layouts
            translate_to_english=False,  # Enable translation for Taiwan-based content
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page, filtering out sold-out products.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs (excluding sold-out products)
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []

        # Find all product links using CSS selector
        product_links = soup.select('a[href*="/products/"]')

        for link in product_links:
            href = link.get("href")
            if not href:
                continue

            # Ensure href is a string
            if not isinstance(href, str):
                continue

            full_url = self.resolve_url(href)

            # Check if this product is sold out by looking for "out-of-stock" class
            # The class should be on a div two children below the <a> tag
            is_sold_out = self._check_if_sold_out(link)

            if is_sold_out:
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Apply standard coffee product filtering
            if self.is_coffee_product_url(full_url, ["/products/"]):
                product_urls.append(full_url)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} in-stock product URLs from {store_url}")
        return unique_urls

    def _check_if_sold_out(self, link_element) -> bool:
        """Check if a product link represents a sold-out product.

        Args:
            link_element: BeautifulSoup element representing the product link

        Returns:
            True if the product is sold out, False otherwise
        """
        try:
            # Navigate two children below the <a> tag to find the div with "out-of-stock" class
            # This could be implemented in multiple ways depending on the exact HTML structure

            # Method 1: Check if the link's parent or siblings contain out-of-stock indicators
            parent = link_element.parent
            if parent:
                # Look for out-of-stock class in the parent container
                if parent.find(class_="out-of-stock"):
                    return True

                # Look for out-of-stock class in siblings
                for sibling in parent.find_all():
                    if "out-of-stock" in sibling.get("class", []):
                        return True

            # Method 2: Look for out-of-stock class in children/descendants of the link's container
            # Find the container that holds the product info
            product_container = link_element.find_parent(
                class_=lambda x: x and any(keyword in str(x).lower() for keyword in ["product", "item", "card"])
            )

            if product_container:
                # Look for out-of-stock indicators in the product container
                out_of_stock_element = product_container.find(class_="out-of-stock")
                if out_of_stock_element:
                    return True

            # Method 3: Check specific structure - div two children below the <a>
            # This assumes a specific HTML structure that may need adjustment
            if link_element.parent and link_element.parent.parent:
                grandparent = link_element.parent.parent
                for div in grandparent.find_all("div", class_="out-of-stock"):
                    return True

            return False

        except Exception as e:
            logger.debug(f"Error checking sold-out status: {e}")
            # If we can't determine the status, assume it's in stock to avoid missing products
            return False
