"""Unit tests for the Brio Coffeeworks scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.brio_coffeeworks import BrioCoffeeworksScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "brio_coffeeworks_products.json"
PRODUCTS_JSON_URL = "https://www.briocoffeeworks.com/collections/all-coffees/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return BrioCoffeeworksScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("brio-coffeeworks")
    assert info is not None
    assert info.roaster_name == "Brio Coffeeworks"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Brio Coffeeworks"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Canonical URL form is /products/<handle> (no collection segment).
    assert all(u.startswith("https://www.briocoffeeworks.com/products/") for u in urls)
    assert "https://www.briocoffeeworks.com/products/calypso" in urls
    assert "https://www.briocoffeeworks.com/products/ethiopia-halo-beriti" in urls


@pytest.mark.asyncio
async def test_fermentation_project_and_tasting_box_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://www.briocoffeeworks.com/products/the-fermentation-project-box-set" in urls
    assert "https://www.briocoffeeworks.com/products/brio-tasting-box" in urls


@pytest.mark.asyncio
async def test_instant_coffee_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("instant" in u for u in urls)


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://www.briocoffeeworks.com/products/the-fermentation-project-box-set"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # cart.js (both plain curl and a Chrome-impersonated client) serves USD,
    # the home market currency, so no geo-conversion pinning is needed.
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
