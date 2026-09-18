"""Unit tests for the Method Coffee Roasters scraper (fixture-based, no network).

The fixture is a trimmed copy of the live ``collections/coffee`` products.json
(4 bean products + gift card / subscription / Aeropress items from ``all``).
"""

import json
from pathlib import Path

from kissaten.scrapers.method_coffee import MethodCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://methodroastery.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "method_coffee_products.json").read_text())["products"]


def _make_scraper() -> MethodCoffeeScraper:
    return MethodCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("method-coffee")
    assert info is not None
    assert info.roaster_name == "Method Coffee Roasters"
    assert info.display_name == "Method Coffee Roasters"
    assert info.currency == "GBP"
    assert info.country == "United Kingdom"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("method-coffee")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_extracts_beans_and_excludes_non_coffee(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 4 bean products kept, gift card / subscription / Aeropress dropped.
    assert len(urls) == 4
    assert "https://methodroastery.com/products/brazil" in urls
    assert "https://methodroastery.com/products/chucho-blend" in urls
    assert not any("gift-card" in u for u in urls)
    assert not any("subscription" in u for u in urls)
    assert not any("aeropress" in u for u in urls)


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[0]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://methodroastery.com/products/brazil"]
