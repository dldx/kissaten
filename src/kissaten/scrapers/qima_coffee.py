"""Qima Coffee scraper implementation with AI-powered extraction."""

import asyncio
import logging
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="qima-coffee",
    display_name="Qima Cafe",
    roaster_name="Qima Cafe",
    website="qimacafe.com",
    description="London-based specialty coffee roaster with life-changing coffee from Yemen, Ethiopia, and Colombia",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class QimaCoffeeScraper(BaseScraper):
    """Scraper for Qima Cafe with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Qima Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Qima Cafe",
            base_url="https://qimacafe.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://qimacafe.com/collections/life-changing-coffee"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Qima Coffee store using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        # Start scraping session
        session = self.start_session()
        coffee_beans = []

        try:
            # Load existing beans for this session to avoid re-scraping
            self._load_existing_beans_for_session()

            store_urls = self.get_store_urls()

            for store_url in store_urls:
                logger.info(f"Scraping store page: {store_url}")

                # Extract product URLs
                product_urls = await self._extract_product_urls_from_store(store_url)
                logger.info(f"Found {len(product_urls)} total product URLs on {store_url}")

                session.pages_scraped += 1

                # Filter out URLs that have already been scraped in this session
                new_product_urls = [url for url in product_urls if not self._is_bean_already_scraped(url)]
                skipped_count = len(product_urls) - len(new_product_urls)

                if skipped_count > 0:
                    logger.info(f"Skipping {skipped_count} already scraped products from today's session")
                logger.info(f"Processing {len(new_product_urls)} new products")

                # Process products in batches of 2 asynchronously
                batch_size = 2
                for i in range(0, len(new_product_urls), batch_size):
                    batch_urls = new_product_urls[i : i + batch_size]
                    batch_num = i // batch_size + 1
                    total_batches = (len(new_product_urls) + batch_size - 1) // batch_size
                    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_urls)} products)")

                    # Process this batch concurrently
                    batch_beans = await self._process_product_batch(batch_urls, session)
                    coffee_beans.extend(batch_beans)

                    # Small delay between batches to be respectful
                    if i + batch_size < len(new_product_urls):
                        await asyncio.sleep(0.5)

            session.beans_found = len(coffee_beans)
            session.beans_processed = len(coffee_beans)

            self.end_session(success=True)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            session.add_error(f"Scraping error: {e}")
            self.end_session(success=False)
            raise

        return coffee_beans

    async def _process_product_batch(self, product_urls: list[str], session) -> list[CoffeeBean]:
        """Process a batch of product URLs concurrently.

        Args:
            product_urls: List of product URLs to process
            session: Current scraping session for tracking

        Returns:
            List of successfully extracted CoffeeBean objects
        """

        async def process_single_product(product_url: str) -> CoffeeBean | None:
            """Process a single product URL."""
            try:
                # Double-check if this URL was already processed (in case of concurrent processing)
                if self._is_bean_already_scraped(product_url):
                    logger.debug(f"Skipping already processed URL: {product_url}")
                    return None

                # Mark as being processed to prevent concurrent processing
                self._mark_bean_as_scraped(product_url)

                logger.debug(f"AI extracting from: {product_url}")
                # For Shopify sites like Qima, standard mode should work well
                product_soup = await self.fetch_page(product_url, use_playwright=False)

                if not product_soup:
                    logger.warning(f"Failed to fetch product page: {product_url}")
                    return None

                session.pages_scraped += 1

                # Use AI to extract detailed bean information (standard mode for Shopify)
                bean = await self._extract_bean_with_ai(product_soup, product_url)
                if bean and self._is_coffee_product(bean.name):
                    logger.debug(f"AI extracted: {bean.name} from {bean.origin}")

                    # Save bean to file
                    self.save_bean_to_file(bean, Path("data"))

                    return bean

                return None

            except Exception as e:
                logger.error(f"Error processing product {product_url}: {e}")
                return None

        # Process all URLs in this batch concurrently
        tasks = [process_single_product(url) for url in product_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        beans = []
        for result in results:
            if isinstance(result, CoffeeBean):
                beans.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception in batch processing: {result}")

        return beans

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the store page.

        Args:
            store_url: URL of the coffee collection page

        Returns:
            List of product URLs for coffee products
        """
        product_urls = []

        try:
            # Fetch the store page - try with regular httpx first for Shopify
            soup = await self.fetch_page(store_url, use_playwright=False)

            if not soup:
                logger.error(f"Failed to fetch store page: {store_url}")
                return []

            # Extract product URLs from the collection page
            product_urls = await self._extract_product_urls(soup)

        except Exception as e:
            logger.error(f"Error extracting URLs from store page: {e}")

        return product_urls

    async def _extract_product_urls(self, soup: BeautifulSoup) -> list[str]:
        """Extract product URLs from the collection page.

        Args:
            soup: BeautifulSoup object of the collection page

        Returns:
            List of product URLs
        """
        product_urls = []

        try:
            # Use a single comprehensive approach to find all product links
            # This avoids the same link being found multiple times through different selectors
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                if isinstance(link, Tag):
                    href = link.get("href", "")
                    if href and isinstance(href, str) and "/products/" in href:
                        if self._is_coffee_product_url(href):
                            full_url = self.resolve_url(href)
                            product_urls.append(full_url)

        except Exception as e:
            logger.error(f"Error extracting product URLs: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Check if a product URL is likely for coffee beans.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be for coffee beans
        """
        url_lower = url.lower().replace("https://qimacafe.com", "")

        # Exclude obvious non-coffee product URLs
        excluded_patterns = [
            # Equipment and accessories
            "grinder", "dripper", "brewer", "maker", "server", "scale", "kettle", "carafe",
            "filter", "papers", "v60", "chemex", "aeropress", "kalita", "hario", "kinto",
            "origami", "fellow", "timemore", "baratza", "comandante",
            # Drinkware
            "mug", "cup", "tumbler", "glass", "ceramics", "tray",
            # Equipment brands and tools
            "acaia", "cafec", "cafelat", "cleaning", "cleaner", "brush", "cloth", "towel",
            "mat", "stand", "tamp", "holder", "rack",
            # Books and guides
            "book", "guide", "manual", "recipe", "magazine",
            # Bundles and kits
            "bundle", "kit", "set", "starter", "combo", "package",
            # Services and subscriptions
            "workshop", "training", "course", "subscription", "membership",
            "gift-card", "voucher", "certificate",
            # Clothing and merchandise
            "shirt", "tee", "clothing", "apparel", "hoodie", "sweater", "jacket",
            "bag", "tote", "pouch", "case", "backpack", "merch", "merchandise",
            # Technical/utility pages
            "cart", "checkout", "account", "login", "register", "search",
            "contact", "about", "shipping", "returns", "privacy", "terms",
        ]

        # URL patterns to exclude
        excluded_url_patterns = [
            "/category/", "/tag/", "/page/", "/cart/", "/checkout/", "/account/",
            "/my-account/", "/contact/", "/about/", "/shipping/", "/returns/",
            "/privacy/", "/terms/", "/blog/", "/news/", "/admin/", "/wp-",
        ]

        # Check excluded patterns in URL
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False

        # Check excluded URL patterns
        for pattern in excluded_url_patterns:
            if pattern in url_lower:
                return False

        # Must contain /products/ to be a valid product URL
        if "/products/" not in url_lower:
            return False

        return True

    async def _extract_bean_with_ai(self, soup: BeautifulSoup, product_url: str) -> CoffeeBean | None:
        """Extract detailed coffee bean information using AI.

        Args:
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Get the HTML content for AI processing
            html_content = str(soup)

            # Use AI extractor with standard mode for Shopify sites (progressive fallback)
            bean = await self.ai_extractor.extract_coffee_data(
                html_content, product_url, use_optimized_mode=False
            )

            if bean:
                # Ensure correct roaster details
                bean.roaster = "Qima Cafe"
                bean.currency = "GBP"
                logger.debug(f"AI extracted: {bean.name} from {bean.origin}")
                return bean
            else:
                logger.warning(f"Failed to extract data from {product_url}")
                return None

        except Exception as e:
            logger.error(f"Error extracting bean from product page {product_url}: {e}")
            return None

    def _is_coffee_product(self, name: str) -> bool:
        """Check if this product is actually coffee beans (not equipment/accessories).

        Args:
            name: Product name to check

        Returns:
            True if the product appears to be coffee beans
        """
        if not name:
            return False

        name_lower = name.lower()

        # Exclude equipment, accessories, and non-coffee items
        excluded_categories = [
            # Equipment
            "grinder", "dripper", "brewer", "maker", "server", "scale", "kettle", "carafe",
            "filter", "papers", "v60", "chemex", "aeropress", "kalita", "hario", "kinto",
            "origami", "fellow", "timemore", "baratza", "comandante",
            # Drinkware
            "mug", "cup", "tumbler", "glass", "ceramics", "tray",
            # Clothing and merchandise
            "shirt", "tee", "clothing", "apparel", "hoodie", "sweater",
            "bag", "tote", "pouch", "case", "merch", "merchandise",
            # Books and guides
            "book", "guide", "manual", "recipe", "magazine",
            # Services and gifts
            "gift card", "voucher", "certificate", "workshop", "training", "course",
            "subscription", "membership",
            # Bundles and kits
            "bundle", "kit", "set", "starter", "combo", "package",
            # Water treatment and cleaning
            "water", "cleaner", "cleaning", "brush", "cloth", "towel",
            # Technical accessories
            "stand", "tamp", "tamper", "mat", "pad", "holder", "rack",
        ]

        # Check if name contains any excluded category
        for category in excluded_categories:
            if category in name_lower:
                return False

        return True
