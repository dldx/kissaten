"""Spring Valley Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="spring-valley-coffee",
    display_name="Spring Valley Coffee",
    roaster_name="Spring Valley Coffee",
    website="https://www.springvalleycoffee.com",
    description="Specialty coffee roaster based in Nairobi, Kenya, roasting Kenyan coffee "
    "at origin — sourcing from Mt. Elgon, Nyeri, Kericho and Machakos estates and "
    "washing stations, with a café and roastery presence in London",
    requires_api_key=True,
    currency="GBP",
    country="Kenya",
    status="available",
)
class SpringValleyCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Spring Valley Coffee (www.springvalleycoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Spring Valley Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Spring Valley Coffee",
            base_url="https://www.springvalleycoffee.com",
            products_json_urls=["https://www.springvalleycoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products. The curated /collections/coffee feed only
        # contains roasted coffee bags, but keep a small guard list in case the
        # collection grows. Capsules and cupping experiences are not in this
        # collection. Tasting kits/samplers are NOT excluded — they must flow
        # through with is_tasting_kit/requires_review flags.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
        ]

        # Pin the store currency. The shop's base currency is GBP
        # (Shopify.currency rate 1.0 on a plain fetch); Shopify Markets can
        # serve converted/adjusted prices for other markets (e.g. the KE
        # market shows different prices), so make sure the detected value
        # cannot override GBP.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match the site's canonical product URLs.

        The site links products as /products/<handle>; the products.json base
        builds /collections/coffee/products/<handle>.
        """
        return url.replace("/collections/coffee/products/", "/products/")
