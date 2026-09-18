"""Moonwake Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="moonwake-coffee",
    display_name="Moonwake",
    roaster_name="Moonwake",
    website="https://moonwakecoffeeroasters.com",
    description="Austin, Texas roaster offering a rotating selection of obsessively curated "
    "small batch coffees, including Cup of Excellence lots and rare varieties",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class MoonwakeCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Moonwake Coffee Roasters (moonwakecoffeeroasters.com) using Shopify products.json.

    JSON-only scrape shape: Moonwake's ``body_html`` already carries the full
    bean detail (roast level, tasting notes, region, elevation, producer,
    process, variety) in a structured "Origin Details" block, so no product
    page fetch is needed. Limitation: cost-transparency fields (FOB /
    farm-gate price, importer) and harvest dates are not published in the
    JSON payload and are not extracted.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Moonwake Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Moonwake",
            base_url="https://moonwakecoffeeroasters.com",
            products_json_urls=["https://moonwakecoffeeroasters.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Moonwake has no curated all-coffee collection: the coffee-specific
        # collections (fruit-forward, cocoa-forward, nova-series, decaf,
        # exploratory, frontpage) hold only 3-7 products each while
        # /collections/all carries the full ~160-bean catalogue. So we use
        # /all and exclude the gear/merch/subscriptions by handle substring.
        # Curated sampler/taster kits (if any appear) are kept and flagged
        # as tasting kits downstream via _apply_product_flags.
        self.exclude_slugs = [
            # Subscriptions & gift cards
            "subscription",
            "gift-card",
            # Brewing gear & accessories
            "coffee-server",
            "filter-paper",
            "cafec",
            "origami",
            "sibarist",
            "melodrip",
            "oshi-for",
            "apax-labs",
            "dripper",
            "brew-kit",
            "cupping-spoon",
            "tumbler",
            "traveler",
            # Merch & apparel
            "sweatshirt",
            "hoodie",
            "shirt",
            "tote-bag",
            "stickers",
            # Grinder seasoning beans (not for drinking)
            "seasoning",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs. The home currency is USD
        # (Austin, Texas store, verified against products.json), so make it
        # authoritative.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Moonwake Coffee product URLs.

        Moonwake's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
