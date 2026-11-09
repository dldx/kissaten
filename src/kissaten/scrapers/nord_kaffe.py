"""Nord Kaffe scraper implementation using the WooCommerce Store API.

Nord Kaffe / ``Norð Kaffebrenneri`` (Oslo, Norway) runs a WordPress +
WooCommerce storefront (``nordoslo.no``) — **not** Shopify, so
``/products.json`` 404s. The store serves server-rendered HTML, but the
WooCommerce Store API (``/wp-json/wc/store/v1/products``) exposes complete
structured product data (name, Norwegian short-description with the
origin/producer/payment prose, description with the tasting notes, price range
in minor units, size × grind variations, current image set, stock status,
categories), so the scraper uses the Store API for both listing and detail
instead of parsing HTML:

- Listing: ``.../products?per_page=100&page=N`` — every product carries a
  permalink, a category list and ``is_in_stock``.
- Detail: ``.../products?slug=<slug>`` returns the same product shape, from
  which a compact soup is built and fed to the AI extractor (driftwood.py
  pattern). This avoids one heavyweight HTML fetch per product and keeps the
  origin/process/tasting-note text the theme buries in styled blocks.

Three WooCommerce Store API traps drive the detail-path handling:

1. ``?slug=<slug>`` also matches the product's **variations**, and the response
   order is not guaranteed. A variation carries only its own ``prices.price``
   and a single variation-specific image: it has neither text field and a
   ``price_range`` of ``null``. ``_select_store_product`` therefore skips
   variations and keeps the parent, the only entry that has the origin prose
   and the full media set.
2. ``prices.price_range`` is ``null`` whenever every variation costs the
   same, so the price line must fall back to ``prices.price``. Amounts are in
   **minor units** (``currency_minor_unit`` is 2 for NOK) and ``_format_price``
   divides by ``10 ** currency_minor_unit``.
3. A synthetic JSON soup carries no ``og:price:currency`` for
   ``_extract_currency_from_html`` to find, and nothing else in the markup lets
   the extractor infer the currency, so the soup names it explicitly.

Two facts shape the text and media blocks of the compact soup:

- ``short_description`` and ``description`` are **complementary, never
  alternatives**: the first holds the origin/producer/payment prose and the
  second the tasting-note block, so both are emitted, each under its own
  heading, and each independently of whether the other is set. Reading them as
  a fallback pair would silently discard the more valuable half of the page.
- The product's ``images`` array is the store's current media set, while the
  WooCommerce text fields can still embed WordPress attachment links that go
  stale when a shop re-uploads a shot. The soup emits ``og:image`` from
  ``images`` — the first thing ``BaseScraper._extract_image_url_from_soup``
  reads — and strips ``<img>`` tags out of the text, so the current media set
  is the only image the document contains.

Norwegian-category gotcha: the coffee category is called **``Kaffe``**, not
``Coffee`` — a coffee product is normally tagged with ``["Filter", "Kaffe"]``
(``/butikk/kaffe/filter/…``) or the espresso blend range under
``/butikk/kaffe/espresso/…``, while equipment lives in ``Utstyr`` and
subscriptions in ``Abonnement``. Two extra traps matter here:

1. ``filter`` and ``espresso`` are Nord Kaffe's *coffee* category slugs, so
   they must **never** appear in the excluded-slug list even though they read
   like filters/equipment to an English-language scraper.
2. Some of the older espresso blends (``Norð Espresso fra Brasil``,
   ``Norð Økologisk Espresso``) are filed under the espresso category only in
   their permalink and return an **empty** ``categories`` array from the Store
   API. Category membership is therefore checked as ``"Kaffe"`` in the
   category names **or** ``/butikk/kaffe/`` in the permalink path, which keeps
   those blends while still excluding ``Utstyr``/``Abonnement``.

Limitations: the parent product's ``variations`` entries carry only ``id`` and
attributes, so per-variant prices are not in the payload — the soup states the
overall price range plus each size's name, and the per-size amounts have to come
from the range.
"""

