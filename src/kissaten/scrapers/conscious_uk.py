"""Conscious (consciousspeciality.com) scraper — Webflow Ecommerce with AI extraction.

Conscious (www.consciousspeciality.com, but the 301 canonical is the non-www
``consciousspeciality.com``) is the real UK Conscious entity, the successor to
the dead ``consciouscoffee.co.uk``. It is an independent UK specialty coffee
roaster — single origins, espresso/filter/allrounder blends and a decaf —
priced in GBP.

Platform (live probe 2026-08-24): **Webflow Ecommerce**. There is no Shopify
``products.json`` / ``collections.json`` and no WooCommerce ``wp-json``; the
storefront is server-rendered Webflow (``data-wf-site``,
``w-commerce-commerce*``), and prices/currency ship in a
``window.__WEBFLOW_CURRENCY_SETTINGS = {"currencyCode":"GBP",...}`` blob with
``£``-prefixed prices. Product pages render the full bean detail server-side
(name, origin country/region, tasting notes, variety, process, brewing, roast,
producer price-to-producer £/KG transparency), so no Playwright is needed and
standard AI extraction reads the rich HTML directly.

Discovery: the Webflow category pages (``/category/all``, ``/category/filter``
...) only render a small subset of the catalogue and expose no pagination
links, so they are not a reliable enumeration source. The static
``/sitemap.xml`` lists every product as a literal ``/product/<slug>`` URL (33
at probe time) and is used as the authoritative discovery source, matching
``/product/`` paths. ``/product/discovery-pack`` returns the shop listing (a
Webflow 404-fallback quirk, not a real product) and never appears in the
sitemap, so it is not picked up.

Exclusions: the base ``_get_excluded_url_patterns`` (which
``is_coffee_product_url`` consults) already drops the four non-coffee
catalogue entries — ``conscious-choice-subscription`` (subscription) and the
``hario-v60-*`` equipment (server, filter papers, plastic dripper) — because
``subscription`` / ``hario`` / ``v60`` / ``filter-papers`` / ``dripper`` are
default patterns. ``pick-mix`` (a Brewed x Conscious collaboration blend) and
``regular-crush`` (a filter blend) are genuine coffee and are deliberately
kept; neither is a sampler/tasting kit, so no review-flag override is needed.
The remaining 29 products are whole-bean coffees.

Stock: Webflow Ecommerce renders both the add-to-cart form and a hidden
``display:none`` "Not in stock" state in the HTML, flipping between them
client-side based on SKU inventory — so the static HTML cannot determine
per-variant sold-out status. The scraper therefore treats every sitemap-listed
product as part of the current catalogue (``create_diffjson_stock_updates``
keeps them in stock) and emits out-of-stock diffs only when a product genuinely
disappears from the sitemap, preserving the base class's failed-listing guard.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

SITEMAP_URL = "https://consciousspeciality.com/sitemap.xml"


@register_scraper(
    name="conscious-uk",
    display_name="Conscious Coffee",
    roaster_name="Conscious Coffee",
    website="https://consciousspeciality.com",
    description="Independent UK speciality coffee roaster of high-quality, "
    "single-origin, ethical coffees for espresso and filter — with "
    "producer-level price transparency.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ConsciousUKScraper(BaseScraper):
    """Scraper for Conscious (consciousspeciality.com) — Webflow Ecommerce.

    Discovers coffee product URLs from the static ``/sitemap.xml`` (the only
    complete catalogue source) and uses AI extraction on the server-rendered
    product pages, pinned to GBP.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Conscious Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Conscious Coffee",
            base_url="https://consciousspeciality.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (gracefully degrades to None when no API key
        # is configured, matching the base class, so connectivity-only smoke
        # tests work without a key).
        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Return the sitemap URL used for product discovery.

        The Webflow category pages only render a small subset with no
        pagination, so the static ``/sitemap.xml`` (which lists every product
        as a ``/product/<slug>`` URL) is the authoritative enumeration source.

        Returns:
            List containing the sitemap URL.
        """
        return [SITEMAP_URL]

    # Non-coffee catalogue entries are all dropped by the base
    # _get_excluded_url_patterns (via is_coffee_product_url): subscription,
    # hario, v60, filter-papers, dripper. No custom exclude list needed.

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the sitemap.xml.

        Webflow publishes a static sitemap with one ``<loc>`` per page. We keep
        only the ``/product/<slug>`` entries (which are already canonical and
        exclude non-coffee equipment/subscription via the base
        ``is_coffee_product_url``), then deduplicate.

        # Sold-out detection: sitemap-based — the sitemap has no listing-card
        # text and Webflow flips the add-to-cart state client-side, so every
        # sitemap-listed product is treated as part of the current catalogue;
        # out-of-stock diffs only fire when a product leaves the sitemap.

        Args:
            store_url: URL of the sitemap XML.

        Returns:
            List of coffee product URLs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            logger.error(f"Failed to fetch sitemap: {store_url}")
            return []

        product_urls: list[str] = []
        for loc in soup.select("loc"):
            url = loc.get_text(strip=True)
            if not url:
                continue
            # Only coffee product detail URLs under /product/.
            if not self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                continue
            product_urls.append(url)

        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} coffee product URLs from sitemap")
        return unique_urls

    async def _scrape_new_products(self, product_urls: list[str], use_optimized_mode: bool = False) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction on server-rendered HTML.

        The Webflow product pages are server-rendered (no Playwright needed)
        and carry rich bean detail, so we use standard AI extraction on the
        HTML (no optimized/screenshot mode) at default concurrency.

        Args:
            product_urls: List of URLs for new products.
            use_optimized_mode: Accepted for the base-class signature; the
                Webflow HTML is rich enough that optimized/screenshot mode is
                not needed, so it is not forwarded.
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Webflow renders product pages server-side
            use_optimized_mode=False,  # Rich HTML — standard extraction is enough
            translate_to_english=False,  # UK site — already in English
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin GBP as the store currency.

        Webflow exposes currency via ``window.__WEBFLOW_CURRENCY_SETTINGS``
        (``currencyCode: GBP``) and ``£`` prices rather than
        ``og:price:currency`` / Shopify metadata that the base detector looks
        for, so we force GBP as a final guard — confirmed by the live feed.
        """
        bean.currency = "GBP"
        return bean
