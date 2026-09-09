"""94 Celcius scraper implementation using Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="94-celcius",
    display_name="94 Celcius",
    roaster_name="94 Celcius",
    website="https://94celcius.com",
    description="French-speaking specialty coffee roaster based in Sainte-Julie on the "
    "South Shore of Montreal, Quebec (since 2017). Known for traceable single origins, "
    "experimental co-fermented lots, and espresso blends roasted on a Probat P12.",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class NinetyFourCelciusScraper(ShopifyJsonScraper):
    """Scraper for 94 Celcius (94celcius.com) using Shopify products.json.

    The storefront is bilingual (French by default, English at ``/en/``), so the
    scraper points at the English-locale ``products.json`` to get translated
    product content without any AI translation pass.

    The ``cafes`` collection is a curated coffee-only collection that exactly
    matches ``cafe-de-specialite``; samplers/trios/instant coffee are kept
    (they flow through with tasting-kit/review flags), while the subscription
    club and water-mineral additives are excluded.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the 94 Celcius scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="94 Celcius",
            base_url="https://94celcius.com",
            products_json_urls=[
                # English locale: body_html/titles come back translated to
                # English, so the JSON-only optimized mode is sufficient.
                "https://94celcius.com/en/collections/cafes/products.json",
            ],
            scrape_product_pages=False,  # body_html already carries origin/process/variety/elevation/notes
            cache_product_pages=False,  # JSON-only scrape; no page caching needed
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude the subscription club and non-coffee water additives only.
        # Samplers/trios (e.g. trio-espresso-classique) and instant coffee are
        # deliberately kept — they get flagged is_tasting_kit/requires_review
        # by the base pipeline instead of being dropped.
        self.exclude_slugs = [
            "le-club-expe",  # monthly subscription box
            "third-wave-water",  # water mineral additives, not coffee
        ]

        # Pin the home-market currency. The store serves localized markets
        # (/en/, /en-us/, /en-jp/) via Shopify Markets, so never let a
        # geo-detected currency override CAD.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, rescuing the surprise trio from the base filter.

        The base class drops any URL containing "surprise" (a pattern aimed at
        mystery-box/club products), but 94 Celcius's "Surprise Trio" is a
        one-off sampler of three coffee bags — a curated tasting kit that must
        flow through with the is_tasting_kit/requires_review review flags
        rather than being silently dropped.

        Args:
            store_url: The products.json URL

        Returns:
            List of product URLs including the rescued surprise trio
        """
        found_urls = await super()._extract_product_urls_from_store(store_url)
        found_set = set(found_urls)
        for url, product in self._shopify_product_data.items():
            if url in found_set:
                continue
            handle = product.get("handle", "")
            if "surprise" in url.lower() and not any(slug in handle for slug in self.exclude_slugs):
                if self.is_coffee_product_name(product.get("title", "")):
                    logger.info(f"Rescuing 'surprise' sampler from base exclusion: {url}")
                    found_urls.append(url)
        return found_urls

    def postprocess_review_flags(self, bean, url):
        """Flag the mystery "surprise" trio as a curated tasting kit.

        Args:
            bean: The extracted CoffeeBean
            url: The product URL the bean was extracted from

        Returns:
            The bean with is_tasting_kit set for surprise sampler URLs
        """
        if bean is not None and "surprise" in str(url).lower():
            bean.is_tasting_kit = True
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the locale/collection prefix to match the site's canonical URLs.

        The products.json base builds ``/en/collections/cafes/products/<handle>``
        URLs, but the store's canonical product pages are plain
        ``/products/<handle>`` (per rel=canonical on product pages).

        Args:
            url: Original product URL

        Returns:
            Canonical product URL without locale/collection segments
        """
        if "/products/" in url:
            handle = url.rsplit("/products/", 1)[1]
            return f"{self.base_url}/products/{handle}"
        return url
