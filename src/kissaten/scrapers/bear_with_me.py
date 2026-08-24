"""Bear With Me Coffee scraper implementation with AI-powered extraction (Wix storefront).

Bear With Me Coffee (www.bearwithmecoffee.co.uk) is a UK speciality coffee
roaster with a Wix storefront (parastorage.com assets, ``data-hook``
attributes, GBP prices). Unlike Asylum's category pages — which render
server-side — this site's ``/category/`` pages render their product tiles
*client-side*: only ONE ``div[data-hook="product-item-root"]`` is
server-rendered, so category crawling cannot enumerate the catalogue. The
authoritative enumeration source is the Wix store sitemap
(``/store-products-sitemap.xml``), which lists every product page as a literal
``/product-page/<slug>`` path — a single fetch gives the full catalogue.

Exclusions: the three subscription products
(``bear-with-me-espresso-subscription``,
``bear-with-me-single-origin-subscription``, ``easy-drip-subscription``) are
services, not coffee, and are dropped by the base URL-pattern filter
(``subscription``). ``easydrip-coffee-collection-mixmatch`` (a mixed
single-serve coffee box) is retained as a coffee product; brew bags and
easydrip single-serve coffees are kept. No equipment/accessory products appear
in the sitemap.

Sold-out handling: discovery is sitemap-based (no listing card text), so
sold-out products remain in the catalogue and their stock state is captured at
scrape time from the page text (the add-to-cart area shows "Unavailable" when a
Wix product is out of stock). The ``og:availability`` meta is also injected
into the narrowed ``<main>`` soup so the AI extractor receives the authoritative
availability signal. Sold-out beans are never skipped at discovery — the base
out-of-stock diffjson path only fires when a product genuinely disappears from
the sitemap.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bear-with-me",
    display_name="Bear With Me Coffee",
    roaster_name="Bear With Me",
    website="https://www.bearwithmecoffee.co.uk",
    description=(
        "Bear With Me Coffee is a UK specialty coffee roaster selling through "
        "the bearwithmecoffee.co.uk Wix store (GBP): single-origin beans, "
        "decaf, Easydrip single-serve coffees and brew bags."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class BearWithMeScraper(BaseScraper):
    """Scraper for Bear With Me Coffee (bearwithmecoffee.co.uk) — Wix storefront.

    Discovery is via the store-products-sitemap.xml because Wix category pages
    render their product tiles client-side, making the sitemap the only
    reliable enumeration source.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Bear With Me Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bear With Me",
            base_url="https://www.bearwithmecoffee.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the enumeration source: the Wix store-products sitemap.

        The ``/category/*`` pages render their product tiles client-side (only
        one ``div[data-hook="product-item-root"]`` is server-rendered), so they
        cannot enumerate the catalogue. The sitemap lists all product pages as
        literal ``/product-page/<slug>`` paths — a single fetch gives the full
        enumeration (24 products at time of writing).

        Returns:
            List containing the sitemap URL.
        """
        return ["https://www.bearwithmecoffee.co.uk/store-products-sitemap.xml"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the store-products sitemap.

        Parses ``<loc>`` entries, keeps only ``/product-page/`` paths and
        drops non-coffee products (subscriptions, equipment) via the base
        URL-pattern filter. Sold-out products are kept in the list so they
        remain in the catalogue — the out-of-stock state is captured at scrape
        time by the AI extractor.

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
        drops a ~1.6 MB page to ~33 KB of relevant markup before it reaches the
        AI extractor — a major token saving with zero information loss for the
        coffee details.

        The ``og:availability`` meta (InStock/OutOfStock) is appended to the
        narrowed soup so the AI extractor receives the authoritative machine-
        readable availability signal even after the ``<head>`` is dropped.

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

        Args:
            bean: Extracted CoffeeBean object.

        Returns:
            Postprocessed CoffeeBean with GBP currency.
        """
        processed = super().postprocess_extracted_bean(bean)
        if processed:
            processed.currency = "GBP"
        return processed
