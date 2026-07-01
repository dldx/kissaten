"""Kaffa Roastery (Slovakia) scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kaffa-sk",
    display_name="Kaffa Roastery SK",
    roaster_name="Kaffa (SK)",
    website="https://kaffaroastery.sk",
    description="Slovak specialty coffee roastery based in Bratislava, offering filter coffees, "
    "espresso blends, and limited edition single origins",
    requires_api_key=True,
    currency="EUR",
    country="Slovakia",
    status="available",
)
class KaffaSKScraper(BaseScraper):
    """Scraper for Kaffa Roastery Slovakia (kaffaroastery.sk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kaffa (SK) scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kaffa (SK)",
            base_url="https://kaffaroastery.sk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the shop listing URLs (paginated).
        """
        return [
            "https://kaffaroastery.sk/shop/",
            "https://kaffaroastery.sk/shop/?upage=2",
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
            use_optimized_mode=False,
            translate_to_english=True,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a shop listing page.

        The kaffaroastery.sk shop is a WooCommerce-backed WordPress site that
        mixes coffee and merchandise (caps, t-shirts) on the same listing. The
        stock status is not shown on the listing, so the only filtering happens
        at the URL level to exclude non-coffee merchandise.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs that look like coffee products
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Sold-out detection: not exposed on the listing (no class or text
        # indicator for stock status on the shop grid), so we cannot filter at
        # the URL level. The AI extractor will return None for products whose
        # detail page has no buyable state, and the diffjson stock-update flow
        # handles products that disappear from the listing.
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/produkt/"],
            selectors=[
                'a[href*="/produkt/"]',
                '.t-entry-visual-tc a',
                'a.pushed',
            ],
        )

        # Strip WooCommerce media_link query param so URLs are canonical, then
        # dedup: each product card has the same href twice (image link with
        # ?media_link=1 + title link without), and we want to extract each bean
        # exactly once.
        product_urls = list(dict.fromkeys(url.split("?")[0] for url in product_urls))

        # Filter out merchandise (caps, t-shirts, hoodies, bags) - the site lists
        # apparel alongside coffee on /shop/
        excluded_products = [
            "siltovka",  # Caps
            "tricko",  # T-shirts
            "tričko",  # T-shirts (Slovak diacritics)
            "mikina",  # Hoodies
            "hoodie",
            "taška",  # Bags
            "taska",  # Bags (Slovak diacritics)
            "-vak",  # Bags (e.g. only-good-kaffa-vak)
            "vak",  # Bags (standalone)
            "merch",
            "gift-card",
            "darček",  # Gift (Slovak)
            "darcek",  # Gift (no diacritics)
            "predplatne",  # Subscription
            "subscription",
        ]

        filtered_urls = []
        for url in product_urls:
            url_lower = url.lower()
            if any(excluded in url_lower for excluded in excluded_products):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue
            filtered_urls.append(url)

        logger.info(
            f"Found {len(filtered_urls)} coffee product URLs out of {len(product_urls)} total on {store_url}"
        )
        return filtered_urls