import asyncio
import logging
from html import escape

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="nord-kaffe",
    display_name="Nord Kaffe",
    roaster_name="Nord Kaffe",
    website="https://nordoslo.no",
    description="Oslo specialty roaster roasting in a light Nordic style with traceable, "
    "direct sourcing from smallholder producers.",
    requires_api_key=True,
    currency="NOK",
    country="Norway",
    status="experimental",
)
class NordKaffeScraper(BaseScraper):
    """Scraper for Nord Kaffe (nordoslo.no) using the WooCommerce Store API."""

    # WooCommerce Store API endpoint (public, no auth required).
    _STORE_API_URL = "https://nordoslo.no/wp-json/wc/store/v1/products"
    _LISTING_QUERY = "per_page=100&page={page}"
    _max_listing_pages = 10

    # Norwegian store layout: equipment lives under ``/butikk/utstyr/`` and
    # subscriptions under ``/butikk/abonnement/``. ``filter`` and ``espresso``
    # are deliberately absent — they are Nord Kaffe's *coffee* category slugs
    # (``/butikk/kaffe/filter/``, ``/butikk/kaffe/espresso/``). Sampler/taster
    # packs are NOT excluded — they are flagged is_tasting_kit/requires_review
    # downstream.
    _excluded_url_slugs = [
        "abonnement",
        "utstyr",
        "hario",
        "v60",
    ]

    # Headings for the two WooCommerce text fields, so the extractor can tell
    # the origin/producer prose from the tasting-note block.
    _SHORT_DESCRIPTION_HEADING = "Product details"
    _DESCRIPTION_HEADING = "Description"

    def __init__(self, api_key: str | None = None):
        """Initialize Nord Kaffe scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Nord Kaffe",
            base_url="https://nordoslo.no",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

        # Pin the home-market currency. The Store API listing is a compact JSON
        # document with no og:price:currency meta tag, so the base class's HTML
        # detection cannot see it and the display-name lookup falls back to GBP,
        # which the extractor then echoed back on every price.
        self.store_currency = "NOK"
        self._currency_detected = True

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (WooCommerce Store API product listing)."""
        return [f"{self._STORE_API_URL}?{self._LISTING_QUERY.format(page=1)}"]

    @staticmethod
    def _format_price(amount: str | None, prices: dict) -> str:
        """Format a WooCommerce minor-unit amount using the payload's currency block.

        A zero amount renders as an empty string: ``PriceOption.price`` is
        ``gt=0``, so handing the extractor a "kr 0.00" line only earns a failed
        validation round-trip (giveaway / placeholder products).
        """
        if amount is None:
            return ""
        try:
            minor_unit = int(prices.get("currency_minor_unit") or 2)
            value = int(amount) / (10**minor_unit)
        except (TypeError, ValueError):
            return amount
        if value <= 0:
            return ""
        prefix = prices.get("currency_prefix") or ""
        suffix = prices.get("currency_suffix") or ""
        decimal = prices.get("currency_decimal_separator") or "."
        return f"{prefix}{value:.{minor_unit}f}".replace(".", decimal) + suffix

    @classmethod
    def _store_image_url(cls, product: dict) -> str | None:
        """Pick the product's primary image from the Store API ``images`` array.

        Every coffee carries 1-5 entries with the bag shot first. ``src`` is
        preferred and ``thumbnail`` is the fallback; non-dict entries and values
        that are not absolute http(s) URLs are skipped.

        Args:
            product: Product object from the Store API

        Returns:
            Normalized image URL, or None when the product has no usable image
        """
        for image in product.get("images") or []:
            if not isinstance(image, dict):
                continue
            candidate = cls._normalize_image_url(image.get("src") or image.get("thumbnail"))
            if candidate:
                return candidate
        return None

    @staticmethod
    def _text_block(raw_html: str | None) -> str:
        """Prepare a WooCommerce text field for the compact soup.

        ``<img>`` tags are removed: the text fields embed WordPress attachment
        links that go stale when a shop re-uploads a shot, and the extractor's
        image choice would then beat the ``og:image`` built from the current
        media set — the base's backfill only fires when the bean has no image
        at all. Returns an empty string when nothing but markup is left, so an
        empty field never emits a heading over nothing.
        """
        if not raw_html:
            return ""
        fragment = BeautifulSoup(raw_html, "html.parser")
        for image in fragment.find_all("img"):
            image.decompose()
        if not fragment.get_text(strip=True):
            return ""
        return str(fragment).strip()

    @staticmethod
    def _select_store_product(items: list[dict]) -> dict | None:
        """Pick the parent product out of a ``?slug=`` Store API response.

        A WooCommerce slug query also matches the product's variations and the
        response order is not stable. A variation carries only its own
        ``prices.price``, neither text field and a ``price_range`` of ``null``,
        so the parent product is the only entry that has the origin prose, the
        tasting notes and the full media set. Falls back to the first item when
        the response holds nothing but variations.

        Args:
            items: Decoded ``?slug=`` response body

        Returns:
            The parent product dict, or None for an empty response
        """
        if not items:
            return None
        for item in items:
            if item.get("type") != "variation":
                return item
        return items[0]

    @classmethod
    def _build_product_soup(cls, product: dict) -> BeautifulSoup:
        """Build a compact product soup from a WooCommerce Store API product.

        Args:
            product: Product object from ``.../products?slug=<slug>``

        Returns:
            BeautifulSoup object of the compact product markup.
        """
        prices = product.get("prices") or {}
        parts: list[str] = ["<div>"]

        name = product.get("name")
        if name:
            parts.append(f"<h1>{name}</h1>")

        # ``price_range`` is only populated when the variations differ in price;
        # for a flat-priced product it is null and ``price`` holds the only
        # (minimum) amount. Both are in minor units.
        price_range = prices.get("price_range") or {}
        raw_low = price_range.get("min_amount") or prices.get("price") or prices.get("regular_price")
        raw_high = price_range.get("max_amount") or raw_low
        low = cls._format_price(raw_low, prices)
        high = cls._format_price(raw_high, prices)
        if low and high and low != high:
            parts.append(f"<p>Price: {low} - {high}</p>")
        elif low or high:
            parts.append(f"<p>Price: {low or high}</p>")

        # Name the currency in the markup: the base class cannot detect it from
        # this compact JSON soup, and without it the extractor picked its own
        # default (GBP) and produced prices that then failed the range check.
        currency_code = prices.get("currency_code")
        if currency_code:
            parts.append(f"<p>Currency: {currency_code}</p>")

        # Declare the current media set the way a rendered page would.
        # ``_extract_image_url_from_soup`` reads og:image before anything else,
        # so this both feeds the extractor and backs it up — and the base's
        # fill-if-empty backfill is only sufficient because the text blocks
        # below carry no ``<img>`` of their own.
        image_src = cls._store_image_url(product)
        if image_src:
            parts.append(f'<meta property="og:image" content="{escape(image_src, quote=True)}">')

        availability = "In stock" if product.get("is_in_stock") else "Out of stock"
        parts.append(f"<p>Availability: {availability}</p>")

        # Variations carry Størrelse (size) × Kverningsgrad (grind) attribute
        # pairs; collapse them into the unique values per attribute so the AI
        # extractor sees the available sizes/grinds without 8+ near-duplicate
        # lines.
        attribute_values: dict[str, list[str]] = {}
        for variation in product.get("variations") or []:
            for attr in variation.get("attributes") or []:
                attr_name = attr.get("name")
                value = attr.get("value")
                if attr_name and value:
                    seen = attribute_values.setdefault(attr_name, [])
                    if value not in seen:
                        seen.append(value)
        if attribute_values:
            lines = ["Variants:"]
            for attr_name, values in attribute_values.items():
                lines.append(f"- {attr_name}: {', '.join(values)}")
            parts.append(f"<pre>{'<br>'.join(lines)}</pre>")

        # Both text fields are emitted, each under its own heading, and each
        # independently of the other: ``short_description`` is the store's
        # long-form copy (region, producer/cooperative, direct-payment figures)
        # and ``description`` is the tasting-note block. They are complementary,
        # so treating either as a fallback for the other would drop the more
        # valuable half of the page. The origin prose goes first so it also
        # survives any downstream truncation of the soup.
        short_description = cls._text_block(product.get("short_description"))
        if short_description:
            parts.append(f"<h2>{cls._SHORT_DESCRIPTION_HEADING}</h2><div>{short_description}</div>")

        description = cls._text_block(product.get("description"))
        if description:
            parts.append(f"<h2>{cls._DESCRIPTION_HEADING}</h2><div>{description}</div>")

        parts.append("</div>")
        return BeautifulSoup("".join(parts), "html.parser")

    async def _fetch_store_product_soup(self, product_url: str) -> BeautifulSoup | None:
        """Fetch a product's data from the WooCommerce Store API as a compact soup.

        Args:
            product_url: Product detail URL (``https://nordoslo.no/butikk/kaffe/filter/<slug>/``)

        Returns:
            Compact BeautifulSoup object, or None if the API fetch failed.
        """
        slug = product_url.rstrip("/").split("/")[-1]
        if not slug:
            return None
        api_url = f"{self._STORE_API_URL}?slug={slug}"

        try:
            await asyncio.sleep(self.rate_limit_delay)
            response = await self.client.get(api_url)
            response.raise_for_status()
            product = self._select_store_product(response.json() or [])
            if product is None:
                logger.warning(f"Empty store API payload for {product_url}")
                return None
            return self._build_product_soup(product)
        except Exception as e:
            logger.warning(f"Store API fetch failed for {product_url}: {e}")
            return None

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, using the Store API for product detail pages.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object or None if fetch failed.
        """
        url = kwargs.get("url")
        if not url and len(args) > 0:
            url = args[0]

        if url and "/butikk/" in url:
            product_soup = await self._fetch_store_product_soup(url)
            if product_soup is not None:
                return product_soup
            logger.warning(f"Falling back to HTML fetch for {url}")

        return await super().fetch_page(*args, **kwargs)

    # Sold-out detection: WooCommerce Store API ``is_in_stock`` flag.
    # The API listing carries explicit per-product stock state, so sold-out
    # items are skipped BEFORE coffee-URL filtering, and the base class's
    # listing-failure guard still applies (a failed API fetch returns [] and
    # is recorded as a failed store URL).
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the WooCommerce Store API listing.

        Args:
            store_url: URL of the Store API products listing (page 1)

        Returns:
            List of in-stock coffee product URLs
        """
        product_urls: list[str] = []

        for page in range(1, self._max_listing_pages + 1):
            listing_url = f"{self._STORE_API_URL}?{self._LISTING_QUERY.format(page=page)}"
            try:
                response = await self.client.get(listing_url)
                response.raise_for_status()
                items = response.json() or []
            except Exception as e:
                logger.error(f"Failed to fetch store API listing {listing_url}: {e}")
                # A failed listing fetch must return [] so the base class
                # records the store URL as failed and skips OOS updates.
                return []

            if not items:
                break

            for item in items:
                # Skip sold-out products before URL-pattern filtering
                if not item.get("is_in_stock", True):
                    logger.debug(f"Skipping sold-out product: {item.get('name')}")
                    continue

                url = item.get("permalink") or ""
                if not url:
                    continue

                # Only the Norwegian "Kaffe" category is coffee; equipment
                # lives in "Utstyr" and subscriptions in "Abonnement". Some of
                # the older espresso blends return an empty category list, so
                # the permalink's /butikk/kaffe/ path counts as well.
                category_names = {c.get("name", "") for c in item.get("categories") or []}
                if "Kaffe" not in category_names and "/butikk/kaffe/" not in url:
                    logger.debug(f"Skipping non-coffee product: {item.get('name')} ({category_names})")
                    continue

                url_lower = url.lower()
                if any(slug in url_lower for slug in self._excluded_url_slugs):
                    logger.debug(f"Excluding non-coffee product URL: {url}")
                    continue
                if not self.is_coffee_product_url(url, required_path_patterns=["/butikk/"]):
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
            use_playwright=False,
            use_optimized_mode=False,
            translate_to_english=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin NOK on the bean and on every price option.

        The base class's display-name currency lookup can silently fall back to
        GBP, so pin the verified home currency (NOK, confirmed via the Store
        API ``currency_code`` field) here as a final guard. ``price_options``
        carry their own ``currency`` field which the extractor leaves unset or
        guesses, and a mismatched entry poisons ``price_usd`` normalization at
        refresh time, so it is normalised to the same code.

        Note: ``CoffeeBean`` sets ``validate_assignment=True``, so assigning
        ``currency`` re-runs the ``check_prices`` range validator. That is
        intentional and matches every other currency-pinning scraper
        (``lantern_coffee``/``delicate_coffee``/``gwo_coffee``): the bean only
        validates once the extractor has been shown the real NOK price, and a
        genuinely wrong price should fail loudly rather than be silently kept.
        """
        bean.currency = "NOK"
        for price_option in bean.price_options or []:
            price_option.currency = "NOK"
        return bean
