"""Django Coffee Co scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="django",
    display_name="Django",
    roaster_name="Django",
    website="https://www.djangocoffeeco.com",
    description="Small batch Manchester coffee roaster specialising in sustainability and "
    "ethically sourced coffee, selling wholebean coffee online across the UK.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class DjangoScraper(ShopifyJsonScraper):
    """Scraper for Django Coffee Co (djangocoffeeco.com) using Shopify products.json.

    Uses the curated ``coffee-beans-online-order-coffee-online`` collection
    (the site's ``/collections/coffee`` slug is empty). ``body_html`` carries the
    full structured field set (Name, Producer, Origin, Varietal, Altitude,
    Process, Flavours/Importer, Roast, brew profile, story), so discovery and
    enrichment run JSON-only with no product-page fetches.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Django Coffee Co scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Django",
            base_url="https://www.djangocoffeeco.com",
            products_json_urls=[
                "https://www.djangocoffeeco.com/collections/coffee-beans-online-order-coffee-online/products.json",
            ],
            # JSON-only shape: products.json body_html already carries the bean
            # details, so fetching the ~600KB rendered pages would burn tokens
            # for no new fields.
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency: the site uses Shopify Markets, and a
        # datacenter IP could otherwise receive geo-converted prices.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize Django product URLs to ``https://www.djangocoffeeco.com/products/<handle>``.

        The live site serves ``rel=canonical`` as ``/products/<handle>`` (no
        collection segment) on the ``www`` host (the bare domain 301s to www),
        so strip the collection path and normalize the host.
        """
        url = url.replace("https://djangocoffeeco.com", "https://www.djangocoffeeco.com")
        url = url.replace(
            "/collections/coffee-beans-online-order-coffee-online/products/", "/products/"
        )
        return url
