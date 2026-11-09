"""Unit tests for the Terres De Café scraper.

Terres De Café's PrestaShop storefront stopped rendering
``<article class="product-miniature">`` tiles in raw HTML; each paginated
listing page now embeds a ``var stape_products = [...]`` JSON blob (a
PrestaShop "stape" data-layer) whose entries carry a fully-qualified ``link``
URL. These tests run against a captured fixture of the listing page payload
(see ``tests/fixtures/terres_de_cafe_listing.json``) and verify the JSON
parsing, coffee-category URL filtering, pagination walking, and the graceful
stop when a listing page fails to fetch.
"""

import json
from pathlib import Path

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.terres_de_cafe import TerresDeCafeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "terres_de_cafe_listing.json"


def _make_scraper() -> TerresDeCafeScraper:
    # No api_key: no network, no AI extractor needed for these tests.
    return TerresDeCafeScraper()


def _fixture_products() -> list[dict]:
    data = json.loads(FIXTURE.read_text())
    return data["stape_products"]


def _build_listing_html(products: list[dict], next_page: int | None = None) -> str:
    """Build a fake listing page HTML with the stape_products blob + pagination."""

    blob = json.dumps(products)
    links = ""
    if next_page:
        links = (
            f'<a href="https://www.terresdecafe.com/en/13-speciality-coffees?page={next_page}" '
            f"data-page-link>{next_page}</a>"
        )
    return f"""<html><body><script>var stape_products = {blob};</script>
    <div class="pagination">{links}</div></body></html>"""


class _FakeSoup:
    """Minimal BeautifulSoup stand-in that supports select() and str()."""

    def __init__(self, html: str):
        self.html = html

    def __str__(self) -> str:
        return self.html

    def select(self, selector: str):
        # Only the pagination selector is used by _next_listing_page.
        import re as _re

        if selector == "a[data-page-link]":
            return _re.findall(r'<a href="[^"]*"[^>]*data-page-link[^>]*>[^<]*</a>', self.html)
        return []

    def select_one(self, selector: str):
        return None


def test_registered_in_registry():
    registry = get_registry()
    assert registry.is_registered("terres-de-cafe")
    info = registry.get_scraper_info("terres-de-cafe")
    assert info is not None
    assert info.scraper_class is TerresDeCafeScraper
    assert info.currency == "EUR"
    assert info.country == "France"
    assert info.status == "available"


async def test_store_urls_point_at_current_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == ["https://www.terresdecafe.com/en/13-speciality-coffees"]


def test_parse_stape_products_from_fixture():
    scraper = _make_scraper()
    products = _fixture_products()
    html = _build_listing_html(products)

    urls = scraper._parse_stape_products(html)

    # Fixture contains 12 products: 8 speciality-coffees + 2 beans-coffee
    # (cross-listed) + 2 gamme-legendes (cross-listed).
    assert len(urls) == 12
    assert all(u.startswith("https://www.terresdecafe.com/en/") for u in urls)
    assert all(u.endswith(".html") for u in urls)
    # Coffee categories only.
    for u in urls:
        assert any(cat in u for cat in ("/speciality-coffees/", "/beans-coffee/", "/gamme-legendes/"))


def test_parse_stape_products_rejects_non_coffee_categories():
    scraper = _make_scraper()
    products = [
        {"link": "https://www.terresdecafe.com/en/tea-chocolate/1025-chocolate-powder-70.html"},
        {"link": "https://www.terresdecafe.com/en/drip-coffee-bags/2000-immersion-coffee-bag.html"},
        {"link": "https://www.terresdecafe.com/en/speciality-coffees/2107-coffee-ksf-limmu-bedaye-washed-bio.html"},
    ]
    html = _build_listing_html(products)

    urls = scraper._parse_stape_products(html)

    # Only the speciality-coffees entry passes the required-path-pattern filter.
    assert urls == ["https://www.terresdecafe.com/en/speciality-coffees/2107-coffee-ksf-limmu-bedaye-washed-bio.html"]


def test_parse_stape_products_empty_when_blob_missing():
    scraper = _make_scraper()
    html = "<html><body><p>No products here</p></body></html>"

    assert scraper._parse_stape_products(html) == []


def test_parse_stape_products_malformed_json_returns_empty():
    scraper = _make_scraper()
    html = "<html><script>var stape_products = [{broken;};</script></html>"

    assert scraper._parse_stape_products(html) == []


def test_next_listing_page_finds_next_page():
    scraper = _make_scraper()
    html = _build_listing_html(_fixture_products(), next_page=2)
    current = "https://www.terresdecafe.com/en/13-speciality-coffees"

    nxt = scraper._next_listing_page(html, current)
    assert nxt == "https://www.terresdecafe.com/en/13-speciality-coffees?page=2"


def test_next_listing_page_returns_none_on_last_page():
    scraper = _make_scraper()
    html = _build_listing_html(_fixture_products(), next_page=None)
    current = "https://www.terresdecafe.com/en/13-speciality-coffees?page=8"

    assert scraper._next_listing_page(html, current) is None


async def test_extract_product_urls_walks_pagination_and_dedupes():
    scraper = _make_scraper()
    products = _fixture_products()
    page_htmls = [
        _FakeSoup(_build_listing_html(products, next_page=2)),
        _FakeSoup(_build_listing_html(products, next_page=3)),
        _FakeSoup(_build_listing_html(products, next_page=None)),
    ]
    fetched: list[str] = []

    async def fake_fetch_page(url, *args, **kwargs):
        fetched.append(url)
        return page_htmls.pop(0) if page_htmls else None

    scraper.fetch_page = fake_fetch_page  # type: ignore[method-assign]

    urls = await scraper._extract_product_urls_from_store("https://www.terresdecafe.com/en/13-speciality-coffees")

    # All three pages serve the same 12 products; the URL set is deduped.
    assert len(fetched) == 3
    assert len(urls) == 12
    assert len(set(urls)) == len(urls)


async def test_extract_stops_when_fetch_fails():
    scraper = _make_scraper()
    fetched: list[str] = []

    async def fake_fetch_page(url, *args, **kwargs):
        fetched.append(url)
        return None

    scraper.fetch_page = fake_fetch_page  # type: ignore[method-assign]

    urls = await scraper._extract_product_urls_from_store("https://www.terresdecafe.com/en/13-speciality-coffees")

    assert urls == []
    assert fetched == ["https://www.terresdecafe.com/en/13-speciality-coffees"]


async def test_extract_stops_when_blob_missing():
    scraper = _make_scraper()

    async def fake_fetch_page(url, *args, **kwargs):
        return _FakeSoup("<html><body>No stape data</body></html>")

    scraper.fetch_page = fake_fetch_page  # type: ignore[method-assign]

    urls = await scraper._extract_product_urls_from_store("https://www.terresdecafe.com/en/13-speciality-coffees")

    assert urls == []
