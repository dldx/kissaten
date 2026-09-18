"""Unit tests for the Square One Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.square_one_coffee import SquareOneCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "square_one_coffee_products.json"
PRODUCTS_JSON_URL = "https://shop.squareonecoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SquareOneCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("square-one-coffee")
    assert info is not None
    assert info.roaster_name == "Square One Coffee"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Square One Coffee"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://shop.squareonecoffee.com/products/") for u in urls)
    assert "https://shop.squareonecoffee.com/products/bolivia-la-paz" in urls
    assert "https://shop.squareonecoffee.com/products/kenya-kichwa-tembo" in urls


@pytest.mark.asyncio
async def test_fermentation_project_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://shop.squareonecoffee.com/products/fermentation-project" in urls


@pytest.mark.asyncio
async def test_eco_pods_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("pods" in u for u in urls)
    assert not any("subscription" in u for u in urls)


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://shop.squareonecoffee.com/products/fermentation-project"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # USD is Square One's home market and the storefront does not convert
    # prices for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
