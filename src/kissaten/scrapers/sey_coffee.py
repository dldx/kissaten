"""Sey Coffee scraper.

Brooklyn-based specialty coffee roaster known for exceptional sourcing,
price transparency, and detailed producer partnerships.
"""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sey-coffee",
    display_name="Sey Coffee",
    roaster_name="Sey Coffee",
    website="https://www.seycoffee.com",
    description="Brooklyn-based specialty coffee roaster known for exceptional "
    "sourcing and price transparency",
    requires_api_key=True,  # Using AI extraction for best results
    currency="USD",
    country="United States",
    status="available",
)
class SeyCoffeeScraper(BaseScraper):
    """Scraper for Sey Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Sey Coffee",
            base_url="https://www.seycoffee.com",
            rate_limit_delay=1.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for complex custom sites)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            "https://www.seycoffee.com/collections/coffee",
            "https://www.seycoffee.com/collections/archived-coffees",
        ]


    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
        )

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Extract bean data with canonical URL check to avoid duplicates."""
        # Predict canonical URL from slug
        try:
            slug = product_url.split("/products/")[-1].split("?")[0].rstrip("/")
        except (IndexError, AttributeError):
            # Fallback to base class behavior if URL structure is unexpected
            return await super()._extract_bean_with_ai(
                ai_extractor, soup, product_url, use_optimized_mode, translate_to_english
            )
            
        canonical_url = f"https://www.seycoffee.com/products/{slug}"
        coffee_url = f"https://www.seycoffee.com/collections/coffee/products/{slug}"

        # If we already have this bean under any variation, skip
        if (self._is_bean_already_scraped_anywhere(canonical_url) or 
            self._is_bean_already_scraped_anywhere(coffee_url) or
            self._is_bean_already_scraped_anywhere(product_url)):
            logger.info(f"Skipping {product_url} as it is already in historical data")
            return None

        # Proceed with AI extraction
        bean = await super()._extract_bean_with_ai(
            ai_extractor,
            soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )

        if bean:
            # If the bean is in the archive, it's out of stock
            if "/collections/archived-coffees/" in product_url:
                bean.in_stock = False
                logger.info(f"Marked {product_url} as out of stock (archived)")

            # Update bean URL to canonical and mark as scraped
            bean.url = canonical_url
            self._mark_bean_as_scraped(canonical_url)

        return bean

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page with slug-based deduplication."""
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Load historical data to enable skip checks before fetching product pages
        from pathlib import Path
        self._load_existing_beans_from_all_sessions(Path("data"))

        # Use the base class method with custom site patterns
        raw_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
                ".collection-item a",
                "h3 a",
                ".coffee-card a",
            ],
        )

        excluded_products = [
            "subscription", "gift-card", "gift", "wholesale", 
            "equipment", "accessory", "merchandise", "test-roast", "recurring"
        ]
        
        is_archive = "archived-coffees" in store_url
        filtered_urls = []
        
        for url in raw_urls:
            if not url or not isinstance(url, str):
                continue
            if any(excluded in url.lower() for excluded in excluded_products):
                continue
            
            # Extract slug from URL to determine canonical form
            try:
                slug = url.split("/products/")[-1].split("?")[0].rstrip("/")
            except (IndexError, AttributeError):
                continue
            if not slug:
                 continue
            
            canonical_url = f"https://www.seycoffee.com/products/{slug}"
            coffee_url = f"https://www.seycoffee.com/collections/coffee/products/{slug}"
            
            # Find which URL variation (if any) is already in our historical data
            matched_url = None
            if self._is_bean_already_scraped_anywhere(canonical_url):
                matched_url = canonical_url
            elif self._is_bean_already_scraped_anywhere(coffee_url):
                matched_url = coffee_url
            elif self._is_bean_already_scraped_anywhere(url):
                matched_url = url
            
            if is_archive:
                if matched_url:
                    # Archived and already known - skip. 
                    # Base scraper will mark it out-of-stock because it's missing from live collections.
                    continue
                else:
                    # New archived product - keep it for extraction (will be marked out-of-stock)
                    filtered_urls.append(url)
            else:
                # Live product - use existing URL to allow efficient stock updates, or canonical if new
                if matched_url:
                    filtered_urls.append(matched_url)
                else:
                    filtered_urls.append(canonical_url)

        return self.deduplicate_urls(filtered_urls)
