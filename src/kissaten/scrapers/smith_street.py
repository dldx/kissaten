"""Smith Street Coffee Roasters scraper implementation with AI-powered extraction (Wix storefront).

Smith Street Coffee Roasters (smithstreetcoffeeroasters.co.uk) is a UK
speciality coffee roaster in Sheffield selling through a Wix storefront
(parastorage.com assets, ``data-hook`` attributes, GBP prices). The catalogue
mixes coffee beans (blends, single origins, decaf, seasonal), coffee bundles
and a tasting-flight sampler with substantial non-coffee inventory (teas,
mugs, cups, pods, gift certificates, brew equipment, apparel).

Discovery is via the Wix store-products sitemap (``/store-products-sitemap.xml``),
which lists every product page as a literal ``/product-page/<slug>`` path — a
single fetch gives the full catalogue (62 products at time of writing,
verified 2026-08-25). Category pages render their product tiles client-side, so
the sitemap is the only reliable enumeration source.

Filtering keeps only whole-bean coffee plus the coffee bundles and the tasting
flight (samplers are NOT excluded per project policy — they are extracted and
flagged ``is_tasting_kit``/``requires_review`` for admin review). All non-coffee
categories are dropped via the extended URL-pattern filter:
``_get_excluded_url_patterns`` appends roaster-specific terms (tea, mugs, cups,
pods, gift certificates/packs, brewing equipment, subscriptions) to the base
set, so ``is_coffee_product_url`` returns the ~19 coffee URLs.

Sold-out handling: discovery is sitemap-based (no listing card text), so
sold-out products remain in the catalogue and their stock state is captured at
scrape time from the page text (Wix shows "Unavailable" in the add-to-cart area
when a product is out of stock). The ``og:availability`` meta (InStock/
OutOfStock) is injected into the narrowed ``<main>`` soup so the AI extractor
receives the authoritative machine-readable availability signal. Sold-out beans
are never skipped at discovery — the base out-of-stock diffjson path only fires
when a product genuinely disappears from the sitemap. The base
``create_diffjson_stock_updates`` (with its failed-listing guard) is used
unchanged.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="smith-street",
    display_name="Smith Street Coffee Roasters",
    roaster_name="Smith Street Coffee Roasters",
    website="https://www.smithstreetcoffeeroasters.co.uk",
    description=(
        "Smith Street Coffee Roasters is a Sheffield (UK) specialty coffee "
        "roaster selling through the smithstreetcoffeeroasters.co.uk Wix store "
        "(GBP): classic espresso blends, single-origin beans, decaf, seasonal "
        "releases, coffee bundles and a tasting sampler."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SmithStreetScraper(BaseScraper):
    """Scraper for Smith Street Coffee Roasters (smithstreetcoffeeroasters.co.uk) — Wix storefront.

    Discovery is via the store-products-sitemap.xml because Wix category pages
    render their product tiles client-side, making the sitemap the only
    reliable enumeration source. Non-coffee catalogue items are filtered out by
    the extended URL-pattern exclusion list; samplers are retained.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Smith Street Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Smith Street Coffee Roasters",
            base_url="https://www.smithstreetcoffeeroasters.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_excluded_url_patterns(self) -> list[str]:
        """Extend the base URL-pattern exclusions with Smith Street specifics.

        The Wix sitemap carries a large non-coffee inventory alongside the
        beans. Base patterns already drop obvious equipment/apparel/gift-card
        terms, but Smith Street's slugs need extra terms for the remaining
        non-coffee categories (teas, mugs, cups, pods, gift certificates/packs,
        brew equipment, apparel, subscriptions not matching "subscription").

        Returns:
            The combined exclusion list.
        """
        base_patterns = super()._get_excluded_url_patterns()
        smith_specific = [
            # Brewing / equipment (base "aeropress" misses the hyphenated slug)
            "aero",
            "cafetiere",
            "moka",
            "coffee-maker",
            "stove-top",
            "grunwerg",
            # Drinkware & bags / apparel
            "mug",
            "cup",
            "ecoffee",
            "enamel",
            "bag",
            "beanie",
            "ribbed",
            "drawstring",
            # Pods & single-serve
            "pods",
            # Teas
            "tea",
            # Gift certificates / gift packs / hot chocolate / subscription card
            "gift",
            "hot-chocolate",
            "roasters-choice",
        ]
        return list(dict.fromkeys(base_patterns + smith_specific))

    async def get_store_urls(self) -> list[str]:
        """Return the enumeration source: the Wix store-products sitemap.

        The ``/product-page/*`` pages render from the sitemap list directly — a
        single fetch gives the full catalogue enumeration.

        Returns:
            List containing the sitemap URL.
        """
        return ["https://www.smithstreetcoffeeroasters.co.uk/store-products-sitemap.xml"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the store-products sitemap.

        # Sold-out detection: sitemap-based — the sitemap has no listing-card
        # text, so sold-out products are kept in the catalogue and their stock
        # state is captured at scrape time from the page text and the injected
        # ``og:availability`` meta (InStock/OutOfStock). Sold-out beans are
        # never dropped at discovery.

        Parses ``<loc>`` entries, keeps only ``/product-page/`` paths and drops
        non-coffee products (teas, mugs, pods, gifts, equipment, subscriptions)
        via the extended base URL-pattern filter. Samplers/bundles are retained.

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
        # non-coffee categories via _get_excluded_url_patterns.
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
        ``PAGES_CONTAINER``) holding the breadcrumb, title, price, grind/weight
        options, description, origin notes and add-to-cart markup. Narrowing the
        soup to ``<main>`` drops a ~1.8 MB page to a few KB of relevant markup
        before it reaches the AI extractor — a major token saving with zero
        information loss for the coffee details.

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

        Verified live: product prices render as ``£13.00`` and the embedded Wix
        product JSON carries ``"GBP"`` as the currency code.

        Args:
            bean: Extracted CoffeeBean object.

        Returns:
            Postprocessed CoffeeBean with GBP currency.
        """
        processed = super().postprocess_extracted_bean(bean)
        if processed:
            processed.currency = "GBP"
        return processed
