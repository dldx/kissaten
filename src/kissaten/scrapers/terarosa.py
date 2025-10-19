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
            roaster_name="Terarosa Coffee",
            base_url="https://www.terarosa.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        homepage = await self.fetch_page("https://www.terarosa.com/product/list/?category=12", use_playwright=True)
        if not homepage:
            logger.error("Failed to fetch Terarosa homepage for store URLs")
            return []
        return [
            self.base_url + str(el["href"])
            for el in homepage.select(".pd_category")[0].select("a")
            if "싱글오리진" in el.text or "블렌드" in el.text or "디카페인" in el.text
        ]

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

        # Extract all product URLs
        all_product_urls_el = soup.select('a.btnViewDetail[href*="/product/"]')

        # Filter out non-coffee products (merch, equipment, etc.)
        coffee_urls = []
        for el in all_product_urls_el:
            coffee_urls.append(f"{self.base_url}{el['href']}")
        coffee_urls += [
            ("https://www.terarosa.com/product/detail/?ItemCode=" + el.get("onclick", "").split("'")[1])
            for el in soup.select("p[onclick*='goView']")
        ]
        coffee_urls = list(set(coffee_urls))  # Deduplicate

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls_el)} total products")
        return coffee_urls
