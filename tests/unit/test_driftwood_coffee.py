"""Unit tests for the Driftwood Coffee scraper (fixture-based, no network).

Fixtures are trimmed copies of the Square Online store API listing/detail/skus
JSON payloads that the scraper uses instead of the JS-rendered product pages.
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.base import BaseScraper
from kissaten.scrapers.driftwood_coffee import DriftwoodCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

LISTING_URL = (
    DriftwoodCoffeeScraper._STORE_API_BASE + "/products?" + DriftwoodCoffeeScraper._LISTING_QUERY.format(page=1)
)
PRODUCT_URL = "https://www.driftwood.coffee/product/the-fermentation-project-tasting-kit/LV6KNVBAUIX33ZPCXGABNI7M"


def _make_scraper() -> DriftwoodCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return DriftwoodCoffeeScraper(api_key="test-api-key")


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
    info = get_registry().get_scraper_info("driftwood-coffee")
    assert info is not None
    assert info.roaster_name == "Driftwood Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Driftwood Coffee"


async def test_store_urls_use_store_api_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [LISTING_URL]


async def test_extracts_coffee_urls_from_store_api(monkeypatch):
    scraper = _make_scraper()
    scraper.client = _FakeClient({"products?": _load("driftwood_products_api.json")})

    monkeypatch.setattr(scraper, "client", scraper.client)
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)

    assert "https://www.driftwood.coffee/product/colombia-huila/289" in urls
    assert "https://www.driftwood.coffee/product/honduras-la-flor/306" in urls
    # The Fermentation Project tasting kit must not be excluded.
    assert "https://www.driftwood.coffee/product/the-fermentation-project-tasting-kit/LV6KNVBAUIX33ZPCXGABNI7M" in urls
    # Every extracted URL uses the Square Online /product/ path format.
    assert all("/product/" in u for u in urls)
    assert len(urls) == 3


async def test_sold_out_products_are_skipped(monkeypatch):
    scraper = _make_scraper()
    scraper.client = _FakeClient({"products?": _load("driftwood_products_api.json")})

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    # Syrup Bottle carries badges.out_of_stock = true in the listing.
    assert "https://www.driftwood.coffee/product/syrup-bottle/185" not in urls


async def test_non_coffee_products_are_excluded(monkeypatch):
    scraper = _make_scraper()
    scraper.client = _FakeClient({"products?": _load("driftwood_products_api.json")})

    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    # Café drinks, wholesale variants ("-ws-") and equipment.
    assert "https://www.driftwood.coffee/product/latte/39" not in urls
    assert "https://www.driftwood.coffee/product/beach-house-ws-10oz/43" not in urls
    assert "https://www.driftwood.coffee/product/aeropress-/136" not in urls


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    class _FailingClient:
        async def get(self, url):
            raise RuntimeError("network down")

    scraper.client = _FailingClient()
    urls = await scraper._extract_product_urls_from_store(LISTING_URL)
    assert urls == []


def test_build_product_soup_contains_product_facts():
    product = _load("driftwood_product_api.json")["data"]
    skus = _load("driftwood_product_skus.json")["data"]
    soup = DriftwoodCoffeeScraper._build_product_soup(product, skus)
    text = soup.get_text(" ", strip=True)

    assert "The Fermentation Project Tasting Kit" in text
    assert "Price: $30.00" in text
    assert "Availability: In stock" in text
    # Per-SKU variants with sizes, prices and stock state.
    assert "One Kit" in text
    assert "Two Kits" in text
    assert "$55.00" in text
    assert "Out of stock" in text
    # Description (origin/process info for AI extraction).
    assert "Antigua, Guatemala" in text
    assert "Lactobacillus" in text


async def test_fetch_page_routes_product_urls_to_store_api(monkeypatch):
    scraper = _make_scraper()
    scraper.client = _FakeClient(
        {
            "/products/LV6KNVBAUIX33ZPCXGABNI7M/skus": _load("driftwood_product_skus.json"),
            "/products/LV6KNVBAUIX33ZPCXGABNI7M": _load("driftwood_product_api.json"),
        }
    )

    result = await scraper.fetch_page(PRODUCT_URL, use_playwright=False)
    assert result is not None
    assert "The Fermentation Project Tasting Kit" in result.get_text()


async def test_fetch_page_falls_back_to_html_for_non_product_urls(monkeypatch):
    scraper = _make_scraper()
    sentinel = BeautifulSoup("<html><body>listing</body></html>", "lxml")

    async def fake_base_fetch(self, url, **kwargs):
        return sentinel

    monkeypatch.setattr(BaseScraper, "fetch_page", fake_base_fetch)
    result = await scraper.fetch_page("https://www.driftwood.coffee/sitemap.xml", use_playwright=False)
    assert result is sentinel


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://www.driftwood.coffee/product/test-bean/1",
        roaster="Driftwood Coffee",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "USD"
