"""Unit tests for the Banibeans scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.banibeans import BanibeansScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://banibeans.si/collections/all/products.json"


def _products():
    return json.loads((FIXTURES / "banibeans_products.json").read_text())["products"]


def _make_scraper() -> BanibeansScraper:
    return BanibeansScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("banibeans")
    assert info is not None
    assert info.roaster_name == "Banibeans"
    assert info.currency == "EUR"
    assert info.country == "Slovenia"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Banibeans"


async def test_extracts_coffee_products_and_keeps_tasting_kit(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # The Fermentation Project tasting kit must be extracted (flagged for
    # review downstream), not dropped.
    assert urls == [
        "https://banibeans.si/products/the-fermentation-project-tasting-kit",
        "https://banibeans.si/products/colombia-felix-alberto-experimental-natural-sl28",
        "https://banibeans.si/products/kenya-mchana-natural",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_paper_filters_and_catering(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("paper-filters" in u for u in urls)
    assert not any("catering" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True
