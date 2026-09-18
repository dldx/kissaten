"""Unit tests for the Driftaway scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.driftaway import DriftawayScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "driftaway_products.json"
PRODUCTS_JSON_URL = "https://store.driftaway.coffee/collections/coffees/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return DriftawayScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("driftaway")
    assert info is not None
    assert info.roaster_name == "Driftaway"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Driftaway"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://store.driftaway.coffee/products/") for u in urls)
    assert "https://store.driftaway.coffee/products/ethiopia-layo-teraga-g1-washed" in urls
    assert "https://store.driftaway.coffee/products/india-kerehaklu-estate" in urls


@pytest.mark.asyncio
async def test_fermentation_project_kit_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://store.driftaway.coffee/products/fermentation-project-kit-by-james-hoffmann" in urls


@pytest.mark.asyncio
async def test_box_sets_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Box sets are coffee products (flagged downstream where applicable).
    assert "https://store.driftaway.coffee/products/coffee-tasting-kit" in urls
    assert "https://store.driftaway.coffee/products/coffee-explorer-box" in urls


@pytest.mark.asyncio
async def test_gift_card_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("gift-card" in u for u in urls)
    assert not any("subscription" in u for u in urls)


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://store.driftaway.coffee/products/fermentation-project-kit-by-james-hoffmann"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_not_pinned(scraper):
    # USD is Driftaway's home market and the storefront does not convert
    # prices for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is False
