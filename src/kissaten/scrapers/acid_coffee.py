"""Acid Coffee scraper implementation with AI-powered extraction (STORES.jp, Japan).

Acid Coffee (acidcoffee.stores.jp) is an Osaka-based specialty roaster running on
STORES.jp (株式会社STORES), a Japanese SaaS storefront. This is **not** Shopify:
there is no public read JSON API at all — ``products.json``,
``/collections/all/products.json``, ``sitemap_products_1.xml``, ``/wp-json/…`` and
``/api/v1/…`` all return 404 and ``/?format=json`` returns 406. The site is
server-side rendered, so everything needed is present in the HTML.

Discovery (``/sitemap.xml``): the sitemap is the only complete, non-overlapping
inventory source — 483 ``/items/<24-hex-ObjectId>`` URLs plus the homepage. The
``&category_id=<id>&page=N`` listings paginate at 30/page and the categories
overlap heavily (every merch item is reachable from "Others" as well as from
"Goods"), so walking them would double-count. ``/sitemap.xml`` is handled
generically: if it is a ``<urlset>`` the ``<loc>`` entries are used directly, and
if it is a ``<sitemapindex>`` the child ``<sitemap><loc>`` entries are fetched
and their locs used (one extra hop, as ``kofra.py`` does).

Detail pages (``/items/<24hex>``): every page carries a JSON-LD array holding a
``Product`` node and a ``BreadcrumbList``. The JSON-LD is the primary parse
target (name, url, image[], description, brand, mpn, ``offers``), and the
``BreadcrumbList`` gives the authoritative full category path. JSON-LD
deliberately omits per-variant price/stock, so those come from the rendered
variation blocks (``div.variation`` → ``h2`` size, ``.prices p`` price,
``.labels .stock_item`` stock text) plus the tax-inclusive range in
``p.item_price``. All of that is folded into a small compact soup before the AI
extractor sees it (the ``lantern_coffee.py`` idea), which is a large token
saving versus sending the raw server-rendered page.

Filtering: the ``Goods`` breadcrumb category contains only non-coffee
(equipment/apparel) — four items as of 2026-10-04: ``ACIDCOFFEE Original
Dripper``, ``ACID COFFEE BB CAP``, ``ACIDCOFFEE スーパーフルーティ両手マグ`` and
``ACID COFFEE PHOTO Tシャツ ver.1``. It is the authoritative non-coffee signal,
so a ``Goods`` breadcrumb rejects the product. The base
``is_coffee_product_name`` blocklist is English-only and therefore misses the
Japanese cases (``サブスクリプション``, ``Tシャツ``, ``両手マグ``), so those are
handled explicitly by name.

Drip bags are coffee, not equipment: ``ACID Drip Bag`` (a filter bag filled
with coffee) flows through normally, and ``カプセルコーヒー10個アソート`` /
``2025Advent Calendar【Drip Bag】`` are kept and flagged ``is_tasting_kit`` /
``requires_review`` so they land in the admin review queue instead of being
silently dropped. Only the empty filter-paper set
``【ほぼ業務用】Drip Bag 10 個セット【お덕用】`` (no coffee at all) is excluded.

Stock updates: ``create_diffjson_stock_updates`` is deliberately *not*
overridden. Because the sitemap is the discovery source, a product that leaves
the sitemap is genuinely delisted, and the base ``_failed_listing_urls`` guard
already suppresses out-of-stock writes for the whole store when the sitemap
fetch fails — which matters here because Cloudflare can fail mid-run.

HTTP: Cloudflare 403s the plain libcurl TLS fingerprint that
``BaseScraper.__init__`` builds by default (``impersonate=None``), so the
client is rebuilt with ``impersonate="chrome"`` — the same 18-scraper idiom as
``twoday.py`` / ``oddy_knocky.py``. Without it the scraper silently returns
nothing. This scraper additionally omits ``WebBotAuth``: Cloudflare's bot rules
403 the Web Bot Auth signature headers on this host (see the comment in
``__init__``), so sending them would break every request.

Screenshots: ``take_screenshot`` is overridden to a no-op. Cloudflare 403s
Playwright's TLS fingerprint on this host (only the impersonated ``_curl_http``
client gets a 200), so the unconditional base-class screenshot would add one
failed browser navigation per product — 483 wasted Cloudflare hits on a run where
the extractor never sends a screenshot to the model anyway.

Currency in the compact soup: the soup states the currency three ways — an
explicit ``<p>Currency: JPY</p>`` line, an unconditional ``og:price:currency``
meta, and a currency code in front of every per-variant price.
``CoffeeBean.currency`` defaults to ``GBP``, so an unset field made the model
validate ¥1,500/16 g as £1,500/16 g ($126.63/g) and ``check_prices`` dropped the
bean.

Rate limiting: ``robots.txt`` declares ``Crawl-delay: 20``, so
``rate_limit_delay`` is 20 s and ``scrape_with_ai_extraction`` is called with
``max_concurrent=1`` — the store is never hit concurrently. That is expensive:
483 detail pages ≈ 2.7 h on a cold run. It is a one-off cost, because
``KISSATEN_INCREMENTAL`` only fetches genuinely new products afterwards and
stock updates are derived from the sitemap without any detail fetch.

Currency: the storefront prices in JPY. ``postprocess_extracted_bean`` pins
``JPY`` explicitly because the base currency lookup by display name can fall
back to GBP. No FX change is needed — JPY already exists in
``src/kissaten/database/fx.py``.
"""

