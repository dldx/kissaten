"""Machina Coffee scraper implementation with Shopify JSON extraction.

Machina Coffee (machina-coffee.co.uk, canonical machina-coffee.com) is a
speciality coffee roaster based in Edinburgh, Scotland, selling curated
coffee beans alongside a very large home/commercial equipment catalogue
(espresso machines, grinders, cups, scales, brewers, subscriptions and
training courses). The store is Shopify-hosted and prices its products in
GBP (£).

Only the curated ``/collections/coffee`` collection is scraped. Verified
2026-08: every published coffee bean on the store (checked against the
products sitemap, 341 products) lives in that collection — the ``espresso``,
``experimental-filter-espresso``, ``accessible-*``, ``africa-*`` and
``south-america-*`` collections are all strict subsets of its 24 handles,
and the 317 remaining sitemap products are all equipment/subscriptions/
training/merch. No collection merge is needed; the expected catalogue is
24 beans, every one with ``product_type == "Coffee"``.

Shape: the products.json ``body_html`` only carries a one-line tagline plus
wholesale/roasting-schedule boilerplate, so JSON-only extraction would lose
the bean detail. The rendered product page carries the real spec
(Origin / Process / Roast / Tasting Notes, "The Profile" prose,
Producer / Region / Varietal / Elevation and the farm story) in dedicated
Mucky-Puddle-theme sections, so product pages are scraped and
``preprocess_product_soup`` whitelists exactly those sections (dropping the
huge header/recommendations chrome). The injected Shopify JSON still
supplies the name/price/variants.

Canonical form: the site's canonical tags and sitemap declare
``https://machina-coffee.com`` as canonical (both domains serve the same
Shopify store), so product URLs are normalised to
``https://machina-coffee.com/products/<handle>``.

Currency: Shopify Markets multi-currency conversion is active (a
``country=US`` / ``currency=USD`` request returns converted prices, e.g.
£40.00 -> 56.00), so ``country=GB`` is pinned on every products.json fetch
and ``store_currency`` is pinned to GBP — the curl_cffi client's datacenter
IP must never see converted prices.

Tasting kits: the two curated variety packs ("Espresso Collection Pack",
"Filter Collection Pack" — 4 x 250g samplers) are kept and flagged
``is_tasting_kit`` for admin review instead of being dropped
(see docs/KIT_REVIEW.md).
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# curl_cffi requests can be geo/market-detected to a non-UK market, which
# would return the catalog priced in a converted currency instead of GBP.
# Pinning country=GB selects the roaster's home market so the returned
# products.json is always priced in the base GBP currency.
_MARKET_PARAM = "country=GB"

# The curated 4-bag variety packs are sampler-style products. Their handles
# carry a "<kind>-collection-pack" token that no single-origin bean handle
# uses, so we can flag exactly those products as tasting kits.
_COLLECTION_PACK_TOKEN = "collection-pack"

# Bean-detail sections of the Mucky-Puddle theme product page. The section
# IDs carry a store/template prefix but a stable ``__<section>`` suffix, so
# an ends-with selector is robust to the numeric template id changing.
_BEAN_SECTION_SUFFIXES = [
    "__product-top",  # title, tagline, size selector, price
    "__product-trust-panel",  # Origin / Process / Roast / Tasting Notes grid
    "__panel-split",  # "The Profile" tasting prose
    "__product-data-points",  # Producer / Region / Varietal / Elevation
    "__panel-split-2",  # "The Producers" farm story
]


@register_scraper(
    name="machina",
    display_name="Machina Coffee",
    roaster_name="Machina Coffee",
    website="https://machina-coffee.com",
    description="Edinburgh speciality coffee roaster selling curated single "
    "origins, blends and decaf alongside home/commercial coffee equipment",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class MachinaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Machina Coffee (machina-coffee.co.uk / machina-coffee.com).

    Only the curated ``/collections/coffee`` bean collection is scraped — it
    contains every published coffee bean on the store (verified against the
    products sitemap) and no equipment. The two curated "Collection Pack"
    4-bag samplers are kept and flagged for admin review.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Machina Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Machina Coffee",
            base_url="https://machina-coffee.com",
            products_json_urls=["https://machina-coffee.com/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The coffee collection is already pure beans (product_type "Coffee",
        # verified 2026-08) and sampler packs must NOT be excluded (they are
        # flagged for review instead, see docs/KIT_REVIEW.md), so no slug
        # exclusions are needed here. The base class filters (URL patterns +
        # product-name categories) still guard against any non-bean product
        # that may later be added to the collection.
        self.exclude_slugs = []

        # The storefront may geolocate curl_cffi requests to a converted-currency
        # market (see _fetch_all_shopify_products). Force the roaster's home GBP
        # currency and mark it as detected so the collection-page detection path
        # in _scrape_new_products (which could see a converted market) is skipped.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Extend the base kit/sampler URL patterns with Machina's pack handles.

        The two curated variety packs (``filter-collection-pack`` and
        ``espresso-collection-pack``, 4 x 250g samplers) carry a
        ``collection-pack`` token that no single-origin bean handle uses and
        that the base patterns do not match. Without this override the AI would
        extract them with no single origin and ``_extract_bean_with_ai`` would
        drop them before ``postprocess_review_flags`` can flag them; matching
        the token here keeps them flowing through so they land in the admin
        review queue instead of being silently discarded.
        """
        return super()._get_tasting_kit_url_patterns() + [_COLLECTION_PACK_TOKEN]

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with the UK market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=GB`` to each paginated request. Without it, curl_cffi requests
        can be geo/market-detected to a converted-currency market instead of the
        home GBP currency.
        """
        all_products = []
        page = 1
        limit = 250

        while True:
            url = f"{products_json_url}?{_MARKET_PARAM}&limit={limit}&page={page}"
            logger.info(f"Fetching Shopify products: {url}")

            data, use_playwright = await self._fetch_page_with_escalation(url)
            if data is None:
                if products_json_url not in self._failed_listing_urls:
                    self._failed_listing_urls.append(products_json_url)
                break

            products = data.get("products", [])
            if not products:
                break

            all_products.extend(products)
            logger.debug(f"Fetched {len(products)} products from page {page}")

            if len(products) < limit:
                break

            page += 1
            if use_playwright:
                logger.debug(f"Page {page - 1} escalated to Playwright; re-attempting httpx on page {page}.")

        return all_products

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Machina product URLs to the canonical form.

        The site's canonical tags and sitemap declare
        ``https://machina-coffee.com/products/<handle>`` (no collection segment,
        .com not .co.uk), so strip the collection segment built from the
        products.json URL base.
        """
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean-detail sections.

        The Mucky-Puddle theme buries the bean spec (Origin / Process / Roast /
        Tasting Notes, "The Profile" prose, Producer / Region / Varietal /
        Elevation and the farm story) in dedicated sections while the rest of
        the page is chrome (header/footer menus, shipping accordions, a ~200KB
        "You Might Also Like" block). We keep only the bean sections so the AI
        sees the detail without burning tokens on the page chrome.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify JSON context (name/price/variants) at the top of ``soup.body``
        AFTER this hook returns, so keeping a valid body preserves that data.
        """
        selectors = [f"div[id$='{suffix}']" for suffix in _BEAN_SECTION_SUFFIXES]
        sections = soup.select(", ".join(selectors))
        if not sections:
            logger.warning("No Machina bean-detail sections found; keeping the full product page soup.")
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        body = minimal.body
        if body is None:
            return soup
        for section in sections:
            # The Delivery & Returns shipping accordion is a modal inside the
            # product-top section; it is generic boilerplate repeated on every
            # product page, so drop it along with the rest of the page chrome.
            shipping_modal = section.select_one("#mp-shipping-delivery-modal")
            if shipping_modal is not None:
                shipping_modal.decompose()
            body.append(section)
        logger.debug(f"Pruned product page to {len(sections)} bean-detail section(s)")
        return minimal

    def postprocess_review_flags(self, bean, url: str):
        """Flag the curated 4-bag variety packs as tasting kits for review.

        The "Espresso Collection Pack (4 x 250g)" and "Filter Collection Pack
        (4 x 250g)" are curated samplers of several different coffees, so they
        are treated like sampler kits: kept in the catalogue but routed to the
        admin review queue (``requires_review``) instead of public search.
        """
        if bean is not None and _COLLECTION_PACK_TOKEN in str(url):
            bean.is_tasting_kit = True
        return bean
