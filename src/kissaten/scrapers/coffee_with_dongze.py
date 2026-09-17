"""Coffee with Dongze scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffee-with-dongze",
    display_name="Coffee with Dongze",
    roaster_name="Coffee with Dongze",
    website="https://coffee-with-dongze.myshopify.com",
    description="US-based roaster of extremely limited 'drop' releases focused on Panamanian "
    "gesha and rare nano-lots (Blackmoon Chiroso, auction sets, Symbiosis Project); "
    "most products are sold out between drops",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CoffeeWithDongzeScraper(ShopifyJsonScraper):
    """Scraper for Coffee with Dongze (coffee-with-dongze.myshopify.com).

    Shopify drop-model store on the default myshopify domain. Collection
    choice: the store only exposes ``classics``, ``in-stock`` (current drop)
    and ``frontpage`` collections — each would miss most of the ~98-product
    catalogue, which is small and entirely coffee, so the root
    ``/products.json`` is used to capture past drops too (many sold out).

    Scrape shape: JSON-only (``scrape_product_pages=False`` +
    ``use_optimized_mode=True``). The product ``body_html`` already carries
    producer, origin, elevation, variety, process and Dongze's tasting notes
    — including the "Dongze's Notes" accordion content, which lives inside
    ``body_html`` rather than a separately rendered panel — so fetching the
    product pages would add nothing. No ``preprocess_product_soup`` pruning
    is needed.

    Limitation: roast level, roast profile, and cost-transparency fields
    (FOB/farm-gate price) are not published anywhere on the store and will
    stay unset; harvest dates are occasionally mentioned in prose only.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee with Dongze scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee with Dongze",
            base_url="https://coffee-with-dongze.myshopify.com",
            products_json_urls=["https://coffee-with-dongze.myshopify.com/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The store sells only coffee (beans, tasting sets and annual premium
        # coffee boxes) — no equipment, merch or subscriptions were observed.
        # Keep a defensive exclusion for gift cards only; curated tasting sets
        # are intentionally kept so _apply_product_flags can flag them as
        # tasting kits for admin review.
        self.exclude_slugs = [
            "gift-card",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs. /cart.js reports USD for
        # the store's default market, so make USD authoritative.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
