"""Unit tests for the Copperopolis Coffee scraper (fixture-based, no network).

The fixture mirrors the real WooCommerce Store API listing JSON of
copperopolis.coffee (coffee products, merch, event, subscription).
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.schemas import CoffeeBean
from kissaten.scrapers.copperopolis import API_PRODUCTS_URL, CopperopolisScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make_scraper() -> CopperopolisScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return CopperopolisScraper(api_key="test-api-key")


def _api_soup() -> BeautifulSoup:
    data = json.loads((FIXTURES / "copperopolis_api.json").read_text())
    return BeautifulSoup(json.dumps(data), "lxml")


def test_registry_entry():
    info = get_registry().get_scraper_info("copperopolis")
    assert info is not None
    assert info.roaster_name == "Copperopolis Coffee"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.requires_api_key is True


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Copperopolis Coffee"


async def test_store_urls_use_store_api():
    scraper = _make_scraper()
    urls = await scraper.get_store_urls()
    assert urls == [f"{API_PRODUCTS_URL}?per_page=100&page=1"]


async def test_extracts_in_stock_coffee_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        if url.endswith("page=1"):
            return _api_soup()
        return BeautifulSoup("[]", "lxml")

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert sorted(urls) == [
        "https://copperopolis.coffee/product/brazil-bom-jesus/",
        "https://copperopolis.coffee/product/brazil-sao-lucas/",
        "https://copperopolis.coffee/product/fermentation-cup-along-swansea-slurp-02/",
    ]


async def test_sold_out_products_are_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    # Roaster's Choice subscription is out of stock in the fixture
    assert "https://copperopolis.coffee/product/roasters-choice/" not in urls


async def test_merch_is_excluded(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    slugs = {u.rstrip("/").rsplit("/", 1)[-1] for u in urls}
    for slug in ("copperopolis-cupping-spoon", "procaffeinate-t-shirt-unisex-crew-neck", "copperopolis-beanie"):
        assert slug not in slugs


async def test_fermentation_project_product_is_kept(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return _api_soup()

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert "https://copperopolis.coffee/product/fermentation-cup-along-swansea-slurp-02/" in urls


async def test_failed_first_page_returns_empty(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(f"{API_PRODUCTS_URL}?per_page=100&page=1")
    assert urls == []


def test_currency_pinned_in_postprocess():
    scraper = _make_scraper()
    bean = CoffeeBean(
        name="Test Bean",
        url="https://copperopolis.coffee/product/test-bean/",
        roaster="Copperopolis Coffee",
        origins=[],
        price_options=[],
        currency="USD",
    )
    out = scraper.postprocess_extracted_bean(bean)
    assert out.currency == "GBP"
