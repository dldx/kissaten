"""Origin Coffee Roasting scraper implementation with Shopify JSON extraction.

Origin Coffee Roasting is a Cape Town, South Africa specialty roaster (founded
2006, Africa's first specialty roaster per their site) on a Shopify storefront
priced in ZAR. The curated ``coffee-beans`` collection is the site's canonical
bean catalogue (single origins, a Yemeni limited reserve line, a seasonal
blend and a decaf); ``collections/all`` mixes in teas, equipment and merch, so
it is not used.

The products.json ``body_html`` is thin (usually just the flavour notes), but
each product page carries a "COFFEE DETAILS" spec block (origin, altitude,
body, acidity, roast level, brewing recommendations, varietals, processing)
plus narrative accordions that the JSON lacks — so product pages are scraped
(``scrape_product_pages=True``) with ``use_optimized_mode=False`` and
``preprocess_product_soup`` pruning the page down to the
``div.accordion-wrapper`` block that holds those sections.

The store serves ZAR (rate 1.0) even from a datacenter IP, but as a defensive
measure against Shopify Markets currency geolocation the store currency is
pinned to ZAR in ``__init__`` and the ``Accept-Language`` header is removed.
Product URLs are canonicalised to the no-collection ``/products/<handle>``
form the live site serves.
"""

import logging
import re

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="origin-roasting",
    display_name="Origin Coffee Roasting",
    roaster_name="Origin Coffee Roasting",
    website="https://originroasting.co.za",
    description="Cape Town, South Africa specialty roasting pioneer (est. 2005, De Waterkant) with single "
    "origins, a Yemeni limited-reserve line and seasonal blends on a Shopify storefront priced in ZAR",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class OriginRoastingScraper(ShopifyJsonScraper):
    """Scraper for Origin Coffee Roasting (originroasting.co.za) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Origin Coffee Roasting scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Origin Coffee Roasting",
            base_url="https://originroasting.co.za",
            products_json_urls=[
                "https://originroasting.co.za/collections/coffee-beans/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency to the home-market ZAR. The site is Shopify
        # Markets-capable; a datacenter IP must never be able to stamp
        # geo-converted prices onto beans.
        self.store_currency = "ZAR"
        self._currency_detected = True

        # The curated coffee-beans collection is already coffee-only; keep a
        # small defensive net for genuine non-bean products in case the
        # collection is ever broadened.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "capsules",
            "pods",
            "tea",
            "tote",
        ]

        # Remove the Accept-Language header so Shopify serves the base ZAR
        # market instead of a geo-localized presentment currency (any
        # Accept-Language, even the home one, can trigger conversion).
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

        Origin Coffee Roasting is a South African roaster priced in ZAR (the
        products.json prices are ZAR). Force ZAR so a geo-localized Shopify
        Markets presentment currency can never override the base currency
        during extraction.
        """
        return "ZAR"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to ZAR (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "ZAR"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Origin's canonical product pages are just ``/products/<handle>``
        (no collection prefix), so remove the ``/collections/<name>/`` added
        by the Shopify base from the collection products.json URL.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Limit extraction to the coffee spec/accordion block.

        The product page's bean information (COFFEE DETAILS spec table with
        origin/altitude/body/acidity/roast/brewing/varietals/processing, plus
        the About-this-coffee / Alchemy-Process narrative accordions) lives in
        a single ``div.accordion-wrapper``. Keep only that block — name, price
        and variants are restored later by the injected Shopify product JSON.
        """
        meta = soup.select_one("div.accordion-wrapper")
        if meta:
            logger.debug("Limiting extraction to div.accordion-wrapper")
            return meta
        return soup
