"""Unit tests for the Arrowroot Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.arrowroot_coffee import ArrowrootCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://arrowrootcoffee.com/collections/all/products.json"


def _products():
    return json.loads((FIXTURES / "arrowroot_coffee_products.json").read_text())["products"]


def _make_scraper() -> ArrowrootCoffeeScraper:
    return ArrowrootCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("arrowroot-coffee")
    assert info is not None
    assert info.roaster_name == "Arrowroot Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Arrowroot Coffee"


async def test_extracts_coffee_products_and_keeps_tasting_kit(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # The Fermentation Project tasting kit must be extracted (flagged for
    # review downstream), not dropped.
    assert urls == [
        "https://arrowrootcoffee.com/products/pre-order-the-fermentation-project-tasting-kit",
        "https://arrowrootcoffee.com/products/colombia-sugarcane-decaf",
        "https://arrowrootcoffee.com/products/honduras-smithsonian-bird-friendly-certified",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_tea_mug_beanie_and_subscription(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("subscription" in u for u in urls)
    assert not any("-tea" in u for u in urls)
    assert not any("mug" in u for u in urls)
    assert not any("beanie" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
