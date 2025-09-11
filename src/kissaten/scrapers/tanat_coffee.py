"""Tanat Coffee scraper.

Scrapes coffee beans from Tanat Coffee (https://tanat.coffee/).
This roaster has multiple pages of products with clear pricing and detailed information.
"""

import logging
from pathlib import Path

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="tanat-coffee",
    display_name="Tanat Coffee",
    roaster_name="Tanat Coffee",
    website="https://tanat.coffee",
    description="French specialty coffee roaster based in Paris",
    requires_api_key=True,  # Using AI extraction for robust data parsing
    currency="EUR",
    country="France",
    status="available",
)
class TanatCoffeeScraper(BaseScraper):
    """Scraper for Tanat Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Tanat Coffee",
            base_url="https://tanat.coffee",
            rate_limit_delay=1.5,  # Be respectful with rate limiting
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
            List containing all pages of the coffee collection
        """
        # Based on the analysis, there are 5 pages of coffee products
        return [
            "https://tanat.coffee/en/categorie-produit/cafes/",
            "https://tanat.coffee/en/categorie-produit/cafes/page/2/",
            "https://tanat.coffee/en/categorie-produit/cafes/page/3/",
            "https://tanat.coffee/en/categorie-produit/cafes/page/4/",
            "https://tanat.coffee/en/categorie-produit/cafes/page/5/",
        ]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Tanat Coffee with efficient stock updates.

        This method will check for existing beans and create diffjson stock updates
        for products that already have bean files, or do full scraping for new products.

        Args:
            force_full_update: If True, perform full scraping for all products instead of diffjson updates

        Returns:
            List of CoffeeBean objects (only new products, or all products if force_full_update=True)
        """
        if not self.ai_extractor:
            logger.error("AI extractor not available - scraping requires AI functionality")
            return []

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
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Static HTML site, no JavaScript needed
            translate_to_english=True,  # Translate French to English for AI processing
        )

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

        # Custom selectors for Tanat Coffee (WordPress/WooCommerce)
        custom_selectors = [
            'a[href*="/boutique/"]',  # Tanat uses /boutique/ for product URLs
            ".product-link",
            ".woocommerce-LoopProduct-link",  # Common WooCommerce selector
            "h3 a",  # Product title links
            ".product-item a",
            ".product-title a",
            ".product-card a",
            'a[href*="/produit/"]',  # Alternative French product URL pattern
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/boutique/", "/produit/"],  # Support both URL patterns
            selectors=custom_selectors,
        )

        excluded_urls = ["abonnement-rarities-90"]
        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/boutique/", "/produit/"]) and not any(
                excluded in url for excluded in excluded_urls
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
