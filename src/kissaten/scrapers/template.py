"""Template for creating new coffee roaster scrapers.

Copy this file and modify it for new roasters. This template demonstrates:

1. NEW APPROACH (RECOMMENDED): Use scrape_with_ai_extraction() for AI-powered scraping
   - Minimal code required (just URL extraction)
   - Built-in session management, batch processing, error handling
   - Concurrent processing and rate limiting
   - Automatic bean saving and deduplication

2. LEGACY APPROACH: Traditional manual parsing (for educational purposes)
   - Full manual control over scraping workflow
   - Custom extraction logic for each field
   - More code but complete flexibility

For new scrapers, strongly prefer the AI-powered approach unless you have
specific requirements that need manual control.

QUICK START GUIDE:
1. Copy this file and rename it to your_roaster_name.py
2. Update the @register_scraper decorator with your roaster's details
3. Update the __init__ method with your roaster's base URL and settings
4. Update get_store_urls() to return your roaster's coffee collection URLs
5. Modify _extract_product_urls_from_store() with your roaster's URL patterns
6. Test with: python -m kissaten.cli scrape your-roaster-name --api-key YOUR_KEY
7. Most scrapers will work with just these changes - no AI training required!
"""

import logging

from bs4 import BeautifulSoup, Tag
from pydantic import HttpUrl

