"""Unit tests for The Brew Company scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.the_brew_company import TheBrewCompanyScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://brew-company.com/collections/coffee-beans/products.json"


def _products():
    return json.loads((FIXTURES / "the_brew_company_products.json").read_text())["products"]


def _make_scraper() -> TheBrewCompanyScraper:
    return TheBrewCompanyScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("the-brew-company")
    assert info is not None
    assert info.roaster_name == "The Brew Company"
    assert info.currency == "EUR"
    assert info.country == "Denmark"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "The Brew Company"


async def test_extracts_coffee_products_and_keeps_fermentation_project(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert urls == [
        "https://brew-company.com/products/the-fermentation-project-kit",
        "https://brew-company.com/products/ethiopia-specialty-whole-bean-coffee",
        "https://brew-company.com/products/bolivia-specialty-whole-bean-coffee",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_coffeebrewers_teabrewers_and_grinders(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # Coffeebrewer/teabrewer devices and grinders must never leak in, even if
    # they drift into the coffee-beans collection.
    assert not any("coffeebrewer" in u for u in urls)
    assert not any("teabrewer" in u for u in urls)
    assert not any("270wi" in u for u in urls)


def test_currency_pinned_to_store_currency():
    scraper = _make_scraper()
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True
