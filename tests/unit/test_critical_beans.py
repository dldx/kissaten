"""Unit tests for the Critical Beans scraper (fixture-based, no network).

The fixtures are copies of the real JSON API responses of
criticalbeansit.be (a React SPA with a JSON backend): the /api/products
listing and a single /api/products/<slug> detail document.
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.critical_beans import API_PRODUCTS_URL, CriticalBeansScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CriticalBeansScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return CriticalBeansScraper(api_key="test-api-key")


def _api_soup() -> BeautifulSoup:
    data = json.loads((FIXTURES / "critical_beans_api.json").read_text())
    return BeautifulSoup(json.dumps(data), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("critical-beans")
    assert info is not None
    assert info.roaster_name == "Critical Beans"
    assert info.currency == "EUR"
    assert info.country == "Belgium"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Critical Beans"


async def test_store_urls_use_api_listing():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [API_PRODUCTS_URL]


async def test_extracts_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(API_PRODUCTS_URL)
    assert urls == ["https://criticalbeansit.be/shop/single-origin-peru"]


async def test_sold_out_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(API_PRODUCTS_URL)
    # All Fermentation Project sets have stock == 0 in the fixture
    for slug in ("blind-tasting-set", "single-origin-guatemala", "fermentation-greens"):
        assert f"https://criticalbeansit.be/shop/{slug}" not in urls


async def test_non_coffee_categories_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(API_PRODUCTS_URL)
    assert all("coffee-pilgrim-t" not in u for u in urls)


async def test_failed_listing_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(API_PRODUCTS_URL)
    assert urls == []


async def test_fetch_page_renders_synthetic_product_html(monkeypatch):
    scraper = _make_scraper()
    detail = json.loads((FIXTURES / "critical_beans_product.json").read_text())

    async def fake_super_fetch(self, url, **kwargs):
        if "/api/products/" in url:
            return BeautifulSoup(json.dumps(detail), "lxml")
        return None

    monkeypatch.setattr(type(scraper).__mro__[1], "fetch_page", fake_super_fetch)
    soup = await scraper.fetch_page("https://criticalbeansit.be/shop/single-origin-peru")
    assert soup is not None
    text = soup.get_text(" ", strip=True)
    assert "Single Origin — Peru" in text
    assert "Price: 18.0 EUR" in text
    assert "Availability: In stock" in text

    # API listing URLs pass through untouched
    listing_soup = await scraper.fetch_page(API_PRODUCTS_URL)
    assert listing_soup is None  # fake returns None for the listing URL

    # Sold-out product renders "Out of stock"
    detail_zero = dict(detail)
    detail_zero["stock"] = 0
    rendered = scraper._render_product_html(detail_zero)
    assert "Out of stock" in rendered.get_text()


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://criticalbeansit.be/shop/test-bean",
        roaster="Critical Beans",
        origins=[],
        price_options=[],
        currency="GBP",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "EUR"
