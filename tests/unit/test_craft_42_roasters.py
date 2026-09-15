"""Unit tests for the Craft 42 Coffee Roasters scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.craft_42_roasters import Craft42RoastersScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://craft42roasters.ca/collections/coffee/products.json"


def _products():
    return json.loads((FIXTURES / "craft_42_roasters_products.json").read_text())["products"]


def _make_scraper() -> Craft42RoastersScraper:
    return Craft42RoastersScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("craft-42-roasters")
    assert info is not None
    assert info.roaster_name == "Craft 42 Coffee Roasters"
    assert info.currency == "CAD"
    assert info.country == "Canada"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Craft 42 Coffee Roasters"


async def test_extracts_coffee_products_with_canonical_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert urls == [
        "https://craft42roasters.ca/products/morning-glory",
        "https://craft42roasters.ca/products/ella-washed-medium-guatemala",
        "https://craft42roasters.ca/products/crossroads",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_memberships_and_gift_cards(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("membership" in u for u in urls)
    assert not any("gift-card" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "CAD"
    assert scraper._currency_detected is True
