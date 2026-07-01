"""miró manufactura de café scraper implementation with AI-powered extraction."""

import logging

from bs4 import Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="miro-manufactura",
    display_name="miró manufactura de café",
    roaster_name="miró manufactura de café",
    website="https://mirocoffee.co",
    description="Specialty coffee roaster in Zürich, Switzerland offering single-origin "
    "coffees from Latin America, Africa, and beyond",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class MiroManufacturaScraper(BaseScraper):
    """Scraper for miró manufactura de café (mirocoffee.co) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize miró manufactura de café scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="miró manufactura de café",
            base_url="https://mirocoffee.co",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://mirocoffee.co/shop/coffee/"]

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
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force currency to CHF since the site doesn't expose it via meta tags."""
        bean.currency = "CHF"
        return super().postprocess_extracted_bean(bean)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the miró coffee archive page.

        The page is a WooCommerce product category archive. Each product is
        rendered server-side inside a ``<li class="TeaserGrid--item product ...">``
        element. WooCommerce adds the token ``outofstock`` to that class list
        when a product is no longer purchasable — we use that as the sold-out
        signal before any URL filtering.

        Args:
            store_url: URL of the store page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Sold-out detection: class — WooCommerce emits `outofstock` (no hyphen)
        # as a class token on the product <li>. Walk only the product list, before
        # running is_coffee_product_url, so excluded products can't leak past
        # the stock check.
        product_urls: list[str] = []
        excluded_products = [
            "giftcard",  # WooCommerce gift card SKU
            "gift-card",  # Base pattern variant
            "subscription",  # Subscription SKUs
            "course",  # Brewing courses
            "workshop",  # Workshops
        ]

        for li in soup.select("li.TeaserGrid--item.product"):
            if not isinstance(li, Tag):
                continue
            classes = li.get("class") or []
            classes_lower = [c.lower() for c in classes]
            if "outofstock" in classes_lower:
                logger.debug(f"Skipping out-of-stock product on {store_url}")
                continue

            link = li.select_one("a[href]")
            if not isinstance(link, Tag):
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            product_url = self.resolve_url(href)
            url_lower = product_url.lower()
            if any(excluded in url_lower for excluded in excluded_products):
                logger.debug(f"Excluding non-coffee product URL: {product_url}")
                continue

            if self.is_coffee_product_url(product_url, required_path_patterns=["/shop/coffee/"]):
                product_urls.append(product_url)

        # De-duplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(
            f"Found {len(unique_urls)} in-stock coffee product URLs on {store_url}"
        )
        return unique_urls