import json
import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from . import _curl_http as httpx
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

SITEMAP_URL = "https://acidcoffee.stores.jp/sitemap.xml"

# STORES.jp product detail URLs are ``/items/<24-hex-ObjectId>`` (optionally with
# a trailing slash). Anything else in the sitemap (the homepage, category
# listings) is not a product.
_ITEM_PATH_RE = re.compile(r"^/items/[0-9a-f]{24}/?$")

# Breadcrumb category that holds only non-coffee goods (equipment / apparel).
_GOODS_CATEGORY = "Goods"

# Base ``is_coffee_product_name`` is English-only: it catches "dripper" but
# misses the Japanese merch/equipment names, so those are listed explicitly.
_NON_COFFEE_NAME_TOKENS = (
    "xbloom",  # 【xBloom】ACIDレシピインストール済み (machines)
    "bb cap",
    "両手マグ",  # super-fruity two-handled mug
    "tシャツ",  # t-shirt
    "マグ",  # mug / tumbler
    "タンブラー",  # tumbler
    "サブスクリプション",  # coffee subscription
    "subscription",
    "ドリッパー",  # dripper (the base blocklist only has the English "dripper")
)

# Non-coffee signals that only count when *every* fragment is present. The
# empty filter-paper set (【ほぼ業務用】Drip Bag 10 個セット) contains no coffee,
# while the real "ACID Drip Bag" (a filter bag filled with coffee) must not be
# caught by it.
_NON_COFFEE_NAME_COMBOS = (("drip bag", "個セット"),)

# JP / seasonal sampler markers. These are real coffee, so they are flagged for
# admin review (is_tasting_kit + requires_review) rather than excluded.
_TASTING_KIT_NAME_TOKENS = (
    "アソート",  # capsule coffee 10-piece assortment
    "advent calendar",
    "カプセル",  # capsules / sampler capsules
    "試飲",  # tasting flight
    "tasting",
    "sampler",
    "starter pack",
)


# Leading currency glyphs / symbols rendered in the variation price text
# ("¥1,500"). The compact soup replaces them with the explicit ISO code, so
# the model never has to infer ``currency`` from a symbol.
_CURRENCY_GLYPH_RE = re.compile(r"^[\s¥￥$€£₤]+")


def _availability_label(availability: str | None) -> str:
    """Map a schema.org availability URL to a short human label."""
    if not availability:
        return ""
    tail = str(availability).rstrip("/").rsplit("/", 1)[-1].lower()
    return {
        "instock": "In stock",
        "outofstock": "Out of stock",
        "preorder": "Pre-order",
        "backorder": "Back-order",
        "soldout": "Out of stock",
        "limitedavailability": "In stock",
    }.get(tail, "")


