"""Ozone Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ozone",
    display_name="Ozone Coffee",
    roaster_name="Ozone Coffee Roasters",
    website="https://ozonecoffee.co.uk",
    description="Specialty coffee roasters with longstanding producer relationships "
    "worldwide - sourcing exceptional beans, roasting them fresh, and supplying "
    "home brewers and cafes across the UK.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class OzoneCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Ozone Coffee Roasters (ozonecoffee.co.uk) using Shopify products.json.

    Ozone publishes its full coffee catalogue in the single ``coffee`` collection
    (the other sub-collections - coffee-origin-*, varietal, process and roast
    groupings - are overlapping views of the same beans), so scraping just that
    one collection covers every bean without duplicate listings.
    ``preprocess_product_url`` canonicalises the collection URL to the
    ``https://ozonecoffee.co.uk/products/<handle>`` form used by the live site
    (verified: every product link in the store HTML is ``/products/<handle>``
    and the www host redirects to the bare domain, so no www normalisation is
    needed).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Ozone Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ozone Coffee Roasters",
            base_url="https://ozonecoffee.co.uk",
            products_json_urls=[
                "https://ozonecoffee.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products. The only non-bean in the ``coffee``
        # collection is the "Test Roasts" placeholder product; the full-handle
        # slug "test-roasts" is used so the substring match can never
        # accidentally drop a coffee (short generic slugs like "filter" or
        # "pack" appear as suffixes in real bean handles). The base-class URL
        # pattern guard ("test-roast") would also drop it, so this is belt and
        # braces.
        self.exclude_slugs = [
            "test-roasts",
            "-pack"
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalise product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoint lives under ``/collections/coffee``, so the
        default URL construction yields
        ``/collections/coffee/products/<handle>``. The live site uses the
        canonical ``/products/<handle>`` form, so we strip the collection
        segment here.
        """
        url = re.sub(r"/collections/[^/]+(?=/products/)", "", url)
        return url
