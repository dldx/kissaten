"""Unit tests for the Corvus Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.corvus_coffee import CorvusCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "corvus_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.corvuscoffee.com/collections/all-coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return CorvusCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("corvus-coffee")
    assert info is not None
    assert info.roaster_name == "Corvus"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Corvus"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://www.corvuscoffee.com/products/") for u in urls)
    assert "https://www.corvuscoffee.com/products/kii-aa-washed-sl28" in urls
    assert "https://www.corvuscoffee.com/products/orchard-thief-seasonal-blend" in urls


@pytest.mark.asyncio
async def test_single_origins_blends_and_decaf_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.corvuscoffee.com/products/wasa-honey" in urls
    assert "https://www.corvuscoffee.com/products/echo-gesha" in urls
    assert "https://www.corvuscoffee.com/products/colombian-decaf-beans" in urls


@pytest.mark.asyncio
async def test_subscriptions_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
