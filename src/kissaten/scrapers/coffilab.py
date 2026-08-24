"""Coffi Lab scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffilab",
    display_name="Coffi Lab",
    roaster_name="Coffilab",
    website="https://coffilab.co.uk",
    description="UK speciality coffee roaster (Coffi Lab) roasting signature single "
    "origins and blends with a dog-lover identity. Each coffee is a 'Lab' "
    "(e.g. Fox Red, Yellow Lab, Black Lab) and many carry Great Taste awards.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CoffilabScraper(ShopifyJsonScraper):
    """Scraper for Coffi Lab (coffilab.co.uk) using Shopify products.json.

    The store is Shopify and serves a curated ``/collections/coffee`` collection
    (verified live: 16 published products, all ``product_type`` "Coffee").
    Subscriptions, personalized-gift repackagings and companion merch live in
    separate collections and are intentionally not scraped (see module notes).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Coffi Lab scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffilab",
            base_url="https://coffilab.co.uk",
            products_json_urls=[
                "https://coffilab.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency (GBP — verified live via /meta.json and the UK
        # home market) so Shopify Markets geolocation on a datacenter IP can
        # never stamp a converted currency onto the beans.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated /collections/coffee holds only coffee products. Fox Red
        # Pods is coffee in single-serve pods (kept as coffee). The Lab Pack
        # and the Lab Duo range are curated sampler/trio boxes — those are NOT
        # excluded; they are extracted and review-flagged (see
        # _get_tasting_kit_url_patterns) so they land in the admin queue.
        self.exclude_slugs = [
            "subscription",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Extend the base kit/sampler URL patterns with Coffi Lab's box handles.

        Coffi Lab sells curated sampler boxes under handles like ``the-lab-pack``
        and ``lab-duo-great-taste`` / ``lab-duo-most-loved`` / ``lab-duo-light-medium`` /
        ``lab-duo-medium-dark`` / ``lab-duo-light-dark``. None match the base
        patterns, so without this override these boxes would be dropped when the
        AI returns them with no single origin. Flagging them keeps them in the
        admin review queue instead of silently discarding them.
        """
        return super()._get_tasting_kit_url_patterns() + [
            "lab-pack",
            "lab-duo",
        ]

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Coffi Lab product URLs.

        The live site canonicalizes to ``https://coffilab.co.uk/products/<handle>``
        (no collection segment — confirmed via the page ``rel=canonical`` and
        ``og:url`` tags), so strip the collection segment the base class builds
        from the products.json base.
        """
        url = url.replace("/collections/coffee/products/", "/products/")
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Limit extraction to the product spec sheet for efficiency.

        Coffi Lab renders a compact ``div.product-details`` "About the coffee"
        block on each bean page (Origin / Roast Profile / Process / Altitude /
        Varieties / Tasting notes) that the products.json payload does NOT carry
        (no metafields in the JSON). Pruning the ~400 KB page to just this block
        keeps AI token usage low while preserving the altitude/variety/tasting
        notes fields. The Shopify JSON context (name, price, variants, body_html)
        is injected separately by the base class, so nothing is lost.

        On kit/box pages there is no ``about-coffee-list`` spec block — those
        pages fall back to the full soup (their description lives in body_html).
        """
        spec = soup.select_one("div.product-details")
        if spec is not None and spec.find(class_="about-coffee-list") is not None:
            logger.debug("Limiting extraction to div.product-details (about-coffee spec)")
            return spec
        return soup
