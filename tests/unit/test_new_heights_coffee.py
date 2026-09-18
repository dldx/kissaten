"""Unit tests for the New Heights Coffee Roasters scraper (fixture-based, no network).

The fixture is a trimmed copy of the live ``collections/coffee`` products.json
(5 bean products incl. the Fermentation Project pre-sale + a merch hat).
"""

import json
from pathlib import Path

from kissaten.scrapers.new_heights_coffee import NewHeightsCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://newheightscoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "new_heights_coffee_products.json").read_text())["products"]


def _make_scraper() -> NewHeightsCoffeeScraper:
    return NewHeightsCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("new-heights-coffee")
    assert info is not None
    assert info.roaster_name == "New Heights Coffee Roasters"
    assert info.display_name == "New Heights Coffee Roasters"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("new-heights-coffee")
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

    # 5 bean products kept (incl. the pre-sale Fermentation Project set), the
    # merch hat dropped.
    assert len(urls) == 5
    assert "https://newheightscoffee.com/products/fermentation-project-set-pre-sale" in urls
    assert "https://newheightscoffee.com/products/esplanade" in urls
    assert not any("hat" in u for u in urls)


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[0]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://newheightscoffee.com/products/fermentation-project-set-pre-sale"]
