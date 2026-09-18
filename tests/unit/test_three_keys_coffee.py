"""Unit tests for the Three Keys Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.three_keys_coffee import ThreeKeysCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "three_keys_coffee_products.json"
PRODUCTS_JSON_URL = "https://threekeyscoffee.com/collections/coffee-1/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return ThreeKeysCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("three-keys-coffee")
    assert info is not None
    assert info.roaster_name == "Three Keys Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Three Keys Coffee"


@pytest.mark.asyncio
async def test_extracts_collection_prefixed_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Three Keys' own collection pages link with the collection segment.
    assert all(u.startswith("https://threekeyscoffee.com/collections/coffee-1/products/") for u in urls)
    assert "https://threekeyscoffee.com/collections/coffee-1/products/ear-candy" in urls
    assert "https://threekeyscoffee.com/collections/coffee-1/products/rwanda-reverb" in urls


@pytest.mark.asyncio
async def test_fermentation_frequency_kit_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://threekeyscoffee.com/collections/coffee-1/products/fermentation-frequency" in urls


@pytest.mark.asyncio
async def test_canned_cold_brew_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Ready-to-drink canned cold brew products are not beans; the single-serve
    # pour-over sachets stay in.
    assert not any("canned-cold-brew" in u for u in urls)
    assert "https://threekeyscoffee.com/collections/coffee-1/products/sonido-del-sol-single-serve-pour-over" in urls


@pytest.mark.asyncio
async def test_stock_status_keyed_by_collection_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://threekeyscoffee.com/collections/coffee-1/products/fermentation-frequency"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # USD is Three Keys' home market and the storefront does not convert
    # prices for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
