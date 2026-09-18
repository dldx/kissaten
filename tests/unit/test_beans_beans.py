"""Unit tests for the Bean's Beans scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.beans_beans import BeansBeansScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "beans_beans_products.json"
PRODUCTS_JSON_URL = "https://beansbeans.coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return BeansBeansScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("beans-beans")
    assert info is not None
    assert info.roaster_name == "Bean's Beans"
    assert info.display_name == "Bean's Beans"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    # Distinct from Bean & Bean (bean-and-bean), a different roaster.
    assert scraper.roaster_name == "Bean's Beans"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://beansbeans.coffee/products/") for u in urls)
    assert "https://beansbeans.coffee/products/gesha-village-oma-natural-26-147" in urls
    assert "https://beansbeans.coffee/products/heza" in urls


@pytest.mark.asyncio
async def test_airworks_exclusives_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Airworks-exclusive lots are still coffee beans, even with 0.00 prices.
    assert "https://beansbeans.coffee/products/gaia-estate-airworks-exclusive" in urls
    assert "https://beansbeans.coffee/products/gute-village" in urls


@pytest.mark.asyncio
async def test_sold_out_status_parsed(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Lots are typically sold out; availability must be tracked per product.
    assert scraper._shopify_stock_status["https://beansbeans.coffee/products/heza"] is False


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
