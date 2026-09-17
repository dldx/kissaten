"""Unit tests for the Superthing Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.superthing_coffee import SuperthingCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "superthing_coffee_products.json"
PRODUCTS_JSON_URL = "https://superthingcoffee.com/collections/coffees/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SuperthingCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("superthing-coffee")
    assert info is not None
    assert info.roaster_name == "Superthing"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Superthing"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://superthingcoffee.com/products/") for u in urls)
    assert "https://superthingcoffee.com/products/power-button-blend" in urls
    assert "https://superthingcoffee.com/products/wush-wush-anaerobic-colombia" in urls


@pytest.mark.asyncio
async def test_espresso_blends_and_decaf_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://superthingcoffee.com/products/tractor-beam-blend" in urls
    assert "https://superthingcoffee.com/products/colombia-valle-del-cauca-decaf" in urls


@pytest.mark.asyncio
async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
