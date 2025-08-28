"""Scenery Coffee scraper for extracting coffee bean information.

Scenery Coffee is a specialty coffee roaster based in London, UK.
They offer a variety of single-origin coffees and blends with detailed
traceability information and tasting notes.
"""

import logging

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from ..schemas import CoffeeBean
from ..schemas.coffee_bean import Bean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="scenery-coffee",
    display_name="Scenery Coffee",
    roaster_name="Scenery Coffee",
    website="https://scenery.coffee",
    description="Specialty coffee roaster based in London, UK",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SceneryCoffeeScraper(BaseScraper):
    """Scraper for Scenery Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Scenery Coffee",
            base_url="https://scenery.coffee",
            rate_limit_delay=1.0,
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
            List containing the store URLs to scrape
        """
        return [
            "https://scenery.coffee/collections/coffee-1",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Scenery Coffee.

        Returns:
            List of CoffeeBean objects
        """
        # Use the AI-powered scraping workflow
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Shopify stores work well with standard requests
                batch_size=2,  # Conservative batch size to respect rate limits
            )

        # Fallback to traditional scraping if AI not available
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

        # Use the base class method with Shopify-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
                ".grid-product__link",
                ".product-card a",
            ],
        )

    async def _scrape_traditional(self) -> list[CoffeeBean]:
        """Traditional scraping fallback method."""
        logger.warning("Using traditional scraping - AI extraction not available")

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

                # Extract product URLs
                product_urls = await self._extract_product_urls_from_store(store_url)
                logger.info(f"Found {len(product_urls)} product URLs on {store_url}")

                # Scrape each product page
                for product_url in product_urls:
                    logger.debug(f"Extracting from: {product_url}")
                    product_soup = await self.fetch_page(product_url)

                    if not product_soup:
                        logger.warning(f"Failed to fetch product page: {product_url}")
                        continue

                    session.pages_scraped += 1

                    # Traditional manual extraction
                    bean = await self._extract_traditional_bean(product_soup, product_url)

                    if bean and self.is_coffee_product_name(bean.name):
                        coffee_beans.append(bean)
                        logger.debug(f"Extracted: {bean.name}")

            session.beans_found = len(coffee_beans)
            session.beans_processed = len(coffee_beans)
            self.end_session(success=True)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            session.add_error(f"Scraping error: {e}")
            self.end_session(success=False)
            raise

        return coffee_beans

    async def _extract_traditional_bean(self, soup: BeautifulSoup, product_url: str) -> CoffeeBean | None:
        """Extract coffee bean information using traditional parsing.

        Args:
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Extract name (required)
            name = None
            name_elem = soup.find("h1")
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            if not name:
                return None

            # Extract price
            price = None
            price_elem = soup.find("span", class_="money")
            if not price_elem:
                # Look for any text containing £ symbol
                price_texts = soup.find_all(string=True)
                for text in price_texts:
                    if text and isinstance(text, str) and "£" in text:
                        price = self.extract_price(text)
                        break
            else:
                price = self.extract_price(price_elem.get_text())

            # Extract description
            description = None
            desc_elem = soup.find("div", class_="product-single__description") or soup.find("div", class_="rte")
            if desc_elem:
                description = self.clean_text(desc_elem.get_text())

            # Check stock availability
            in_stock = True
            page_text = soup.get_text()
            if "sold out" in page_text.lower():
                in_stock = False

            # Create a basic origin object
            origin = Bean(country=None, region=None, producer=None, farm=None, elevation=0)

            # Create CoffeeBean object with required fields
            return CoffeeBean(
                name=name,
                roaster="Scenery Coffee",
                url=HttpUrl(product_url),
                image_url=None,
                origin=origin,
                is_single_origin=True,
                process=None,
                variety=None,
                harvest_date=None,
                price_paid_for_green_coffee=None,
                currency_of_price_paid_for_green_coffee=None,
                roast_level=None,
                roast_profile=None,
                weight=None,
                price=price,
                currency="GBP",
                is_decaf=False,
                tasting_notes=[],
                description=description,
                in_stock=in_stock,
                scraper_version="1.0",
                raw_data=None,
            )

        except Exception as e:
            logger.error(f"Traditional extraction failed for {product_url}: {e}")
            return None
