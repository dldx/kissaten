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
        product_urls = self.extract_product_urls_from_soup(
            limited_soup,
            url_path_patterns=["/products/"],
            selectors=[
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
                ".grid-product__link",
            ],
        )
        # Filter out excluded products
        excluded_products = [
            "discovery",  # Sample pack
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return product_urls

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
