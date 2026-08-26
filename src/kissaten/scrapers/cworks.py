"""Cworks (The Coffeeworks) scraper implementation with Shopify JSON extraction.

The Coffeeworks (www.cworks.co.uk) is a UK roaster running a Shopify storefront.
The curated whole-bean catalogue lives on the ``/collections/coffeebeans``
collection, and every coffee product carries a ``Whole Bean`` variant, so the
whole-bean set is that collection minus the gift card and the money-saving
``bundle-deal`` combo packs. Curated multi-bean sampler sets (``*-collection``)
are NOT excluded: they are extracted and flagged ``is_tasting_kit`` so they
land in the admin review queue instead of public search.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cworks",
    display_name="Cworks",
    roaster_name="Cworks",
    website="https://www.cworks.co.uk",
    description="UK roaster known for dessert-inspired blends, half-caffeine "
    "and single-origin coffees sold whole-bean or pre-ground.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CWorksScraper(ShopifyJsonScraper):
    """Scraper for The Coffeeworks (cworks.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Cworks scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cworks",
            base_url="https://www.cworks.co.uk",
            products_json_urls=[
                "https://www.cworks.co.uk/collections/coffeebeans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The store prices in GBP (its home market). Pin the currency so
        # Shopify's geo-detection can't rewrite prices to the caller's market.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude the non-bean gift card and the money-saving two-bag
        # "bundle deal" combo packs. Curated sampler sets ("*-collection")
        # are intentionally NOT excluded -- they are extracted and flagged as
        # tasting kits for the admin review queue.
        self.exclude_slugs = [
            "bundle-deal",
            "gift-card",
            "giftcard",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Cworks product URLs to the canonical ``/products/<handle>`` form.

        The site's real product pages live at ``/products/<handle>`` (no
        collection segment). ``ShopifyJsonScraper`` builds collection-prefixed
        URLs from the products.json base, so strip the collection segment here.

        Args:
            url: Original product URL

        Returns:
            Canonical ``https://www.cworks.co.uk/products/<handle>`` URL
        """
        prefix = "https://www.cworks.co.uk"
        if url.startswith(f"{prefix}/collections/"):
            # /collections/<slug>/products/<handle> -> /products/<handle>
            url = f"{prefix}/products/{url.rsplit('/products/', 1)[-1]}"
        return url

    def postprocess_review_flags(self, bean, url: str):
        """Flag The Coffeeworks' curated multi-bean sampler sets for review.

        The ``*-collection`` products (e.g. "Best Sellers Collection",
        "Big & Bold Collection") bundle several 250g bags into one sampler set.
        Their handles carry no tasting-kit token, so mark them as tasting kits
        here so they land in the admin review queue rather than public search.

        Args:
            bean: The extracted CoffeeBean
            url: The product URL the bean was extracted from

        Returns:
            The (possibly mutated) CoffeeBean
        """
        if bean is not None and "-collection" in str(url).lower():
            bean.is_tasting_kit = True
        return bean
