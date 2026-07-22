"""Square Mile Coffee Roasters scraper using Shopify products.json with first-image disambiguation."""

import logging
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="square-mile",
    display_name="Square Mile Coffee Roasters",
    roaster_name="Square Mile Coffee Roasters",
    website="https://shop.squaremilecoffee.com",
    description="Speciality coffee roaster founded in 2008 and based in London, United Kingdom.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SquareMileCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Square Mile using Shopify products.json.

    Square Mile rotates coffees seasonally under stable product handles
    (``red-brick``, ``sweetshop``, ``decaf-espresso``, …): at any given time
    each handle maps to exactly one coffee, but the same handle is reused
    for a different lot/bean every few months. The product title does NOT
    change with rotation, but the first product image does — Shopify CDN
    URLs carry a ``?v=<timestamp>`` version parameter that updates when a
    new image is uploaded. We use that version as the URL fragment so a
    rotation produces a new URL: the new bean is scraped fresh while the
    old URL drops out of products.json and the base scraper's stock-update
    logic marks the previous bean as out-of-stock, preserving history.

    Roast profile (Espresso/Filter/Both) is derived from the Shopify ``tags``
    field in ``postprocess_extracted_bean`` since Square Mile tags every
    coffee with ``espresso`` or ``filter`` (or both).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Square Mile scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Square Mile Coffee Roasters",
            base_url="https://shop.squaremilecoffee.com",
            products_json_urls=[
                "https://shop.squaremilecoffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
            custom_headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )

        # Exclude packs and bundles (not individual coffees).
        self.exclude_slugs = [
            "summer-coffee-pack",
            "the-filter-tasting-pack",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoint lives under ``/collections/coffee``, so
        the default URL construction yields ``/collections/coffee/products/…``.
        Historical bean data uses the canonical ``/products/<handle>`` form,
        so we strip any ``/collections/<slug>`` segment here. Any ``#fragment``
        (used for image-version disambiguation) is preserved.
        """
        if "/products/" in url:
            handle_and_rest = url.split("/products/")[-1]
            fragment = ""
            if "#" in handle_and_rest:
                handle, fragment = handle_and_rest.split("#", 1)
                fragment = "#" + fragment
            else:
                handle = handle_and_rest
            return f"{self.base_url}/products/{handle}{fragment}"
        return url

    @staticmethod
    def _image_variant(image_src: str) -> str | None:
        """Extract the ``?v=<id>`` version parameter from a Shopify CDN URL."""
        return parse_qs(urlparse(image_src).query).get("v", [None])[0]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from products.json, one per product.

        Each URL is suffixed with ``#<image-version>`` (the ``?v=<timestamp>``
        parameter of the first product image) so that when Square Mile rotates
        the coffee under a stable handle (e.g. ``red-brick`` v88 → v89), the
        image changes and the fragment changes, producing a new URL. The
        previous bean's URL then drops out of the catalog and the base
        scraper marks it out-of-stock, while the new bean is scraped fresh.

        Args:
            store_url: URL of the products.json endpoint

        Returns:
            List of disambiguated product URLs (one per product)
        """
        products = await self._fetch_all_shopify_products(store_url)
        base_path = store_url.replace("/products.json", "")
        found_urls: list[str] = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            if not self.is_coffee_product_name(product.get("title", "")):
                continue

            product_base_url = self.preprocess_product_url(f"{base_path}/products/{handle}")
            url_base = product_base_url.split("#", 1)[0]

            images = product.get("images", [])
            if images:
                first_image_src = images[0].get("src", "") or ""
                version = self._image_variant(first_image_src) or str(images[0].get("id", ""))
                url = f"{url_base}#{version}"
            else:
                url = url_base

            self._shopify_product_data[url] = product
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            if self.is_coffee_product_url(url_base):
                found_urls.append(url)

        return found_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Set roast profile from Shopify ``tags`` if present.

        Square Mile tags every coffee with ``espresso`` and/or ``filter`` in
        the products.json ``tags`` array. We use those to override the
        AI-extracted roast profile, since the tags are authoritative.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            Postprocessed CoffeeBean with roast_profile set from tags
        """
        url_str = str(bean.url)
        product = self._shopify_product_data.get(url_str)
        if product:
            tags = product.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            tags_lower = {t.lower() for t in tags}

            has_espresso = "espresso" in tags_lower
            has_filter = "filter" in tags_lower

            if has_espresso and has_filter:
                bean.roast_profile = "Both"
            elif has_espresso:
                bean.roast_profile = "Espresso"
            elif has_filter:
                bean.roast_profile = "Filter"

            if bean.roast_profile:
                logger.info(f"Set roast_profile={bean.roast_profile} from tags: {tags}")

        return super().postprocess_extracted_bean(bean)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Keep only the ``section.main-product-section`` before AI extraction.

        Square Mile product pages contain navigation, footers, related
        products, and marketing content outside the product detail area.
        The product metadata we want the AI to extract lives in
        ``section.main-product-section``, so we replace the body's contents
        with just that section to avoid confusing the AI and wasting tokens.
        If the section (or the body) is missing, fall back to leaving the
        soup untouched.
        """
        if not soup.body:
            logger.info("No <body> found; leaving soup untouched")
            return soup
        section = soup.find("section", class_="main-product-section")
        if section is None:
            logger.info("No section.main-product-section found; leaving soup untouched")
            return soup
        section.extract()
        for child in list(soup.body.children):
            if hasattr(child, "decompose"):
                child.decompose()
        soup.body.append(section)
        return soup
