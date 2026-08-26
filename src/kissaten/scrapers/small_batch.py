"""Small Batch Coffee Roasters scraper implementation with Shopify JSON extraction.

Small Batch Coffee Roasters (www.smallbatchcoffeeroasters.co.uk) is a
specialty coffee roaster based in Brighton & Hove (UK) since 2006. The live
domain (2026-08-25) serves its Shopify storefront from
``www.smallbatchcoffeeroasters.co.uk`` — the legacy ``smallbatchcoffee.co.uk``
host redirects there. The catalogue is a curated range of espresso/blend and
single-origin beans priced in GBP.

Feed selection (live discovery, 2026-08-25): the roaster curates an ``all``
coffee collection at ``/collections/all-coffee`` which mixes 32 products —
13 whole-bean coffees, 4 curated multi-bean tasting sets, plus genuine
non-coffee items (pods, bundles, subscriptions, chocolate, pairings and a pod
machine). ``product_type`` is empty across the feed, so filtering is done by
slug. ``collections/coffee-1`` (``Coffee``) publishes 11 whole beans but omits
``ethiopia-aricha`` and ``cherry-velvet``, so ``all-coffee`` + slug filtering
is used instead.

Kit handling: the four curated tasting/sample sets (``*-discovery-kit``,
``*-connoisseur-set``, ``*-blend-set``) are samplers, NOT exclusions. The base
``_get_excluded_url_patterns`` drops any URL containing ``discovery``, which
would silently delete the two ``* Discovery Kit`` tasting sets, so
``_get_excluded_url_patterns`` strips that pattern here (same override as
``colonna.py`` / ``gold_box.py``). The base ``_apply_product_flags`` then
catches the two ``* Discovery Kit`` products via their ``Coffee Tasting Set`` /
``Single Origin Tasting Set`` names, while the two plain ``… Set`` products
carry no kit token in name or handle so ``postprocess_review_flags`` forces
``is_tasting_kit`` on them too — every sampler lands ``is_tasting_kit`` /
``requires_review`` in the admin review queue rather than being dropped or shown
to the public. Only genuine non-bean products (bundles of two named coffees,
pods, subscriptions, chocolate, the mocha bundle and the pod-machine ``Adventurer
Set``) are excluded.

Scrape mode: ``body_html`` in the products.json payload is uniformly structured
— a bolded tasting-note line followed by prose on origin/process — and the
variants carry grind, weight and GBP price. So the JSON-only path is used:
``scrape_product_pages=False`` with ``use_optimized_mode=True`` (the AI extracts
from the injected Shopify JSON context; the cheapest token option). Note that the
rendered product pages also carry a metafield spec table (COUNTRY/REGION/
PROCESS/VARIETAL/ALTITUDE) that the JSON lacks; per the build plan the JSON-only
path is used now, and a future upgrade could flip to page-scraping to enrich
those origin fields.

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed via
``rel=canonical`` on the live pages), so the collection segment produced by the
products.json base is stripped in ``preprocess_product_url``.

Currency: the store is UK-only and prices in the feed are plain GBP decimals
(no ``presentment_prices``), so ``store_currency`` is pinned to ``GBP`` and
``_currency_detected`` to True up front — a geo-detected market must never
overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="small-batch",
    display_name="Small Batch Coffee Roasters",
    roaster_name="Small Batch Coffee Roasters",
    website="https://www.smallbatchcoffeeroasters.co.uk",
    description="Specialty coffee roaster in Brighton & Hove (since 2006) "
    "roasting a curated, rotating set of espresso blends and single origins in "
    "small batches, priced in GBP.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SmallBatchScraper(ShopifyJsonScraper):
    """Scraper for Small Batch Coffee Roasters using Shopify products.json.

    Uses the curated ``all-coffee`` collection rather than
    ``collections/all``, and filters the feed down to whole-bean coffee plus
    curated tasting sets via ``exclude_slugs`` + ``postprocess_review_flags``.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Small Batch Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Small Batch Coffee Roasters",
            base_url="https://www.smallbatchcoffeeroasters.co.uk",
            products_json_urls=["https://www.smallbatchcoffeeroasters.co.uk/collections/all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Small Batch is a UK store priced in GBP. Pin the home currency and
        # mark it as detected so the collection-page currency-detection path
        # can never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only: multi-bean bundles, pods,
        # the pod subscription, chocolate/pairings, the mocha bundle, and the
        # pod-machine "Adventurer Set" (equipment). Deliberately NOT excluded:
        # the sampler/tasting-set products — the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue. Note
        # "gift-card"/"giftcard" (not a bare "gift") so a future coffee gift
        # handle is not caught.
        self.exclude_slugs = [
            "bundle",
            "pod",
            "subscription",
            "chocolate",
            "mocha",
            "adventurer",
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
            "capsule",
            "cold-brew-cans",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Small Batch product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical``), so strip the
        ``/collections/all-coffee`` segment that the products.json base URL
        injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def _get_excluded_url_patterns(self) -> list[str]:
        """Keep curated discovery tasting sets out of the base exclusions.

        The base ``_get_excluded_url_patterns`` treats ``discovery`` as an
        equipment/subscription pattern, but here ``discovery`` only appears in
        the two curated ``* Discovery Kit`` coffee tasting sets — samplers that
        must flow through to be flagged (``is_tasting_kit`` / ``requires_review``)
        rather than dropped. Everything else in the base patterns stays.
        """
        return [p for p in super()._get_excluded_url_patterns() if p != "discovery"]

    def postprocess_review_flags(self, bean, url: str):
        """Force ``is_tasting_kit`` on the curated sampler sets.

        The base name-based flagger catches the two ``* Discovery Kit``
        products via their "Coffee Tasting Set" / "Single Origin Tasting Set"
        names, but the plain "Global Connoisseur Set" and "Small Batch Roaster's
        Blend Set" products carry no kit token in their name or handle. Their
        URLs identify them as curated multi-sample sets, so force
        ``is_tasting_kit`` here — ``_apply_product_flags`` then raises
        ``requires_review`` and they land in the admin review queue.
        """
        if not url:
            return bean
        url_lower = str(url).lower()
        if any(token in url_lower for token in ("discovery-kit", "connoisseur-set", "blend-set")):
            bean.is_tasting_kit = True
        return bean
