"""Assembly Coffee scraper implementation.

Assembly Coffee is a specialty coffee roastery based in Brixton, London, UK.
They focus on single-origin coffees and are known for their sustainable practices.
"""

import logging

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="assembly-coffee",
    display_name="Assembly Coffee",
    roaster_name="Assembly Coffee London",
    website="https://assemblycoffee.co.uk",
    description="Award-winning specialty coffee roastery founded in 2015 and based in Brixton, London",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AssemblyCoffeeScraper(BaseScraper):
    """Scraper for Assembly Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Assembly Coffee London",
            base_url="https://assemblycoffee.co.uk",
            rate_limit_delay=1.5,  # Be respectful to the site
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
            List containing the coffee collection URLs
        """
        return [
            f"https://assemblycoffee.co.uk/collections/buy-coffee?page={i}"
            for i in range(1, 5)  # Scrape first 4 pages
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Assembly Coffee.

        Returns:
            List of CoffeeBean objects
        """
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Shopify sites usually work fine with httpx
                batch_size=2,  # Conservative batch size to be respectful
            )

        # Fallback to traditional scraping if AI is not available
        return await self._scrape_traditional()

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page, limited to div.collectionGrid-container.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Limit extraction to the collection grid container as requested
        collection_grid = soup.find("div", class_="collectionGrid-container")
        if collection_grid:
            # Create a new soup object with just the collection grid content
            limited_soup = BeautifulSoup(str(collection_grid), 'html.parser')
            logger.debug(f"Limiting product extraction to div.collectionGrid-container for {store_url}")
        else:
            # Fallback to full page if container not found
            limited_soup = soup
            logger.warning(f"div.collectionGrid-container not found, using full page for {store_url}")

        # Use the base class method with Assembly Coffee's URL patterns
        return self.extract_product_urls_from_soup(
            limited_soup,
            url_path_patterns=["/products/"],
            selectors=[
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
                ".grid-product__link",
            ],
        )

    async def _extract_bean_with_ai(
        self, ai_extractor, soup: BeautifulSoup, product_url: str, use_optimized_mode: bool = False
    ) -> CoffeeBean | None:
        """Extract coffee bean data using AI, limiting to article tag content.

        Args:
            ai_extractor: AI extractor instance
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            use_optimized_mode: Whether to use optimized mode (with screenshots)

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Limit extraction to the <article> tag as requested
            article_tag = soup.find("article")
            if article_tag:
                # Create a new soup object with just the article content
                limited_soup = BeautifulSoup(str(article_tag), 'html.parser')
                logger.debug(f"Limiting extraction to <article> tag for {product_url}")
            else:
                # Fallback to main content area if no article tag
                main_content = soup.find("main") or soup.find("div", class_="main-content")
                if main_content:
                    limited_soup = BeautifulSoup(str(main_content), 'html.parser')
                    logger.debug(f"No <article> tag found, using main content for {product_url}")
                else:
                    # Last resort: use full page content
                    limited_soup = soup
                    logger.warning(f"No <article> or main content found, using full page for {product_url}")

            # Get the HTML content for AI processing
            html_content = str(limited_soup)

            # Use AI extractor to get structured data
            if use_optimized_mode:
                # For complex sites that benefit from visual analysis
                screenshot_bytes = await self.take_screenshot(product_url)
                bean: CoffeeBean = await ai_extractor.extract_coffee_data(
                    html_content, product_url, screenshot_bytes, use_optimized_mode=True
                )
            else:
                # Standard mode for most sites (Assembly Coffee appears well-structured)
                bean: CoffeeBean = await ai_extractor.extract_coffee_data(html_content, product_url)

            if bean:
                # Ensure correct roaster details
                bean.roaster = "Assembly Coffee London"
                bean.currency = "GBP"
                return bean

        except Exception as e:
            logger.error(f"AI extraction failed for {product_url}: {e}")

        return None

    async def _scrape_traditional(self) -> list[CoffeeBean]:
        """Traditional fallback scraping method."""
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

                    # Traditional extraction
                    bean = await self._extract_traditional_bean(product_soup, product_url)

                    if bean and self.is_coffee_product_name(bean.name):
                        coffee_beans.append(bean)
                        logger.debug(f"Extracted: {bean.name}")

            session.beans_found = len(coffee_beans)
            session.beans_processed = len(coffee_beans)

            self.end_session(success=True)

        except Exception as e:
            logger.error(f"Error during traditional scraping: {e}")
            session.add_error(f"Scraping error: {e}")
            self.end_session(success=False)
            raise

        return coffee_beans

    async def _extract_traditional_bean(self, soup: BeautifulSoup, product_url: str) -> CoffeeBean | None:
        """Extract coffee bean information using traditional CSS selectors.

        Args:
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Limit to article tag content as requested
            article_tag = soup.find("article")
            if article_tag:
                working_soup = BeautifulSoup(str(article_tag), 'html.parser')
            else:
                working_soup = soup

            # Extract name (required)
            name = None
            name_selectors = [
                "h1.product-title",
                "h1",
                ".product-meta h1",
                ".product__title",
            ]

            for selector in name_selectors:
                name_elem = working_soup.select_one(selector)
                if name_elem:
                    name = self.clean_text(name_elem.get_text())
                    if name:
                        break

            if not name:
                return None

            # Extract price
            price = None
            price_selectors = [
                ".price",
                ".product-price",
                ".money",
                "[data-price]",
                ".price-current",
            ]

            for selector in price_selectors:
                price_elem = working_soup.select_one(selector)
                if price_elem:
                    price = self.extract_price(price_elem.get_text())
                    if price:
                        break

            # Extract weight - Assembly Coffee typically uses 200g and 1kg
            weight = None
            weight_selectors = [
                ".product-form__option",
                ".variant-option",
                ".size-option",
            ]

            for selector in weight_selectors:
                weight_elems = working_soup.select(selector)
                for elem in weight_elems:
                    weight_text = elem.get_text()
                    if weight_text and ("200g" in weight_text or "1kg" in weight_text):
                        weight = self.extract_weight(weight_text)
                        if weight:
                            break
                if weight:
                    break

            # Default to 200g if not found (common size for Assembly Coffee)
            if not weight:
                weight = 200

            # Extract origin from product title or description
            origin = None
            if name:
                # Try to extract country from name (e.g., "Colombia — Deyanira Avendaño")
                if "—" in name or "–" in name:
                    parts = name.replace("—", "–").split("–")[0].strip()
                    # Common origin countries
                    origin_countries = [
                        "Colombia", "Ethiopia", "Brazil", "Guatemala", "Kenya",
                        "Rwanda", "Honduras", "Peru", "Panama", "Costa Rica"
                    ]
                    for country in origin_countries:
                        if country.lower() in parts.lower():
                            origin = country
                            break

            # Extract tasting notes
            tasting_notes = []
            taste_selectors = [
                ".taste-notes",
                ".tasting-notes",
                ".flavor-notes",
                ".product-description",
            ]

            for selector in taste_selectors:
                taste_elem = working_soup.select_one(selector)
                if taste_elem:
                    taste_text = taste_elem.get_text()
                    # Look for patterns like "Orange + Macadamia nut + Creamy"
                    if "+" in taste_text:
                        notes = [note.strip() for note in taste_text.split("+")]
                        tasting_notes = [note for note in notes if note and len(note) > 2]
                        break

            # Extract description
            description = None
            desc_selectors = [
                ".product-description",
                ".product__description",
                ".rte",
                ".description",
            ]

            for selector in desc_selectors:
                desc_elem = working_soup.select_one(selector)
                if desc_elem:
                    description = self.clean_text(desc_elem.get_text())
                    if description:
                        break

            # Check availability
            in_stock = None
            stock_selectors = [
                ".product-form__cart-submit",
                ".btn-product-add",
                ".add-to-cart",
                "button[name='add']",
            ]

            for selector in stock_selectors:
                stock_elem = working_soup.select_one(selector)
                if stock_elem:
                    button_text = stock_elem.get_text().lower()
                    in_stock = "sold out" not in button_text and "out of stock" not in button_text
                    break

            # Create basic origin object
            from ..schemas.coffee_bean import Origin
            origin_obj = Origin(country=origin, region=None, producer=None, farm=None, elevation=0)

            return CoffeeBean(
                name=name,
                roaster="Assembly Coffee London",
                url=HttpUrl(product_url),
                image_url=None,
                origin=origin_obj,
                is_single_origin=True,  # Most specialty coffee is single origin
                process=None,
                variety=None,
                harvest_date=None,
                price_paid_for_green_coffee=None,
                currency_of_price_paid_for_green_coffee=None,
                roast_level=None,
                roast_profile=None,
                weight=weight,
                is_decaf=False,
                price=price,
                currency="GBP",
                tasting_notes=tasting_notes,
                description=description,
                in_stock=in_stock,
                cupping_score=None,
                scraper_version="1.0",
                raw_data=None,
            )

        except Exception as e:
            logger.error(f"Traditional extraction failed for {product_url}: {e}")
            return None
