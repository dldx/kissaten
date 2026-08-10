"""Rave Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rave",
    display_name="Rave Coffee",
    roaster_name="Rave Coffee",
    website="https://ravecoffee.co.uk",
    description="Shop freshly roasted speciality coffee from RAVE. Bold blends "
    "and single origin beans, roasted in the UK and delivered fast.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RaveCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Rave Coffee (ravecoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Rave Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Rave Coffee",
            base_url="https://ravecoffee.co.uk",
            products_json_urls=[
                "https://ravecoffee.co.uk/collections/roasted-coffee/products.json",
                "https://ravecoffee.co.uk/collections/single-origin-coffee/products.json",
                "https://ravecoffee.co.uk/collections/coffee-blends/products.json",
                "https://ravecoffee.co.uk/collections/decaf-coffee-beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products: Nespresso-style pods, bundle/taster
        # packs, coffee liqueur, compostable bags and zip-lock bags. The
        # exclude check is a SUBSTRING match against the product handle, so
        # short generic slugs (e.g. "pod", "bag", "pack") would risk dropping
        # real beans whose handles happen to contain them. Every slug below
        # was verified to appear in no coffee-bean handle.
        self.exclude_slugs = [
            "pods",
            "bundle",
            "liqueur",
            "capsules",
            "compostable",
            "zip-lock",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalise product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoints live under ``/collections/<slug>``, so the
        default URL construction yields ``/collections/<slug>/products/<handle>``.
        The live site uses the canonical ``/products/<handle>`` form with no
        collection segment and no www subdomain, so the collection segment is
        stripped here. Overlapping collections therefore merge onto a single
        URL and are never duplicated.
        """
        url = re.sub(r"/collections/[^/]+(?=/products/)", "", url)
        return url
