"""Second Spin Roasting Co. scraper implementation with Shopify JSON extraction.

Second Spin Roasting Co. (secondspinroasting.com) is a California roaster known
for its seasonal dark roast ("Grave Wave"), its Limited 66 exotic micro-lot
program (e.g. Ethiopia Gori Gesha 96h carbonic maceration), and coffee
subscriptions.

Scrape shape: JSON-only. The Shopify ``body_html`` of every coffee carries a
structured spec list (Country / Region / Farm / Varietal / Process / Altitude /
Cupping Notes) plus descriptive paragraphs, so
``scrape_product_pages=False`` + ``use_optimized_mode=True`` (AI extraction
from the injected products.json context) is sufficient; the rendered product
pages add nothing beyond the JSON.

Collection choice: the store's coffee products are fragmented across three
curated collections — ``coffee`` (retail lineup incl. the two subscriptions),
``limited-66-gallery`` (Limited 66 micro lots), and ``wholesale`` (which also
lists the retail Ethiopia Niguse Nara lot). No single curated collection
covers the retail catalog, so all three are fetched and deduplicated.
Known limitation: the Costa Rica Hacienda Sonora micro lot
(``costa-rica-palmichael-anaerobic-natural``) is only present in
``collections/all`` and is therefore not covered.

Subscriptions are excluded via ``exclude_slugs``; the store carries no
equipment/merch inside the curated collections. If a curated sampler/tasting
kit ever appears it will be picked up and flagged ``is_tasting_kit`` /
``requires_review`` by the base class rather than dropped.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="second-spin-roasting",
    display_name="Second Spin",
    roaster_name="Second Spin",
    website="https://secondspinroasting.com",
    description="California roaster offering seasonal dark roasts (Grave Wave), single origins "
    "and experimental Limited 66 micro lots with extended fermentations",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class SecondSpinRoastingScraper(ShopifyJsonScraper):
    """Scraper for Second Spin Roasting Co. (secondspinroasting.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Second Spin Roasting Co. scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Second Spin",
            base_url="https://secondspinroasting.com",
            products_json_urls=[
                "https://secondspinroasting.com/collections/coffee/products.json",
                "https://secondspinroasting.com/collections/limited-66-gallery/products.json",
                "https://secondspinroasting.com/collections/wholesale/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated coffee collection includes both subscription products.
        # Everything else in these three collections is coffee.
        self.exclude_slugs = [
            "monthly-subscription",
            "monthly-roasters-selection",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs. The products.json prices
        # were verified as USD (the store's home market), so make it
        # authoritative and skip base-class currency detection.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Second Spin product URLs.

        The site's canonical product pages are the no-collection form
        ``/products/<handle>`` (confirmed via the ``link rel=canonical`` tag),
        so strip the ``/collections/<slug>`` segment the base class builds
        from the products.json URLs.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
