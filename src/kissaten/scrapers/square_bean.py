"""Square Bean Coffee scraper implementation using Shopify products.json."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="square-bean",
    display_name="Square Bean Coffee",
    roaster_name="Square Bean Coffee",
    website="https://squarebean.co.uk",
    description="UK specialty coffee roaster sourcing single-origin lots and blends "
    "from Peru, Uganda, Ethiopia, Colombia and beyond, roasted to order.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SquareBeanCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Square Bean Coffee (squarebean.co.uk) using Shopify products.json.

    The curated ``all-coffees`` collection lists only coffee beans (whole bean and
    grind options as variants), so no ``exclude_slugs`` filtering is needed — genuine
    equipment and non-bean products live in separate collections and never appear here.
    Sampler/taster-kit style products, if any, are kept and flagged via
    ``_apply_product_flags`` rather than being silently dropped.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Square Bean Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Square Bean Coffee",
            base_url="https://squarebean.co.uk",
            products_json_urls=[
                "https://squarebean.co.uk/collections/all-coffees/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Square Bean prices in GBP (UK roaster). Pin the store currency so the
        # geolocated Shopify market conversion (datacenter IP / Accept-Language)
        # cannot stamp a converted currency onto every bean.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Square Bean Coffee product URLs.

        The canonical product page is ``https://squarebean.co.uk/products/<handle>``
        (no collection segment). Strip the collection prefix that ShopifyJsonScraper
        builds from the collection ``products.json`` URL.
        """
        return url.replace(
            "https://squarebean.co.uk/collections/all-coffees/products/",
            "https://squarebean.co.uk/products/",
        )
