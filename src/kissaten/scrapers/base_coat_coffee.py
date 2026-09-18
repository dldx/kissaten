"""Base Coat Coffee scraper implementation with Shopify JSON extraction.

Base Coat (basecoatcoffee.com) is an "extra light" / Nordic-profile US roaster
that sells coffee in limited, numbered "drops" from its shop in Grand Rapids,
Michigan. Every product in the store is a coffee (single origins, A/B
comparison sets, roast experiments, and garage-sale clearance lots) — there is
no equipment, merch, or subscription product to exclude.

Scrape shape: the products.json ``body_html`` carries the narrative cupping
notes, but the structured bean details (Varietal / Process / Region / Altitude /
"Funk" score / importer "Sourced by" line) live in a statically rendered spec
block on the product page, and the Farm & Producer, Coffee Varietal and
Processing, Cost Transparency, and Brewing and Resting Recommendation sections
live inside ``<details>`` accordions. The accordion content is present in the
raw HTML (no JS click needed), so we scrape product pages with
``preprocess_product_soup`` pruning the page down to the ``div.product-details``
block plus the ``div.accordion`` elements — no carousel/click handling required.

Known limitation: the roast-profile option on each variant (Ultralight /
Nordic Light / Light / Espresso-Drip) is a variant-level choice, and some
drop-history pages (e.g. ``drop-1``) are $0.00 archive placeholders with no
real variants; the AI extractor sees those as best it can from the injected
Shopify JSON context.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="base-coat-coffee",
    display_name="Base Coat",
    roaster_name="Base Coat",
    website="https://basecoatcoffee.com",
    description="Michigan 'extra light' / Nordic-profile roaster selling limited-drop "
    "single origins, A/B comparison sets, and ultralight roast experiments",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class BaseCoatCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Base Coat Coffee (basecoatcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Base Coat Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Base Coat",
            base_url="https://basecoatcoffee.com",
            # The store is split into the current `coffee` drop collection and
            # the `archives` collection of past releases; both are 100% coffee,
            # so together they cover the full catalogue without pulling in
            # non-coffee noise from collections/all.
            products_json_urls=[
                "https://basecoatcoffee.com/collections/coffee/products.json",
                "https://basecoatcoffee.com/collections/archives/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Every product in the catalogue is a coffee bean product (including
        # the A/B comparison sets and roast-experiment add-ons, which are
        # flagged as tasting kits downstream if the base-class heuristics
        # consider them sampler-like). Nothing to exclude by slug.
        self.exclude_slugs = []

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs. The store's products.json
        # reports plain USD prices, so make that authoritative.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Base Coat product URLs.

        Base Coat's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        This also makes products that appear in both the `coffee` and
        `archives` collections deduplicate to a single URL.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean-detail content.

        Base Coat keeps the description plus a "Varietal: / Process: /
        Region: / Altitude: / Funk: / Sourced by" spec block in
        ``div.product-details``, and its Farm & Producer, Coffee Varietal and
        Processing, Cost Transparency, and Brewing and Resting Recommendation
        sections inside ``<details>`` accordions (``div.accordion``). The
        accordion content is statically present in the HTML, so keeping those
        elements gives the AI all the bean information without page chrome,
        carousels, or recommendations.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects
        the Shopify JSON context (name/price/variants) at the top of
        ``soup.body`` AFTER this hook returns, so keeping a valid body
        preserves that data.
        """
        keep = soup.select("div.product-details, div.accordion")
        if not keep:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for element in keep:
            minimal.body.append(element)
        return minimal
