"""Unit tests for the Common Time Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

from kissaten.scrapers.common_time_coffee import CommonTimeCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURES = Path(__file__).parent.parent / "fixtures"

STORE_URL = "https://commontimecoffee.com/collections/coffee/products.json"


def _products():
    return json.loads((FIXTURES / "common_time_coffee_products.json").read_text())["products"]


def _make_scraper() -> CommonTimeCoffeeScraper:
    return CommonTimeCoffeeScraper(api_key="test-api-key")


def test_registry_entry():
    info = get_registry().get_scraper_info("common-time-coffee")
    assert info is not None
    assert info.roaster_name == "Common Time Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry():
    scraper = _make_scraper()
    assert scraper.roaster_name == "Common Time Coffee"


async def test_extracts_coffee_products_and_keeps_tasting_set(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    # The Fermentation Project tasting set must be extracted (flagged for
    # review downstream), not dropped.
    assert urls == [
        "https://commontimecoffee.com/products/thefermentationproject",
        "https://commontimecoffee.com/products/ethiopia-buku-abel-natural",
        "https://commontimecoffee.com/products/rwanda-kinini-village-washed-bourbon",
    ]
    assert all("/collections/" not in u for u in urls)


async def test_excludes_subscriptions_and_grinders(monkeypatch):
    scraper = _make_scraper()

    async def fake_fetch(products_json_url):
        return _products()

    monkeypatch.setattr(scraper, "_fetch_all_shopify_products", fake_fetch)
    urls = await scraper._extract_product_urls_from_store(STORE_URL)

    assert not any("subscription" in u for u in urls)
    assert not any("grinder" in u for u in urls)


def test_currency_pinned_to_home_market():
    scraper = _make_scraper()
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
