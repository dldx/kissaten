"""Unit tests for the Salt Winds Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.salt_winds_coffee import SaltWindsCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "salt_winds_coffee_products.json"
PRODUCTS_JSON_URL = "https://saltwindscoffee.com/collections/shop-all-coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SaltWindsCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("salt-winds-coffee")
    assert info is not None
    assert info.roaster_name == "Salt Winds Coffee"
    assert info.currency == "CAD"
    assert info.country == "Canada"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Salt Winds Coffee"


@pytest.mark.asyncio
async def test_extracts_collection_prefixed_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Salt Winds' own collection pages link with the collection segment.
    assert all(u.startswith("https://saltwindscoffee.com/collections/shop-all-coffee/products/") for u in urls)
    assert "https://saltwindscoffee.com/collections/shop-all-coffee/products/guatemalan-antigua" in urls
    assert "https://saltwindscoffee.com/collections/shop-all-coffee/products/captains-blend" in urls


@pytest.mark.asyncio
async def test_fermentation_project_bundle_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://saltwindscoffee.com/collections/shop-all-coffee/products/fermentation-project-bundle" in urls


@pytest.mark.asyncio
async def test_taster_packs_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Taster packs/bundles are coffee products; they are flagged downstream.
    assert any("taster-pack" in u for u in urls)


@pytest.mark.asyncio
async def test_stock_status_keyed_by_collection_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://saltwindscoffee.com/collections/shop-all-coffee/products/fermentation-project-bundle"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # CAD is Salt Winds' home market and the storefront does not convert
    # prices for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "CAD"
    assert scraper._currency_detected is True
