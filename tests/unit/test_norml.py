"""Unit tests for the Norml scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.norml import NormlScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "norml_products.json"
PRODUCTS_JSON_URL = "https://normlppl.coffee/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return NormlScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("norml")
    assert info is not None
    assert info.roaster_name == "Norml"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Norml"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://normlppl.coffee/products/") for u in urls)
    assert "https://normlppl.coffee/products/rotating-blend-400g-14-10oz" in urls


@pytest.mark.asyncio
async def test_green_coffee_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Green (unroasted) lots are excluded per roaster-scraper precedent —
    # only the roasted rotating blend is tracked.
    assert not any("green-coffee" in u for u in urls)


@pytest.mark.asyncio
async def test_subscriptions_and_gear_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)
    assert not any("filter-paper" in u for u in urls)


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
