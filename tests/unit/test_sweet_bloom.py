"""Unit tests for the Sweet Bloom scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.sweet_bloom import SweetBloomScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sweet_bloom_products.json"
PRODUCTS_JSON_URL = "https://sweetbloomcoffee.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SweetBloomScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("sweet-bloom")
    assert info is not None
    assert info.roaster_name == "Sweet Bloom"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Sweet Bloom"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://sweetbloomcoffee.com/products/") for u in urls)
    assert "https://sweetbloomcoffee.com/products/wuri" in urls
    assert "https://sweetbloomcoffee.com/products/uraga" in urls


@pytest.mark.asyncio
async def test_fermentation_project_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://sweetbloomcoffee.com/products/the-fermentation-project" in urls


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://sweetbloomcoffee.com/products/the-fermentation-project"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # USD is Sweet Bloom's home market and the storefront does not convert
    # prices for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
