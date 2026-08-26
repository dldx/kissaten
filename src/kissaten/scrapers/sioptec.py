"""Sioptec scraper implementation with Shopify JSON extraction.

Sioptec (sioptec.co) is the coffee roasting arm of Siop Shop, a Manchester,
UK coffee business ("Coffee roasting services from Siop Shop in Manchester").
The storefront is a Shopify site priced in GBP.

Feed selection (live discovery, 2026-08-25): the canonical host is the
``www`` subdomain — ``https://sioptec.co`` 301-redirects to
``https://www.sioptec.co``. The root ``/products.json`` publishes 17
products (15 Coffee-type plus 2 merch: a tote and a t-shirt), while the
roaster curates a dedicated ``coffee`` collection —
``/collections/coffee/products.json`` — which publishes exactly 9
whole-bean coffees, all ``product_type == "Coffee"`` and none of them
equipment/merch/subscriptions. That curated collection is preferred: it is
cleaner (no merch to filter, smaller, cheaper for AI extraction) and needs
no per-product exclusions beyond a defensive safety net.

The ``coffee`` collection ``body_html`` is uniformly structured — ``<h4>``
sections for origin / variety / altitude / farm plus a prose producer note
that carries tasting notes and process — so the injection-only path is used:
``scrape_product_pages=False`` with ``use_optimized_mode=True`` (the AI
extracts from the Shopify JSON context, the cheapest token option; the
rendered product page mirrors the same content and adds nothing the JSON
lacks).

Kit handling: none of the whole-bean handles carry a tasting-kit token
(e.g. ``sample`` / ``taster`` / ``sampler``), so the base
``_apply_product_flags`` review pipeline is used unchanged — any future
sampler/taster product is flagged ``is_tasting_kit``/``requires_review``
into the admin review queue rather than excluded. Only generic non-coffee
tokens are excluded as a safety net in case the curated feed ever mixes
equipment/merch back in.

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed
via ``rel=canonical`` and ``og:url`` on the live product pages), so the
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
    name="sioptec",
    display_name="Sioptec",
    roaster_name="Sioptec",
    website="https://www.sioptec.co",
    description="Manchester (UK) coffee roasting arm of Siop Shop — a small "
    "curated range of single origins and micro-lots roasted in small "
    "batches, priced in GBP.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SioptecScraper(ShopifyJsonScraper):
    """Scraper for Sioptec (sioptec.co) using Shopify products.json.

    Uses the roaster's curated ``coffee`` collection rather than the root
    ``/products.json``, which mixes in 2 merch products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Sioptec scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sioptec",
            base_url="https://www.sioptec.co",
            products_json_urls=["https://www.sioptec.co/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Sioptec is a UK store priced in GBP. Pin the home currency and mark
        # it as detected so the collection-page currency-detection path can
        # never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The curated coffee
        # collection is entirely whole-bean, so these tokens are a defensive
        # safety net in case the feed later mixes in equipment/merch/
        # subscriptions. Deliberately NOT excluded: sampler / taster-pack /
        # gift-box slugs — the base class flags tasting kits (flag-don't-
        # exclude) so they land in the admin review queue rather than being
        # dropped. Note "gift-card" / "giftcard" (not a bare "gift") so a
        # future "Coffee Gift Pack" handle is not caught.
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
        """Standardize Sioptec product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/coffee`` segment that the
        products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
