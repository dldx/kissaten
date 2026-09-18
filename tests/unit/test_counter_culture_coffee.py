"""Unit tests for the Counter Culture Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.counter_culture_coffee import CounterCultureCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "counter_culture_coffee_products.json"
PRODUCTS_JSON_URL = "https://counterculturecoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return CounterCultureCoffeeScraper()


def test_registry_entry(scraper):
    info = get_registry().get_scraper_info("counter-culture-coffee")
    assert info is not None
    assert info.roaster_name == "Counter Culture Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Counter Culture Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://counterculturecoffee.com/products/") for u in urls)
    assert "https://counterculturecoffee.com/products/idido" in urls
    assert "https://counterculturecoffee.com/products/apollo" in urls
    assert "https://counterculturecoffee.com/products/big-trouble" in urls


@pytest.mark.asyncio
async def test_bundles_and_decaf_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Multi-bag bundles are genuine coffee; keep them.
    assert "https://counterculturecoffee.com/products/bestsellers-bundle" in urls
    # Decaf blends are genuine coffee.
    assert "https://counterculturecoffee.com/products/12-oz-slow-motion" in urls


@pytest.mark.asyncio
async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)


@pytest.mark.asyncio
async def test_equipment_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("grinder" in u for u in urls)


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
