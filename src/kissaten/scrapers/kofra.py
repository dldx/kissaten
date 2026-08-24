"""Kofra Coffee scraper implementation with AI-powered extraction (Wix storefront).

Kofra Speciality Coffee Roasters (kofra.co.uk) is a small UK speciality
coffee roaster in Norwich with a Wix storefront (parastorage.com assets,
``data-hook`` attributes, GBP prices). The catalogue is small and stable: the
Wix store sitemap (``/store-products-sitemap.xml``) lists exactly three
products at time of writing (verified 2026-08-18 against the sitemap, the
homepage, and the ``/shop`` and ``/coffee`` category pages):

- ``/product-page/joy`` (Joy, an everyday seasonal blend)
- ``/product-page/brazil-es-blend`` (Brazil ES Blend)
- ``/product-page/telila-decaf`` (Los Nogales decaf)

The sitemap index (``/sitemap.xml``) lists no other product sitemaps, so this
three-product set is the complete catalogue.

Exclusions: no subscriptions, equipment, or services appear in the sitemap —
all three products are coffee. The base URL-pattern filter
(``required_path_patterns=["/product-page/"]``) is applied defensively anyway.

Sold-out handling: discovery is sitemap-based (no listing card text), so
sold-out products remain in the catalogue and their stock state is captured at
scrape time from the page text (Wix shows "Unavailable" in the add-to-cart
area when a product is out of stock). The ``og:availability`` meta (note: Wix
emits ``og:availability``, not ``product:availability``, on this store) is
injected into the narrowed ``<main>`` soup so the AI extractor receives the
authoritative machine-readable availability signal (InStock/OutOfStock).
Sold-out beans are never skipped at discovery — the base out-of-stock diffjson
path only fires when a product genuinely disappears from the sitemap.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kofra",
    display_name="Kofra Coffee",
    roaster_name="Kofra",
    website="https://www.kofra.co.uk",
    description=(
        "Kofra Speciality Coffee Roasters is a small UK coffee roaster in "
        "Norwich selling through the kofra.co.uk Wix store (GBP): a compact "
        "catalogue of seasonal single-origin and blend beans plus a decaf."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class KofraScraper(BaseScraper):
    """Scraper for Kofra Coffee (kofra.co.uk) — Wix storefront.

    Discovery is via the store-products-sitemap.xml because it is the only
    authoritative catalogue enumeration source (a single fetch lists every
    product page as a literal ``/product-page/<slug>`` path).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Kofra Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kofra",
            base_url="https://www.kofra.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the enumeration source: the Wix store-products sitemap.

        The sitemap lists all product pages as literal ``/product-page/<slug>``
        paths — a single fetch gives the full enumeration (3 products at time
        of writing).

        Returns:
            List containing the sitemap URL.
        """
        return ["https://www.kofra.co.uk/store-products-sitemap.xml"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the store-products sitemap.

        # Sold-out detection: sitemap-based — the sitemap has no listing-card
        # text, so sold-out products are kept in the catalogue and their stock
        # state is captured at scrape time from the page text and the
        # injected ``og:availability`` meta (InStock/OutOfStock). Sold-out
        # beans are never dropped at discovery.

        Parses ``<loc>`` entries, keeps only ``/product-page/`` paths and
        drops non-coffee products (subscriptions, equipment) via the base
        URL-pattern filter.

        Args:
            store_url: URL of the sitemap XML.

        Returns:
            List of coffee product URLs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        for loc in soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if url:
                product_urls.append(self.resolve_url(url))

        # De-duplicate while preserving order
        product_urls = list(dict.fromkeys(product_urls))

        # Filter to coffee products: keeps /product-page/ paths, excludes
        # subscriptions (via "subscription" in _get_excluded_url_patterns),
        # equipment, gift cards, etc.
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/product-page/"])
        ]

        logger.info(
            f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total from {store_url}"
        )
        return coffee_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Wix product pages are server-rendered, so httpx (``use_playwright=False``)
        suffices; no screenshot / translation is needed (UK site, English).

        Args:
            product_urls: List of URLs for new products.

        Returns:
            List of newly scraped CoffeeBean objects.
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Wix product pages render server-side (verified)
            use_optimized_mode=False,
            translate_to_english=False,
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the product content.

        This site's product pages have a single ``<main>`` element (id
        ``PAGES_CONTAINER``) holding the breadcrumb, title, price, gallery,
        description, and add-to-cart markup. Narrowing the soup to ``<main>``
        drops a ~1.5 MB page to a few KB of relevant markup before it reaches
        the AI extractor — a major token saving with zero information loss for
        the coffee details (name, price, description, origin, process,
        variety, altitude and weight all live inside ``<main>``).

        The ``og:availability`` meta (InStock/OutOfStock — this store emits
        ``og:availability`` rather than ``product:availability``) is appended
        to the narrowed soup so the AI extractor receives the authoritative
        machine-readable availability signal even after the ``<head>`` is
        dropped.

        Listing pages (the sitemap XML) are left untouched — they do not
        contain ``/product-page/`` in their URL.

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
            # Only narrow product detail pages, leave the sitemap listing untouched
            if "/product-page/" not in (url or ""):
                return soup
            if soup is None:
                return None

            main_el = soup.select("main")
            if len(main_el) == 1:
                narrowed = main_el[0]

                # Inject the availability meta so the AI receives the
                # authoritative stock signal (InStock / OutOfStock) even
                # after <main> narrowing drops the <head>.
                avail_meta = soup.select_one('meta[property="og:availability"]')
                if avail_meta is not None:
                    content = str(avail_meta.get("content", "")).strip()
                    # Normalise the content to the exact phrasing the AI
                    # extractor's prompt checks ("in stock" / "out of stock").
                    in_stock = content.lower() == "instock" or content.lower() == "in stock"
                    marker_text = (
                        f"Product availability: {content} "
                        f"({'in stock' if in_stock else 'out of stock'})"
                    )
                    marker = soup.new_tag("div", attrs={"data-kissaten-availability": content})
                    marker.string = marker_text
                    narrowed.append(marker)

                logger.debug(f"Narrowed soup to <main> for {url}")
                return narrowed

            logger.warning(f"Expected 1 <main> for {url}, found {len(main_el)}")
            return soup

        except Exception as e:
            current_url = kwargs.get("url") or (args[0] if args else "?")
            logger.error(f"Error fetching page {current_url}: {e}")
            return None

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the bean currency to GBP (the site sells exclusively in GBP).

        Verified live: product prices render as ``£14.00``/``£16.00`` and the
        embedded Wix product JSON carries ``"GBP"`` as the currency code.

        Args:
            bean: Extracted CoffeeBean object.

        Returns:
            Postprocessed CoffeeBean with GBP currency.
        """
        processed = super().postprocess_extracted_bean(bean)
        if processed:
            processed.currency = "GBP"
        return processed
