"""Now Coffee scraper implementation with Shopify JSON extraction.

Now Coffee (nowcoffee.co.za) is a Durban (Glenashley), South Africa coffee
lab / drive-through / roastery that roasts on Thursdays and dispatches on
Fridays. The store is Shopify-hosted and priced in ZAR.

The site has no single curated "coffee" collection that covers everything:
``collections/all`` mixes beans with barista training courses, socks and
mushroom coffee. The beans live across two clean collections —
``single-origins`` (which also carries a coffee drip-bag product) and
``blends`` — so we scrape both and drop the drip bags via ``exclude_slugs``
(single-serve sachet format, not whole beans). No tasting kits/samplers are
excluded — any that appear are flagged by the base ``_apply_product_flags``
pipeline instead.

The products.json ``body_html`` already carries the bean detail (origin,
processing, varietal, tasting notes, altitude) plus size/grind variants, so
the scraper uses JSON-only extraction (``scrape_product_pages=False``).

The store runs Shopify Markets with currency geolocation, so we pin the store
currency to ZAR (the site's home-market currency) in ``__init__``, from
``_extract_currency_from_html`` and again in ``postprocess_extracted_bean`` so
a datacenter IP can never stamp geo-converted prices onto beans. Product URLs
are canonicalised to the no-collection ``/products/<handle>`` form used by the
live site (verified against sitemap_products_1.xml).
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="now-coffee",
    display_name="Now Coffee",
    roaster_name="Now Coffee",
    website="https://nowcoffee.co.za",
    description="Durban, South Africa coffee lab, drive-through and roastery roasting single "
    "origins and blends from a Shopify storefront priced in ZAR",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class NowCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Now Coffee (nowcoffee.co.za) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Now Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Now Coffee",
            base_url="https://nowcoffee.co.za",
            products_json_urls=[
                "https://nowcoffee.co.za/collections/single-origins/products.json",
                "https://nowcoffee.co.za/collections/blends/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency to the home-market ZAR. The site runs
        # Shopify Markets currency geolocation; a datacenter IP may receive
        # converted prices, so the geo-detected value must never override ZAR.
        self.store_currency = "ZAR"
        self._currency_detected = True

        # The two curated bean collections carry a coffee drip-bag product
        # (single-serve sachet format, not whole beans); the courses, socks
        # and mushroom-coffee products live outside them, but the extra
        # slugs act as a safety net against collection drift. Genuine
        # tasting kits/samplers are NOT excluded — the base
        # ``_apply_product_flags`` pipeline flags them for admin review.
        self.exclude_slugs = [
            "drip-bag",
            "course",
            "training",
            "socks",
            "mushroom",
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

        Now Coffee is a South African roaster priced in ZAR (the
        products.json prices are ZAR). The site serves a geo-localized
        presentment currency via Shopify Markets based on the caller's IP,
        which would otherwise override the correct base currency during
        extraction. Force ZAR so the AI prices the beans correctly.
        """
        return "ZAR"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to ZAR (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "ZAR"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Now Coffee's canonical product pages are just ``/products/<handle>``
        (no collection prefix), so remove the ``/collections/<name>/``
        added by the Shopify base from the collection products.json URLs.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
