"""April Coffee scraper implementation with Shopify JSON extraction."""

import logging

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="april-coffee",
    display_name="April Coffee",
    roaster_name="April Coffee",
    website="https://www.aprilcoffeeroasters.com",
    description="Specialty coffee roastery based in Copenhagen, Denmark",
    requires_api_key=True,
    currency="DKK",  # Danish Krone
    country="Denmark",
    status="available",
)
class AprilCoffeeScraper(ShopifyJsonScraper):
    """Scraper for April Coffee (aprilcoffeeroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize April Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="April Coffee",
            base_url="https://www.aprilcoffeeroasters.com",
            products_json_urls=[
                "https://www.aprilcoffeeroasters.com/collections/filter-beans/products.json",
                "https://www.aprilcoffeeroasters.com/collections/espresso-beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, etc.)
        self.exclude_slugs = [
            "subscription",
            "sample-box",
            "gift",
            "giftcard",
            "merchandise",
            "equipment",
            "brew-gear",
            "-merch",
            "from-nerd-to-pro",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Override to ensure currency and roast profiles based on URL."""
        bean.currency = "DKK"
        # If filter-beans in URL, set roast_type to Filter
        if "filter-beans" in str(bean.url):
            bean.roast_profile = "Filter"
        elif "espresso-beans" in str(bean.url):
            bean.roast_profile = "Espresso"

        return super().postprocess_extracted_bean(bean)
