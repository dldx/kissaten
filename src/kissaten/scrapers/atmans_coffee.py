"""atmans Coffee scraper for extracting coffee bean information.

atmans Coffee is a specialty coffee roaster based in Barcelona, Spain.
They offer curated selection of specialty coffees from around the world,
focusing on Process, Origin and Variety (POV).
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
    name="atmans-coffee",
    display_name="atmans Coffee",
    roaster_name="atmans Coffee",
    website="https://www.atmanscoffee.com",
    description="Specialty coffee roaster based in Barcelona, Spain with curated selection focusing on POV",
    requires_api_key=True,
    currency="EUR",
    country="Spain",
    status="available",
)
class AtmansCoffeeScraper(BaseScraper):
    """Scraper for atmans Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="atmans Coffee",
            base_url="https://www.atmanscoffee.com",
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
            "https://www.atmanscoffee.com/en/collections/all-coffees",
            # Check if there are more pages by looking at pagination
            "https://www.atmanscoffee.com/en/collections/all-coffees?page=2",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from atmans Coffee.

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
        logger.warning("AI extractor not available - traditional scraping not implemented for atmans Coffee")
        return []

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page, focusing on filter-container.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # First, try to find the filter-container element
        filter_container = soup.find("filter-container")
        if filter_container:
            logger.debug("Found filter-container, extracting products from it")
            # Create a new BeautifulSoup object from the filter-container
            from bs4 import BeautifulSoup
            filter_soup = BeautifulSoup(str(filter_container), "lxml")
            # Extract URLs specifically from the filter-container
            return self.extract_product_urls_from_soup(
                filter_soup,
                url_path_patterns=["/products/"],
                selectors=[
                    'a[href*="/products/"]',
                    ".product-item a",
                    ".product-link",
                    ".grid-product__link",
                    ".product-card a",
                    ".product-title a",
                ],
            )
        else:
            logger.warning("filter-container not found, using full page")
            # Fallback to full page if filter-container not found
            return self.extract_product_urls_from_soup(
                soup,
                url_path_patterns=["/products/"],
                selectors=[
                    'a[href*="/products/"]',
                    ".product-item a",
                    ".product-link",
                    ".grid-product__link",
                    ".product-card a",
                    ".product-title a",
                ],
            )

    async def _extract_bean_with_ai(
        self, ai_extractor, soup: BeautifulSoup, product_url: str, use_optimized_mode: bool = False
    ) -> CoffeeBean | None:
        """Extract coffee bean information using AI with custom product description extraction.

        Args:
            ai_extractor: AI extractor instance
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            use_optimized_mode: Whether to use optimized mode (with screenshots)

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Extract the main product description specifically
            main_product_section = soup.select_one("div.section-main-product")
            if main_product_section:
                # Use only the main product section for better AI extraction
                html_content = str(main_product_section)
            else:
                # Fallback to full page content
                html_content = str(soup)

            # Use AI extractor to get structured data
            if use_optimized_mode:
                # For complex sites that benefit from visual analysis
                screenshot_bytes = await self.take_screenshot(product_url)
                bean = await ai_extractor.extract_coffee_data(
                    html_content, product_url, screenshot_bytes, use_optimized_mode=True
                )
            else:
                # Standard mode for most sites
                bean = await ai_extractor.extract_coffee_data(html_content, product_url)

            if bean:
                # Ensure correct roaster details
                bean.roaster = "atmans Coffee"
                bean.currency = "EUR"
                logger.debug(f"AI extracted: {bean.name} from {bean.origin}")
                return bean

            return None

        except Exception as e:
            logger.error(f"AI extraction failed for {product_url}: {e}")
            return None

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
            # Look for price elements in various formats
            price_selectors = [
                ".price",
                ".money",
                '[class*="price"]',
                '[data-price]',
            ]

            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text()
                    if "£" in price_text or "€" in price_text or "$" in price_text:
                        price = self.extract_price(price_text)
                        break

            # Extract description from main product section if available
            description = None
            main_section = soup.find("div", class_="section-main-product")
            if main_section:
                # Get text from the main section
                description = self.clean_text(main_section.get_text())
            else:
                # Fallback to other description elements
                desc_selectors = [
                    ".product-description",
                    ".product-single__description",
                    ".rte",
                    ".description",
                ]
                for selector in desc_selectors:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        description = self.clean_text(desc_elem.get_text())
                        break

            # Check stock availability
            in_stock = True
            page_text = soup.get_text().lower()
            if any(phrase in page_text for phrase in ["sold out", "out of stock", "agotado"]):
                in_stock = False

            # Detect currency
            currency = "EUR"  # Default for Spain
            page_text = soup.get_text()
            if "£" in page_text:
                currency = "GBP"
            elif "$" in page_text:
                currency = "USD"

            # Create a basic origin object
            origin = Bean(
                country=None,
                region=None,
                producer=None,
                farm=None,
                elevation=0,
                process=None,
                variety=None,
                harvest_date=None,
                latitude=None,
                longitude=None,
            )

            # Create CoffeeBean object with required fields
            return CoffeeBean(
                name=name,
                roaster="atmans Coffee",
                url=HttpUrl(product_url),
                image_url=None,
                is_single_origin=True,
                price_paid_for_green_coffee=None,
                currency_of_price_paid_for_green_coffee=None,
                roast_level=None,
                roast_profile=None,
                weight=None,
                price=price,
                currency=currency,
                is_decaf=False,
                tasting_notes=[],
                description=description,
                in_stock=in_stock,
                scraper_version="1.0",
                raw_data=None,
                origins=[origin],
                cupping_score=None,
            )

        except Exception as e:
            logger.error(f"Traditional extraction failed for {product_url}: {e}")
            return None
