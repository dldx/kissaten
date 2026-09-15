"""Unit tests for the Nucleus Coffee scraper (fixture-based, no network).

The fixture mirrors the live ``collections/all`` products.json: beans, the
James Hoffmann Fermentation Project kit, plus subscriptions, cupping gear and
xbloom machines that must be excluded.
"""

import json
from pathlib import Path

from kissaten.scrapers.nucleus_coffee import NucleusCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

PRODUCTS_JSON_URL = "https://nucleuscoffee.com/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads((FIXTURES / "nucleus_coffee_products.json").read_text())["products"]


def _make_scraper() -> NucleusCoffeeScraper:
    return NucleusCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("nucleus-coffee")
    assert info is not None
    assert info.roaster_name == "Nucleus Coffee"
    assert info.display_name == "Nucleus Coffee"
    assert info.currency == "CAD"
    assert info.country == "Canada"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    info = get_registry().get_scraper_info("nucleus-coffee")
    assert scraper.roaster_name == info.roaster_name


async def test_store_urls():
    scraper = _make_scraper()
    assert await scraper.get_store_urls() == [PRODUCTS_JSON_URL]


async def test_extracts_beans_and_excludes_subscriptions_and_gear(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return _fixture_products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # 5 kept: beans + the Fermentation Project kit + the Café Bonus bundle;
    # subscriptions, cupping gear and xbloom machines dropped.
    assert len(urls) == 5
    assert "https://nucleuscoffee.com/products/kit-du-projet-fermentation-de-james-hoffmann" in urls
    assert "https://nucleuscoffee.com/products/finca-el-paraiso" in urls
    assert "https://nucleuscoffee.com/products/cafe-bonus" in urls
    assert not any("subscription" in u or "club-lab" in u for u in urls)
    assert not any("cupping" in u for u in urls)
    assert not any("xbloom" in u for u in urls)


async def test_canonicalizes_to_no_collection_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(url):
        return [_fixture_products()[1]]

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert urls == ["https://nucleuscoffee.com/products/finca-el-paraiso"]
