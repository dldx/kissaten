"""Little Fin Coffee Roastery scraper implementation with Shopify JSON extraction.

Little Fin Coffee Roastery (littlefinroastery.com) is a UK (Leigh-on-Sea/Southend,
Essex) roaster running a Shopify storefront. The curated ``/collections/the-coffee``
products.json carries the whole-bean catalogue (~10 whole-bean coffees, each with a
"Whole Bean" grind variant alongside espresso/moka/cafetiere/aeropress/drip grinds).
Product ``body_html`` is rich enough (description, roast level, tasting notes,
origin, process, altitude, SCA score) that we scrape purely from the Shopify JSON
context without fetching each product page.

The collection also mixes in wholesale listings, a gift card and coffee pods, all of
which are excluded via ``exclude_slugs``. Curated sampler/selection packs (Triple
Shot, The Five) are deliberately NOT excluded: ``postprocess_review_flags`` flags
them with ``is_tasting_kit`` so they land in the admin review queue instead of being
silently dropped. Product pages canonicalize to the no-collection
``/products/<handle>`` form, so ``preprocess_product_url`` strips the collection
segment to stay aligned with the site's real URLs.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="little-fin",
    display_name="Little Fin Coffee Roastery",
    roaster_name="Little Fin Coffee Roastery",
    website="https://www.littlefinroastery.com",
    description="Independent speciality roasters based in Leigh-on-Sea, Essex (Shopify storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class LittleFinScraper(ShopifyJsonScraper):
    """Scraper for Little Fin Coffee Roastery (littlefinroastery.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Little Fin Coffee Roastery scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Little Fin Coffee Roastery",
            base_url="https://www.littlefinroastery.com",
            products_json_urls=[
                "https://www.littlefinroastery.com/collections/the-coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The storefront serves the UK market by default (Shopify.currency
        # "GBP"). Pin GBP so a geo-localized storefront (which Shopify can serve
        # to non-local clients) can't convert prices.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude non-coffee items mixed into the curated collection: wholesale
        # listings, the gift card and coffee pods. Tasting-kit/sampler/
        # selection-pack products are intentionally NOT excluded here — the base
        # and the postprocess_review_flags hook flag them for the review queue.
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
            "mug",
            "tumbler",
            "pod",
            "experience",
            "cap",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Little Fin product URLs to the canonical /products/<handle> form.

        The products.json endpoint lives under ``/collections/the-coffee/``, so the
        base class builds collection-prefixed URLs. The site's real canonical
        product pages drop the collection segment, so we strip it here to keep the
        scraper's URLs aligned with the site (and with any historical data stored
        under the canonical form).

        Args:
            url: Original product URL (collection-prefixed).

        Returns:
            Canonical ``https://www.littlefinroastery.com/products/<handle>`` URL.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url

    def postprocess_review_flags(self, bean, url: str):
        """Flag Little Fin's curated selection-pack samplers as tasting kits.

        The base class flags kits whose URL or name carries a known kit token
        (``sampler``, ``tasting-kit``, …). Little Fin's curated samplers ship under
        plain handles ("triple-shot-3-selection-pack-espresso", "the-five-selection-
        pack-espresso") that none of those tokens match, so we extend detection to
        the roaster's own "selection pack" / "selection-pack" wording.

        Args:
            bean: The extracted CoffeeBean.
            url: The product URL the bean was extracted from.

        Returns:
            The bean, with ``is_tasting_kit`` forced True when it is a selection pack.
        """
        url_lower = str(url or "").lower()
        name = getattr(bean, "name", "") or ""
        name_lower = str(name).lower()
        if "selection pack" in name_lower or "selection-pack" in url_lower:
            bean.is_tasting_kit = True
        return bean

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Collect product URLs, keeping only whole-bean coffee products.

        The superclass already restricts to coffee products (``is_coffee_product_url``
        + ``is_coffee_product_name``), applies ``exclude_slugs`` and keys the Shopify
        product metadata by the preprocessed URL. This override additionally enforces
        the whole-bean filter: a product must have at least one "Whole Bean" variant
        to be kept. Non-bean items (cold-brew-only blends, pods, gift cards,
        wholesale) and samplers/taster packs are handled by the base logic — samplers
        are flagged for review, not dropped.

        Args:
            store_url: URL of the products.json endpoint.

        Returns:
            List of canonical whole-bean product URLs.
        """
        found_urls = await super()._extract_product_urls_from_store(store_url)

        whole_bean: list[str] = []
        for url in found_urls:
            product = self._shopify_product_data.get(url, {})
            variants = product.get("variants", [])
            if any("whole bean" in str(v.get("title", "")).lower() for v in variants):
                whole_bean.append(url)
            else:
                logger.debug(f"Skipping non-whole-bean product: {url}")

        return whole_bean
