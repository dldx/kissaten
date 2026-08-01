"""Terarosa Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="terarosa",
    display_name="Terarosa",
    roaster_name="Terarosa",
    website="https://www.terarosa.com",
    description="Speciality coffee roastery based in South Korea.",
    requires_api_key=True,
    currency="KRW",
    country="South Korea",
    status="available",
)
class TerarosaCoffeeScraper(BaseScraper):
    """Scraper for Terarosa Coffee (terarosa.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Terarosa Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Terarosa",  # Must match registry roaster_name
            base_url="https://www.terarosa.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Discovers the current coffee sub-categories from the ``ol`` inside
        ``div.category.pd_category`` on the listing page, instead of relying
        on a hardcoded list of Korean category names. ``전체보기`` (View All)
        is skipped because it points back at the parent page we just fetched.

        Returns:
            List of category listing URLs.
        """
        homepage = await self.fetch_page(
            "https://www.terarosa.com/product/list/?category=12", use_playwright=True
        )
        if not homepage:
            logger.error("Failed to fetch Terarosa homepage for store URLs")
            return []

        store_urls = []
        for el in homepage.select("div.category.pd_category ol li a"):
            if el.text.strip() == "전체보기":
                continue
            store_urls.append(self.base_url + str(el["href"]))
        return store_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
            use_optimized_mode=True,
            translate_to_english=True,  # Translate Korean content to English
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []

        # The product grid is <ul id="itemList" class="productBox">; each
        # product <li> carries a wishlist <a data-key="ItemCode">. Using
        # data-key (rather than the old goView onclick) avoids duplicates
        # (the image and the info card each render their own onclick).
        product_urls = [
            f"https://www.terarosa.com/product/detail/?ItemCode={a['data-key']}"
            for a in soup.select("#itemList a[data-key]")
            if a.get("data-key")
        ]

        logger.info(f"Found {len(product_urls)} coffee product URLs from {store_url}")
        return product_urls
