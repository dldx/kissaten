"""Colours Coffee scraper implementation with Shopify JSON extraction.

Colours Coffee (colourscoffee.com, Instagram @colourscoffeeco) is a UK
specialty coffee roaster that rebranded/moved from the now-dead
colourscoffee.co.uk to this Shopify storefront. The mission, per the site
copy, is to make complex specialty brews approachable for everyday coffee
lovers; the catalogue is a small curated range of single origins, blends and
a decaf, priced in GBP.

Feed selection (live discovery, 2026-08-24): ``collections/all`` mixes the 11
coffee beans with 10 equipment/merch products (Aeropress, filters, grinders,
cup, cap...). The roaster curates a dedicated ``beans`` collection instead —
``/collections/beans/products.json`` publishes exactly the 12 Coffee-type
products, one of which (``subscription-box``) is a subscription and is the
only exclusion needed. The remaining 11 are real beans: Gombe, La Coipa,
Jorge Osorio, Kilimbi Honey, Mosaic, Chapadão de Ferro, William Munchay,
Migoti Lot 9, Kanya, Nandi PB and Araponga EA Decaf.

The ``beans`` collection ``body_html`` is uniformly structured — ``<h3>``
sections for Tasting Notes, Process, Varietal, Altitude and Origin plus a
prose farm/producer description — so the injection-only path is used:
``scrape_product_pages=False`` with ``use_optimized_mode=True`` (the AI
extracts from the Shopify JSON context, cheapest token option; the rendered
product page mirrors the same content and adds nothing the JSON lacks).

Kit handling: none of the coffee handles carry a tasting-kit token, so the
base ``_apply_product_flags`` review pipeline is used unchanged — any future
sampler/taster product is flagged ``is_tasting_kit``/``requires_review`` into
the admin review queue rather than excluded. Only the ``subscription-box`` is
excluded here, along with generic non-coffee tokens as a safety net in case
the collection feed ever mixes equipment/merch back in.

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed
via ``rel=canonical`` / ``og:url`` on the live product pages), so the
collection segment produced by the products.json base is stripped in
``preprocess_product_url``.

Currency: the store ships SQL ``Shopify.currency = {"active":"GBP", ...}``
on product pages and prices are GBP, so ``store_currency`` is pinned to
``GBP`` and ``_currency_detected`` to True up front — a geo-detected market
must never overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="colours-coffee",
    display_name="Colours Coffee",
    roaster_name="Colours Coffee",
    website="https://colourscoffee.com",
    description="UK specialty coffee roaster bridging the gap between complex "
    "specialty brews and everyday coffee lovers — a curated, rotating set of "
    "single origins and blends roasted in small batches.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ColoursCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Colours Coffee (colourscoffee.com) using Shopify products.json.

    Uses the roaster's curated ``beans`` collection rather than
    ``collections/all``, which mixes in 10 equipment/merch products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Colours Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Colours Coffee",
            base_url="https://colourscoffee.com",
            products_json_urls=["https://colourscoffee.com/collections/beans/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Colours Coffee is a UK store priced in GBP. Pin the home currency
        # and mark it as detected so the collection-page currency-detection
        # path can never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The curated beans
        # collection contains a single non-bean item (subscription-box);
        # the rest of these tokens are a defensive safety net in case the
        # feed later mixes in equipment/merch. Deliberately NOT excluded:
        # sampler / taster-pack / gift-box slugs — the base class flags
        # tasting kits (flag-don't-exclude) so they land in the admin
        # review queue rather than being dropped. Note "gift-card" /
        # "giftcard" (not a bare "gift") so a future "Coffee Gift Pack"
        # handle is not caught.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Colours Coffee product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/beans`` segment that the
        products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
