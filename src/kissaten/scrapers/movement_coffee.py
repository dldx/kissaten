"""Movement Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="movement-coffee",
    display_name="Movement Coffee",
    roaster_name="Movement Coffee",
    website="https://movementcoffee.com",
    description="Stowe, Vermont roaster specializing in Panamanian coffees — including "
    "Hacienda Esmeralda Geisha lots — alongside light-roast single origins, house blends "
    "and small-batch seasonal releases.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class MovementCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Movement Coffee (movementcoffee.com) using Shopify products.json.

    Page extraction is required: the products.json ``body_html`` only lists
    tasting notes, while the page's collapsed ``Coffee Info`` accordion
    carries variety, roast level, farm and growing altitude.
    ``preprocess_product_soup`` prunes each page to the product description
    plus the accordions so the AI sees only bean-relevant content.

    Uses the curated ``buy-coffee`` collection. Sold-out lots (e.g. Esmeralda)
    remain listed with unavailable variants, which is expected — limited
    stock rotates frequently. The store exposes a multi-currency Shopify
    Markets selector, so the home currency is pinned.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Movement Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Movement Coffee",
            base_url="https://movementcoffee.com",
            products_json_urls=[
                "https://movementcoffee.com/collections/buy-coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The buy-coffee collection mixes in the cold-brew RTD pack and the
        # gift card; the rest guards against teas/merch/gear drifting into
        # the collection later. Subscriptions live in a separate collection.
        self.exclude_slugs = [
            "cold-brew",
            "gift-card",
            "subscription",
            "tea",
            "matcha",
            "t-shirt",
            "long-sleeve",
            "tote-bag",
            "travel-mug",
            "mug",
            "scale",
            "dripper",
            "grinder",
        ]

        # Pin the home-market currency (verified against /cart.js): the store
        # ships a multi-currency country/region selector (AUD/CAD/EUR/...),
        # so datacenter IPs may receive geo-converted prices.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Movement Coffee product URLs.

        Movement's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page to the description and detail accordions.

        Movement (Dawn theme) hides the Coffee Info / Shipping details in
        ``div.product__accordion`` sections next to the
        ``div.product__description``. We build a new minimal soup WITH a body:
        ShopifyJsonScraper injects the Shopify JSON context
        (name/price/variants) at the top of ``soup.body`` AFTER this hook
        returns, so keeping a valid body preserves that data.
        """
        keepers = soup.select("div.product__description, div.product__accordion")
        if not keepers:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for keeper in keepers:
            minimal.body.append(keeper)
        return minimal
