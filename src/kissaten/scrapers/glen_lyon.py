"""Glen Lyon Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="glen-lyon",
    display_name="Glen Lyon",
    roaster_name="Glen Lyon",
    website="https://www.glenlyoncoffee.co.uk",
    description="Scottish speciality coffee roasters based in Perthshire (Glen Lyon "
    "coffee roasters), roasting single origins and signature blends from their "
    "Perthshire roastery.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class GlenLyonScraper(ShopifyJsonScraper):
    """Scraper for Glen Lyon Coffee Roasters (glenlyoncoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Glen Lyon scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Glen Lyon",
            base_url="https://www.glenlyoncoffee.co.uk",
            products_json_urls=[
                "https://glenlyoncoffee.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency so Shopify Markets geolocation (datacenter IP
        # can receive a converted currency) can never stamp a non-GBP value.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-bean products only. The curated /collections/coffee
        # holds 59 products; the single non-bean is the recurring subscription.
        # Sampler/trio/duo/quartet boxes are kept (extracted and review-flagged).
        self.exclude_slugs = [
            "subscription",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Extend the base kit/sampler URL patterns with Glen Lyon's box handles.

        Glen Lyon sells curated sampler boxes under handles like
        ``blend-trio-box``, ``low-caff-duo``, ``quartet-box``, ``mocha-box``
        and ``build-your-own-trio-box``. None match the base patterns, so
        without this override these kits would be dropped when the AI returns
        them with no single origin. Flagging them keeps them in the admin
        review queue instead of silently discarding them.
        """
        return super()._get_tasting_kit_url_patterns() + [
            "trio-box",
            "duo-box",
            "quartet-box",
            "mocha-box",
            "build-your-own-trio-box",
        ]

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Glen Lyon product URLs.

        The live site canonicalizes to ``https://www.glenlyoncoffee.co.uk/products/<handle>``
        (no collection segment) and serves content under the ``www.`` domain, so strip
        the collection segment and normalize to ``www``.
        """
        url = url.replace("https://glenlyoncoffee.co.uk", "https://www.glenlyoncoffee.co.uk")
        url = url.replace("/collections/coffee/products/", "/products/")
        return url
