"""Lucid Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="lucid",
    display_name="Lucid Coffee Roasters",
    roaster_name="Lucid Coffee Roasters",
    website="https://www.lucidcoffeeroasters.com",
    description="Belfast-based speciality coffee roaster roasting filter and espresso "
    "single origins in small batches.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class LucidCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Lucid Coffee Roasters (lucidcoffeeroasters.com) using Shopify products.json.

    The ``coffee`` collection holds the beans but also subscriptions and a gift
    card (filtered by base name/URL rules plus ``exclude_slugs``);
    ``collections/all`` adds third-party brewing equipment (Orea, Sibarist,
    BWT, Ratio, Fellow, Hario) that is excluded explicitly. Both endpoints are
    scraped so a bean is found even if it is not yet tagged into ``coffee``;
    ``preprocess_product_url`` collapses every collection URL onto the
    canonical ``https://www.lucidcoffeeroasters.com/products/<handle>`` form
    (the exact shape used on the live site), so overlapping listings are never
    duplicated.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Lucid Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Lucid Coffee Roasters",
            base_url="https://www.lucidcoffeeroasters.com",
            products_json_urls=[
                "https://www.lucidcoffeeroasters.com/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products: equipment brands (Orea, Sibarist, BWT,
        # Ratio, Fellow Aiden; Hario and grinder are caught by the base URL
        # filters), merch (socks, t-shirts, prints) and subscriptions/gift
        # cards. Only distinctive brand slugs are used — the beans' own
        # handles use "-filter"/"-espresso" as a roast-style suffix, so broad
        # slugs like "filter", "brewer" or "grinder" would wrongly drop them.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "orea",
            "sibarist",
            "bwt",
            "water-filter-jug",
            "ratio-6",
            "aiden",
            "lucid-sporty-socks",
            "t-shirt",
            "collab-a3-print",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalise product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoints live under ``/collections/<slug>``, so the
        default URL construction yields ``/collections/<slug>/products/...``.
        The live site uses the canonical ``/products/<handle>`` form, so we
        strip the collection segment here. Overlapping collections therefore
        merge onto a single URL and are never duplicated.
        """
        url = re.sub(r"/collections/[^/]+(?=/products/)", "", url)
        return url
