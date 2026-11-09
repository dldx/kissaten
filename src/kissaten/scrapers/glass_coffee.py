"""Elsewhere Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="glass-coffee",
    display_name="Glass Coffee",
    roaster_name="Glass Coffee",
    website="https://glasscoffee.co.uk",
    description="Specialty coffee roaster based in Camden, UK",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class GlassCoffeeScraper(BaseScraper):
    """Scraper for Glass Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Glass Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Glass Coffee",
            base_url="https://glasscoffee.co.uk",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee category URL
        """
        # Plain collection URL: the ``?filter.v.availability=1`` variant renders
        # an empty grid on page 2 and the ``#coffee`` fragment is inert, so the
        # unfiltered listing (one page, all products) is the robust choice.
        # Sold-out products are filtered client-side in
        # _extract_product_urls_from_store.
        return ["https://glasscoffee.co.uk/collections/coffee"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
        )

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

        # Extract all product URLs using the base class method
        product_grids = soup.select(".product-grid")
        if not product_grids:
            logger.warning(f"No product grid found on store page: {store_url}")
            return []
        # Current theme renders product cards as ``<a class="product-card"
        # id="CardLink-template--...">`` inside ``.product-card-wrapper``
        # (previously the link carried an ``aria-labelledby`` attribute).
        all_product_url_el = soup.select('.product-grid a.product-card[href*="/products/"]')
        all_product_urls = []
        seen_urls = set()
        for el in all_product_url_el:
            if "Sold out" in el.parent.text:
                continue
            product_url = f"{self.base_url}{el['href'].split('?')[0]}"
            if product_url not in seen_urls:
                seen_urls.add(product_url)
                all_product_urls.append(product_url)

        # Filter coffee products using base class method
        excluded_patterns = []
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                pattern in url for pattern in excluded_patterns
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
