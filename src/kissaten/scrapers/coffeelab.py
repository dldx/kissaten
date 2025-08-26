"""Scraper for Coffee Lab (coffeelab.pl) - Polish specialty coffee roaster."""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffeelab",
    display_name="Coffee Lab",
    roaster_name="Coffee Lab",
    website="coffeelab.pl",
    description="Specialty coffee roaster from Warsaw, Poland focusing on quality and precision",
    requires_api_key=True,  # Use AI extraction for best results
    currency="PLN",
    country="Poland",
    status="available",
)
class CoffeeLabScraper(BaseScraper):
    """Scraper for Coffee Lab - Polish specialty coffee roaster."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Coffee Lab",
            base_url="https://coffeelab.pl",
            rate_limit_delay=1.5,  # Be respectful to the site
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for this site)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Coffee Lab has paginated coffee listings and multiple categories.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            # Main coffee page (page 1)
            "https://coffeelab.pl/en/3-coffee",
            # Page 2 of coffee
            "https://coffeelab.pl/en/3-coffee?page=2",
            # We could also scrape specific categories, but the main coffee page
            # seems to include all products across categories
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Coffee Lab.

        Returns:
            List of CoffeeBean objects
        """
        # Use the AI-powered scraping workflow (recommended)
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Static HTML site, no JS needed
                batch_size=2,  # Conservative batch size to be respectful
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

        # Use the base class method with Coffee Lab specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # Coffee Lab URL patterns - products are in different categories
            url_path_patterns=[
                "/en/filter/",
                "/en/espresso/",
                "/en/magic-beans/",
                "/en/brewlab/",
                "/en/cascara/",
                "/en/omniroast/",
            ],
            selectors=[
                # Try specific selectors for Coffee Lab
                'a[href*="/en/filter/"]',
                'a[href*="/en/espresso/"]',
                'a[href*="/en/magic-beans/"]',
                'a[href*="/en/brewlab/"]',
                'a[href*="/en/cascara/"]',
                'a[href*="/en/omniroast/"]',
                # Fallback selectors
                ".product-item a",
                "a.product-link",
            ],
        )

    async def _scrape_traditional(self) -> list[CoffeeBean]:
        """Traditional scraping approach as fallback."""
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
                product_urls = await self._extract_product_urls_from_store(store_url)
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
            # Extract name from page title/heading
            name = None
            name_elem = soup.find("h1")
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            if not name:
                # Fallback to page title
                title_elem = soup.find("title")
                if title_elem:
                    name = title_elem.get_text().split("-")[0].strip()

            if not name:
                return None

            # Extract price - Coffee Lab shows price in PLN
            price = None
            # Look for price elements - might be in different formats
            price_selectors = [
                ".price",
                ".price-current",
                ".product-price",
                '[class*="price"]',
            ]

            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text()
                    if "PLN" in price_text:
                        price = self.extract_price(price_text)
                        if price:
                            break

            # Extract weight - usually 250g, 200g, or 500g
            weight = None
            weight_text = name  # Often weight is in the product name
            if weight_text:
                weight = self.extract_weight(weight_text)

            # Extract origin country - Coffee Lab has structured data
            origin_country = None
            # Look for origin information
            origin_selectors = [
                '[class*="origin"]',
                '[class*="country"]',
                ".product-details",
            ]

            for selector in origin_selectors:
                origin_elem = soup.select_one(selector)
                if origin_elem:
                    origin_text = origin_elem.get_text()
                    if origin_text and len(origin_text.strip()) < 50:  # Reasonable country name length
                        origin_country = self.clean_text(origin_text)
                        break

            # Try to extract from the name if origin not found separately
            if not origin_country and name:
                # Coffee Lab often includes country in product name
                countries = [
                    "Ethiopia",
                    "Brazil",
                    "Colombia",
                    "Guatemala",
                    "Honduras",
                    "Peru",
                    "Kenya",
                    "Rwanda",
                    "Tanzania",
                    "Uganda",
                    "Mexico",
                    "Myanmar",
                    "El Salvador",
                    "Dominican",
                ]
                for country in countries:
                    if country.lower() in name.lower():
                        origin_country = country
                        break

            # Extract tasting notes/flavor profile
            tasting_notes = []
            notes_selectors = [
                '[class*="flavour"]',
                '[class*="flavor"]',
                '[class*="taste"]',
                '[class*="notes"]',
                ".product-description",
            ]

            for selector in notes_selectors:
                notes_elem = soup.select_one(selector)
                if notes_elem:
                    notes_text = notes_elem.get_text()
                    if notes_text and len(notes_text.strip()) < 200:  # Reasonable notes length
                        # Split on common separators
                        if "," in notes_text:
                            tasting_notes = [note.strip() for note in notes_text.split(",")]
                        elif "/" in notes_text:
                            tasting_notes = [note.strip() for note in notes_text.split("/")]
                        else:
                            tasting_notes = [notes_text.strip()]
                        break

            # Extract process method
            process = None
            process_selectors = [
                '[class*="process"]',
                '[class*="method"]',
            ]

            for selector in process_selectors:
                process_elem = soup.select_one(selector)
                if process_elem:
                    process_text = process_elem.get_text().strip()
                    if process_text and len(process_text) < 50:
                        process = process_text
                        break

            # Extract variety
            variety = None
            variety_selectors = [
                '[class*="variety"]',
                '[class*="varietal"]',
            ]

            for selector in variety_selectors:
                variety_elem = soup.select_one(selector)
                if variety_elem:
                    variety_text = variety_elem.get_text().strip()
                    if variety_text and len(variety_text) < 100:
                        variety = variety_text
                        break

            # Extract description
            description = None
            desc_selectors = [
                ".product-description",
                '[class*="description"]',
                ".product-details",
            ]

            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text().strip()
                    if desc_text and len(desc_text) > 50:  # Substantial description
                        description = self.clean_text(desc_text)
                        break

            # Check availability
            in_stock = None
            # Look for add to cart button or stock indicators
            stock_indicators = soup.find_all(string=True)
            stock_text = " ".join(
                [str(text).strip().lower() for text in stock_indicators if text and str(text).strip()]
            )

            if "add to cart" in stock_text or "add to basket" in stock_text:
                in_stock = True
            elif "out of stock" in stock_text or "sold out" in stock_text:
                in_stock = False

            # Create origin object
            from ..schemas.coffee_bean import Origin

            origin_obj = Origin(country=origin_country, region=None, producer=None, farm=None, elevation=0)

            # Create CoffeeBean object
            from pydantic import HttpUrl

            return CoffeeBean(
                name=name,
                roaster="Coffee Lab",
                url=HttpUrl(product_url),
                image_url=None,  # Would need to extract image URL
                origin=origin_obj,
                price=price,
                currency="PLN",
                weight=weight,
                tasting_notes=tasting_notes,
                description=description,
                in_stock=in_stock,
                process=process,
                variety=variety,
                roast_profile=None,  # Would need to determine from product category
                is_decaf=False,  # Default, could be improved by checking name/description
                scraper_version="1.0",
                # Required fields with default values
                is_single_origin=True,  # Most Coffee Lab products appear to be single origin
                harvest_date=None,
                price_paid_for_green_coffee=None,
                currency_of_price_paid_for_green_coffee=None,
                roast_level=None,
                raw_data=None,
            )

        except Exception as e:
            logger.error(f"Traditional extraction failed for {product_url}: {e}")
            return None
