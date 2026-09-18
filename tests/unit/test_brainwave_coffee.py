"""Unit tests for the Brainwave Coffee Roasters scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.brainwave_coffee import BrainwaveCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://brainwaveroasters.com/collections/all/products.json"


def _products():
    return json.loads((FIXTURES / "brainwave_coffee_products.json").read_text())["products"]


def _make_scraper() -> BrainwaveCoffeeScraper:
    return BrainwaveCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("brainwave-coffee")
    assert info is not None
    assert info.roaster_name == "Brainwave Coffee Roasters"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Brainwave Coffee Roasters"


async def test_extracts_coffee_products_and_keeps_fermentation_project(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert urls == [
        "https://brainwaveroasters.com/products/james-hoffmann-fermentation-project",
        "https://brainwaveroasters.com/products/colombia-jairo-arcila-lychee-coferment",
        "https://brainwaveroasters.com/products/colombia-finca-anaya-geisha-z",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_subscription(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("subscription" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
