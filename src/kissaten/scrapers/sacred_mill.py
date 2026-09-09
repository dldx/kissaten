"""Sacred Mill scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sacred-mill",
    display_name="Sacred Mill",
    roaster_name="Sacred Mill",
    website="https://sacredmill.coffee",
    description="Specialty coffee roaster founded in 2019 by founders with African and Asian "
    "roots, importing directly traded Kenyan coffee to Poland before opening their Warsaw brew "
    "bar and Nairobi roastery; known for their Roots/Renaissance/Rare series and experimental "
    "co-fermentation lots processed at their own Los Patios HQ in Huila, Colombia.",
    requires_api_key=True,
    currency="PLN",
    country="Kenya",
    status="available",
)
class SacredMillScraper(ShopifyJsonScraper):
    """Scraper for Sacred Mill (sacredmill.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Sacred Mill scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sacred Mill",
            base_url="https://sacredmill.coffee",
            products_json_urls=["https://sacredmill.coffee/collections/all/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The storefront serves all its European markets in PLN (base currency, rate
        # 1.0), but Shopify Markets can serve geo-converted prices to datacenter IPs.
        # Pin the base currency so the detection path (which would read the
        # geo-converted value) is skipped entirely.
        self.store_currency = "PLN"
        self._currency_detected = True

        # No curated coffee-only collection exists (coffee is split across the
        # filter/espresso/rare/renaissance/roots/drip-bags collections), so we use
        # collections/all and exclude merch, spirits and green-coffee lots. Drip bags
        # and any sampler-style products stay in and flow through the review flags.
        self.exclude_slugs = [
            "gift-card",
            "subscription",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "tote-bag",
            "sweatshirt",
            "liqueur",
            "green-coffee",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the site's canonical /products/<handle> form.

        The products.json endpoint is /collections/all/products.json, but the site's
        real (and historically archived) product pages live at /products/<handle>.
        """
        return url.replace("/collections/all/products/", "/products/")

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the page to the main product section for token-efficient extraction.

        Sacred Mill product pages keep all the bean detail (Flavor Profile, Cup
        Score, Terroir, Producers, Altitude, Variety, Process — Shopify metafields
        that products.json does not carry) in the theme's ``__main`` product
        section; header, footer, related products and promo/cookie overlays can be
        dropped.
        """
        for selector in (
            'div[class*="shopify-section"][class*="__main"]',
            'section[class*="__main"]',
            "main",
        ):
            main = soup.select_one(selector)
            if main:
                logger.debug(f"Limiting extraction to {selector}")
                return BeautifulSoup(str(main), "lxml")
        return soup
