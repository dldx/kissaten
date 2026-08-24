"""Artisan Roast Coffee Roasters (Edinburgh) scraper implementation with Shopify JSON extraction.

Artisan Roast Coffee Roasters (artisanroast.co.uk) is a Scottish specialty
coffee roaster founded in 2007 with four cafes in Edinburgh. The store is
Shopify-hosted; the curated ``coffee`` collection is the site's canonical
coffee page and holds 16 products — the single origins (La Guaca, Banko
Gotiti, Rancho São Benedito, Sitio São Francisco, La Carolina, El Palto, La
Virgen, Bosques de San Francisco, …), the three house blends (Janszoon,
Trigonometry, Cobblestone), the decaf, and the Taster Pack kit. Every one of
the 16 has Shopify ``product_type == "Coffee"``, so filtering on that type
within the collection yields only beans plus the Taster Pack, which must flow
through and be flagged ``is_tasting_kit``/``requires_review`` (never excluded).

Product URLs are canonicalised to the no-collection form used by the live
site (``/products/<handle>``). For most single origins the products.json
``body_html`` carries only the tasting notes, while the rendered product page
holds a Coffee Info spec table (roast level, type, origin, region,
farm/producer, altitude, cultivar, process) plus Flavour Profile and brewing
accordions — so product pages are scraped with a ``preprocess_product_soup``
prune that keeps just those accordions and the tasting-notes subheading.

The store is GBP (Edinburgh), but Shopify can geo-convert pricing for
non-local client IPs, so the currency is pinned to GBP in ``__init__``.
"""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="artisan-roast",
    display_name="Artisan Roast Coffee Roasters",
    roaster_name="Artisan Roast Coffee Roasters",
    website="https://artisanroast.co.uk",
    description="Edinburgh-based Scottish specialty coffee roaster founded in 2007, "
    "known for single origin coffees and signature blends (Janszoon, "
    "Trigonometry, Cobblestone) served across four city cafes",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ArtisanRoastScraper(ShopifyJsonScraper):
    """Scraper for Artisan Roast Coffee Roasters (artisanroast.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Artisan Roast Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Artisan Roast Coffee Roasters",
            base_url="https://artisanroast.co.uk",
            products_json_urls=[
                "https://artisanroast.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The storefront is GBP (Edinburgh). Pin the currency so Shopify's
        # geo-localized market conversion — which can serve converted prices to
        # datacenter client IPs — can't overwrite it.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated coffee collection is a bean-only, type-filtered list, so
        # this excludes the genuine non-coffee product slugs the roaster sells
        # (equipment, merch, gift cards, subscriptions, masterclasses, bespoke)
        # as a defensive net in case any are ever added to the collection. The
        # Taster Pack is intentionally NOT excluded — it flows through and is
        # flagged is_tasting_kit / requires_review by the base class.
        self.exclude_slugs = [
            "grinder",
            "espresso-machine",
            "coffee-brewer",
            "paper-filter",
            "merch",
            "apparel",
            "mug",
            "tumbler",
            "gift-card",
            "gift-coffee-subscription",
            "office-subscription",
            "the-rare-club",
            "ongoing-subscription",
            "selection-ongoing",
            "masterclass",
            "bespoke",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Artisan Roast product URLs.

        Artisan Roast's canonical/live product pages are the no-collection form
        ``/products/<handle>`` (confirmed via the pages' ``rel=canonical``), so
        strip the ``/collections/<slug>`` segment that the products.json base
        URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee and the Taster Pack kit.

        The default base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative and would pass
        any future non-coffee product added to the collection. The curated
        ``coffee`` collection is entirely ``product_type == "Coffee"`` products
        (including the Taster Pack kit), so filter explicitly on the Shopify
        ``product_type == "Coffee"`` before building the URL.
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

            # Store metadata for later enrichment and stock status, keyed by the
            # canonical/formatted URL.
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
        """Filter the product page HTML down to the bean detail accordions.

        Artisan Roast hides the sourcing detail (roast level, type, origin,
        region, farm/producer, altitude, cultivar, process), flavour profile and
        brewing recommendations behind collapsible ``div.product__accordion``
        sections, with the tasting notes in ``div.product__subheading``. The
        accordion bodies are present in the static HTML, so keep only those plus
        the subheading for the AI.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify JSON context (name/price/variants) at the top of ``soup.body``
        AFTER this hook returns, so keeping a valid body preserves that data.
        """
        blocks = soup.select("div.product__accordion") + soup.select("div.product__subheading")
        if not blocks:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for block in blocks:
            minimal.body.append(block)
        return minimal

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the extracted bean's currency to the store currency (GBP)."""
        if bean is not None:
            bean.currency = self.store_currency
        return super().postprocess_extracted_bean(bean)
