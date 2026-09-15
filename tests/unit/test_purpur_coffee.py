"""Unit tests for the purpur Café & Kaffeerösterei scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.purpur_coffee import PurpurCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "purpur_coffee_products.json"
PRODUCTS_JSON_URL = "https://purpur.coffee/collections/frontpage/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return PurpurCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("purpur-coffee")
    assert info is not None
    assert info.roaster_name == "purpur Café & Kaffeerösterei"
    assert info.currency == "EUR"
    assert info.country == "Germany"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "purpur Café & Kaffeerösterei"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://purpur.coffee/products/") for u in urls)
    assert "https://purpur.coffee/products/ruli" in urls
    assert "https://purpur.coffee/products/daye-bensa" in urls


@pytest.mark.asyncio
async def test_fermentation_project_tasting_set_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://purpur.coffee/products/fermentation-project-probierset" in urls


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://purpur.coffee/products/fermentation-project-probierset"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # EUR is purpur's home market and the storefront does not convert prices
    # for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True
