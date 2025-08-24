"""Cartwheel Coffee scraper implementation with AI-powered extraction."""

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
    name="cartwheel",
    display_name="Cartwheel Coffee",
    roaster_name="Cartwheel Coffee",
    website="cartwheelcoffee.com",
    description="UK-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="UK",
    status="available",
)
class CartwheelCoffeeScraper(BaseScraper):
    """Scraper for Cartwheel Coffee (cartwheelcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cartwheel Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cartwheel Coffee",
            base_url="https://cartwheelcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://cartwheelcoffee.com/pages/store"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Cartwheel Coffee store using AI extraction.

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
                soup = await self.fetch_page(store_url)

                if not soup:
                    logger.error(f"Failed to fetch store page: {store_url}")
                    continue

                session.pages_scraped += 1

                # Extract product URLs from the index page
                product_urls = await self._extract_product_urls(soup)
                logger.info(f"Found {len(product_urls)} total product URLs on {store_url}")

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
                logger.debug(f"AI extracting from: {product_url}")
                product_soup = await self.fetch_page(product_url)

                if not product_soup:
                    logger.warning(f"Failed to fetch product page: {product_url}")
                    return None

                session.pages_scraped += 1

                # Use AI to extract detailed bean information
                bean = await self._extract_bean_with_ai(product_soup, product_url)
                if bean and self._is_coffee_product(bean.name):
                    logger.debug(f"AI extracted: {bean.name} from {bean.origin}")

                    # Save bean to file and mark as scraped
                    self.save_bean_to_file(bean, Path("data"))
                    self._mark_bean_as_scraped(product_url)

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

    async def _extract_product_urls(self, soup: BeautifulSoup) -> list[str]:
        """Extract product URLs from the store index page.

        Args:
            soup: BeautifulSoup object of the store page

        Returns:
            List of product URLs
        """
        product_urls = []

        # Look for links to coffee products
        # Based on the HTML structure, product links are in the shop_collection containers
        # Look for links with shop-img_hover class (more direct approach)
        product_links = soup.find_all("a", class_="shop-img_hover is--store w-inline-block")

        if not product_links:
            # Fallback 1: Look for any element with shop-img_hover in class
            def has_shop_img_hover(css_class):
                if css_class:
                    if isinstance(css_class, list):
                        return "shop-img_hover" in " ".join(css_class)
                    else:
                        return "shop-img_hover" in css_class
                return False

            product_links = soup.find_all("a", class_=has_shop_img_hover)

        if not product_links:
            # Fallback 2: Look for any links with /products/ in href
            def has_products_in_href(href):
                return href and "/products/" in href

            product_links = soup.find_all("a", href=has_products_in_href)

        for link in product_links:
            if isinstance(link, Tag):
                href = link.get("href")
                if href and isinstance(href, str):

                    # Filter out non-coffee products based on URL patterns
                    if self._is_coffee_product_url(href):
                        product_urls.append(self.resolve_url(href))

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Check if a product URL is likely for coffee beans."""
        url_lower = url.lower()

        # Exclude obvious non-coffee product URLs
        excluded_patterns = [
            # Equipment
            "brewer",
            "dripper",
            "grinder",
            "maker",
            "server",
            "scale",
            "kettle",
            "carafe",
            # Cups and drinkware
            "mug",
            "cup",
            "tumbler",
            "tray",
            "glass",
            # Brewing accessories
            "papers",
            "v60",
            "chemex",
            "aeropress",
            "kalita",
            "hario",
            "kinto",
            # Brands (equipment manufacturers)
            "baratza",
            "fellow",
            "timemore",
            "comandante",
            # Bundles and kits
            "bundle",
            "kit",
            "set",
            "starter",
            "combo",
            # Services
            "workshop",
            "training",
            "subscription",
            "gift-card",
            "voucher",
            # Clothing and merchandise
            "tee",
            "shirt",
            "clothing",
            "apparel",
            "hoodie",
            "sweater",
            "bag",
            "tote",
            "pouch",
            "case",
            # Books and guides
            "guide",
            "book",
            "manual",
            "recipe",
            # Non-coffee consumables
            "milk",
            "syrup",
            "sugar",
            "sweetener",
            "chocolate",
            # Cart and checkout pages
            "checkout",
            "payment",
            "account",
        ]

        # Also exclude common URL patterns that aren't products
        excluded_url_patterns = [
            "/pages/",
            "/blogs/",
            "/collections/",
            "/cart",
            "/checkout",
            "/account",
            "/search",
            "/admin",
            "/api/",
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

            # Use AI extractor to get structured data
            bean = await self.ai_extractor.extract_coffee_data(html_content, product_url)

            if bean:
                logger.debug(f"AI extracted: {bean.name} from {bean.origin}")
                return bean
            else:
                logger.warning(f"Failed to extract data from {product_url}")
                return None

        except Exception as e:
            logger.error(f"Error extracting bean from product page {product_url}: {e}")
            return None

    def _is_coffee_product(self, name: str) -> bool:
        """Check if this product is actually coffee beans (not equipment/gifts)."""
        if not name:
            return False

        name_lower = name.lower()

        # Exclude equipment, accessories, and gifts
        excluded_categories = [
            "brewer",
            "dripper",
            "grinder",
            "mug",
            "cup",
            "tumbler",
            "tray",
            "papers",
            "bundle",
            "kit",
            "workshop",
            "gift card",
            "tees",
            "shirt",
            "clothing",
            "bag",
            "tote",
            "guide",
            "book",
            "maker",
            "server",
            "scale",
            "kettle",
            "carafe",
            "v60",
            "chemex",
            "aeropress",
            "kalita",
            "hario",
            "kinto",
            "baratza",
            "cart",
        ]

        # Check if name contains any excluded category
        for category in excluded_categories:
            if category in name_lower:
                return False

        return True
