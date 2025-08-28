"""Tanat Coffee scraper.

Scrapes coffee beans from Tanat Coffee (https://tanat.coffee/).
This roaster has multiple pages of products with clear pricing and detailed information.
"""

import logging

from bs4 import BeautifulSoup

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

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Tanat Coffee.

        Returns:
            List of CoffeeBean objects
        """
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Static HTML site, no JavaScript needed
                batch_size=3,  # Conservative batch size for respectful scraping
            )
        else:
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

        # Use the base class method with Tanat Coffee specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/boutique/"],  # Tanat uses /boutique/ for product URLs
            selectors=[
                # Try multiple selectors to catch different page layouts
                'a[href*="/boutique/"]',
                ".product-link",
                ".woocommerce-LoopProduct-link",  # Common WooCommerce selector
                "h3 a",  # Product title links
                ".product-item a",
            ],
        )

    async def _scrape_traditional(self) -> list[CoffeeBean]:
        """Traditional scraping fallback for when AI extraction is not available."""
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

                    if bean and self._is_coffee_product(bean.name):
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
            # Extract name from h1 or title
            name = None
            name_elem = soup.find("h1")
            if name_elem:
                name = self.clean_text(name_elem.get_text())

            if not name:
                # Fallback to page title
                title_elem = soup.find("title")
                if title_elem:
                    title_text = title_elem.get_text()
                    if "|" in title_text:
                        name = title_text.split("|")[0].strip()
                    else:
                        name = title_text.strip()

            if not name:
                return None

            # Extract price - look for Euro symbol and price patterns
            price = None
            price_elements = soup.find_all(text=lambda text: text and "€" in text)
            for price_text in price_elements:
                extracted_price = self.extract_price(price_text)
                if extracted_price:
                    price = extracted_price
                    break

            # Extract origin from tables or text containing country names
            origin = None
            # Look for common coffee-producing countries in the text
            countries = [
                "Colombia",
                "Ethiopia",
                "Brazil",
                "Guatemala",
                "Kenya",
                "Panama",
                "Peru",
                "Bolivia",
                "Tanzania",
                "Jamaica",
                "Yemen",
            ]
            page_text = soup.get_text()
            for country in countries:
                if country in page_text:
                    origin = country
                    break

            # Extract tasting notes - commonly separated by commas, dashes, or pipes
            tasting_notes = []
            # Look for text patterns that might contain tasting notes
            text_content = soup.get_text()
            lines = text_content.split("\n")
            for line in lines:
                line = line.strip()
                # Look for lines with flavor descriptors
                flavor_words = [
                    "chocolate",
                    "vanilla",
                    "cherry",
                    "citrus",
                    "berry",
                    "fruit",
                    "caramel",
                    "honey",
                    "floral",
                ]
                if any(flavor_word in line.lower() for flavor_word in flavor_words):
                    # Clean and split the line
                    if " - " in line:
                        notes = [note.strip() for note in line.split(" - ")]
                        tasting_notes.extend([note for note in notes if note and len(note) < 50])
                    elif ", " in line:
                        notes = [note.strip() for note in line.split(", ")]
                        tasting_notes.extend([note for note in notes if note and len(note) < 50])
                    break

            # Extract description from paragraphs
            description = None
            description_elem = soup.find("p")
            if description_elem:
                desc_text = description_elem.get_text().strip()
                if len(desc_text) > 50:  # Only use substantial descriptions
                    description = self.clean_text(desc_text)

            # Basic availability check
            in_stock = True  # Default to in stock
            if any(text in soup.get_text().lower() for text in ["out of stock", "sold out", "unavailable"]):
                in_stock = False

            # Create basic origin object
            from ..schemas.coffee_bean import Bean

            origin_obj = Bean(country=origin, region=None, producer=None, farm=None, elevation=0)

            # Create CoffeeBean object
            from pydantic import HttpUrl

            return CoffeeBean(
                name=name,
                roaster="Tanat Coffee",
                url=HttpUrl(product_url),
                origin=origin_obj,
                price=price,
                currency="EUR",
                weight=None,  # Will be extracted by AI if available
                tasting_notes=tasting_notes[:5],  # Limit to first 5 notes
                description=description,
                in_stock=in_stock,
                scraper_version="1.0",
                # Required fields with default values
                is_single_origin=True,  # Most specialty coffees are single origin
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
        """Check if this product is actually coffee beans (not equipment/subscriptions)."""
        if not name:
            return False

        name_lower = name.lower()

        # Exclude non-coffee products
        excluded_terms = [
            "equipment",
            "grinder",
            "machine",
            "filter",
            "cup",
            "mug",
            "subscription",
            "book",
            "merchandise",
            "cascara",
            "tea",
        ]

        for term in excluded_terms:
            if term in name_lower:
                return False

        return True
