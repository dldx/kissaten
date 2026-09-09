"""Father Coffee scraper implementation with Shopify JSON extraction.

Father Coffee (father.coffee) is a Johannesburg, South Africa-based specialty
coffee roaster. The store is Shopify-hosted and priced in ZAR. Note: this is
not the Czech roaster "Fathers" (fathers.py).

The curated ``coffee`` collection holds the full bean line-up (microlots,
special releases, Rare Release® lots, blends and decafs); the broader ``all``
collection mixes in brew gear, merch, pantry goods and hot sauce. The one
non-bean entry inside the coffee collection itself (Seasonal Capsules) is
dropped via the ``capsules`` exclude slug.

The product pages carry a "Product Details" collapsible tab (producer, region,
variety, altitude, process, cupping and brew notes as Shopify metafields) that
the collection products.json ``body_html`` lacks, so we scrape the product
pages and prune the soup to the description + collapsible-tab blocks before AI
extraction.

The store serves unconverted ZAR prices from this machine (SAST timestamps,
ZAR-magnitude prices), but as a Shopify Markets store it could geo-convert
prices for a datacenter IP, so we pin the store currency to ZAR in ``__init__``
and remove the ``Accept-Language`` header.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="father-coffee",
    display_name="Father Coffee",
    roaster_name="Father Coffee",
    website="https://www.father.coffee",
    description="Johannesburg specialty coffee roaster focused on African and "
    "Latin American microlots, special releases and blends, priced in ZAR",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class FatherCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Father Coffee (father.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Father Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Father Coffee",
            base_url="https://www.father.coffee",
            products_json_urls=[
                "https://www.father.coffee/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency to the home-market ZAR. The site is a
        # Shopify Markets store; a datacenter IP may receive geo-converted
        # prices, so the geo-detected value must never override ZAR.
        self.store_currency = "ZAR"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The curated coffee
        # collection is beans (microlots, special/rare releases, blends);
        # ``capsules`` drops the Seasonal Capsules entry. Any tasting kit that
        # slips through is flagged for review by the base
        # ``_apply_product_flags`` pipeline instead of being silently dropped.
        self.exclude_slugs = [
            "capsules",
            "pods",
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "apparel",
            "tee",
            "mug",
            "hoodie",
        ]

        # Remove the Accept-Language header so Shopify serves the base ZAR
        # market instead of a geo-localized presentment currency (any
        # Accept-Language, even en-US, can trigger conversion).
        self.headers.pop("Accept-Language", None)
        self.client._base_headers.pop("Accept-Language", None)
        session_headers = getattr(self.client._session, "headers", None)
        if session_headers:
            session_headers.pop("Accept-Language", None)

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _extract_currency_from_html(self, soup) -> str:
        """Pin the store currency to ZAR.

        Father Coffee is a South African roaster priced in ZAR (the
        products.json prices are ZAR). Shopify Markets could serve a
        geo-localized presentment currency based on the caller's IP, which
        would otherwise override the correct base currency during extraction.
        Force ZAR so the AI prices the beans correctly.
        """
        return "ZAR"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to ZAR (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "ZAR"
        return bean

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean-detail sections.

        Father Coffee hides producer/region/variety/altitude/process/cupping
        and brew notes behind collapsible ``div.product-block-collapsible-tab``
        sections (rendered as static ``<details>`` markup); the main story
        lives in ``div.product-block-description``. Keep only those so the AI
        gets the bean information without the page chrome. We build a new
        minimal soup WITH a body: ShopifyJsonScraper injects the Shopify JSON
        context (name/price/variants) at the top of ``soup.body`` AFTER this
        hook returns, so keeping a valid body preserves that data.
        """
        blocks = soup.select("div.product-block-collapsible-tab, div.product-block-description")
        if not blocks:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for block in blocks:
            minimal.body.append(block)
        return minimal
