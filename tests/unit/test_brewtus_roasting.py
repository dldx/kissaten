"""Unit tests for the Brewtus Roasting scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.brewtus_roasting import BrewtusRoastingScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://brewtusroasting.com/collections/coffee/products.json"


def _products():
    return json.loads((FIXTURES / "brewtus_roasting_products.json").read_text())["products"]


def _make_scraper() -> BrewtusRoastingScraper:
    return BrewtusRoastingScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("brewtus-roasting")
    assert info is not None
    assert info.roaster_name == "Brewtus Roasting"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Brewtus Roasting"


async def test_extracts_coffee_products_with_canonical_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert urls == [
        "https://brewtusroasting.com/products/the-fermentation-project",
        "https://brewtusroasting.com/products/kenya-ab-nyeri-kiangundo",
        "https://brewtusroasting.com/products/colombia-finca-el-recuerdo",
        "https://brewtusroasting.com/products/roaster-choice-of-the-month",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_gift_cards(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("gift-card" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
