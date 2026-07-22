"""Wide Awake Coffee scraper using Shopify products.json with image-variant disambiguation."""

import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="wide-awake-coffee",
    display_name="Wide Awake Coffee",
    roaster_name="Wide Awake Coffee",
    website="https://wideawake.coffee",
    description="Speciality coffee roaster based in Brussels, Belgium.",
    requires_api_key=True,
    currency="EUR",
    country="Belgium",
    status="available",
)
class WideAwakeCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Wide Awake Coffee using Shopify products.json.

    Wide Awake reuses the same Shopify product handle for several distinct
    coffee beans (e.g. different origins sold under the same product name).
    The storefront disambiguates them visually using image variants, so we
    mirror that here by emitting ``<product_url>#<image-version>`` — one URL
    per image attached to a product — preserving the original behavior of
    the BaseScraper implementation that parsed ``product-card`` elements.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Wide Awake Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Wide Awake Coffee",
            base_url="https://wideawake.coffee",
            products_json_urls=[
                "https://wideawake.coffee/collections/frontpage/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            # Send the full product page screenshot alongside the injected
            # Shopify JSON so the AI can disambiguate same-name beans visually.
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (subscriptions, gear, café items, etc.).
        self.exclude_slugs = [
            "discovery-box",
            "subscription",
            "6kg",
            "steep-bags",
            "cascara",
            "matcha",
            "hojicha",
            "verbena",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoint lives under ``/collections/frontpage``, so
        the default URL construction yields ``/collections/frontpage/products/…``.
        Historical bean data uses the canonical ``/products/<handle>#<version>``
        form, so we strip any ``/collections/<slug>`` segment here.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url

    @staticmethod
    def _image_variant(image_src: str) -> str | None:
        """Extract the ``?v=<id>`` version parameter from a Shopify CDN URL."""
        return parse_qs(urlparse(image_src).query).get("v", [None])[0]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from products.json, expanding one URL per image variant.

        Wide Awake sells several distinct coffees under a single Shopify product,
        disambiguated by image. We replicate the original HTML-scraping behavior
        by emitting ``<product_url>#<image-version>`` for each image attached to
        a product so downstream AI extraction can pick the correct variant. Per-
        image stock status is derived from the variants bound to that image.

        Args:
            store_url: URL of the products.json endpoint

        Returns:
            List of disambiguated product URLs (one per image variant)
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

            # Map image id -> availability of any variant tied to that image.
            variants = product.get("variants", [])
            image_id_to_available: dict[Any, bool] = {}
            for variant in variants:
                image_id = variant.get("image_id")
                if variant.get("available", False):
                    image_id_to_available[image_id] = True
                elif image_id not in image_id_to_available:
                    image_id_to_available[image_id] = False

            any_variant_available = any(v.get("available", False) for v in variants)

            images = product.get("images", [])
            if not images:
                # No images: emit a single URL without a fragment as a fallback.
                self._shopify_product_data[product_base_url] = product
                self._shopify_stock_status[product_base_url] = any_variant_available
                if self.is_coffee_product_url(product_base_url):
                    found_urls.append(product_base_url)
                continue

            seen_versions: set[str] = set()
            for image in images:
                image_src = image.get("src", "") or ""
                # Mirror the original scraper, which used the `?v=<id>` query
                # param of the CDN URL as the disambiguator. Fall back to the
                # image id if the CDN URL lacks the version param.
                version = self._image_variant(image_src) or str(image.get("id", ""))
                if version in seen_versions:
                    continue
                seen_versions.add(version)

                url = f"{product_base_url}#{version}"

                # All variants of the product share the same JSON context so
                # the AI can pick the right one using the fragment hint.
                self._shopify_product_data[url] = product
                self._shopify_stock_status[url] = image_id_to_available.get(
                    image.get("id"), any_variant_available
                )

                if self.is_coffee_product_url(product_base_url):
                    found_urls.append(url)

        return found_urls

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Strip non-essential Shopify sections before AI extraction.

        Replicates the original ``fetch_page`` override: keep only the first
        four ``div.shopify-section`` elements (which contain the product
        details) and drop the rest (recommendations, footers, etc.) to avoid
        confusing the AI and wasting tokens.
        """
        shopify_sections = soup.find_all("div", class_="shopify-section")
        logger.info(f"Found {len(shopify_sections)} sections matching div.shopify-section")
        for section in shopify_sections[4:]:
            section.decompose()
        return soup
