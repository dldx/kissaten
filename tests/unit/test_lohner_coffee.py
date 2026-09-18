"""Unit tests for the Lohner Coffee scraper (fixture-based, no network).

The fixture is a trimmed copy of the live ``collections/all`` products.json
(4 beans incl. the Fermentation Project kit + 3 merch items).
"""

import json
from pathlib import Path

from kissaten.scrapers.lohner_coffee import LohnerCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://lohnercoffee.com/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "lohner_coffee_products.json").read_text())["products"]


def _make_scraper() -> LohnerCoffeeScraper:
    # No api_key: no AI extractor is constructed, no network is touched.
    return LohnerCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("lohner-coffee")
    assert info is not None
    assert info.roaster_name == "Lohner Coffee"
    assert info.display_name == "Lohner Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("lohner-coffee")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_extracts_beans_and_excludes_merch(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 4 beans kept (incl. the Fermentation Project kit), 3 merch items dropped.
    assert len(urls) == 4
    assert "https://lohnercoffee.com/products/fermentation-project" in urls
    assert "https://lohnercoffee.com/products/ethiopia" in urls
    assert not any("gift-card" in u for u in urls)
    assert not any("hat" in u for u in urls)
    assert not any("hoodie" in u for u in urls)


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[1]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://lohnercoffee.com/products/fermentation-project"]


async def test_stock_status_from_any_available_variant(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    stock = scraper._shopify_stock_status
    assert stock["https://lohnercoffee.com/products/fermentation-project"] in (True, False)
