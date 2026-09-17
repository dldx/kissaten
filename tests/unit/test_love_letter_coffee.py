"""Unit tests for the Love Letter Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.love_letter_coffee import LoveLetterCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SITEMAP_URL = "https://love-letter-coffee.square.site/sitemap.xml"
PRODUCT_URL = "https://love-letter-coffee.square.site/product/chelchele/76"

EXPECTED_BEAN_URLS = [
    "https://love-letter-coffee.square.site/product/chelchele/76",
    "https://love-letter-coffee.square.site/product/fatima/XA7ZSBIV2A3NS54OVXIJCV2J",
    "https://love-letter-coffee.square.site/product/finca-san-antonio/78",
    "https://love-letter-coffee.square.site/product/habtamu/5MUK3KRQDZHJGEPV375NJSAY",
    "https://love-letter-coffee.square.site/product/metapan/QVQGN73XT5FSKGAGSQ7NX3VS",
    "https://love-letter-coffee.square.site/product/ojo-de-agua/2V7J5OFOIEHWDINXFU54FCCP",
    "https://love-letter-coffee.square.site/product/san-carlos/ZVROTZ5SAFKKCDBISW67JJ7P",
]


def _load(name: str):
    return (FIXTURES / name).read_text()


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


def _make_scraper() -> LoveLetterCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return LoveLetterCoffeeScraper(api_key="test-api-key")


def _sitemap_soup() -> BeautifulSoup:
    return BeautifulSoup(_load("love_letter_coffee_sitemap.xml"), "xml")


def test_registry_entry():
    info = get_registry().get_scraper_info("love-letter-coffee")
    assert info is not None
    assert info.roaster_name == "Love Letter Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Love Letter Coffee"


async def test_store_urls_use_sitemap():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [SITEMAP_URL]


async def test_extracts_whole_bean_urls_from_sitemap(mocker):
    scraper = _make_scraper()
    mocker.patch.object(BaseScraper, "fetch_page", return_value=_sitemap_soup())

    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)

    for bean_url in EXPECTED_BEAN_URLS:
        assert bean_url in urls
    # Every extracted URL uses the Square Online /product/ path format.
    assert all("/product/" in u for u in urls)
    assert len(urls) == len(EXPECTED_BEAN_URLS)


async def test_cafe_drinks_bakery_and_merch_are_excluded(mocker):
    scraper = _make_scraper()
    mocker.patch.object(BaseScraper, "fetch_page", return_value=_sitemap_soup())

    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)

    # Espresso-bar drinks, teas, bakery and merch must never surface.
    assert not any("cortado" in u or "latte" in u for u in urls)
    assert not any("cold-brew" in u or "drip" in u for u in urls)
    assert not any("texas-fog" in u or "the-evelyn" in u or "spritz" in u for u in urls)
    assert not any("muffin" in u or "macaron" in u or "pop-tart" in u or "cookie" in u for u in urls)
    assert not any("chai" in u or "tea" in u for u in urls)
    assert not any("shirt" in u or "ringer" in u or "wholesale" in u for u in urls)
    assert not any("traveler" in u or "milk" in u or "water" in u for u in urls)


async def test_failed_sitemap_returns_empty(mocker):
    scraper = _make_scraper()
    mocker.patch.object(BaseScraper, "fetch_page", return_value=None)

    urls = await scraper._extract_product_urls_from_store(SITEMAP_URL)
    assert urls == []


def test_build_product_soup_contains_product_facts():
    payload = json.loads(_load("love_letter_coffee_product_api.json"))
    skus = json.loads(_load("love_letter_coffee_product_skus.json"))["data"]
    soup = LoveLetterCoffeeScraper._build_product_soup(payload["data"], skus)
    text = soup.get_text(" ", strip=True)

    assert "Chelchele" in text
    assert "Price: $22.00" in text
    assert "Availability: In stock" in text
    # Per-SKU variants with price and stock state.
    assert "Regular" in text
    assert "$22.00" in text
    assert "In stock" in text


async def test_fetch_page_routes_product_urls_to_store_api(mocker):
    scraper = _make_scraper()
    mocker.patch.object(
        scraper,
        "client",
        _FakeClient(
            {
                "/products/76/skus": json.loads(_load("love_letter_coffee_product_skus.json")),
                "/products/76": json.loads(_load("love_letter_coffee_product_api.json")),
            }
        ),
    )

    result = await scraper.fetch_page(PRODUCT_URL, use_playwright=False)
    assert result is not None
    assert "Chelchele" in result.get_text()


async def test_fetch_page_falls_back_to_html_for_non_product_urls(mocker):
    scraper = _make_scraper()
    sentinel = BeautifulSoup("<html><body>sitemap</body></html>", "lxml")

    async def fake_base_fetch(self, url, **kwargs):
        return sentinel

    mocker.patch.object(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page("https://love-letter-coffee.square.site/sitemap.xml", use_playwright=False)
    assert result is sentinel


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://love-letter-coffee.square.site/product/test-bean/1",
        roaster="Love Letter Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
