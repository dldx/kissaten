"""Unit tests for the Moonwake Coffee scraper (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from kissaten.scrapers.moonwake_coffee import MoonwakeCoffeeScraper
from kissaten.scrapers.registry import get_registry

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "moonwake_coffee_products.json"
PRODUCTS_JSON_URL = "https://moonwakecoffeeroasters.com/collections/all/products.json"


def _fixture_products() -> list[dict]:
    return json.loads(FIXTURE.read_text())["products"]


@pytest.fixture
def scraper():
    return MoonwakeCoffeeScraper()


def test_registry_entry():
    info = get_registry().get_scraper_info("moonwake-coffee")
    assert info is not None
    assert info.roaster_name == "Moonwake"
    assert info.display_name == "Moonwake"
    assert info.currency == "USD"
    assert info.country == "United States"
    assert info.requires_api_key is True
    assert info.status == "experimental"


def test_roaster_name_matches_registry(scraper):
    assert scraper.roaster_name == "Moonwake"


@pytest.mark.asyncio
async def test_extracts_canonical_product_urls(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert all(u.startswith("https://moonwakecoffeeroasters.com/products/") for u in urls)
    assert "https://moonwakecoffeeroasters.com/products/san-sebastian-julio-chavez-washed-sl9-peru" in urls
    assert "https://moonwakecoffeeroasters.com/products/el-salado-yuri-ordonez-anaerobic-washed-gesha-colombia" in urls


@pytest.mark.asyncio
async def test_praised_single_origins_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    bambito = (
        "https://moonwakecoffeeroasters.com/products/"
        "bambito-estate-priscilla-and-ivan-gonzalez-washed-gesha-panama"
    )
    assert bambito in urls


@pytest.mark.asyncio
async def test_decaf_and_mystery_coffee_are_kept(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    assert "https://moonwakecoffeeroasters.com/products/nyamyumba-decaf-rwanda" in urls
    assert "https://moonwakecoffeeroasters.com/products/mystery-coffee-league-coffee-june-2025" in urls


@pytest.mark.asyncio
async def test_gear_subscriptions_and_gift_cards_are_excluded(scraper, mocker):
    mocker.patch.object(scraper, "_fetch_all_shopify_products", return_value=_fixture_products())

    urls = await scraper._extract_product_urls_from_store(PRODUCTS_JSON_URL)

    # Brewing gear
    assert not any("v60-neo-dripper" in u for u in urls)
    # Subscriptions
    assert not any("subscription" in u for u in urls)
    # Gift cards
    assert not any("gift-card" in u for u in urls)


def test_home_currency_pinned(scraper):
    assert scraper.store_currency == "USD"
    assert scraper._currency_detected is True
