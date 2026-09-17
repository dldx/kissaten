"""Lume Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="lume-roasters",
    display_name="Lume Roasters",
    roaster_name="Lume Roasters",
    website="https://lumeroasters.coffee",
    description="Small US roaster specializing in rare micro-lot coffees sold as "
    "100g (and 50g) bags — Pepe Jijon, Luz Helena Salazar, Kenyan factories and more",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class LumeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Lume Roasters (lumeroasters.coffee) using Shopify products.json.

    The store's product pages are image-led with the bean details rendered by
    JS from the theme, so scraping is JSON-only: the Shopify ``body_html``
    already carries everything worth extracting (origin, region, process,
    varietal, altitude, tasting notes, roast level, importer/source), and the
    AI extraction runs against the injected product JSON in optimized mode.

    Catalog shape: the curated ``frontpage`` ("Coffee") collection lists the
    currently available beans while the ``archive`` collection holds sold-out
    ones; both are fetched (plus ``all`` for completeness) and deduplicated by
    the base class. Most products are single-variant 100g bags (a few 50g), so
    ``price_options`` are typically limited to one weight/price pair.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Lume Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Lume Roasters",
            base_url="https://lumeroasters.coffee",
            products_json_urls=[
                "https://lumeroasters.coffee/collections/frontpage/products.json",
                "https://lumeroasters.coffee/collections/archive/products.json",
                "https://lumeroasters.coffee/collections/all/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The catalog contains only coffee (the 60g "Reddit Sample" offer is a
        # genuine coffee sampler and is kept, flagged as a tasting kit for
        # admin review via the base-class URL pattern match on "sample").
        self.exclude_slugs = []

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs. The home currency was
        # verified against the storefront (Shopify.currency active=USD,
        # rate=1.0), so make it authoritative.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Lume Roasters product URLs.

        The site's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
