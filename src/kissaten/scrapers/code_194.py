"""Code.194 Coffee scraper implementation with Shopify JSON extraction.

Code.194 Coffee Roasters (code194coffee.com) is a UK (London) roaster running a
Shopify storefront. The curated ``/collections/coffee`` products.json carries
the whole-bean catalogue (10 whole-bean coffees, each with a Whole Bean
variant). Product ``body_html`` is rich enough (origin, process, tasting notes,
blend description) that we scrape purely from the Shopify JSON context without
fetching each product page.

The former ``code194coffee.co.uk`` domain redirects to ``code194coffee.com``;
product pages canonicalize to the no-collection ``/products/<handle>`` form, so
``preprocess_product_url`` strips the collection segment to stay aligned with
the site's real URLs.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="code-194",
    display_name="Code.194 Coffee Roasters",
    roaster_name="Code.194 Coffee Roasters",
    website="https://code194coffee.com",
    description="London, UK specialty coffee roaster (Shopify storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class Code194CoffeeScraper(ShopifyJsonScraper):
    """Scraper for Code.194. Coffee (code194coffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Code.194. Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Code.194 Coffee Roasters",
            base_url="https://code194coffee.com",
            products_json_urls=[
                "https://code194coffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The storefront serves the UK market by default (Shopify.currency
        # "GBP" rate 1.0). Pin GBP so a geo-localized storefront (which Shopify
        # can serve to non-local clients) can't convert prices.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated /collections/coffee catalogue is whole-bean coffee only,
        # so no exclude_slugs are needed. Tasting-kit/sampler products are NOT
        # excluded here: the base flags them via _apply_product_flags so they
        # land in the admin review queue instead of being silently dropped.
        self.exclude_slugs: list[str] = []

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Code.194. product URLs to the canonical /products/<handle> form.

        The products.json endpoint lives under ``/collections/coffee/``, so the
        base class builds collection-prefixed URLs. The site's real product
        pages drop the collection segment, so we strip it here to keep the
        scraper's URLs aligned with the site (and with any historical data
        stored under the canonical form).

        Args:
            url: Original product URL (collection-prefixed).

        Returns:
            Canonical ``https://code194coffee.com/products/<handle>`` URL.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Collect product URLs, keeping only whole-bean coffee products.

        The superclass already restricts to coffee products (``is_coffee_product_url``
        + ``is_coffee_product_name``) and keys the Shopify product metadata by the
        preprocessed URL. This override additionally enforces the whole-bean filter:
        a product must have at least one "Whole Bean" variant to be kept. Non-bean
        items (equipment, merch, subscriptions, gift cards) and samplers/taster packs
        are handled by the base logic — samplers are flagged for review, not dropped.

        Args:
            store_url: URL of the products.json endpoint.

        Returns:
            List of canonical whole-bean product URLs.
        """
        found_urls = await super()._extract_product_urls_from_store(store_url)

        whole_bean: list[str] = []
        for url in found_urls:
            product = self._shopify_product_data.get(url, {})
            variants = product.get("variants", [])
            if any("whole bean" in str(v.get("title", "")).lower() for v in variants):
                whole_bean.append(url)
            else:
                logger.debug(f"Skipping non-whole-bean product: {url}")

        return whole_bean
