"""Beanworks Coffee Roasters scraper implementation with AI-powered extraction.

The checklist location for Bean Works (Northampton) is beanworks.co.uk, which
is dead; the live store is thebeanworks.co.uk, self-described as
"Beanworks Coffee Roasters" (WooCommerce). Coffee lives under
``/product-category/coffee-beans/`` (core-collection, forager-series and
new-coffee-releases subcategories) plus ``/product-category/decaf-coffee/``.
Subscriptions (``discovery-coffee-subscription``, ``*-subscription``, gifts)
and merch are genuine excludes; every category page also features the
discovery subscription card, so the ``subscription`` slug filter is essential.

Sold-out detection: card-level text on the WooCommerce ``li.product`` card
before URL coalescing ("Out of stock").
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="beanworks",
    display_name="Beanworks Coffee Roasters",
    roaster_name="Beanworks Coffee Roasters",
    website="https://thebeanworks.co.uk",
    description="Award-winning specialty coffee roaster based in Northampton, "
    "UK. WooCommerce storefront selling core blends, single-origin filter "
    "coffees and decaf, roasted to order.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class BeanworksScraper(BaseScraper):
    """Scraper for Beanworks Coffee Roasters (thebeanworks.co.uk) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Beanworks Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Beanworks Coffee Roasters",
            base_url="https://thebeanworks.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Genuine non-coffee products (subscriptions, gifts, merch).
        # NOTE: tasting-kit tokens are intentionally NOT listed here - any
        # sampler/kit products flow through and get flagged for review.
        self.exclude_slugs = [
            "subscription",
            "gift",
            "merch",
            "brewing",
            "equipment",
        ]

    async def get_store_urls(self) -> list[str]:
        """Get the category URLs to crawl (coffee beans + decaf)."""
        return [
            "https://thebeanworks.co.uk/product-category/coffee-beans/",
            "https://thebeanworks.co.uk/product-category/decaf-coffee/",
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # Pin to the roaster's home currency (GBP).
        bean.currency = "GBP"
        return bean

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a WooCommerce category page.

        # Sold-out detection: card-level text detection on li.product
        Cards are ``li.product`` containers with an "Out of stock" badge in
        the card text when sold out; filter the card text BEFORE URL
        filtering so excluded products never leak past the stock check.
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        all_product_urls = []
        for card in soup.select("li.product"):
            card_text = card.get_text(" ", strip=True)
            if "Out of stock" in card_text or "Sold out" in card_text or "Unavailable" in card_text:
                continue
            link = card.select_one('a[href*="/product/"]') or card.select_one(".woocommerce-loop-product__link")
            if link:
                href = link.get("href")
                if href:
                    all_product_urls.append(href)

        # Filter non-coffee products using base class logic and required path pattern.
        filtered_urls = []
        for url in all_product_urls:
            if not url:
                continue
            # Never drop sampler/kit products; only genuine non-coffee slugs.
            if any(slug in url.lower() for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {url}")
                continue
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return list(dict.fromkeys(filtered_urls))
