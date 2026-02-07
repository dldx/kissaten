"""Workshop Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@register_scraper(
    name="workshop-coffee",
    display_name="Workshop Coffee",
    roaster_name="Workshop Coffee",
    website="https://workshopcoffee.com",
    description="Specialty coffee roaster focused on long-term relationships with producers based in London, UK",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class WorkshopCoffeeScraper(BaseScraper):
    """Scraper for Workshop Coffee (workshopcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Workshop Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Workshop Coffee",
            base_url="https://workshopcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs
        """
        return [
            "https://workshopcoffee.com/collections/house-blends",
            "https://workshopcoffee.com/collections/single-origin",
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
            use_playwright=True,
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return its BeautifulSoup object.

        Args:
            url: URL of the page to fetch
            use_playwright: Whether to use Playwright for fetching

        Returns:
            BeautifulSoup object of the page, or None if fetch failed
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            if "/products" not in (url or ""):
                return soup  # Only modify product pages
            # Remove unneeded sections
            unneeded_sections = [
                "section[id*='related_product_slider']",
                "div[id*='judge_me_reviews_review_widget']",
            ]
            for section in unneeded_sections:
                product_section = soup.select(section)
                logger.info(f"Found {len(product_section)} sections matching {section}")
                if len(product_section) > 0:
                    product_section[0].decompose()
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    def _get_excluded_url_patterns(self) -> list[str]:
        patterns = super()._get_excluded_url_patterns()
        # Remove workshop from patterns
        patterns.remove("workshop")
        return patterns

    def _get_excluded_product_name_categories(self) -> list[str]:
        patterns = super()._get_excluded_product_name_categories()
        patterns.remove("workshop")
        return patterns

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        custom_selectors = [
            'a[href*="/products/"][id*="CardLink-template"]',
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        excluded_products = [
            "subscription",
            "gift-card",
            "gift",
            "tasting-pack",
            "collection-box"
        ]
        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
