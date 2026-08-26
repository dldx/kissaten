"""Jet Bean Coffee scraper implementation with Shopify JSON extraction.

Jet Bean is a UK aviation-themed specialty coffee roaster (jetbeancoffee.com).
The site was rebuilt on Shopify; a curated coffee collection
``/collections/specialty-coffee-for-aviation-lovers/products.json`` carries the
whole-bean catalogue alongside a few merch/pod items that are excluded here.
The product JSON ``body_html``/variants carry rich bean detail (origin, tasting
notes, grind/weight options) and per-variant ``price_currency: "GBP"``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="jet-bean",
    display_name="Jet Bean",
    roaster_name="Jet Bean",
    website="https://jetbeancoffee.com",
    description="UK specialty coffee roaster with an aviation theme, roasting "
    "single-origin coffees inspired by classic aircraft.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class JetBeanScraper(ShopifyJsonScraper):
    """Scraper for Jet Bean Coffee (jetbeancoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Jet Bean Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Jet Bean",
            base_url="https://jetbeancoffee.com",
            products_json_urls=[
                "https://jetbeancoffee.com/collections/specialty-coffee-for-aviation-lovers/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )
        # The curated coffee collection mixes whole beans with a few non-coffee
        # items (Jumbo Jet pods, a baseball cap, a keyring) and a coffee sampler
        # bundle (The Flight Deck Collection). Pods and merch are excluded;
        # the sampler is intentionally kept and flagged for review instead.
        self.exclude_slugs = ["pods", "baseball-cap", "keyring"]

        # Jet Bean is a UK store and every product.json variant carries
        # ``price_currency: "GBP"``. Pin the currency so a geo-converted market
        # (datacenter IP, Accept-Language) can never overwrite the home GBP.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to the canonical ``/products/<handle>`` form.

        ShopifyJsonScraper builds collection-prefixed URLs from the products.json
        base (``/collections/specialty-coffee-for-aviation-lovers/products/<handle>``),
        but the site's real product pages are the no-collection canonical form
        (``/products/<handle>``). Normalising here keeps dedup and diffjson
        matching aligned with the live site.
        """
        if "/collections/" in url and "/products/" in url:
            url = url.split("/collections/", 1)[0] + "/products/" + url.rsplit("/products/", 1)[1]
        return url

    def postprocess_review_flags(self, bean, url: str):
        """Flag the curated Flight Deck sampler bundle for admin review.

        ``The Flight Deck Collection`` is a 3-bag multi-origin sampler, not a
        single whole-bean product, so it is not caught by the default
        tasting-kit heuristics (its handle carries no kit token). Force
        ``is_tasting_kit`` so it lands in the admin review queue instead of
        showing up in public search.
        """
        url_lower = str(url).lower()
        name_lower = (getattr(bean, "name", None) or "").lower()
        if "flight-deck-collection" in url_lower or "flight deck collection" in name_lower:
            bean.is_tasting_kit = True
        return bean
