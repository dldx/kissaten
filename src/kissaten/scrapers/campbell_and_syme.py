"""Campbell & Syme scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="campbell-and-syme",
    display_name="Campbell & Syme",
    roaster_name="Campbell & Syme",
    website="https://campbellandsyme.co.uk",
    description="Scottish specialty coffee roaster based in Glasgow, sourcing single "
    "origin coffees and offering curated 250g/1kg bags across origins in the UK.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CampbellAndSymeScraper(ShopifyJsonScraper):
    """Scraper for Campbell & Syme (campbellandsyme.co.uk) using Shopify products.json.

    Uses the curated ``/collections/shop-page`` collection (250G & 1KG coffee), which
    carries only coffee beans. There is no ``/collections/coffee`` (it 404s), and
    ``collections/all`` would mix in subscriptions/classes/equipment/merch, so this
    collection is preferred.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Campbell & Syme scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Campbell & Syme",
            base_url="https://campbellandsyme.co.uk",
            products_json_urls=[
                "https://campbellandsyme.co.uk/collections/shop-page/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Campbell & Syme is a UK store priced in GBP. The storefront can
        # geolocate the datacenter IP to a non-GBP market, so pin the home
        # currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT include sampler /
        # taster-pack slugs here: the base class flags tasting kits (flag-don't-
        # exclude) so they land in the admin review queue rather than being
        # dropped. The shop-page collection contains only coffee beans, so these
        # slugs are a safety net for any non-bean that slips through.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "classes",
            "workshop",
            "brewing",
            "equipment",
            "accessory",
            "merch",
            "merchandise",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
