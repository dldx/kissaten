"""Black Mass Roasters scraper implementation with Shopify JSON extraction.

Black Mass Roasters (blackmassroasters.com) is a Brisbane (Meanjin),
Australia-based specialty roaster with a heavy-metal / occult-themed brand. The
store is Shopify-hosted and priced in AUD.

The site has no dedicated "coffee" collection: the canonical live coffee set is
the ``view-all-live-offerings`` collection (single origins, blends, decaf and
multi-bag bundles), and every product in it carries ``product_type == "Coffee"``
— so we filter on that plus an ``exclude_slugs`` net to drop the genuine
"Blend Subscription" recurring products. Multi-bag bundles (THE INFERNAL
TRINITY, BEHEMOTH | FUROR DIVINUS, Roasters Choice Bundle 'Triune') are kept;
any that the AI extractor recognises as tasting kits are flagged by the base
``_apply_product_flags`` pipeline into the admin review queue.

The products.json ``body_html`` already carries the bean detail (tasting notes,
producer, farm, region, varietal, processing, altitude) plus price variants, so
the scraper uses JSON-only extraction (``scrape_product_pages=False``).

The store runs Shopify Markets with currency geolocation, so we pin the store
currency to AUD (the site's home-market currency) in ``__init__``, from
``_extract_currency_from_html`` and again in ``postprocess_extracted_bean`` so
a datacenter IP can never stamp geo-converted prices onto beans. Product URLs
are canonicalised to the no-collection ``/products/<handle>`` form used by the
live site.
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="black-mass-roasters",
    display_name="Black Mass Roasters",
    roaster_name="Black Mass Roasters",
    website="https://blackmassroasters.com",
    description="Brisbane (Meanjin), Australia specialty roaster with a heavy-metal / "
    "occult-themed brand, roasting single origins, blends and a decaf from "
    "a Shopify storefront priced in AUD",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class BlackMassRoastersScraper(ShopifyJsonScraper):
    """Scraper for Black Mass Roasters (blackmassroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Black Mass Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Black Mass Roasters",
            base_url="https://blackmassroasters.com",
            products_json_urls=[
                "https://blackmassroasters.com/collections/view-all-live-offerings/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency to the home-market AUD. The site runs
        # Shopify Markets currency geolocation and serves a country/currency
        # selector; a datacenter IP may receive converted prices, so the
        # geo-detected value must never override AUD.
        self.store_currency = "AUD"
        self._currency_detected = True

        # Exclude genuine non-bean services only. Multi-bag coffee bundles are
        # kept: any recognized tasting kit is flagged for review by the base
        # ``_apply_product_flags`` pipeline instead of being silently dropped.
        self.exclude_slugs = [
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
            "hoodie",
            "cap",
            "mug",
            "tumbler",
            "sticker",
        ]

        # Remove the Accept-Language header so Shopify serves the base AUD
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
        """Pin the store currency to AUD.

        Black Mass Roasters is an Australian roaster priced in AUD (the
        products.json prices are AUD). The site serves a geo-localized
        presentment currency (e.g. USD/GBP) via Shopify Markets based on the
        caller's IP, which would otherwise override the correct base currency
        during extraction. Force AUD so the AI prices the beans correctly.
        """
        return "AUD"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to AUD (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "AUD"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Black Mass Roasters' canonical product pages are just
        ``/products/<handle>`` (no collection prefix), so remove the
        ``/collections/<name>/`` added by the Shopify base from the
        collection products.json URLs.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only Coffee-type products.

        The ``view-all-live-offerings`` collection is the site's canonical live
        coffee set and every entry carries ``product_type == "Coffee"``
        (single origins, blends, decaf, multi-bag bundles and the genuine
        "Blend Subscription" products). Filter on ``product_type == "Coffee"``
        and then the ``exclude_slugs`` net, which drops the subscriptions while
        keeping the multi-bag bundles for review-queue flagging.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify itself classifies as coffee.
            if product.get("product_type", "") != "Coffee":
                logger.debug(f"Skipping non-coffee product type: {handle} ({product.get('product_type')})")
                continue

            # Skip explicitly excluded product slugs (matches if slug is a substring of handle).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Preprocess the URL (e.g. to remove collection segments).
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status.
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available.
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic.
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs (post-preprocess) so the returned
        # list is unique even before the base discover_all_product_urls dedups.
        return self.deduplicate_urls(found_urls)
