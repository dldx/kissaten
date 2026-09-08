"""Langøra Kaffebrenneri scraper implementation with Shopify JSON extraction.

Langøra Kaffebrenneri (langorakaffe.no) is a Norwegian specialty coffee
roastery in Stjørdal that finds green beans from around the world, roasts them
in-house and ships fresh on order. The storefront is Shopify and prices are in
Norwegian kroner (NOK).

The curated ``produkter`` collection (the full shop) mixes whole-bean coffees
with brewing equipment (``Kaffeutstyr``), merch, a subscription club
(``Abonnement``) and the seasonal Advent calendar (``Adventskalender``). We
filter on Shopify's own ``product_type == "Kaffe"`` to keep only the coffee set
(single origins, the decaf, house blends and multi-bag coffee packs), mirroring
the ``seven_seeds.py`` pattern.

Product URLs are canonicalised to the live, no-collection form
``https://www.langorakaffe.no/products/<handle>`` (confirmed via the product
page ``rel=canonical``). The Shopify JSON ``body_html`` is empty for the single
origins, so the bean detail (tasting notes, process, variety, producer, region,
elevation) lives on the rendered product page; we scrape those pages and prune
to the ``<main>`` element to keep AI token usage low while preserving the
injected Shopify context (see ``seven_seeds.py`` / ``morgon.py``).

The multi-coffee bundle "Hverdag + Fest | 4-pk" (handle ``hverdag-fest``)
bundles 3× Dagens Kaffe (200g) + 1× Ukens favoritt (250g) — two different
coffees in one curated pack with no standard tasting-kit token in its
URL/name, so ``postprocess_review_flags`` flags it ``is_tasting_kit`` so it
flows through the admin review queue rather than public search (per
docs/KIT_REVIEW.md).
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="langora-kaffebrenneri",
    display_name="Langøra Kaffebrenneri",
    roaster_name="Langøra Kaffebrenneri",
    website="https://www.langorakaffe.no",
    description="Norwegian specialty coffee roastery in Stjørdal, roasting "
    "single origins from around the world fresh on order and shipping "
    "free across Norway",
    requires_api_key=True,
    currency="NOK",
    country="Norway",
    status="available",
)
class LangoraKaffebrenneriScraper(ShopifyJsonScraper):
    """Scraper for Langøra Kaffebrenneri (langorakaffe.no) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Langøra Kaffebrenneri scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Langøra Kaffebrenneri",
            base_url="https://www.langorakaffe.no",
            products_json_urls=[
                "https://langorakaffe.no/collections/produkter/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Keep only genuine coffee; the product_type == "Kaffe" filter in
        # _extract_product_urls_from_store is the primary gate, with this
        # defensive net on top for any non-coffee slug that slips through.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "adventskalender",
            "merch",
            "tote",
            "sweatshirt",
            "t-skjorte",
            "kaffeklubb",
            "turkopp",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Pin the base NOK currency and remove the Accept-Language header so a
        # geo-localized presentment currency (e.g. GBP/EUR) served to a
        # datacenter IP can't override the real Norwegian-market prices.
        self.store_currency = "NOK"
        self._currency_detected = True
        self.headers.pop("Accept-Language", None)
        self.client._base_headers.pop("Accept-Language", None)
        session_headers = getattr(self.client._session, "headers", None)
        if session_headers:
            session_headers.pop("Accept-Language", None)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Langøra product URLs.

        Langøra's canonical/live product pages are the no-collection form
        ``https://www.langorakaffe.no/products/<handle>`` (confirmed via the
        product page's ``rel=canonical``), so strip the ``/collections/<slug>``
        segment the products.json base URL injects and normalize to the ``www``
        host.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only the coffee set.

        The full ``produkter`` shop mixes beans with equipment, merch, a
        subscription club and the seasonal Advent calendar. Filter on the
        Shopify ``product_type == "Kaffe"`` so only whole-bean coffee (and the
        multi-bag coffee packs) are kept; genuine non-bean items never reach
        the catalogue, while the multi-coffee bundle still flows through to
        ``_apply_product_flags`` for admin review.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify itself classifies as coffee.
            if product.get("product_type", "") != "Kaffe":
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

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean detail section.

        The Shopify JSON ``body_html`` is empty for the single origins, so all
        the bean detail (tasting notes, process, variety, producer, region,
        elevation and the "Nerdy stuff" accordion) lives on the rendered page
        in ``<main>``. We keep only that container to drop the header, footer,
        gallery and shipping banners, keeping token usage low.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify JSON context (name/price/variants) at the top of ``soup.body``
        AFTER this hook returns, so keeping a valid body preserves that data.
        """
        main = soup.find("main")
        if main is None:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        minimal.body.append(main)
        return minimal

    def _extract_currency_from_html(self, soup) -> str:
        """Pin the store currency to NOK.

        Langøra is a Norwegian roastery priced in NOK (the products.json prices
        are NOK). The site can serve a geo-localized presentment currency to a
        datacenter IP, which would otherwise override the correct base currency
        during extraction. Force NOK so the AI prices the beans correctly.
        """
        return "NOK"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to NOK (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "NOK"
        return bean

    def postprocess_review_flags(self, bean, url: str):
        """Flag Langøra's multi-coffee bundle for admin review.

        "Hverdag + Fest | 4-pk" (handle ``hverdag-fest``) is a curated pack of
        two different coffees — 3× Dagens Kaffe (200g) + 1× Ukens favoritt
        (250g). Its URL/name carry no standard tasting-kit token (the base
        patterns don't match "4-pk"), so the base heuristics miss it. Mark it
        ``is_tasting_kit`` so it lands in the admin review queue instead of
        public search (docs/KIT_REVIEW.md). Dagens Kaffe 4-pk (same blend x4)
        and Grut På Tur drip bags (a single coffee format) are not multi-coffee
        kits and stay unflagged.
        """
        if bean is not None and url and "hverdag-fest" in url:
            bean.is_tasting_kit = True
        return bean
