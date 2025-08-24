"""Template for creating new coffee roaster scrapers.

Copy this file and modify it for new roasters. This template shows both
AI-powered and traditional extraction approaches.
"""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="example",  # CLI name - should be lowercase, no spaces
    display_name="Example Coffee Roaster",  # Human-readable name
    roaster_name="Example Coffee Co",  # Official company name
    website="example-coffee.com",  # Website domain
    description="Example template for new scrapers",
    requires_api_key=False,  # Set to True if using AI extraction
    currency="USD",  # Default currency for this roaster
    country="USA",  # Country where roaster is based
    status="experimental"  # available, experimental, or deprecated
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
            timeout=30.0
        )

        # Only initialize AI extractor if needed and API key provided
        self.ai_extractor = None
        if api_key:
            try:
                from ..ai import CoffeeDataExtractor
                self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
            except ImportError:
                logger.warning("AI extractor not available")

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

                    # Choose extraction method based on availability
                    if self.ai_extractor:
                        bean = await self._extract_with_ai(product_soup, product_url)
                    else:
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
        """Extract product URLs from the store index page.

        Args:
            soup: BeautifulSoup object of the store page

        Returns:
            List of product URLs
        """
        product_urls = []

        # TODO: Replace with actual selectors for this roaster
        # Example patterns to look for:

        # Method 1: Look for product links by class
        product_links = soup.find_all('a', class_='product-link')

        # Method 2: Look for links in product containers
        if not product_links:
            containers = soup.find_all('div', class_='product-item')
            product_links = [container.find('a') for container in containers if container.find('a')]

        # Method 3: Look for any links with /products/ in href
        if not product_links:
            product_links = soup.find_all('a', href=lambda x: x and '/products/' in x)

        for link in product_links:
            if link and link.get('href'):
                href = link.get('href')
                product_url = self.resolve_url(href)

                # Filter out non-coffee products
                if self._is_coffee_product_url(product_url):
                    product_urls.append(product_url)

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
            'equipment', 'gear', 'merch', 'merchandise', 'apparel',
            'mug', 'cup', 'tumbler', 'bottle', 'grinder', 'brewer',
            'filter', 'gift-card', 'subscription', 'bundle',
            'book', 'guide', 'accessory', 'brewing', 'kettle'
        ]

        return not any(pattern in url_lower for pattern in excluded_patterns)

    async def _extract_with_ai(self, soup: BeautifulSoup, product_url: str) -> CoffeeBean | None:
        """Extract coffee bean information using AI.

        Args:
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            html_content = str(soup)
            bean = await self.ai_extractor.extract_coffee_data(html_content, product_url)

            if bean:
                # Ensure correct roaster name and currency
                bean.roaster = "Example Coffee Co"
                bean.currency = "USD"
                return bean

        except Exception as e:
            logger.error(f"AI extraction failed for {product_url}: {e}")

        return None

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
            name_elem = soup.find('h1', class_='product-title')
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            if not name:
                # Fallback to page title
                title_elem = soup.find('title')
                if title_elem:
                    name = title_elem.get_text().split('|')[0].strip()

            if not name:
                return None

            # Extract price
            price = None
            price_elem = soup.find('span', class_='price')
            if price_elem:
                price = self.extract_price(price_elem.get_text())

            # Extract weight
            weight = None
            weight_elem = soup.find('span', class_='weight')
            if weight_elem:
                weight = self.extract_weight(weight_elem.get_text())

            # Extract origin
            origin = None
            origin_elem = soup.find('span', class_='origin')
            if origin_elem:
                origin = self.clean_text(origin_elem.get_text())

            # Extract tasting notes
            tasting_notes = []
            notes_elem = soup.find('div', class_='tasting-notes')
            if notes_elem:
                notes_text = notes_elem.get_text()
                # Split on common separators
                if ',' in notes_text:
                    tasting_notes = [note.strip() for note in notes_text.split(',')]
                elif '/' in notes_text:
                    tasting_notes = [note.strip() for note in notes_text.split('/')]

            # Extract description
            description = None
            desc_elem = soup.find('div', class_='product-description')
            if desc_elem:
                description = self.clean_text(desc_elem.get_text())

            # Check stock availability
            in_stock = None
            stock_elem = soup.find('button', class_='add-to-cart')
            if stock_elem:
                in_stock = 'out of stock' not in stock_elem.get_text().lower()

            # Create CoffeeBean object
            return CoffeeBean(
                name=name,
                roaster="Example Coffee Co",
                url=product_url,
                origin=origin,
                price=price,
                currency="USD",
                weight=weight,
                tasting_notes=tasting_notes,
                description=description,
                in_stock=in_stock,
                scraper_version="1.0"
            )

        except Exception as e:
            logger.error(f"Traditional extraction failed for {product_url}: {e}")
            return None

    def _is_coffee_product(self, name: str) -> bool:
        """Check if this product is actually coffee beans (not equipment/gifts)."""
        if not name:
            return False

        name_lower = name.lower()

        # Exclude equipment, accessories, and gifts
        excluded_categories = [
            'mug', 'cup', 'tumbler', 'bottle', 'grinder', 'brewer',
            'filter', 'gift', 'card', 'subscription', 'bundle',
            'book', 'guide', 'shirt', 'hat', 'bag', 'tote',
            'equipment', 'gear', 'accessory', 'kettle', 'scale'
        ]

        # Check if name contains any excluded category
        for category in excluded_categories:
            if category in name_lower:
                return False

        return True
