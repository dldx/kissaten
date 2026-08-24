"""Inverness Coffee Roasting scraper implementation with Shopify JSON extraction.

Inverness Coffee Roasting Co. is an Inverness (Scottish Highlands) roastery
(invernesscoffeeroasting.co.uk). This scraper uses the curated ``coffee``
collection's products.json for discovery and stock status, then AI-extracts
bean detail from the rendered product page.

Shape decision: the products.json ``body_html`` carries only prose
descriptions (origin stories, brewing tips); the structured bean detail
(Region / Altitude / Harvest / Varietal / Milling Process / Cupping Notes /
Strength) lives exclusively on the rendered product page in
``div.extra-details`` inside ``div.product__info-wrapper``. So we scrape
product pages and prune the soup to that one info wrapper (1600-2600 chars of
text) for token-efficient AI extraction. Currency is pinned to GBP because the
store is UK-based (verified live: ``Shopify.currency = {"active": "GBP"}``).
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="inverness-coffee",
    display_name="Inverness Coffee Roasting",
    roaster_name="Inverness Coffee Roasting",
    website="https://invernesscoffeeroasting.co.uk",
    description="Specialty coffee roaster based in Inverness, Scottish "
    "Highlands, roasting single origins and signature blends from their "
    "Highland roastery.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class InvernessCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Inverness Coffee Roasting (invernesscoffeeroasting.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Inverness Coffee Roasting scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Inverness Coffee Roasting",
            base_url="https://invernesscoffeeroasting.co.uk",
            products_json_urls=[
                "https://invernesscoffeeroasting.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency (GBP — verified live via the homepage
        # Shopify.currency block) so Shopify Markets geolocation on a
        # datacenter IP can never stamp a converted currency onto the beans.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated /collections/coffee holds 19 live products. 17 are
        # whole-bean coffees; the only two non-beans are single-serve capsule
        # products (handles be-gone-yawn / strike-the-light-capsules), which
        # are excluded by explicit handle (the base URL pattern "capsules"
        # catches only the latter, whose handle contains the word). There are
        # no sampler/taster/gift-box products in this collection, so no
        # tasting-kit URL pattern override is needed; any kit the AI returns
        # is flagged for review by the base _apply_product_flags logic.
        self.exclude_slugs = [
            "be-gone-yawn",
            "strike-the-light-capsules",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize Inverness product URLs to the site's real form.

        The live site serves product pages at ``/products/<handle>`` (no
        collection segment) — confirmed by the product pages' canonical link
        tags and the sitemap. The base class builds collection-prefixed URLs
        from the products.json base, so strip the ``/collections/coffee``
        segment.
        """
        return url.replace("/collections/coffee", "")

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page to just the informative wrapper.

        Keeps ``div.product__info-wrapper`` — the sticky info column holding
        the product title, the ``div.extra-details`` sections (Lot Info with
        Region/Altitude/Harvest/Varietal/Process, Cupping Notes, Strength),
        and the price — for token-efficient AI extraction, discarding images,
        nav, and recommendation boilerplate. The wrapper is ~1600-2600 chars
        of text on every checked product.
        """
        new_soup = BeautifulSoup("<html><body></body></html>", "lxml")
        body = new_soup.body

        info_wrapper = soup.select_one("div.product__info-wrapper")
        if body is not None:
            if info_wrapper:
                body.append(info_wrapper.extract())

            if body.find_all(True):
                logger.debug("Pruned Inverness product page to div.product__info-wrapper")
                return new_soup
        return soup
