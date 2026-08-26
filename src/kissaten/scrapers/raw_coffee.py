"""RAW Coffee Roasters scraper implementation with Shopify page-JSON extraction.

RAW Coffee Roasters (www.rawcoffeeroasters.co.uk) is a UK specialty coffee
roaster on Shopify, priced in GBP. Its Leeds shop carries a small, curated
roasted-bean range (bubblegum, mill-hill, lullaby-ea-decaf, jasmine-honey,
amber-cake, cherry-truffle, velvet-forest, grape-fizz, peach-crumble).

Non-standard discovery — products.json is disabled:

Unlike most Shopify storefronts, this store returns a custom 404 for both
``/products.json`` and ``/collections.json``, so the standard Shopify
``products_json_urls`` discovery cannot enumerate the catalogue. Instead,
URL discovery parses ``/sitemap.xml`` (which is served normally) and keeps
only ``/products/<slug>`` URLs — a single fetch yields the full published
catalogue (~10 URLs at time of writing). The sitemap lists one duplicate
handle, ``jasmine-honey-copy`` (a copy of ``jasmine-honey``), which is dropped
so each bean is counted once.

Scraping product pages:

Because the JSON endpoints are disabled, the scraper cannot rely on a
products.json ``body_html`` payload for bean detail. Instead it fetches each
product *page* (``scrape_product_pages=True``) and extracts the structured
bean fields from the embedded Shopify graph JSON / JSON-LD ``Product`` block
(``gid://`` ids), which carries the description plus ``additionalProperty``
entries for origin, region, altitude, producer, farm, varietal, process and
tasting notes. ``fetch_page`` narrows product pages to that JSON-LD block so
the AI extractor receives the full bean detail without the surrounding page
markup (a token saving with no information loss).

Currency and stock:

The store prices exclusively in GBP, so ``store_currency`` is pinned to
``"GBP"`` and ``_currency_detected`` set ``True`` to skip geolocation
detection. Discovery is sitemap-based, so sold-out products remain in the
catalogue (they stay listed in the sitemap); the per-product stock state is
captured at scrape time by the AI extractor reading the page availability.
The Shopify stock-diff path treats every sitemap-listed product as part of the
current catalogue (in stock at the catalogue level), so a product genuinely
removed from the sitemap is still marked out of stock.

Samplers are not excluded here; if any appear they flow through the base
``_apply_product_flags`` review pipeline rather than being dropped.
"""

import json
import logging
import re

from bs4 import BeautifulSoup, Tag

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

SITEMAP_URL = "https://www.rawcoffeeroasters.co.uk/sitemap.xml"


