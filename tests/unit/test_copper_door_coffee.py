"""Unit tests for the Copper Door Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.copper_door_coffee import CopperDoorCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://copperdoorcoffee.com/collections/coffee/products.json"


def _products():
    return json.loads((FIXTURES / "copper_door_coffee_products.json").read_text())["products"]


def _make_scraper() -> CopperDoorCoffeeScraper:
    return CopperDoorCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("copper-door-coffee")
    assert info is not None
    assert info.roaster_name == "Copper Door Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Copper Door Coffee"


async def test_extracts_coffee_products_and_keeps_fermentation_project(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # Note the store's real (typo'd) handle "the-frementation-project-kit".
    assert urls == [
        "https://copperdoorcoffee.com/products/the-frementation-project-kit",
        "https://copperdoorcoffee.com/products/guatemala-huehuetenango-coffee-beans",
        "https://copperdoorcoffee.com/products/colombia-monserrate-1",
        "https://copperdoorcoffee.com/products/four-sisters-instant-packets",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_subscriptions_mugs_and_gift_cards(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("subscription" in u for u in urls)
    assert not any("mug" in u for u in urls)
    assert not any("gift" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