@register_scraper(
    name="acid-coffee",
    display_name="Acid Coffee",
    roaster_name="Acid Coffee",
    website="https://acidcoffee.stores.jp",
    description="Tokyo/Shibuya-based Japanese specialty roaster with a large single-origin "
    "catalogue, quality-tiered process categories and a large drip-bag line.",
    requires_api_key=True,
    currency="JPY",  # Japanese Yen
    country="Japan",
    status="experimental",
)
class AcidCoffeeScraper(BaseScraper):
    """Scraper for Acid Coffee (acidcoffee.stores.jp, STORES.jp storefront)."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Acid Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Acid Coffee",
            base_url="https://acidcoffee.stores.jp",
            # robots.txt declares "Crawl-delay: 20" for this host.
            rate_limit_delay=20.0,
            max_retries=3,
            timeout=30.0,
        )

        # Cloudflare 403s curl_cffi's default libcurl TLS fingerprint, while the
        # "chrome" impersonation profile negotiates successfully (verified live
        # against /sitemap.xml and item pages: impersonate="chrome" -> 200,
        # impersonate=None -> 403). Rebuild the client with that profile,
        # preserving headers/proxy — the same idiom as twoday.py and
        # oddy_knocky.py. Without this the scraper silently scrapes nothing.
        #
        # Deviation from that idiom: WebBotAuth is deliberately NOT attached.
        # Cloudflare's bot rules reject the Web Bot Auth signature headers on
        # this host — verified live, and narrowed down to a single header:
        #   impersonate="chrome" + plain headers          -> 200 (65,860 bytes)
        #   ... + Signature-Agent                        -> 403
        #   ... + Signature-Input / Signature            -> 403
        #   ... + full WebBotAuth                        -> 403
        # Sending them would turn every request into a 403, so this scraper
        # opts out of Web Bot Auth.
        proxy_url = self.https_proxy or self.http_proxy
        client_kwargs: dict = {
            "headers": self.headers,
            "timeout": self.timeout,
            "impersonate": "chrome",
        }
        if proxy_url:
            client_kwargs["proxy"] = proxy_url
        self.client = httpx.AsyncClient(**client_kwargs)

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        The sitemap is the only complete, non-overlapping inventory source
        (the category listings overlap heavily and would double-count).

        Returns:
            List containing the sitemap URL.
        """
        return [SITEMAP_URL]

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract ``/items/<hex>`` product URLs from a sitemap.

        Handles both sitemap shapes: a plain ``<urlset>`` and a
        ``<sitemapindex>`` whose child ``<sitemap><loc>`` entries are fetched
        and followed (one hop).

        Sold-out detection: sitemap-based — the sitemap carries no listing-card
        text and STORES.jp flips the add-to-cart state client-side, so every
        sitemap-listed product is treated as part of the current catalogue;
        out-of-stock diffs only fire when a product leaves the sitemap.

        Args:
            store_url: URL of the sitemap XML.

        Returns:
            List of coffee product URLs. Empty when the sitemap fetch fails, so
            the base class records the listing failure and suppresses out-of-stock
            updates for the whole store.
        """
        try:
            soup = await self.fetch_page(store_url)
        except Exception as e:
            # A hard failure (Cloudflare, timeout, …) must look exactly like a
            # missing listing so the base class records the listing failure and
            # suppresses out-of-stock diffs for the whole store.
            logger.error(f"Failed to fetch sitemap {store_url}: {e}")
            return []
        if not soup:
            logger.error(f"Failed to fetch sitemap: {store_url}")
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        async def collect(sitemap_soup: BeautifulSoup | Tag) -> None:
            """Add every ``/items/<hex>`` loc in ``sitemap_soup`` to the result."""
            for loc in sitemap_soup.select("loc"):
                url = loc.get_text(strip=True)
                if not url or url in seen:
                    continue
                path = urlparse(url).path.lower()
                if not _ITEM_PATH_RE.match(path):
                    continue
                if not self.is_coffee_product_url(url, required_path_patterns=["/items/"]):
                    continue
                seen.add(url)
                product_urls.append(url)

        # ``fetch_page`` parses with lxml (HTML parser), so the tag arrives
        # lowercased; match either casing so an XML-parsed soup works too.
        if soup.find("sitemapindex") is not None or soup.find("SitemapIndex") is not None:
            # Sitemap index: one more hop into each child sitemap.
            children: list[str] = []
            for loc in soup.select("sitemap > loc, Sitemap > loc"):
                child = loc.get_text(strip=True)
                if child:
                    children.append(child)
            logger.info(f"Sitemap index with {len(children)} child sitemap(s)")
            for child_url in children:
                try:
                    child_soup = await self.fetch_page(child_url)
                except Exception as e:
                    logger.error(f"Failed to fetch child sitemap {child_url}: {e}")
                    return []
                if not child_soup:
                    logger.error(f"Failed to fetch child sitemap: {child_url}")
                    return []
                await collect(child_soup)
        else:
            await collect(soup)

        logger.info(f"Found {len(product_urls)} product URLs from sitemap ({store_url})")
        return product_urls

    # ------------------------------------------------------------------
    # Detail-page parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_jsonld(soup: BeautifulSoup | Tag):
        """Yield every parsed JSON-LD node from ``application/ld+json`` scripts."""
        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string or script.get_text()
            if not raw or not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(data, list):
                for node in data:
                    if isinstance(node, dict):
                        yield node
            elif isinstance(data, dict):
                yield data

    @classmethod
    def _parse_item_page(cls, soup: BeautifulSoup | Tag) -> tuple[dict | None, list[str]]:
        """Extract the JSON-LD ``Product`` node and the breadcrumb path names.

        Args:
            soup: Parsed item page soup.

        Returns:
            Tuple of (product node or None, breadcrumb category names). The
            breadcrumb list excludes the "HOME" root and the product itself, so
            it is exactly the category path.
        """
        product: dict | None = None
        crumbs: list[str] = []
        for node in cls._iter_jsonld(soup):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if "Product" in types and product is None:
                product = node
            if "BreadcrumbList" in types:
                elements = node.get("itemListElement") or []
                names = [
                    str(element.get("name")).strip()
                    for element in elements
                    if isinstance(element, dict) and element.get("name")
                ]
                if len(names) > 2:
                    crumbs = names[1:-1]
                break
        return product, crumbs

    def _is_non_coffee(self, name: str, crumbs: list[str]) -> bool:
        """Return True when the JSON-LD says the product is not coffee.

        Args:
            name: Product name from JSON-LD.
            crumbs: Breadcrumb category path (root and product name removed).

        Returns:
            True if the product should be dropped before any AI call.
        """
        if _GOODS_CATEGORY in crumbs:
            logger.debug(f"Excluding non-coffee '{_GOODS_CATEGORY}' product: {name}")
            return True

        name_lower = (name or "").lower()
        for token in _NON_COFFEE_NAME_TOKENS:
            if token in name_lower:
                logger.debug(f"Excluding non-coffee product by name token '{token}': {name}")
                return True
        for combo in _NON_COFFEE_NAME_COMBOS:
            if all(fragment in name_lower for fragment in combo):
                logger.debug(f"Excluding empty-set product by name combo {combo}: {name}")
                return True
        return False

    @staticmethod
    def _parse_variations(soup: BeautifulSoup | Tag) -> list[dict]:
        """Parse the rendered ``div.variation`` blocks.

        STORES.jp renders one ``div.variation`` per purchasable variant with the
        size in ``h2``, the tax-inclusive price in ``.prices p`` and the stock
        text in ``.labels .stock_item`` (absent when the variant is in stock).
        The same values are also serialised in an ``ng-click`` addCart payload;
        the rendered DOM is the simpler and more stable source.

        Args:
            soup: Parsed item page soup.

        Returns:
            List of ``{"size", "price", "stock"}`` dicts in page order.
        """
        variations: list[dict] = []
        for block in soup.select("div.variation"):
            heading = block.find("h2")
            size = heading.get_text(strip=True) if heading else ""
            price_tag = block.select_one(".prices p")
            price = price_tag.get_text(strip=True) if price_tag else ""
            stock_tag = block.select_one(".labels .stock_item")
            stock = stock_tag.get_text(" ", strip=True) if stock_tag else ""
            if not (size or price or stock):
                continue
            variations.append({"size": size, "price": price, "stock": stock})
        return variations

    @classmethod
    def _build_item_soup(cls, soup: BeautifulSoup | Tag, product: dict, crumbs: list[str]) -> BeautifulSoup:
        """Build a compact product soup for the AI extractor.

        Folds the JSON-LD (name, description, brand, image, offers) and the
        rendered variation blocks into a small HTML fragment. Sending this
        instead of the ~60 KB server-rendered page is a large token saving.

        Args:
            soup: Parsed item page soup (for the rendered variation blocks).
            product: JSON-LD ``Product`` node.
            crumbs: Breadcrumb category path.

        Returns:
            Compact BeautifulSoup object.
        """
        offers = product.get("offers") or {}
        if not isinstance(offers, dict):
            offers = {}

        image = product.get("image")
        if isinstance(image, list):
            image = next((i for i in image if isinstance(i, str) and i.startswith("http")), "")
        elif isinstance(image, dict):
            image = image.get("url") or image.get("contentUrl") or ""
        elif not isinstance(image, str):
            image = ""

        currency = offers.get("priceCurrency") or "JPY"
        availability = _availability_label(offers.get("availability"))
        low = offers.get("lowPrice") if offers.get("lowPrice") is not None else offers.get("price")
        high = offers.get("highPrice") if offers.get("highPrice") is not None else offers.get("price")

        parts: list[str] = ["<div>"]

        name = product.get("name")
        if name:
            parts.append(f"<h1>{name}</h1>")
        if crumbs:
            parts.append(f"<p>Category: {' &gt; '.join(crumbs)}</p>")
        brand = product.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        if brand:
            parts.append(f"<p>Brand: {brand}</p>")
        if low is not None and high is not None:
            if str(low) == str(high):
                parts.append(f"<p>Price: {currency} {high} (tax included)</p>")
            else:
                parts.append(f"<p>Price range (tax included): {currency} {low} - {high}</p>")
        elif low is not None or high is not None:
            parts.append(f"<p>Price: {currency} {low if low is not None else high} (tax included)</p>")
        if availability:
            parts.append(f"<p>Availability: {availability}</p>")
        # Name the currency in plain, labelled prose. ``CoffeeBean.currency``
        # defaults to "GBP", and when the model leaves the field unset the JPY
        # amounts are validated as pounds (¥1,500/16 g is $0.64/g in JPY but
        # $126.63/g in GBP) and the bean is dropped by ``check_prices`` — exactly
        # what happened on the live run. The per-variant prices below carry the
        # same problem: they are rendered as a bare "¥" glyph, so the model has
        # nothing unambiguous to map onto the ``currency`` field. Emitted
        # unconditionally (not inside the ``if image`` block) so an image-less
        # product still gets it. Same idiom as nord_kaffe.py.
        parts.append(f"<p>Currency: {currency}</p>")
        # Unconditional so ``BaseScraper._extract_currency_from_html`` can pick
        # up the priceCurrency from an image-less product too.
        parts.append(f'<meta property="og:price:currency" content="{currency}">')
        if image:
            # Lets the base JSON-LD/og:image backfill resolve the product photo
            # from the compact soup.
            parts.append(f'<meta property="og:image" content="{image}">')

        variations = cls._parse_variations(soup)
        if variations:
            # Per-variant prices are rendered as a bare "¥1,500" glyph with no
            # code, so each is relabelled with the currency code here and the
            # glyph stripped ("16g / JPY 1500 / in stock"). This is the text the
            # model reads per variant, and on the live run it left ``currency``
            # unset -> GBP -> the bean was dropped by ``check_prices``.
            lines = [f"Variants (size / price in {currency} / stock):"]
            for variation in variations:
                stock = variation["stock"] or "in stock"
                amount = _CURRENCY_GLYPH_RE.sub("", variation["price"]).strip()
                lines.append(f"- {variation['size']} / {currency} {amount} / {stock}")
            parts.append(f"<pre>{'<br>'.join(lines)}</pre>")

        description = product.get("description")
        if description:
            parts.append(f"<div>{description}</div>")

        parts.append("</div>")
        return BeautifulSoup("".join(parts), "html.parser")

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Filter on the JSON-LD, then extract from the compact soup.

        ``BaseScraper.scrape_with_ai_extraction`` calls this hook with the raw
        server-rendered soup and handles a ``None`` return safely (its
        ``_apply_product_flags`` call is a no-op for ``None`` and the subsequent
        ``if bean and self.is_coffee_product_name(...)`` guard drops it), so the
        cheap JSON-LD classification runs here instead of duplicating the whole
        save / flag / mark-as-scraped sequence in a hand-written
        ``_scrape_new_products``.

        Args:
            ai_extractor: AI extractor instance.
            soup: Parsed (server-rendered) product page soup.
            product_url: URL of the product page.
            use_optimized_mode: Forwarded to the base implementation.
            translate_to_english: Forwarded to the base implementation.

        Returns:
            CoffeeBean object, or None when the product is non-coffee or the
            page carries no JSON-LD ``Product`` node.
        """
        product, crumbs = self._parse_item_page(soup)
        if not product:
            logger.warning(f"No JSON-LD Product node found for {product_url}")
            return None

        if self._is_non_coffee(str(product.get("name") or ""), crumbs):
            return None

        compact_soup = self._build_item_soup(soup, product, crumbs)
        return await super()._extract_bean_with_ai(
            ai_extractor,
            compact_soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction on the compact soup.

        Args:
            product_urls: List of URLs for new products.

        Returns:
            List of newly scraped CoffeeBean objects.
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        # max_concurrent=1: robots.txt declares "Crawl-delay: 20" and STORES.jp
        # sits behind Cloudflare, so the store is never hit concurrently.
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
            max_concurrent=1,
            translate_to_english=True,
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """No-op: Cloudflare 403s Playwright on this host, so screenshots are impossible.

        ``BaseScraper.fetch_page_with_screenshot`` calls this unconditionally on
        every fetch, which means all 483 detail pages triggered a wasted browser
        navigation that Cloudflare rejected: only the impersonated ``_curl_http``
        client (``impersonate="chrome"``) gets a 200, while Playwright's own TLS
        fingerprint is 403'd — so one of our two clients is already failing on
        every single page. Nothing on this code path consumes the bytes: the
        extractor runs ``use_playwright=False`` / ``use_optimized_mode=False``,
        so no screenshot is ever sent to the model, and ``_save_page_cache``
        stores ``None`` happily. Suppressing it halves the request count against
        Cloudflare on a host that already rejects half of them.
        """
        return None

    # ------------------------------------------------------------------
    # Postprocessing hooks
    # ------------------------------------------------------------------

    def postprocess_review_flags(self, bean: CoffeeBean, url: str) -> CoffeeBean:
        """Flag the JP / seasonal sampler products for admin review.

        ``カプセルコーヒー10個アソート``, ``2025Advent Calendar【Drip Bag】`` and
        friends are real coffee, so they must not be excluded — they are flagged
        ``is_tasting_kit`` here and ``_apply_product_flags`` mirrors
        ``requires_review`` for new beans, parking them in the admin review
        queue until an approver releases them.

        Args:
            bean: The extracted bean.
            url: The product URL the bean was extracted from.

        Returns:
            The bean, with ``is_tasting_kit`` set when a kit marker is present.
        """
        haystack = f"{url} {getattr(bean, 'name', '') or ''}".lower()
        for token in _TASTING_KIT_NAME_TOKENS:
            if token in haystack:
                bean.is_tasting_kit = True
                break
        return bean

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency (the registry lookup by display name can fall back to GBP)."""
        bean.currency = "JPY"
        return bean
