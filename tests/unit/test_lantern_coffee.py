"""Unit tests for the Lantern Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.lantern_coffee import LanternCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
LISTING_URL = LanternCoffeeScraper._STORE_API_URL + "?" + LanternCoffeeScraper._LISTING_QUERY.format(page=1)
PRODUCT_URL = "https://lanterncoffee.com/product/finca-ecologica-gesha-washed/"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "lantern_coffee_products_api.json").read_text())


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


def _make_scraper() -> LanternCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return LanternCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("lantern-coffee")
    assert info is not None
    assert info.roaster_name == "Lantern Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Lantern Coffee"


async def test_store_urls_use_store_api_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [LISTING_URL]


async def test_extracts_coffee_urls_from_store_api(mocker):
    scraper = _make_scraper()
    # Page 1 serves the fixture, page 2 is empty (ends the pagination loop).
    mocker.patch.object(
        scraper,
        "client",
        _FakeClient({"page=1": _fixture_products(), "page=2": []}),
    )

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    assert "https://lanterncoffee.com/product/finca-ecologica-gesha-washed/" in urls
    assert "https://lanterncoffee.com/product/wuri-ethiopia-natural/" in urls
    assert "https://lanterncoffee.com/product/los-naranjos-colombia-decaf/" in urls
    assert "https://lanterncoffee.com/product/juiced-up-filter-blend/" in urls
    # Every extracted URL uses the WooCommerce /product/ path format.
    assert all("/product/" in u for u in urls)
    assert len(urls) == 4


async def test_sold_out_products_are_skipped(mocker):
    scraper = _make_scraper()
    mocker.patch.object(
        scraper,
        "client",
        _FakeClient({"page=1": _fixture_products(), "page=2": []}),
    )

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # home-blend carries is_in_stock = false in the listing.
    assert "https://lanterncoffee.com/product/home-blend/" not in urls


async def test_merch_and_subscription_categories_are_excluded(mocker):
    scraper = _make_scraper()
    mocker.patch.object(
        scraper,
        "client",
        _FakeClient({"page=1": _fixture_products(), "page=2": []}),
    )

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    # Hoodie/mug live in "Merch", the subscription in "Subscriptions"; only
    # the "Coffee" category is scraped.
    assert not any("hoodie" in u for u in urls)
    assert not any("zombie-mug" in u for u in urls)
    assert not any("subscription" in u for u in urls)


async def test_failed_listing_returns_empty(mocker):
    scraper = _make_scraper()

    class _FailingClient:
        async def get(self, url):
            raise RuntimeError("network down")

    mocker.patch.object(scraper, "client", _FailingClient())
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    assert urls == []


def test_format_price_from_minor_units():
    prices = {
        "currency_minor_unit": 2,
        "currency_prefix": "$",
        "currency_suffix": "",
        "currency_decimal_separator": ".",
    }
    assert LanternCoffeeScraper._format_price("1600", prices) == "$16.00"
    assert LanternCoffeeScraper._format_price(None, prices) == ""


def test_build_product_soup_contains_product_facts():
    product = _fixture_products()[1]  # finca-ecologica-gesha-washed
    soup = LanternCoffeeScraper._build_product_soup(product)
    text = soup.get_text(" ", strip=True)

    assert product["name"] in text
    assert "Price: $16.00" in text
    assert "Availability: In stock" in text
    # Description (origin/process info for AI extraction).
    assert "Gesha" in text


def test_build_product_soup_collapses_variant_attributes():
    product = _fixture_products()[1]
    soup = LanternCoffeeScraper._build_product_soup(product)
    text = soup.get_text(" ", strip=True)

    # Variation attribute values (e.g. Weight/Grind) collapse to unique values.
    assert "Variants:" in text


async def test_fetch_page_routes_product_urls_to_store_api(mocker):
    scraper = _make_scraper()
    product = _fixture_products()[1]
    mocker.patch.object(
        scraper,
        "client",
        _FakeClient({"products?slug=finca-ecologica-gesha-washed": [product]}),
    )

    result = await scraper.fetch_page(PRODUCT_URL, use_playwright=False)
    assert result is not None
    assert product["name"] in result.get_text()


async def test_fetch_page_falls_back_to_html_for_non_product_urls(mocker):
    scraper = _make_scraper()
    sentinel = BeautifulSoup("<html><body>listing</body></html>", "lxml")

    async def fake_base_fetch(self, url, **kwargs):
        return sentinel

    mocker.patch.object(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page("https://lanterncoffee.com/shop/", use_playwright=False)
    assert result is sentinel


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://lanterncoffee.com/product/test-bean/",
        roaster="Lantern Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
