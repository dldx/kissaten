"""Rounton Coffee scraper implementation.

Rounton Coffee Roasters is a specialty coffee roastery based in North Yorkshire, UK.
They focus on sustainable sourcing and are proud members of 1% for the planet.
"""

import logging

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rounton-coffee",
    display_name="Rounton Coffee",
    roaster_name="Rounton Coffee Roasters",
    website="https://rountoncoffee.co.uk",
    description="Specialty coffee roastery from North Yorkshire, focusing on sustainable sourcing",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RountonCoffeeScraper(BaseScraper):
    """Scraper for Rounton Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Rounton Coffee Roasters",
            base_url="https://rountoncoffee.co.uk",
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
            "https://rountoncoffee.co.uk/collections/coffee",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Rounton Coffee.

        Returns:
            List of CoffeeBean objects
        """
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Shopify sites usually work fine with httpx
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

        product_urls = []

        # Custom extraction for Rounton Coffee to handle URL spaces properly
        selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link",
            ".grid-product__link",
            "a.product-title",
        ]

        for selector in selectors:
            try:
                links = soup.select(selector)
                if links:
                    for link in links:
                        href = link.get("href")
                        if href and isinstance(href, str):
                            # Clean the href to remove any leading/trailing spaces
                            href = href.strip()

                            # Ensure it's a product URL
                            if "/products/" in href:
                                # Resolve to full URL, making sure to clean it
                                if href.startswith("/"):
                                    full_url = f"{self.base_url}{href}"
                                else:
                                    full_url = href

                                # Final cleanup to remove any spaces
                                full_url = full_url.replace(" ", "")

                                # Filter out non-coffee products
                                if self.is_coffee_product_url(full_url, ["/products/"]):
                                    product_urls.append(full_url)
                    break  # Use first successful selector
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Extracted {len(unique_urls)} product URLs from {store_url}")
        if unique_urls:
            logger.debug(f"Sample URLs: {unique_urls[:3]}")

        return unique_urls

    async def _extract_bean_with_ai(
        self, ai_extractor, soup: BeautifulSoup, product_url: str, use_optimized_mode: bool = False
    ) -> CoffeeBean | None:
        """Extract coffee bean data using AI.

        Args:
            ai_extractor: AI extractor instance
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            use_optimized_mode: Whether to use optimized mode (with screenshots)

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Get the HTML content for AI processing
            html_content = str(soup)

            # Use AI extractor to get structured data
            if use_optimized_mode:
                # For complex sites that benefit from visual analysis
                screenshot_bytes = await self.take_screenshot(product_url)
                bean: CoffeeBean = await ai_extractor.extract_coffee_data(
                    html_content, product_url, screenshot_bytes, use_optimized_mode=True
                )
            else:
                # Standard mode for most sites (Rounton Coffee appears well-structured)
                bean: CoffeeBean = await ai_extractor.extract_coffee_data(html_content, product_url)

            # if we don't have country and process and variety, then we probably don't have a valid bean
            if not bean.origins[0].country and not bean.origins[0].process and not bean.origins[0].variety:
                logger.warning(f"Failed to extract data from {product_url}")
                return None

            if bean:
                # Ensure correct roaster details
                bean.roaster = "Rounton Coffee Roasters"
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
            # Extract name (required)
            name = None
            name_selectors = [
                "h1.product-title",
                "h1",
                ".product-meta h1",
                ".product__title",
                ".product-single__title",
            ]

            for selector in name_selectors:
                name_elem = soup.select_one(selector)
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
                ".product-single__price",
            ]

            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price = self.extract_price(price_elem.get_text())
                    if price:
                        break

            # Extract weight - Rounton Coffee typically uses 250g and 1kg
            weight = None
            weight_selectors = [
                ".product-form__option",
                ".variant-option",
                ".size-option",
                ".product-single__variant",
            ]

            for selector in weight_selectors:
                weight_elems = soup.select(selector)
                for elem in weight_elems:
                    weight_text = elem.get_text()
                    if weight_text and ("250g" in weight_text or "1kg" in weight_text):
                        weight = self.extract_weight(weight_text)
                        if weight:
                            break
                if weight:
                    break

            # Default to 250g if not found (common size for Rounton Coffee)
            if not weight:
                weight = 250

            # Extract origin from product title or description
            origin = None
            if name:
                # Common origin countries
                origin_countries = [
                    "Colombia", "Ethiopia", "Brazil", "Guatemala", "Kenya",
                    "Rwanda", "Honduras", "Peru", "Panama", "Costa Rica",
                    "Uganda", "El Salvador", "Zambia"
                ]
                for country in origin_countries:
                    if country.lower() in name.lower():
                        origin = country
                        break

            # Extract tasting notes
            tasting_notes = []
            taste_selectors = [
                ".taste-notes",
                ".tasting-notes",
                ".flavor-notes",
                ".product-description",
                ".product-single__description",
            ]

            for selector in taste_selectors:
                taste_elem = soup.select_one(selector)
                if taste_elem:
                    taste_text = taste_elem.get_text()
                    # Look for patterns like "Chocolate, Hazelnut, Caramel"
                    if "," in taste_text:
                        notes = [note.strip() for note in taste_text.split(",")]
                        tasting_notes = [note for note in notes if note and len(note) > 2]
                        break

            # Extract description
            description = None
            desc_selectors = [
                ".product-description",
                ".product__description",
                ".rte",
                ".description",
                ".product-single__description",
            ]

            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
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
                ".product-single__add-to-cart",
            ]

            for selector in stock_selectors:
                stock_elem = soup.select_one(selector)
                if stock_elem:
                    button_text = stock_elem.get_text().lower()
                    in_stock = "sold out" not in button_text and "out of stock" not in button_text
                    break

            # Create basic origin object
            from ..schemas.coffee_bean import Bean

            origin_obj = [
                Bean(
                    country=origin,
                    region=None,
                    producer=None,
                    farm=None,
                    elevation=0,
                    latitude=None,
                    longitude=None,
                    process=None,
                    variety=None,
                    harvest_date=None,
                )
            ]

            return CoffeeBean(
                name=name,
                roaster="Rounton Coffee Roasters",
                url=HttpUrl(product_url),
                image_url=None,
                origins=origin_obj,
                is_single_origin=True,  # Most specialty coffee is single origin
                price_paid_for_green_coffee=None,
                currency_of_price_paid_for_green_coffee=None,
                roast_level=None,
                roast_profile=None,
                weight=weight,
                is_decaf="decaf" in name.lower(),
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
