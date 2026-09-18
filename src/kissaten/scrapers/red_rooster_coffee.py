"""Red Rooster Coffee scraper implementation with AI-powered extraction (Next.js + Sanity).

Red Rooster Coffee (Floyd, Virginia) runs a bespoke **Next.js storefront on
Vercel** backed by a Sanity CMS content lake with Shopify-powered commerce
(``Shopify Collective`` / Shopify variant ids). Platform diagnosis (2026-09):
no Shopify products.json endpoint (``/products.json`` and
``/collections/<slug>/products.json`` both 404), no WordPress/WooCommerce
(``/wp-json`` 308 to a stub), ``server: Vercel`` / ``x-powered-by: Next.js``
response headers, and a ``<script id="__NEXT_DATA__">`` JSON island on every
page — so the Shopify/Woo skills do not apply and the site is scraped from
its embedded Next.js data:

- Listing: ``/shop`` renders the coffee collection grid; its ``__NEXT_DATA__``
  ``props.pageProps.tiles`` carries every product tile (title, slug, cents,
  and the inner Shopify product with per-variant ``inventoryQuantity``).
- Detail: ``/products/<slug>`` pages embed the full Sanity document in
  ``__NEXT_DATA__`` — title, tags (roast/process/tasting), ``tastingNotes``
  titles, a portable-text ``description`` and ``productDetails`` (origin
  region, process, varietal, altitude, farm, fair-trade premiums). A compact
  soup is built from that JSON and fed to the AI extractor, avoiding the
  600+ KB rendered page.

Known limitations: sold-out coffees are omitted from the ``/shop`` grid
(also guarded here by the all-variants ``inventoryQuantity == 0`` check) and
reappear on the separate ``/archive`` page, which is intentionally not
scraped; subscription plans live under ``/subscribe`` (Recharge) and are not
product pages. Any future sampler/tasting kit is flagged
``is_tasting_kit``/``requires_review`` downstream instead of dropped.
"""

