"""People's Possession Coffee scraper implementation with AI-powered extraction."""

import logging
from typing import Optional

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="people-possession",
    display_name="People's Possession",
    roaster_name="People's Possession",
    website="peoplepossession.com",
    description="Radically sourced specialty coffee from Europe",
    requires_api_key=True,
    currency="EUR",
    country="Europe",
    status="available",
)
class PeoplePossessionScraper(BaseScraper):
    """Scraper for People's Possession Coffee (peoplepossession.com) with AI-powered extraction."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize People's Possession scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="People's Possession",
            base_url="https://peoplepossession.com",
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
        return ["https://peoplepossession.com/shop/"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from People's Possession shop using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        session = self.start_session()
        coffee_beans = []

        try:
            # Load existing beans for this session to avoid re-scraping
            self._load_existing_beans_for_session()

            store_urls = self.get_store_urls()

            for store_url in store_urls:
                logger.info(f"Scraping store page: {store_url}")
                soup = await self.fetch_page(store_url, use_playwright=True)

                if not soup:
                    logger.error(f"Failed to fetch store page: {store_url}")
                    continue

                session.pages_scraped += 1

                # Extract product URLs from the shop page
                product_urls = await self._extract_product_urls(soup)
                logger.info(f"Found {len(product_urls)} total product URLs on {store_url}")

                # Filter out URLs that have already been scraped in this session
                new_product_urls = [url for url in product_urls if not self._is_bean_already_scraped(url)]
                skipped_count = len(product_urls) - len(new_product_urls)

                if skipped_count > 0:
                    logger.info(f"Skipping {skipped_count} already scraped products from today's session")
                logger.info(f"Processing {len(new_product_urls)} new products")

                # Scrape each individual product page
                for product_url in new_product_urls:
                    logger.debug(f"AI extracting from: {product_url}")
                    product_soup = await self.fetch_page(product_url)

                    if not product_soup:
                        logger.warning(f"Failed to fetch product page: {product_url}")
                        continue

                    session.pages_scraped += 1

                    # Use AI to extract detailed bean information
                    bean = await self._extract_bean_with_ai(product_soup, product_url)
                    if bean and self._is_coffee_product(bean.name):
                        coffee_beans.append(bean)
                        logger.debug(f"AI extracted: {bean.name} from {bean.origin}")

                        # Save bean to file and mark as scraped
                        from pathlib import Path
                        self.save_bean_to_file(bean, Path("data"))
                        self._mark_bean_as_scraped(product_url)

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
        """Extract product URLs from the shop page.

        Args:
            soup: BeautifulSoup object of the shop page

        Returns:
            List of product URLs
        """
        product_urls = []

        # Strategy 1: Look for product links based on common e-commerce patterns
        # Try to find product containers or product links
        product_links = []

        # Method 1: Look for links with product names or specific classes
        # Check for common product link patterns
        possible_product_selectors = [
            'a[href*="/product/"]',
        ]

        for selector in possible_product_selectors:
            try:
                links = soup.select(selector)
                if links:
                    product_links.extend(links)
                    logger.debug(f"Found {len(links)} links with selector: {selector}")
                    break  # Use first successful selector
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue


        # Process found links
        for link in product_links:
            if isinstance(link, Tag):
                href = link.get('href')
                if href and isinstance(href, str):
                    # Filter out non-coffee products and administrative pages
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
            # Equipment and accessories
            'equipment', 'gear', 'merch', 'merchandise', 'apparel',
            'mug', 'cup', 'tumbler', 'bottle', 'grinder', 'brewer',
             'gift-card', 'subscription', 'bundle',
            'guide', 'accessory', 'brewing', 'kettle',
            'shirt', 't-shirt', 'hoodie', 'clothing', 'poster',
            'keychain', 'key-chain', 'postcard',

            # Administrative pages
            'cart', 'checkout', 'account', 'login', 'register',
            'contact', 'about', 'shipping', 'privacy', 'terms',
            'dealer', 'manifesto', 'news', 'blog',

            # Non-product pages
            '/pages/', '/blogs/', '/collections/', '/api/',
            '/admin/', '/search/', '/help/', '/support/'
        ]

        # Check if URL contains excluded patterns
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False

        # Allow URLs that suggest coffee products
        coffee_indicators = [
            '/product/', '/shop/', '/coffee/', '/bean',
            'filter', 'blend', 'omni', 'espresso', 'geisha',
            'bourbon', 'natural', 'washed', 'honey'
        ]

        # If it has coffee indicators, it's likely a coffee product
        if any(indicator in url_lower for indicator in coffee_indicators):
            return True

        # If it's a product URL but doesn't match coffee indicators,
        # we'll let AI decide during extraction
        return '/product/' in url_lower or len(url_lower.split('/')) > 4

    async def _extract_bean_with_ai(self, soup: BeautifulSoup, product_url: str) -> Optional[CoffeeBean]:
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
                # Ensure correct roaster details for People's Possession
                bean.roaster = "People's Possession"
                bean.currency = "EUR"
                logger.debug(f"AI extracted: {bean.name} from {bean.origin}")
                return bean
            else:
                logger.warning(f"Failed to extract data from {product_url}")
                return None

        except Exception as e:
            logger.error(f"Error extracting bean from product page {product_url}: {e}")
            return None

    def _is_coffee_product(self, name: str) -> bool:
        """Check if this product is actually coffee beans (not equipment/merch)."""
        if not name:
            return False

        name_lower = name.lower()

        # Exclude obvious non-coffee products
        excluded_categories = [
            # Equipment
            'grinder', 'brewer', 'dripper', 'maker', 'kettle', 'scale',
            'papers', 'v60', 'chemex', 'aeropress',

            # Drinkware
            'mug', 'cup', 'tumbler', 'bottle', 'glass',

            # Clothing and merchandise
            'shirt', 't-shirt', 'hoodie', 'clothing', 'apparel',
            'bag', 'tote', 'poster', 'postcard', 'keychain',
            'coin', 'holder', 'better than you', 'dive into',
            'new world', 'summer trash',

            # Services
            'gift card', 'subscription', 'workshop', 'training',

            # Equipment brands
            'baratza', 'fellow', 'timemore', 'comandante',

            # Non-coffee items
            'lid', 'reusable lid'
        ]

        # Check if name contains any excluded category
        for category in excluded_categories:
            if category in name_lower:
                return False

        # Coffee product indicators
        coffee_indicators = [
            'filter', 'blend', 'omni', 'espresso',  # Categories from the site
            'geisha', 'bourbon', 'castillo', 'maragogipe',  # Coffee varieties
            'natural', 'washed', 'honey', 'anaerobic',  # Processing methods
            'lot', 'finca', 'farm', 'estate',  # Origin indicators
            'colombia', 'ethiopia', 'kenya', 'guatemala',  # Countries
            'g', 'gr', 'gram'  # Weight indicators
        ]

        # If it has coffee indicators, likely coffee
        if any(indicator in name_lower for indicator in coffee_indicators):
            return True

        # If no clear indicators, be conservative and include it
        # (AI extraction will filter out non-coffee during processing)
        return True
