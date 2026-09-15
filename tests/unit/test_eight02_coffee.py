"""Unit tests for the 802 Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.eight02_coffee import Eight02CoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://802coffee.com/collections/coffees/products.json"


def _products():
    return json.loads((FIXTURES / "eight02_coffee_products.json").read_text())["products"]


def _make_scraper() -> Eight02CoffeeScraper:
    return Eight02CoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("802-coffee")
    assert info is not None
    assert info.roaster_name == "802 Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "802 Coffee"


async def test_extracts_coffee_products_with_canonical_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert urls == [
        "https://802coffee.com/products/the-fermentation-project",
        "https://802coffee.com/products/colombia-pink-bourbon",
        "https://802coffee.com/products/ethiopia-natural-sidamo-1",
        "https://802coffee.com/products/peru-decaf",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_merch_and_gift_cards(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("gift-card" in u for u in urls)
    assert not any("tumbler" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
