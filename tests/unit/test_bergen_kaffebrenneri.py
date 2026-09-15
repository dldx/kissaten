"""Unit tests for the Kaffe Brenneri scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.bergen_kaffebrenneri import BergenKaffebrenneriScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://bergenkaffebrenneri.no/collections/all/products.json"


def _products():
    return json.loads((FIXTURES / "bergen_kaffebrenneri_products.json").read_text())["products"]


def _make_scraper() -> BergenKaffebrenneriScraper:
    return BergenKaffebrenneriScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("bergen-kaffebrenneri")
    assert info is not None
    assert info.roaster_name == "Kaffe Brenneri"
    assert info.currency == "NOK"
    assert info.country == "Norway"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Kaffe Brenneri"


async def test_extracts_coffee_products_with_canonical_urls(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # Beans survive; the coffee advent calendar (Kaffe product_type) is kept.
    assert urls == [
        "https://bergenkaffebrenneri.no/products/the-fermentation-project",
        "https://bergenkaffebrenneri.no/products/kenya-lesk",
        "https://bergenkaffebrenneri.no/products/monte-cristo",
        "https://bergenkaffebrenneri.no/products/bkb-julekalender",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_subscriptions_courses_merch_and_equipment(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("abonnement" in u for u in urls)
    assert not any("manedens-bkb" in u for u in urls)
    assert not any("kurs" in u for u in urls)
    assert not any("gavekort" in u for u in urls)
    assert not any("kopp" in u for u in urls)
    assert not any("filter" in u for u in urls)
    assert not any("la-marzocco" in u for u in urls)
    assert not any("luer" in u for u in urls)
    assert not any("caps" in u for u in urls)
    assert not any("handkle" in u for u in urls)
    assert not any("lommelerke" in u for u in urls)
    assert not any("jubileumsbok" in u for u in urls)
    assert not any("dvd" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "NOK"
    assert scraper._currency_detected is True
