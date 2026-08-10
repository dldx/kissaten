"""Redemption Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="redemption",
    display_name="Redemption Roasters",
    roaster_name="Redemption Roasters",
    website="https://redemptionroasters.com",
    description="London-based social enterprise on a mission to reduce reoffending "
    "through coffee.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RedemptionRoastersScraper(ShopifyJsonScraper):
    """Scraper for Redemption Roasters (redemptionroasters.com) using Shopify products.json.

    The coffee catalogue is spread across three overlapping collections
    (``all-coffee``, ``single-origin``, ``house-coffee``), so a product is
    discovered even if Redemption reorganises one collection;
    ``preprocess_product_url`` canonicalises every collection URL to
    ``https://redemptionroasters.com/products/<handle>`` (the exact form used
    on the live site, whose www host redirects to the bare domain), so
    duplicate listings across collections collapse to one URL and are never
    scraped twice.

    Redemption keeps stable product slugs (``the-yard``, ``the-block``, ...)
    but the underlying bean rotates — e.g. ``The Yard`` is a seasonally
    blended espresso whose origins and tasting notes change each edition
    while the handle stays put. To track these content changes, each product
    URL is suffixed with ``#<image-version>`` (the Shopify CDN ``?v=``
    parameter of the product's first image). When an edition rotates the main
    image's version changes, producing a new URL: the new bean is scraped
    fresh while the old URL drops out of products.json and is marked
    out-of-stock by the diffjson flow, preserving history instead of
    overwriting the same record. We use only the FIRST image (not one URL per
    gallery image) because Redemption's extra images are marketing shots of
    the same bean — unlike Wide Awake, where each image is a distinct coffee.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Redemption Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Redemption Roasters",
            base_url="https://redemptionroasters.com",
            products_json_urls=[
                "https://redemptionroasters.com/collections/all-coffee/products.json",
            ],
            # Fetch and send the product page soup to the AI extractor (limited
            # to the POWER-theme product containers in ``preprocess_product_soup``),
            # alongside the Shopify products.json metadata.
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products. "pods" catches the four coffee-pod
        # SKUs listed alongside the beans (everyday/dark-roast/light-roast/
        # taster-pack); it appears in NO bean handle, while the bean handles
        # (the-yard, the-block, the-governor, mutungati-ab, kigeri-anoxic-
        # natural, ngila-estate, decaf, the-roll-call, roasters-roulette-
        # filter) all survive. The remaining slugs are distinctive substrings
        # of equipment/tea/merch handles from the full catalog, all verified
        # against every bean handle.
        self.exclude_slugs = [
            "pods",
            "taster-pack",
            "tea-bags",
            "blendsmiths",
            "aeropress",
            "chemex",
            "grinder",
            "kettle",
            "voucher",
            "subscription",
            "gift",
            "sage",
            "moka",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalise product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoints live under ``/collections/<slug>``, so the
        default URL construction yields ``/collections/<slug>/products/<handle>``.
        The live site uses the canonical ``/products/<handle>`` form (and
        redirects the bare domain's www host back to the bare domain), so we
        strip the collection segment here and normalise the host. Overlapping
        collections therefore merge onto a single URL and are never duplicated.
        """
        url = re.sub(r"/collections/[^/]+(?=/products/)", "", url)
        url = re.sub(r"^https://www\.redemptionroasters\.com", "https://redemptionroasters.com", url)
        return url

    @staticmethod
    def _image_variant(image_src: str) -> str | None:
        """Extract the ``?v=<id>`` version parameter from a Shopify CDN URL."""
        return parse_qs(urlparse(image_src).query).get("v", [None])[0]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from products.json, one per product.

        Redemption reuses the same product slug for a rotating bean (e.g. a
        new edition of ``The Yard`` keeps the same handle while the origins
        and notes change), so we append the first product image's CDN version
        as a URL fragment. A rotation changes the version (and therefore the
        URL), which the base ``scrape()`` flow treats as a NEW product —
        triggering full re-extraction while the base stock-update logic marks
        the prior URL (now absent from products.json) as out-of-stock.

        Only the first image is used (one URL per product) because Redemption's
        remaining images are a gallery of the same bean, not distinct coffees.

        Args:
            store_url: URL of the products.json endpoint.

        Returns:
            List of disambiguated product URLs (one per product).
        """
        products = await self._fetch_all_shopify_products(store_url)
        base_path = store_url.replace("/products.json", "")
        found_urls: list[str] = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            if not self.is_coffee_product_name(product.get("title", "")):
                continue

            product_base_url = self.preprocess_product_url(f"{base_path}/products/{handle}")
            url_base = product_base_url.split("#", 1)[0]

            # Append the first image version so content rotation produces a
            # fresh URL identity (triggers full re-extraction on rotation).
            images = product.get("images", [])
            if images:
                first_image_src = images[0].get("src", "") or ""
                version = self._image_variant(first_image_src) or str(images[0].get("id", ""))
                url = f"{url_base}#{version}"
            else:
                url = url_base

            # Store metadata for later enrichment and stock status
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            if self.is_coffee_product_url(url_base):
                found_urls.append(url)

        return found_urls

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Limit the product page soup to the information-bearing containers.

        Redemption's pages run the Shopify POWER theme, whose HTML is large
        (header, footer, scripts, related-product and recommendation blocks).
        Before AI extraction we keep only the product containers:

          * ``<section id*="power_section">`` — product story / brand sections
          * ``div.product`` — the main product block (title, price, description)

        Everything else is dropped so the AI gets a small, focused payload on
        top of the injected products.json metadata. If neither container is
        found (e.g. the theme changed), we fall back to the full page so the
        product information is never silently lost.
        """
        keep = soup.select('section[id*="power_section"]') + soup.select("div.product")
        if not keep:
            logger.debug("No POWER-theme product containers found; sending full product page soup.")
            return soup

        limited = BeautifulSoup("<html><head></head><body></body></html>", "lxml")
        for el in keep:
            limited.body.append(el)

        # Strip markup and buy-chrome that carries no product facts (scripts,
        # icon SVGs, hidden containers, form controls, heavy image URLs) so we
        # send the extractor only the relevant text-bearing containers.
        self._prune_soup_for_ai(limited)
        logger.debug(f"Sending product page soup limited to {len(keep)} POWER-theme container(s).")
        return limited

    def _prune_soup_for_ai(self, soup: BeautifulSoup) -> None:
        """Remove elements that add markup but no product facts, to cut tokens.

        The cards/containers kept by :meth:`preprocess_product_soup` still ship
        scripts, style blocks, SVG icons, hidden variant-select widths, and the
        add-to-cart chrome. None of those help extraction, so they are dropped
        in place. We keep the headings, paragraphs, spec table, list items and
        variant weight/grind text that carry the bean facts the extractor
        needs. Exact variant prices and availability are still supplied by the
        injected Shopify JSON context (added afterwards by
        ``_inject_shopify_context``), so trimming the HTML buys no information
        loss.
        """
        # 1) Pure-markup / non-visual elements (no text the extractor needs).
        for name in (
            "script",
            "style",
            "noscript",
            "template",
            "link",
            "meta",
            "svg",
            "path",
            "circle",
            "iframe",
            "source",
            "picture",
        ):
            for tag in soup.find_all(name):
                tag.decompose()

        # 2) Hidden containers (e.g. the JS variant-select backbone that only
        #    mirrors the price data already present in the Shopify JSON).
        for tag in soup.find_all(True):
            style = tag.get("style") or ""
            if "display:none" in style.replace(" ", ""):
                tag.decompose()

        # 3) Collapse images to their alt text; drop long CDN src/srcset URLs
        #    that inflate the payload, and drop images with no alt at all.
        for img in soup.find_all("img"):
            for attr in (
                "src",
                "srcset",
                "data-src",
                "data-srcset",
                "sizes",
                "loading",
                "width",
                "height",
                "fetchpriority",
                "class",
            ):
                img.attrs.pop(attr, None)
            if not (img.get("alt") or ""):
                img.decompose()

        # 4) Buy-form / gallery chrome: buttons, inputs, quantity/pickup/
        #    rewards widgets carry no bean facts. Keep variant-selects (the
        #    weight/grind text) and the spec table.
        for name in (
            "media-gallery",
            "slider-component",
            "modal-opener",
            "button",
            "input",
            "label",
            "quantity-input",
            "recharge-subscription-widget",
            "pickup-availability",
            "pickup-availability-preview",
            "product-form",
        ):
            for tag in soup.find_all(name):
                tag.decompose()

        # 5) Collapse now-empty wrappers so we do not ship hundreds of empty
        #    <div>/<span> tags.
        changed = True
        while changed:
            changed = False
            for tag in soup.find_all(True):
                if tag.name in (
                    "html",
                    "head",
                    "body",
                    "section",
                    "div",
                    "span",
                    "p",
                    "ul",
                    "li",
                    "a",
                ):
                    if not tag.get_text(strip=True) and not tag.find("img"):
                        tag.decompose()
                        changed = True
