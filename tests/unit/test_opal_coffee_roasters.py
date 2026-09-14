"""Unit tests for the Opal Coffee Roasters scraper (Squarespace storefront).

All network access is stubbed: the listing extraction runs against synthetic
Squarespace markup captured from the live ``/seasonal-coffee`` collection
(10 products on capture: Burundi, Rwanda, Peru, 4x Colombia, 2x Kenya,
Brazil), so catalogue drift — a new collection path, a URL-format change —
fails the test and is visible as a stub diff.

Covered per-scraper behaviour:
- Listing extraction via the ``product-list-item`` cards and the
  ``/seasonal-coffee/p/`` product URL pattern.
- Sold-out detection via the card-level "Sold out" badge text.
- Exclusion of the equipment-collection products (AeroPress, Hario V60, ...).
- Meta-only ``fetch_page`` compaction + ``Static.SQUARESPACE_CONTEXT``
  variant parsing (size, price, currency, stock).
- GBP currency pin in ``postprocess_extracted_bean``.
- Registry metadata (roaster_name byte-identity, currency, country).
"""

import json

from bs4 import BeautifulSoup

from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.opal_coffee_roasters import OpalCoffeeRoastersScraper

LISTING_URL = "https://www.opalcoffeeroasters.co.uk/seasonal-coffee"
PRODUCT_URL_TEMPLATE = "https://www.opalcoffeeroasters.co.uk/seasonal-coffee/p/"

# Slugs captured from the live /seasonal-coffee listing (2026-09-14).
LIVE_COFFEE_SLUGS = [
    "xqtpb8l7prv5ae9jh84w0tfq70yxqm",  # Migoti Hill Burundi
    "whscuryrb8z34ivifcv4cuscz68bkc",  # Kirunga Natural Rwanda
    "4rtp208fpoylvwgg61xogj7ase56p1",  # San Ignacio Peru
    "xr6cq7l3s8wc9fwfrtplxlwn3ommb3",  # La Esperanza Colombia
    "67psm4o096ko9lp63xsdw3t49qybuj",  # El Jaragual Colombia
    "tp33b98hbdqgg7trktcnqrlnu0gkd9",  # Edinson Argote Colombia
    "vau99bspt9wvulkvcavhfre6osw9ls",  # Aponte Honey Colombia
    "558xekoewmdl56ts00erotik8mku9r",  # AA Thunguri Kenya
    "vttgonl6sunkumyr10e18hbnqljdbn",  # Neyri AA Kenya
    "jfyiudg2dqn647g6z4yswp0oxcturl",  # Lillian Gallo Brazil
]


def make_scraper() -> OpalCoffeeRoastersScraper:
    scraper = OpalCoffeeRoastersScraper()
    scraper._force_playwright = False
    return scraper


def _listing_card(slug: str, title: str, sold_out: bool = False) -> str:
    status = '<div class="product-list-item-status"><span>Sold out</span></div>' if sold_out else ""
    return f"""
    <div class="product-list-item" data-product-id="{slug[:8]}">
      <a class="product-list-item-link" href="/seasonal-coffee/p/{slug}" aria-label="{title}">
        <div class="product-list-image-wrapper">
          <figure class="product-list-item-image"><img data-src="https://images.squarespace-cdn.com/x.jpg"></figure>
        </div>
        <div class="product-list-item-title">{title}</div>
        <div class="product-list-item-price">£17.25</div>
        {status}
      </a>
    </div>
    """


def _listing_html(*cards: str) -> str:
    return f"""
    <html><head><title>Seasonal Coffee — Opal coffee roasters</title></head><body>
    <div class="product-list">
      {''.join(cards)}
    </div>
    <nav><a href="/equipment">Equipment</a><a href="/wholesale">Wholesale</a></nav>
    </body></html>
    """


def _install_listing(scraper: OpalCoffeeRoastersScraper, html: str) -> None:
    async def fake_fetch_page(url: str, **kwargs) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    scraper.fetch_page = fake_fetch_page  # type: ignore[method-assign]


