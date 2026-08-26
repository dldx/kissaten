"""New Ground Coffee scraper implementation with Shopify JSON extraction.

New Ground Coffee (newgroundcoffee.com) is an Oxford-based social enterprise
that trains ex-offenders in specialty coffee. The shopfront is a *headless*
Shopify setup: the public ``www.newgroundcoffee.com`` is a custom SvelteKit
frontend (no public ``products.json``), and the machine-readable catalogue
lives on the myshopify host ``newgroundcoffee.myshopify.com/products.json``
(70 published products, one page at ``limit=250``).

The catalogue is typed, so we filter the root feed on Shopify's own
``product_type == "Coffee"``; that reproduces the roaster's curated
``collections/coffee`` collection exactly (verified: both return the same 20
handles). That set still mixes in Nespresso-compatible pods, which are
removed via ``exclude_slugs`` (``pods``); the remaining 16 are whole-bean
coffees. Equipment, merch, chocolate, subscriptions and gift cards are all
non-``Coffee`` types and are dropped by the type filter.

The Shopify ``body_html`` is unstructured marketing copy (no tasting notes,
process, or origin detail), but the rendered www product page carries the
bean fields the JSON lacks — tasting notes, country, region, varietal,
process and a sourcing story with altitude — all statically rendered inside
``div.ProductMain_product*`` (no tabs/carousels gate the specs). So the
scraper uses ``scrape_product_pages=True`` with ``use_optimized_mode=False``
and ``preprocess_product_soup`` pruning that page down to that section.

Canonical product URLs: the public frontend serves ``/product/<handle>``
(singular; confirmed via the page ``rel=canonical`` and the sitemap), and the
plural Shopify form ``www.newgroundcoffee.com/products/<handle>`` is a 308
redirect to it. ``preprocess_product_url`` therefore rewrites every
Shopify-hosted URL to ``https://www.newgroundcoffee.com/product/<handle>``.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="new-ground",
    display_name="New Ground Coffee",
    roaster_name="New Ground Coffee",
    website="https://www.newgroundcoffee.com",
    description="Oxford social enterprise roaster training ex-offenders in "
    "specialty coffee, offering single origins, seasonal blends and decaf.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class NewGroundScraper(ShopifyJsonScraper):
    """Scraper for New Ground Coffee (www.newgroundcoffee.com) using Shopify products.json.

    The headless store keeps its catalogue on the myshopify host, so the feed
    source is ``newgroundcoffee.myshopify.com/products.json`` with a
    ``product_type == "Coffee"`` filter (equivalent to the roaster's curated
    ``collections/coffee`` collection), and product pages are scraped from the
    canonical www domain where the real bean detail lives.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize New Ground Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="New Ground Coffee",
            base_url="https://www.newgroundcoffee.com",
            products_json_urls=[
                "https://newgroundcoffee.myshopify.com/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # GBP store (GB / United Kingdom). Shopify Markets geolocation can
        # hand the datacenter IP a converted currency, so pin the home
        # currency and mark it as detected to skip the detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude only genuine non-bean products in the Coffee type set: the
        # Nespresso-compatible pods (e.g. ``juice-pods``, ``big-house-pods``).
        # Sampler/selection/discovery items are NOT excluded so they flow
        # through the base _apply_product_flags pipeline into the admin
        # review queue. The current feed has no sampler products, so no custom
        # tasting-kit URL patterns are needed.
        self.exclude_slugs = [
            "pods",
            "pod",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Normalize every product URL to the canonical public form.

        The products.json source builds ``https://newgroundcoffee.myshopify.com/products/<handle>``
        URLs. The real storefront is ``www.newgroundcoffee.com`` where the
        canonical page is ``/product/<handle>`` (singular — confirmed via
        ``rel=canonical`` and the sitemap; the plural ``/products/`` form is a
        308 redirect there), so we rewrite the host and path accordingly. This
        keeps historical identity stable and makes the saved URL the one users
        actually visit.
        """
        handle = (
            url.split("/products/")[-1].split("?")[0]
            if "/products/" in url
            else url.rsplit("/", 1)[-1].split("?")[0]
        )
        return f"{self.base_url}/product/{handle}"

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The base-class filter (``is_coffee_product_url`` + ``is_coffee_product_name``)
        would pass the Coffee-typed pod and non-coffee items whose handles
        don't trip an exclude keyword, so we filter explicitly on the
        Shopify ``product_type == "Coffee"`` (the same set the roaster curates
        in ``collections/coffee``) before building the canonical URL.
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

            # Skip explicitly excluded product slugs (matches if slug is a
            # substring of the handle — e.g. the Coffee-typed Nespresso pods).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build the URL from the products.json base, then normalize it to
            # the canonical www.newgroundcoffee.com/product/<handle> form.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status.
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available.
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic.
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs (post-preprocess) so the
        # returned list is unique even before discover_all_product_urls dedups.
        return self.deduplicate_urls(found_urls)

    def preprocess_product_soup(self, soup):
        """Prune the product page to the bean-detail section.

        The SvelteKit-rendered page carries the tasting notes, country,
        region, varietal, process and sourcing story in the
        ``ProductMain_product`` block (hashed class), while the surrounding
        page is mostly chrome and dataLayer JSON. Keeping just that block
        gives the AI all the bean detail at a small token cost. Falls back to
        the full soup when the block is missing (layout change).
        """
        main = soup.select_one("[class*=\"ProductMain_product\"]")
        if main:
            minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
            body = minimal.body
            if body is not None:
                body.append(main)
                return minimal
        return soup
