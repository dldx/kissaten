"""Julius Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="julius-coffee",
    display_name="Julius Coffee",
    roaster_name="Julius Coffee",
    website="https://juliuscoffee.com",
    description="French-language Quebec roaster specializing in altitude-ranked Costa Rican and Colombian microlots",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="experimental",
)
class JuliusCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Julius Coffee (juliuscoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Julius Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Julius Coffee",
            base_url="https://juliuscoffee.com",
            # `cafes` is the main catalogue; `cafe-de-specialite` additionally holds the
        # James Hoffmann Fermentation Project kit, so both are fetched.
        products_json_urls=[
            "https://juliuscoffee.com/collections/cafes/products.json",
            "https://juliuscoffee.com/collections/cafe-de-specialite/products.json",
        ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude subscription and gift-card products; the cafes collection is
        # otherwise all beans (cascara items are kept for downstream review).
        self.exclude_slugs = [
            "abonnement",
            "carte-cadeau",
        ]

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports CAD.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup,
        product_url,
        use_optimized_mode: bool = False,
        translate_to_english: bool = True,
    ):
        """Override to ensure French product content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )
