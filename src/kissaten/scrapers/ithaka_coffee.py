"""Ithaka Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ithaka",
    display_name="Ithaka Coffee",
    roaster_name="Ithaka Coffee",
    website="https://ithaka.coffee",
    description="Birmingham-based speciality coffee roaster sourcing rare and "
    "experimental lots from Guatemala, Bolivia, Mozambique, Rwanda, Thailand "
    "and beyond.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class IthakaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Ithaka Coffee (ithaka.coffee) using Shopify products.json.

    Ithaka publishes its coffees under the ``coffee`` collection but also under
    ``collections/all`` (which additionally holds brew gear from third-party
    brands). Both endpoints are scraped so a bean is found even if it is not
    yet tagged into ``coffee``; ``preprocess_product_url`` collapses every
    collection URL onto the canonical ``https://ithaka.coffee/products/<handle>``
    form (the exact shape used on the live site), so overlapping listings are
    never duplicated.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Ithaka Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ithaka Coffee",
            base_url="https://ithaka.coffee",
            products_json_urls=[
                "https://ithaka.coffee/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude third-party brew gear that Shopify's base URL/name filters
        # would otherwise pass through (AeroPress/Timemore are caught by the
        # base patterns; the Barista Hustle pitcher is not).
        self.exclude_slugs = [
            "barista-hustle",
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
