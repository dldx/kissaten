"""Unit tests for the Arcane Estate Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.arcane_estate_coffee import ArcaneEstateCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "arcane_estate_coffee_products.json"
PRODUCTS_JSON_URL = "https://arcaneestatecoffee.com/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return ArcaneEstateCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("arcane-estate-coffee")
    assert info is not None
    assert info.roaster_name == "Arcane Estate"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Arcane Estate"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://arcaneestatecoffee.com/products/") for u in urls)
    assert "https://arcaneestatecoffee.com/products/la-reina" in urls
    assert "https://arcaneestatecoffee.com/products/villa-luna" in urls
    assert "https://arcaneestatecoffee.com/products/villa-luna-natural" in urls


@pytest.mark.asyncio
async def test_subscription_is_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("subscription" in u for u in urls)


@pytest.mark.asyncio
async def test_estate_coffees_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # The four Panamanian estate coffees (Panama-only catalogue) stay in.
    assert len(urls) == 4
    assert "https://arcaneestatecoffee.com/products/villa-luna-espresso" in urls


@pytest.mark.asyncio
async def test_stock_status_parsed(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Catalogue currently unpublished: every variant reports unavailable.
    assert scraper._shopify_stock_status["https://arcaneestatecoffee.com/products/la-reina"] is False


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
