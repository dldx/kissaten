"""Subtext scraper implementation with Shopify JSON extraction.

Subtext Coffee Roasters (Toronto, Canada) runs a Shopify storefront at
subtext.coffee using the "Flow" theme with Shogun page-builder product
descriptions. The products.json ``body_html`` for most beans only carries
shipping/ordering copy, while the real bean detail (origin, process, variety,
cupping score) lives in the Shogun-rendered product page and the tasting notes
only appear in the page's ``<meta name="description">``. So we scrape product
pages and prune the soup to those two sources before AI extraction.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="subtext",
    display_name="Subtext",
    roaster_name="Subtext",
    website="https://www.subtext.coffee",
    description="Canadian specialty coffee roaster based in Toronto, known for a "
    "rotating seasonal menu of washed and high quality single-origin coffees with "
    "a cupping-score focused approach.",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class SubtextScraper(ShopifyJsonScraper):
    """Scraper for Subtext Coffee Roasters (subtext.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Subtext scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Subtext",
            base_url="https://www.subtext.coffee",
            products_json_urls=[
                "https://www.subtext.coffee/collections/filter-coffee-beans/products.json",
                "https://www.subtext.coffee/collections/espresso-coffee-beans/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The storefront serves the Canadian market by default (Shopify.currency
        # "CAD" rate 1.0). Pin CAD so a geo-localized storefront (which Shopify
        # can serve to non-local clients) can't convert prices.
        self.store_currency = "CAD"
        self._currency_detected = True

        # The two coffee collections are curated bean lists, but still hold a
        # test/sample product that is not a real single-origin bean.
        # "test-batch-1kg" is a placeholder test product; "seasonal-sample-box"
        # is a merch/sample item. Keep a small exclude list as a safety net
        # against these and any future sample/subscription/merch products.
        self.exclude_slugs = [
            "test",
            "seasonal-sample",
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "tee",
            "bandana",
            "hat",
            "tote",
            "sticker",
            "spoon",
        ]

        # `colombia-huila-fortune-washed-wp-decaf` appears in BOTH the
        # filter-coffee-beans and espresso-coffee-beans collections, so its
        # products.json carries two different collection-prefixed URLs that
        # BaseScraper's string-based de-dup does not collapse. Track handles
        # seen across collections to scrape each bean exactly once.
        self._seen_handles: set[str] = set()

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page for token-efficient AI extraction.

        Subtext renders its bean descriptions through Shogun. The worthwhile
        content is:
        - ``div.shogun-root``: the description body with origin/process/
          variety/cupping-score detail.
        - ``<meta name="description">``: carries the tasting notes, which are
          not repeated in the Shogun body.

        Keep only those two and drop page chrome (header/footer/nav, the huge
        Shogun scripts) so the AI sees the bean info without wasting tokens.
        The Shopify product JSON (name/price/variants) is injected separately
        after this hook, so pruning here is safe.
        """
        # Only prune the standalone product page; keep the full doc otherwise
        # (e.g. if the structure is unexpected).
        root = soup.select_one("div.shogun-root")
        meta = soup.find("meta", attrs={"name": "description"})
        if root is None and (meta is None or not meta.get("content")):
            return soup

        wrapper = soup.new_tag("div")
        wrapper["id"] = "subtext-product-info"
        if meta and meta.get("content"):
            p = soup.new_tag("p")
            p.string = meta["content"]
            wrapper.append(p)
        if root is not None:
            wrapper.append(root)
        return wrapper

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Collect product URLs, de-duplicating by Shopify handle across collections.

        Super builds one URL per product from each products.json endpoint. The
        decaf, ``colombia-huila-fortune-washed-wp-decaf``, is listed in both the
        filter and espresso collections, so without handle-based de-dup it would
        be scraped twice under two different collection-prefixed URLs. Skip any
        handle already seen by an earlier collection.
        """
        urls = await super()._extract_product_urls_from_store(store_url)
        unique: list[str] = []
        for url in urls:
            handle = url.rstrip("/").split("/products/")[-1]
            if handle in self._seen_handles:
                logger.debug(f"Skipping duplicate handle across collections: {handle}")
                continue
            self._seen_handles.add(handle)
            unique.append(url)
        return unique