async def test_listing_extraction_returns_all_live_coffees():
    scraper = make_scraper()
    cards = [
        _listing_card("xqtpb8l7prv5ae9jh84w0tfq70yxqm", "Migoti Hill Burundi"),
        _listing_card("whscuryrb8z34ivifcv4cuscz68bkc", "Kirunga Natural Rwanda"),
        _listing_card("4rtp208fpoylvwgg61xogj7ase56p1", "San Ignacio Peru"),
        _listing_card("xr6cq7l3s8wc9fwfrtplxlwn3ommb3", "La Esperanza Colombia"),
        _listing_card("67psm4o096ko9lp63xsdw3t49qybuj", "El Jaragual Colombia"),
        _listing_card("tp33b98hbdqgg7trktcnqrlnu0gkd9", "Edinson Argote Colombia"),
        _listing_card("vau99bspt9wvulkvcavhfre6osw9ls", "Aponte Honey Colombia"),
        _listing_card("558xekoewmdl56ts00erotik8mku9r", "AA Thunguri Kenya"),
        _listing_card("vttgonl6sunkumyr10e18hbnqljdbn", "Neyri AA Kenya"),
        _listing_card("jfyiudg2dqn647g6z4yswp0oxcturl", "Lillian Gallo Brazil"),
    ]
    _install_listing(scraper, _listing_html(*cards))

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    assert len(urls) == 10
    assert all(u.startswith(PRODUCT_URL_TEMPLATE) for u in urls)
    for slug in LIVE_COFFEE_SLUGS:
        assert f"{PRODUCT_URL_TEMPLATE}{slug}" in urls


async def test_sold_out_card_is_skipped():
    scraper = make_scraper()
    _install_listing(
        scraper,
        _listing_html(
            _listing_card("xqtpb8l7prv5ae9jh84w0tfq70yxqm", "Migoti Hill Burundi"),
            _listing_card("558xekoewmdl56ts00erotik8mku9r", "AA Thunguri Kenya", sold_out=True),
        ),
    )

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    assert urls == [f"{PRODUCT_URL_TEMPLATE}xqtpb8l7prv5ae9jh84w0tfq70yxqm"]
    assert f"{PRODUCT_URL_TEMPLATE}558xekoewmdl56ts00erotik8mku9r" not in urls


async def test_duplicate_urls_are_deduplicated():
    scraper = make_scraper()
    slug = "xqtpb8l7prv5ae9jh84w0tfq70yxqm"
    _install_listing(
        scraper,
        _listing_html(_listing_card(slug, "Migoti Hill Burundi"))
        + f'<a href="/seasonal-coffee/p/{slug}">Migoti Hill Burundi</a>',
    )

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    assert urls == [f"{PRODUCT_URL_TEMPLATE}{slug}"]


async def test_equipment_and_non_coffee_urls_are_excluded():
    scraper = make_scraper()
    _install_listing(
        scraper,
        _listing_html(_listing_card("xqtpb8l7prv5ae9jh84w0tfq70yxqm", "Migoti Hill Burundi")),
    )

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # Only /seasonal-coffee/p/ paths pass the required-path gate: the equipment
    # collection (/equipment/p/aeropress, /equipment/p/hario-v60-coffee-dripper)
    # lives on a separate Squarespace page and must never leak in.
    assert all("/seasonal-coffee/p/" in u for u in urls)


def test_store_urls_point_at_seasonal_coffee_listing():
    scraper = make_scraper()

    assert scraper.get_store_urls.__self__.base_url == "https://www.opalcoffeeroasters.co.uk"


async def test_get_store_urls_returns_listing_page():
    scraper = make_scraper()

    urls = await scraper.get_store_urls()

    assert urls == [LISTING_URL]


