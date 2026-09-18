"""Unit tests for the Roosevelt Coffeehouse scraper (fixture-based, no network)."""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.roosevelt_coffeehouse import RooseveltCoffeehouseScraper

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
LISTING_URL = (
    RooseveltCoffeehouseScraper._STORE_API_URL + "?" + RooseveltCoffeehouseScraper._LISTING_QUERY.format(page=1)
)
PRODUCT_URL = "https://roosevelt.coffee/product/guatemala-blue-ayarza/"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "roosevelt_coffeehouse_products_api.json").read_text())


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeClient:
    """Minimal stand-in for the httpx async client, keyed by URL substring."""

    def __init__(self, routes):
        self._routes = routes

    async def get(self, url):
        for token, payload in self._routes.items():
            if token in url:
                return _FakeResponse(payload)
        raise AssertionError(f"Unexpected URL requested in test: {url}")


def _make_scraper() -> RooseveltCoffeehouseScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return RooseveltCoffeehouseScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("roosevelt-coffeehouse")
    assert info is not None
    assert info.roaster_name == "Roosevelt Coffeehouse"
    assert info.display_name == "Roosevelt Coffeehouse"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Roosevelt Coffeehouse"


async def test_store_urls_use_store_api_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [LISTING_URL]


async def test_extracts_coffee_urls_from_store_api(mocker):
    scraper = _make_scraper()
    mocker.patch.object(scraper, "client", _FakeClient({"products?per_page=100": _fixture_products()}))

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    assert "https://roosevelt.coffee/product/rwanda-kamonyi-district/" in urls
    assert "https://roosevelt.coffee/product/guatemala-blue-ayarza/" in urls
    assert "https://roosevelt.coffee/product/5lb-coffee/" in urls
    # Every extracted URL uses the WooCommerce /product/ path format.
    assert all("/product/" in u for u in urls)
    assert len(urls) == 5


async def test_sold_out_products_are_skipped(mocker):
    scraper = _make_scraper()
    mocker.patch.object(scraper, "client", _FakeClient({"products?per_page=100": _fixture_products()}))

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # Colombia sugarcane decaf carries is_in_stock = false in the listing.
    assert "https://roosevelt.coffee/product/colombia-sugarcane-decaf/" not in urls


async def test_merch_gifts_and_subscription_categories_are_excluded(mocker):
    scraper = _make_scraper()
    mocker.patch.object(scraper, "client", _FakeClient({"products?per_page=100": _fixture_products()}))

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # Merch, gift cards, and the Franks Choice subscription all carry
    # non-coffee categories; coffee beans carry no category at all.
    assert not any("t-shirt" in u for u in urls)
    assert not any("baseball-hat" in u for u in urls)
    assert not any("coffee-mug" in u for u in urls)
    assert not any("gift-card" in u for u in urls)
    assert not any("subscription" in u for u in urls)


async def test_failed_listing_returns_empty(mocker):
    scraper = _make_scraper()

    class _FailingClient:
        async def get(self, url):
            raise RuntimeError("network down")

    mocker.patch.object(scraper, "client", _FailingClient())
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    assert urls == []


def test_build_product_soup_contains_product_facts():
    products = _fixture_products()
    product = next(p for p in products if p["slug"] == "guatemala-blue-ayarza")
    soup = RooseveltCoffeehouseScraper._build_product_soup(product)
    text = soup.get_text(" ", strip=True)

    assert "Guatemala Blue Ayarza" in text
    assert "Price: $23.00" in text
    assert "Availability: In stock" in text
    # Description (origin/process info for AI extraction).
    assert "Ayarza region" in text


def test_build_product_soup_price_range_and_variants():
    products = _fixture_products()
    product = next(p for p in products if p["slug"] == "guatemala-blue-ayarza")
    soup = RooseveltCoffeehouseScraper._build_product_soup(product)
    text = soup.get_text(" ", strip=True)

    # Weight/grind variations collapse into unique values per attribute.
    assert "Variants:" in text


async def test_fetch_page_routes_product_urls_to_store_api(mocker):
    scraper = _make_scraper()
    products = _fixture_products()
    product = next(p for p in products if p["slug"] == "guatemala-blue-ayarza")
    mocker.patch.object(scraper, "client", _FakeClient({"products?slug=guatemala-blue-ayarza": [product]}))

    result = await scraper.fetch_page(PRODUCT_URL, use_playwright=False)
    assert result is not None
    assert "Guatemala Blue Ayarza" in result.get_text()


async def test_fetch_page_falls_back_to_html_for_non_product_urls(mocker):
    scraper = _make_scraper()
    sentinel = BeautifulSoup("<html><body>listing</body></html>", "lxml")

    async def fake_base_fetch(self, url, **kwargs):
        return sentinel

    mocker.patch.object(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page("https://roosevelt.coffee/shop/", use_playwright=False)
    assert result is sentinel


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://roosevelt.coffee/product/test-bean/",
        roaster="Roosevelt Coffeehouse",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
