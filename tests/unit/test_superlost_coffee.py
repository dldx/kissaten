"""Unit tests for the Superlost Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.registry import get_registry
from kissaten.scrapers.superlost_coffee import SuperlostCoffeeScraper

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "superlost_coffee_products.json"
PRODUCTS_JSON_URL = "https://www.superlost.com/collections/coffee/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return SuperlostCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("superlost-coffee")
    assert info is not None
    assert info.roaster_name == "Superlost"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Superlost"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://www.superlost.com/products/") for u in urls)
    assert "https://www.superlost.com/products/supernatural" in urls
    assert "https://www.superlost.com/products/new-light" in urls


@pytest.mark.asyncio
async def test_espresso_blends_and_bundles_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Espresso blends and line coffees are genuine beans (the fixture reflects
    # the live catalogue; the old "Dark Side" bundle has since been delisted).
    assert "https://www.superlost.com/products/supernova-espresso" in urls
    assert "https://www.superlost.com/products/new-light" in urls


@pytest.mark.asyncio
async def test_cotm_microlot_is_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert (
        "https://www.superlost.com/products/coffee-of-the-moment-48-nestor-lasso-bourbon-aji-anaerobic-washed"
        in urls
    )


@pytest.mark.asyncio
async def test_subscription_and_concentrate_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert not any("instant-coffee-concentrate" in u for u in urls)
    assert "https://www.superlost.com/products/coffee-of-the-moment" not in urls


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
