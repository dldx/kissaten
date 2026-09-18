"""Dark Pony Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dark-pony",
    display_name="Dark Pony",
    roaster_name="Dark Pony",
    website="https://darkponycoffee.com",
    description="Specialty coffee roaster and cafe in Falmouth, Cornwall, roasting "
    "small batches of traceable single-origin coffees",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="experimental",
)
class DarkPonyScraper(ShopifyJsonScraper):
    """Scraper for Dark Pony Coffee (darkponycoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dark Pony scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Dark Pony",
            base_url="https://darkponycoffee.com",
            products_json_urls=["https://darkponycoffee.com/collections/coffee/products.json"],
            # The store's products.json carries an empty body_html and no tags;
            # the rendered page is the only source for origin/region/producer/
            # variety/elevation/process/importer details, so page scraping is
            # required (with soup pruning for token efficiency).
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # No exclusions needed: the curated coffee collection only holds beans
        # plus the Fermentation Project tasting kit (kept — flagged downstream).

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports GBP.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_soup(self, soup):
        """Limit extraction to the product info section for token efficiency.

        Dark Pony's bean details (origin, region, producer, variety, elevation,
        process, importer, green price) live in accordion blocks inside
        ``div.product__info-wrapper`` — statically present in the HTML.
        """
        info = soup.select_one("div.product__info-wrapper")
        if info:
            logger.debug("Limiting extraction to div.product__info-wrapper")
            return info
        return soup