from ..schemas import CoffeeBean
from ..schemas.coffee_bean import Bean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="example",  # CLI name - should be lowercase, no spaces
    display_name="Example Coffee Roaster",  # Human-readable name
    roaster_name="Example Coffee Co",  # Official company name
    website="https://example-coffee.com",  # Website domain
    description="Example template for new scrapers",
    requires_api_key=True,  # Set to True if using AI extraction (RECOMMENDED)
    currency="USD",  # Default currency for this roaster
    country="USA",  # Country where roaster is based
    status="experimental",  # available, experimental, or deprecated
)
class ExampleCoffeeScraper(BaseScraper):
    """Example scraper template - replace with actual roaster implementation."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Example Coffee Co",
            base_url="https://example-coffee.com",
            rate_limit_delay=1.0,  # Seconds between requests
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (RECOMMENDED for new scrapers)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            "https://example-coffee.com/collections/coffee",
            # Add more URLs if the roaster has multiple collection pages
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Example Coffee.

        Returns:
            List of CoffeeBean objects
        """
        # OPTION 1: Use the new simplified AI-powered scraping workflow (RECOMMENDED)
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Set to True for JavaScript-heavy sites
                batch_size=2,  # Adjust based on site's rate limits
            )

        # OPTION 2: Traditional manual scraping (for sites that don't need AI)
        return await self._scrape_traditional()

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page using the new base class method.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Use the new base class method with roaster-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # Adjust URL path patterns for your roaster's structure:
            # Common patterns: ["/products/"], ["/product/"], ["/shop/p/"], ["/coffee/"]
            url_path_patterns=["/products/"],
            selectors=[
                # Add roaster-specific CSS selectors if the default ones don't work
                # Leave empty to use default selectors from base class
                "a.product-link",
                ".product-item a",
                'a[href*="/products/"]',
            ],
        )

    async def _scrape_traditional(self) -> list[CoffeeBean]:
        """Traditional scraping approach for sites that don't need AI extraction.

        This method shows the old manual approach for educational purposes.
        For new scrapers, prefer the AI-powered approach above.
        """
        session = self.start_session()
        coffee_beans = []

        try:
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
                logger.info(f"Found {len(product_urls)} product URLs on {store_url}")

                # Scrape each individual product page
                for product_url in product_urls:
                    logger.debug(f"Extracting from: {product_url}")
                    product_soup = await self.fetch_page(product_url)

                    if not product_soup:
                        logger.warning(f"Failed to fetch product page: {product_url}")
                        continue

                    session.pages_scraped += 1

                    # Traditional manual extraction
                    bean = await self._extract_traditional(product_soup, product_url)

                    if bean and self._is_coffee_product(bean.name):
                        coffee_beans.append(bean)
                        logger.debug(f"Extracted: {bean.name} from {bean.origin}")

            session.beans_found = len(coffee_beans)
            session.beans_processed = len(coffee_beans)

            self.end_session(success=True)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            session.add_error(f"Scraping error: {e}")
            self.end_session(success=False)
            raise

        return coffee_beans

    async def _extract_product_urls(self, soup: BeautifulSoup) -> list[str]:
        """Extract product URLs from the store index page (legacy method for traditional scraping).

        NOTE: For new scrapers, use _extract_product_urls_from_store() with the new
        base class extract_product_urls_from_soup() method instead.

        Args:
            soup: BeautifulSoup object of the store page

        Returns:
            List of product URLs
        """
        product_urls = []

        # TODO: Replace with actual selectors for this roaster
        # Example patterns to look for:

        # Method 1: Look for product links by class
        product_links = soup.find_all("a", class_="product-link")

        # Method 2: Look for links in product containers
        if not product_links:
            containers = soup.find_all("div", class_="product-item")
            for container in containers:
                if isinstance(container, Tag):
                    link = container.find("a")
                    if isinstance(link, Tag):
                        product_links.append(link)

        # Method 3: Look for any links with /products/ in href
        if not product_links:
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                if isinstance(link, Tag):
                    href = link.get("href")
                    if href and isinstance(href, str) and "/products/" in href:
                        product_links.append(link)

        for link in product_links:
            if isinstance(link, Tag):
                href = link.get("href")
                if href and isinstance(href, str):
                    product_url = self.resolve_url(href)

                    # Filter out non-coffee products using base class method
                    if self.is_coffee_product_url(product_url, required_path_patterns=["/products/"]):
                        product_urls.append(product_url)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    async def _extract_traditional(self, soup: BeautifulSoup, product_url: str) -> CoffeeBean | None:
        """Extract coffee bean information using traditional parsing.

        Args:
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # TODO: Replace with actual selectors for this roaster

            # Extract name (required)
            name = None
            name_elem = soup.find("h1", class_="product-title")
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            if not name:
                # Fallback to page title
                title_elem = soup.find("title")
                if title_elem:
                    name = title_elem.get_text().split("|")[0].strip()

            if not name:
                return None

            # Extract price
            price = None
            price_elem = soup.find("span", class_="price")
            if price_elem:
                price = self.extract_price(price_elem.get_text())

            # Extract weight
            weight = None
            weight_elem = soup.find("span", class_="weight")
            if weight_elem:
                weight = self.extract_weight(weight_elem.get_text())

            # Extract origin
            origin = None
            origin_elem = soup.find("span", class_="origin")
            if origin_elem:
                origin = self.clean_text(origin_elem.get_text())

            # Extract tasting notes
            tasting_notes = []
            notes_elem = soup.find("div", class_="tasting-notes")
            if notes_elem:
                notes_text = notes_elem.get_text()
                # Split on common separators
                if "," in notes_text:
                    tasting_notes = [note.strip() for note in notes_text.split(",")]
                elif "/" in notes_text:
                    tasting_notes = [note.strip() for note in notes_text.split("/")]

            # Extract description
            description = None
            desc_elem = soup.find("div", class_="product-description")
            if desc_elem:
                description = self.clean_text(desc_elem.get_text())

            # Check stock availability
            in_stock = None
            stock_elem = soup.find("button", class_="add-to-cart")
            if stock_elem:
                in_stock = "out of stock" not in stock_elem.get_text().lower()

            # Create basic origin object
            origin_obj = Bean(country=origin, region=None, producer=None, farm=None, elevation=0)

            # Create CoffeeBean object
            return CoffeeBean(
                name=name,
                roaster="Example Coffee Co",
                url=HttpUrl(product_url),
                origin=origin_obj,
                price=price,
                currency="USD",
                weight=weight,
                tasting_notes=tasting_notes,
                description=description,
                in_stock=in_stock,
                scraper_version="1.0",
                # Required fields with default values
                is_single_origin=False,
                process=None,
                variety=None,
                harvest_date=None,
                price_paid_for_green_coffee=None,
                currency_of_price_paid_for_green_coffee=None,
                roast_level=None,
                raw_data=None,
            )

        except Exception as e:
            logger.error(f"Traditional extraction failed for {product_url}: {e}")
            return None

    def _is_coffee_product(self, name: str) -> bool:
        """Check if this product is actually coffee beans (not equipment/gifts)."""
        # Use base class method
        return self.is_coffee_product_name(name)
