"""Unit tests for the Found Coffee scraper (fixture-based, no network).

Fixtures are trimmed copies of the Square Online store API listing/detail/skus
JSON payloads that the scraper uses instead of the JS-rendered product pages.
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.found_coffee import FoundCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

LISTING_URL = FoundCoffeeScraper._STORE_API_BASE + "/products?" + FoundCoffeeScraper._LISTING_QUERY.format(page=1)
PRODUCT_URL = "https://www.found.coffee/product/huehuetenango-guatemala/3S7KHRH3RY4HIQASOL5SAYZV"


def _make_scraper() -> FoundCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return FoundCoffeeScraper(api_key="test-api-key")


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


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


async def test_registry_entry():
    info = get_registry().get_scraper_info("found-coffee")
    assert info is not None
    assert info.roaster_name == "Found Coffee"
    assert info.currency == "CAD"
    assert info.country == "Canada"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Found Coffee"


async def test_store_urls_use_store_api_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [LISTING_URL]


async def test_extracts_coffee_urls_from_store_api(monkeypatch):
    scraper = _make_scraper()
    scraper.client = _FakeClient({"products?": _load("found_products_api.json")})

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    assert "https://www.found.coffee/product/huehuetenango-guatemala/3S7KHRH3RY4HIQASOL5SAYZV" in urls
    assert "https://www.found.coffee/product/el-para-so-92-typica-colombia/KWIAIALBX4YZNGWHO466LHBI" in urls
    assert "https://www.found.coffee/product/sun-of-a-beach-summer-blend/XEPVHRRYEDXGNTM4ODEIAC6W" in urls
    # The Fermentation Project tasting kit must not be excluded.
    assert (
        "https://www.found.coffee/product/the-fermentation-project-with-james-hoffman-tasting-kit/LD6IHMRRYDSXYOFUZIQ4E7RL"
        in urls
    )
    # Every extracted URL uses the Square Online /product/ path format.
    assert all("/product/" in u for u in urls)
    assert len(urls) == 4


async def test_non_coffee_products_are_excluded(monkeypatch):
    scraper = _make_scraper()
    scraper.client = _FakeClient({"products?": _load("found_products_api.json")})

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    # Café drinks, equipment, subscriptions and initiatives.
    assert "https://www.found.coffee/product/iced-latte/91" not in urls
    assert "https://www.found.coffee/product/fellow-stagg-ekg-kettle/119" not in urls
    assert "https://www.found.coffee/product/found-on-brew-subscription/402" not in urls
    assert (
        "https://www.found.coffee/product/found-after-hours-re-caffeination-station/W3JZPDDMHUQ44BAMMWIC5THY"
        not in urls
    )


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    class _FailingClient:
        async def get(self, url):
            raise RuntimeError("network down")

    scraper.client = _FailingClient()
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    assert urls == []


def test_build_product_soup_contains_product_facts():
    product = _load("found_product_api.json")["data"]
    skus = _load("found_product_skus.json")["data"]
    soup = FoundCoffeeScraper._build_product_soup(product, skus)
    text = soup.get_text(" ", strip=True)

    assert "Huehuetenango | Guatemala" in text
    assert "Price: $21.00" in text
    assert "Availability: In stock" in text
    # Per-SKU variants with sizes, prices and stock state.
    assert "12oz" in text
    assert "5lb" in text
    assert "$105.00" in text
    assert "Out of stock" in text
    # Description (origin/process info for AI extraction).
    assert "Huehuetenango highlands" in text
    assert "1,650 masl" in text


async def test_fetch_page_routes_product_urls_to_store_api(monkeypatch):
    scraper = _make_scraper()
    scraper.client = _FakeClient(
        {
            "/products/3S7KHRH3RY4HIQASOL5SAYZV/skus": _load("found_product_skus.json"),
            "/products/3S7KHRH3RY4HIQASOL5SAYZV": _load("found_product_api.json"),
        }
    )

    result = await scraper.fetch_page(PRODUCT_URL, use_playwright=False)
    assert result is not None
    assert "Huehuetenango | Guatemala" in result.get_text()


async def test_fetch_page_falls_back_to_html_for_non_product_urls(monkeypatch):
    scraper = _make_scraper()
    sentinel = BeautifulSoup("<html><body>listing</body></html>", "lxml")

    async def fake_base_fetch(self, url, **kwargs):
        return sentinel

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page("https://www.found.coffee/sitemap.xml", use_playwright=False)
    assert result is sentinel


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.found.coffee/product/test-bean/1",
        roaster="Found Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "CAD"