def _product_html(static_context: dict | None = None) -> str:
    context_script = ""
    if static_context is not None:
        context_script = (
            '<script type="application/json" data-name="static-context">'
            f"Static.SQUARESPACE_CONTEXT = {json.dumps(static_context)};"
            "</script>"
        )
    return f"""
    <html><head>
      <title>Migoti Hill Burundi — Opal coffee roasters</title>
      <meta property="og:site_name" content="Opal coffee roasters">
      <meta property="og:title" content="Migoti Hill Burundi — Opal coffee roasters">
      <meta property="og:url" content="{PRODUCT_URL_TEMPLATE}xqtpb8l7prv5ae9jh84w0tfq70yxqm">
      <meta property="og:type" content="product">
      <meta property="og:description" content="Grown in the Nyabiraba Commune, Burundi. Plum, brown sugar.">
      <meta property="product:price:amount" content="17.25">
      <meta property="product:price:currency" content="GBP">
      <meta property="product:availability" content="instock">
      <meta name="description" content="Migoti Hill Burundi seasonal coffee">
      <meta property="og:image" content="https://images.squarespace-cdn.com/bean.jpg">
      {context_script}
    </head><body>
      <div class="product-related-products"><a href="/seasonal-coffee/p/other">Related</a></div>
      <h1>Migoti Hill Burundi</h1>
      <p>Body noise that must be dropped by the meta-only compaction.</p>
    </body></html>
    """


STATIC_CONTEXT = {
    "product": {
        "title": "Migoti Hill Burundi",
        "variants": [
            {
                "attributes": {"Size": "200g"},
                "price": {"decimalValue": "17.25", "currencyCode": "GBP"},
                "stock": {"unlimited": True},
            },
            {
                "attributes": {"Size": "1kg"},
                "price": {"decimalValue": "39.95", "currencyCode": "GBP"},
                "stock": {"unlimited": False},
            },
        ],
    }
}


async def test_fetch_page_product_page_returns_meta_only_soup_with_variants(monkeypatch):
    scraper = make_scraper()
    full_soup = BeautifulSoup(_product_html(STATIC_CONTEXT), "html.parser")

    async def fake_base_fetch_page(self, url: str, **kwargs) -> BeautifulSoup:
        return full_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch_page)

    compact = await scraper.fetch_page(f"{PRODUCT_URL_TEMPLATE}xqtpb8l7prv5ae9jh84w0tfq70yxqm")

    html = str(compact)
    # Kept: product meta tags + variants block
    assert 'property="og:title"' in html
    assert 'property="product:price:amount"' in html
    assert 'property="product:availability"' in html
    assert "Variants:" in compact.get_text()
    variants_text = compact.find("div").get_text()
    assert "- Size: 200g | Price: 17.25 GBP | Stock: instock" in variants_text
    assert "- Size: 1kg | Price: 39.95 GBP | Stock: unknown" in variants_text
    # Dropped: body noise, images, related-product links
    assert "Body noise" not in html
    assert "og:image" not in html
    assert "product-related-products" not in html


async def test_fetch_page_non_product_url_returns_unmodified_soup(monkeypatch):
    scraper = make_scraper()
    full_soup = BeautifulSoup(
        _listing_html(_listing_card("xqtpb8l7prv5ae9jh84w0tfq70yxqm", "Migoti Hill Burundi")), "html.parser"
    )

    async def fake_base_fetch_page(self, url: str, **kwargs) -> BeautifulSoup:
        return full_soup

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch_page)

    compact = await scraper.fetch_page(LISTING_URL)

    assert compact is full_soup


def test_extract_variants_without_static_context_returns_empty_container():
    soup = BeautifulSoup(_product_html(static_context=None), "html.parser")

    container = OpalCoffeeRoastersScraper._extract_variants(soup)

    assert container.get_text(strip=True) == ""


def test_postprocess_extracted_bean_forces_gbp():
    scraper = make_scraper()

    class FakeBean:
        currency = "USD"

    bean = scraper.postprocess_extracted_bean(FakeBean())  # type: ignore[arg-type]

    assert bean.currency == "GBP"


def test_registry_metadata():
    from kissaten.scrapers.registry import get_registry

    info = get_registry().get_scraper_info("opal-coffee-roasters")

    assert info is not None
    assert info.roaster_name == "Opal Coffee Roasters"
    assert info.display_name == "Opal Coffee Roasters"
    assert info.website == "https://www.opalcoffeeroasters.co.uk"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"

    scraper = make_scraper()
    # Byte-identical roaster_name between @register_scraper and super().__init__.
    assert scraper.roaster_name == info.roaster_name


def test_scraper_init_defaults():
    scraper = make_scraper()

    assert scraper.base_url == "https://www.opalcoffeeroasters.co.uk"
    assert scraper.rate_limit_delay == 2.0
