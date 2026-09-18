"""Unit tests for the Sprout Coffee Roasters scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.sprout_coffee import SproutCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sprout_coffee_products.json"
PRODUCTS_JSON_URL = "https://sproutcoffeeroasters.art/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SproutCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("sprout-coffee")
    assert info is not None
    assert info.roaster_name == "Sprout Coffee Roasters"
    assert info.currency == "EUR"
    assert info.country == "Netherlands"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Sprout Coffee Roasters"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://sproutcoffeeroasters.art/products/") for u in urls)
    assert "https://sproutcoffeeroasters.art/products/andes" in urls
    assert "https://sproutcoffeeroasters.art/products/banana-bubble-butt" in urls


@pytest.mark.asyncio
async def test_fermentation_project_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://sproutcoffeeroasters.art/products/the-fermentation-project" in urls


@pytest.mark.asyncio
async def test_non_coffee_product_types_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Brewing gear, merch, workshops, tea/matcha and gift cards are filtered
    # by product_type == "Coffee".
    for excluded in (
        "acaia-pearl",
        "aeropress-clear",
        "commandante-c40-mk4-nitro-blade",
        "dad-cap",
        "bucket-hat",
        "espresso",
        "latte-art",
        "matcha",
        "chai-500g",
        "sprout-coffee-gift-card",
        "la-marzocco-linea-mini",
    ):
        assert f"https://sproutcoffeeroasters.art/products/{excluded}" not in urls
    assert not any("workshops" in u for u in urls)


@pytest.mark.asyncio
async def test_stock_status_keyed_by_canonical_url(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    url = "https://sproutcoffeeroasters.art/products/the-fermentation-project"
    assert url in scraper._shopify_stock_status
    assert url in scraper._shopify_product_data


def test_home_currency_pinned(scraper):
    # EUR is Sprout's home market and the storefront does not convert prices
    # for the scraper's default headers, so detection stays dynamic.
    assert scraper.store_currency == "EUR"
    assert scraper._currency_detected is True
