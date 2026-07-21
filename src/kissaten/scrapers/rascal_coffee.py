"""Rascal Coffee scraper implementation with Shopify JSON + label image extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rascal-coffee",
    display_name="Rascal Coffee",
    roaster_name="Rascal Coffee",
    website="https://rascal.coffee",
    description="Guatemalan specialty coffee roaster based in London (Hackney) sourcing "
    "direct-trade single origin coffees from Guatemala and beyond",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RascalCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Rascal Coffee (rascal.coffee) using Shopify products.json + label images."""

    def __init__(self, api_key: str | None = None):
        """Initialize Rascal Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Rascal Coffee",
            base_url="https://rascal.coffee",
            products_json_urls=["https://rascal.coffee/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (subscriptions, gift cards, etc.)
        self.exclude_slugs = [
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
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "sampler",
            "taster-pack",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so URLs are canonical (e.g. /products/<handle>).

        ``ShopifyJsonScraper`` builds URLs relative to the products.json base
        (``/collections/coffee/products/<handle>``). Rascal's canonical URLs
        omit the collection segment.
        """
        if "/collections/" in url and "/products/" in url:
            parts = url.split("/products/")
            if len(parts) > 1:
                return f"{self.base_url}/products/{parts[1]}"
        return url

    def _format_shopify_context(self, product: dict[str, Any]) -> str:
        """Inject Shopify metadata plus the coffee label image URL for AI extraction."""
        html_parts = [super()._format_shopify_context(product)]

        images = product.get("images", [])
        label_keywords = ("label", "etiqueta", "etiquetas")
        label_images: list[str] = []
        for img in images:
            src = str(img.get("src", ""))
            if any(kw in src.lower() for kw in label_keywords):
                label_images.append(src)

        # Fallback: if no explicit label image, use the second image if available
        # (Rascal typically pairs a bag shot with a label/flat-lay shot), else first.
        if not label_images and len(images) >= 2:
            label_images = [str(images[1].get("src", ""))]
        elif not label_images and images:
            label_images = [str(images[0].get("src", ""))]

        if label_images:
            html_parts.append('<div id="coffee-label-images" style="display:none;">')
            for img_url in label_images:
                html_parts.append(f'<img src="{img_url}" data-type="coffee-label" />')
            html_parts.append("</div>")

        return "\n".join(html_parts)

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Use the product label image (downloaded) for visual AI extraction.

        No product page is fetched; the Shopify JSON context (with the label
        image URL injected) is the only text context, and the downloaded label
        image is passed as ``screenshot_bytes`` to the AI extractor.
        """
        url_str = str(product_url)

        # Ensure currency context is available even without product page fetches.
        if not self._currency_detected and self.products_json_urls:
            collection_url = self.products_json_urls[0].replace("/products.json", "")
            try:
                collection_soup = await self.fetch_page(collection_url)
                if collection_soup:
                    currency = self._extract_currency_from_html(collection_soup)
                    if currency:
                        self.store_currency = currency
                        self._currency_detected = True
                        logger.info(f"Detected store currency from collection page: {currency}")
            except Exception as e:
                logger.warning(f"Failed to fetch collection page for currency detection: {e}")
        page_currency = self.store_currency

        # Build a soup purely from the (label-enriched) Shopify JSON context.
        if url_str in self._shopify_product_data:
            product_json = self._shopify_product_data[url_str]
            context_html = self._format_shopify_context(product_json)
            soup = BeautifulSoup(context_html, "lxml")

        # Locate the label image URL inside the injected context and download it.
        label_url: str | None = None
        label_div = soup.find("div", id="coffee-label-images")
        if isinstance(label_div, Tag):
            img = label_div.find("img", {"data-type": "coffee-label"})
            if isinstance(img, Tag):
                label_url = str(img.get("src", "")) or None

        screenshot_bytes = None
        if label_url:
            logger.info(f"Downloading label image for visual AI analysis: {label_url}")
            try:
                response = await self.client.get(label_url)
                response.raise_for_status()
                screenshot_bytes = response.content
            except Exception as e:
                logger.warning(f"Failed to download label image {label_url}: {e}")

        bean = await ai_extractor.extract_coffee_data(
            str(soup),
            url_str,
            screenshot_bytes=screenshot_bytes,
            use_optimized_mode=True,
            default_currency=page_currency,
        )

        if bean:
            bean.roaster = self.roaster_name
            return self.postprocess_extracted_bean(bean)

        return None