@register_scraper(
    name="raw-coffee",
    display_name="RAW Coffee Roasters",
    roaster_name="RAW Coffee Roasters",
    website="https://www.rawcoffeeroasters.co.uk",
    description=(
        "RAW Coffee Roasters is a UK specialty coffee roaster based in Leeds, "
        "sourcing and roasting a small curated range of single-origin beans "
        "and decaf on the rawcoffeeroasters.co.uk Shopify store (GBP)."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RawCoffeeScraper(ShopifyJsonScraper):
    """Scraper for RAW Coffee Roasters (rawcoffeeroasters.co.uk) — Shopify.

    ``products.json`` / ``collections.json`` are disabled (custom 404), so
    catalogue discovery uses ``/sitemap.xml`` and bean extraction reads the
    embedded Shopify JSON-LD ``Product`` block on each product page.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize RAW Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        # products.json is disabled (custom 404) on this store, so no
        # products_json_urls are used: discovery is overridden to parse the
        # sitemap. The empty list is passed because the base class requires the
        # argument, but get_store_urls()/discovery never consult it.
        super().__init__(
            roaster_name="RAW Coffee Roasters",
            base_url="https://www.rawcoffeeroasters.co.uk",
            products_json_urls=[],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # RAW Coffee is a UK store priced in GBP. The storefront can geolocate
        # the datacenter IP to a non-GBP market, so pin the home currency and
        # mark it as detected to skip the collection-page detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # All sitemap /products/ URLs are roasted beans; genuine non-coffee
        # products (equipment, merch) are not published. Samplers are not
        # excluded here — they are flagged is_tasting_kit/requires_review by
        # the base review pipeline instead of being dropped.
        self.exclude_slugs: list[str] = []

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the enumeration source: the Shopify sitemap.

        ``/products.json`` and ``/collections.json`` are disabled on this
        store (custom 404), so the sitemap is the only reliable catalogue
        enumeration source.

        Returns:
            List containing the sitemap URL.
        """
        return [SITEMAP_URL]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Shopify sitemap.

        Parses ``<loc>`` entries, keeps only canonical ``/products/<slug>``
        paths, drops the sitemap's ``jasmine-honey-copy`` duplicate handle
        (a copy of ``jasmine-honey``), and filters to coffee products via the
        base URL-pattern check. Products are recorded in
        ``_shopify_stock_status`` so the Shopify stock-update path treats the
        sitemap catalogue as populated.

        Args:
            store_url: URL of the sitemap XML.

        Returns:
            List of de-duplicated coffee product URLs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        for loc in soup.find_all("loc"):
            url = self.resolve_url(loc.get_text(strip=True))
            if not url:
                continue
            url = self.preprocess_product_url(url)
            if "/products/" in url:
                product_urls.append(url)

        # De-duplicate while preserving order.
        product_urls = self.deduplicate_urls(product_urls)

        coffee_urls: list[str] = []
        for url in product_urls:
            # Drop the sitemap's duplicate copy handles (e.g. jasmine-honey-copy),
            # which are just stale copies of the canonical product.
            if self._is_copy_handle(url):
                logger.info(f"Skipping sitemap duplicate copy handle: {url}")
                continue
            if not self.is_coffee_product_url(url, required_path_patterns=["/products/"]):
                continue
            # Sitemap-listed products are part of the published catalogue. Record
            # them so the Shopify stock-diff path treats them as populated.
            self._shopify_stock_status[url] = True
            coffee_urls.append(url)

        logger.info(
            f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} "
            f"total from {store_url}"
        )
        return coffee_urls

    @staticmethod
    def _is_copy_handle(url: str) -> bool:
        """Return True if a product URL is a Shopify `-copy` duplicate handle.

        Shopify appends ``-copy`` (and ``-copy-2`` etc.) when a product is
        duplicated from the admin. RAW Coffee's sitemap exposes one such
        duplicate (``jasmine-honey-copy``); it is the same bean as the
        canonical ``jasmine-honey`` product, so it must not be counted twice.

        Args:
            url: Product URL to check.

        Returns:
            True if the URL ends in a ``-copy`` style duplicate handle.
        """
        path = url.rstrip("/").split("/")[-1]
        if not path:
            return False
        # Matches trailing "-copy", "-copy-2", "-copy-3", ... Shopify handles.
        return bool(re.search(r"-copy(-\d+)?$", path))

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product pages to the embedded product JSON-LD.

        RAW Coffee product pages carry a single ``application/ld+json``
        ``Product`` block (with ``@type == "Product"``) holding the description
        and ``additionalProperty`` origin/process/tasting-note fields the
        ``CoffeeBean`` schema needs. Narrowing the soup to that script block
        drops the surrounding Shopify page markup before it reaches the AI
        extractor — a token saving with zero information loss for the coffee
        details.

        The ``og:availability`` meta is appended so the AI extractor still
        receives the authoritative machine-readable stock signal.

        Listing pages (the sitemap XML) are left untouched.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            # Only narrow product detail pages, leave the sitemap listing untouched.
            if "/products/" not in (url or ""):
                return soup
            if soup is None:
                return None

            product_ld = None
            for script in soup.find_all("script", type="application/ld+json"):
                text = script.get_text(strip=True)
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(data, dict) and data.get("@type") == "Product":
                    product_ld = data
                    break

            if product_ld is None:
                logger.warning(f"No product JSON-LD found on {url}; returning full page")
                return soup

            # Build a minimal soup carrying only the product JSON-LD block so the
            # AI extractor works from the authoritative structured data.
            narrow_soup = BeautifulSoup("<html><body></body></html>", "lxml")
            if narrow_soup.body is None:
                return soup
            body = narrow_soup.body
            holder = narrow_soup.new_tag("div", attrs={"data-kissaten-product-json": "true"})
            holder.string = json.dumps(product_ld, indent=2)
            body.append(holder)

            # Inject availability so the AI gets the authoritative stock signal.
            avail_meta = soup.select_one('meta[property="og:availability"]')
            if avail_meta is not None:
                content = str(avail_meta.get("content", "")).strip()
                in_stock = content.lower() in ("instock", "in stock")
                marker = narrow_soup.new_tag(
                    "div", attrs={"data-kissaten-availability": content}
                )
                marker.string = (
                    f"Product availability: {content} "
                    f"({'in stock' if in_stock else 'out of stock'})"
                )
                body.append(marker)

            logger.debug(f"Narrowed soup to product JSON-LD for {url}")
            return narrow_soup

        except Exception as e:
            current_url = kwargs.get("url") or (args[0] if args else "?")
            logger.error(f"Error fetching page {current_url}: {e}")
            return None