import json
import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="red-rooster-coffee",
    display_name="Red Rooster",
    roaster_name="Red Rooster",
    website="https://www.redroostercoffee.com",
    description="Certified B-Corp roaster in Floyd, Virginia, known for its organic blends "
    "and single origins in a converted textile mill.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class RedRoosterCoffeeScraper(BaseScraper):
    """Scraper for Red Rooster Coffee (Next.js + Sanity) with AI-powered extraction."""

    _SHOP_URL = "https://www.redroostercoffee.com/shop"
    _NEXT_DATA_MARKER = '<script id="__NEXT_DATA__" type="application/json">'

    # Belt-and-braces slug guard: the /shop grid is coffee-only, but bundles of
    # merch or future equipment/subscription products should never slip in.
    # Sampler/tasting kits are NOT excluded — they are flagged
    # is_tasting_kit/requires_review downstream.
    _excluded_url_slugs = [
        "subscription",
        "gift-card",
        "wholesale",
        "t-shirt",
        "tee",
        "shirt",
        "hoodie",
        "sweatshirt",
        "crewneck",
        "windbreaker",
        "tank",
        "onesie",
        "hat",
        "beanie",
        "mug",
        "tumbler",
        "poster",
        "sticker",
        "socks",
        "grinder",
        "syrup",
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize Red Rooster Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Red Rooster",
            base_url="https://www.redroostercoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (the Next.js coffee collection grid)."""
        return [self._SHOP_URL]

    @staticmethod
    def parse_next_data(soup_or_html) -> dict | None:
        """Extract and parse the ``__NEXT_DATA__`` JSON island from a page.

        Args:
            soup_or_html: BeautifulSoup object or raw HTML string

        Returns:
            Parsed JSON payload dict, or None if the island is missing/malformed.
        """
        html = str(soup_or_html)
        marker = RedRoosterCoffeeScraper._NEXT_DATA_MARKER
        start = html.find(marker)
        if start == -1:
            return None
        payload = html[start + len(marker):]
        end = payload.find("</script>")
        if end == -1:
            return None
        try:
            return json.loads(payload[:end])
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _portable_text_to_plain(blocks) -> str:
        """Flatten a Sanity portable-text block list into plain text."""
        parts: list[str] = []
        for block in blocks or []:
            if not isinstance(block, dict):
                continue
            for child in block.get("children") or []:
                text = child.get("text")
                if text:
                    parts.append(text)
        return " ".join(parts).strip()

    @classmethod
    def _format_price(cls, cents) -> str:
        """Format a cent amount as a USD price string."""
        try:
            return f"${int(cents) / 100:.2f}"
        except (TypeError, ValueError):
            return ""

    @classmethod
    def _tile_is_sold_out(cls, tile_product: dict) -> bool:
        """A tile is sold out when every variant has zero inventory."""
        variants = (tile_product.get("product") or {}).get("variants") or []
        if not variants:
            return False
        return all((v.get("inventoryQuantity") or 0) <= 0 for v in variants)

    @classmethod
    def _build_product_soup(cls, page_props: dict) -> BeautifulSoup:
        """Build a compact product soup from a product page's __NEXT_DATA__ props.

        Args:
            page_props: ``props.pageProps`` of the product page's __NEXT_DATA__

        Returns:
            BeautifulSoup object of the compact product markup.
        """
        parts: list[str] = ["<div>"]

        title = page_props.get("title")
        if title:
            parts.append(f"<h1>{title}</h1>")

        price = cls._format_price((page_props.get("product") or {}).get("cents"))
        if price:
            parts.append(f"<p>Price: {price}</p>")

        variants = (page_props.get("product") or {}).get("variants") or []
        sold_out = bool(page_props.get("disablePurchase")) or (
            bool(variants) and all((v.get("inventoryQuantity") or 0) <= 0 for v in variants)
        )
        availability = "Out of stock" if sold_out else "In stock"
        parts.append(f"<p>Availability: {availability}</p>")

        # Tags carry roast level / process / tasting theme titles.
        tags = [t.get("title") for t in page_props.get("tags") or [] if isinstance(t, dict) and t.get("title")]
        if tags:
            parts.append(f"<p>Tags: {', '.join(tags)}</p>")

        # Tasting notes are colour-chip entries with human titles.
        notes = [
            t.get("title") for t in page_props.get("tastingNotes") or [] if isinstance(t, dict) and t.get("title")
        ]
        if notes:
            parts.append(f"<p>Tasting notes: {', '.join(notes)}</p>")

        # Variant size × grind options.
        if variants:
            lines = ["Variants:"]
            seen: list[str] = []
            for v in variants:
                variant_title = v.get("variantTitle")
                if variant_title and variant_title not in seen:
                    seen.append(variant_title)
                    lines.append(f"- {variant_title} | Price: {cls._format_price(v.get('cents'))}")
            parts.append(f"<pre>{'<br>'.join(lines)}</pre>")

        # Sanity description paragraphs.
        description_text = cls._portable_text_to_plain(page_props.get("description"))
        if description_text:
            parts.append(f"<div>{description_text}</div>")

        # productDetails carry the structured spec sheet (origin region,
        # process, varietal, altitude, farm, premiums).
        details = [
            d.get("detail") for d in page_props.get("productDetails") or [] if isinstance(d, dict) and d.get("detail")
        ]
        if details:
            parts.append(f"<p>Details: {'; '.join(details)}</p>")

        parts.append("</div>")
        return BeautifulSoup("".join(parts), "html.parser")

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, narrowing product pages to their __NEXT_DATA__ content.

        Product detail pages are 600+ KB of React markup; the actual product
        content lives in the embedded ``__NEXT_DATA__`` JSON island, so the
        soup is narrowed to a compact rebuild of that JSON. Non-product pages
        are returned untouched.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object or None if fetch failed.
        """
        url = kwargs.get("url")
        if not url and len(args) > 0:
            url = args[0]

        soup = await super().fetch_page(*args, **kwargs)

        if soup and url and "/products/" in url:
            data = self.parse_next_data(soup)
            page_props = (data or {}).get("props", {}).get("pageProps") or {}
            if page_props.get("title"):
                return self._build_product_soup(page_props)
            logger.warning(f"No product __NEXT_DATA__ payload for {url}; returning full page soup")

        return soup

    # Sold-out detection: the /shop grid's __NEXT_DATA__ tiles carry per-variant
    # Shopify ``inventoryQuantity``; tiles with every variant at zero quantity
    # are skipped BEFORE coffee-URL filtering (sold-out coffees are usually
    # omitted from the grid entirely). The base class's listing-failure guard
    # still applies (a failed listing fetch returns [] and is recorded as a
    # failed store URL).
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the /shop page's __NEXT_DATA__ tiles.

        Args:
            store_url: URL of the shop page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        data = self.parse_next_data(soup)
        tiles = ((data or {}).get("props", {}).get("pageProps") or {}).get("tiles") or []
        if not tiles:
            logger.error(f"No product tiles found on {store_url}")
            return []

        product_urls: list[str] = []
        for tile in tiles:
            tile_product = tile.get("product") or {}
            slug = tile_product.get("slug")
            if not slug:
                # Banner/promo tiles carry no product.
                continue

            # Skip sold-out products before URL-pattern filtering
            if self._tile_is_sold_out(tile_product):
                logger.debug(f"Skipping sold-out product: {tile_product.get('title')}")
                continue

            url = f"{self.base_url}/products/{slug}"

            url_lower = url.lower()
            if any(pattern in url_lower for pattern in self._excluded_url_slugs):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue
            if not self.is_coffee_product_url(url, required_path_patterns=["/products/"]):
                continue

            product_urls.append(url)

        # Deduplicate while preserving order
        unique_urls = list(dict.fromkeys(product_urls))
        logger.info(f"Found {len(unique_urls)} in-stock coffee product URLs from {store_url}")
        return unique_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # product content is embedded in __NEXT_DATA__
            use_optimized_mode=False,
            translate_to_english=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD as the store currency.

        The Sanity payloads carry cent amounts with no ISO currency code, so
        the base class's currency detection never fires and the registry
        default could silently fall back to GBP. Pin the verified home
        currency (USD) here as a final guard.
        """
        bean.currency = "USD"
        return bean
